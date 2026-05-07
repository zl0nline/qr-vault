from __future__ import annotations

"""
QR Vault — шифрование файлов с гибридным RSA+AES и генерацией QR-ключей.

Ядро: не зависит от GUI, может использоваться как CLI или как библиотека.
"""

import os
import argparse
from secrets import token_bytes

from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.backends import default_backend
import qrcode


APP_NAME = "QR Vault"
APP_VERSION = "0.3"
FORMAT_MAGIC = b"QRC1"


def _non_conflicting_path(path: str) -> str:
    """Return *path* or a numbered variant if the file already exists."""
    if not os.path.exists(path):
        return path

    root, ext = os.path.splitext(path)
    i = 1
    while True:
        candidate = f"{root}_{i}{ext}"
        if not os.path.exists(candidate):
            return candidate
        i += 1


# ---------------------------------------------------------------------------
# Key generation
# ---------------------------------------------------------------------------

def generate_keys():
    """Генерация пары RSA-2048 ключей."""
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend(),
    )
    public_key = private_key.public_key()
    return private_key, public_key


# ---------------------------------------------------------------------------
# Key persistence
# ---------------------------------------------------------------------------

def save_keys(private_key, public_key, output_dir: str, prefix: str = ""):
    """Сохраняет PEM-файлы и QR-коды в *output_dir*.

    Создаёт:
        private_key.pem, public_key.pem,
        private_key_qr.png, public_key_qr.png
    """
    os.makedirs(output_dir, exist_ok=True)
    safe_prefix = f"{prefix}_" if prefix else ""

    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    priv_path = _non_conflicting_path(os.path.join(output_dir, safe_prefix + "private_key.pem"))
    pub_path = _non_conflicting_path(os.path.join(output_dir, safe_prefix + "public_key.pem"))

    with open(priv_path, "wb") as f:
        f.write(private_pem)
    with open(pub_path, "wb") as f:
        f.write(public_pem)

    qr_priv = qrcode.make(private_pem.decode())
    qr_pub = qrcode.make(public_pem.decode())

    qr_priv.save(_non_conflicting_path(os.path.join(output_dir, safe_prefix + "private_key_qr.png")))
    qr_pub.save(_non_conflicting_path(os.path.join(output_dir, safe_prefix + "public_key_qr.png")))

    return priv_path, pub_path


# ---------------------------------------------------------------------------
# Encryption
# ---------------------------------------------------------------------------

def encrypt_file(file_path: str, public_key, output_dir: str | None = None):
    """Шифрует файл гибридной схемой AES-256-GCM + RSA-OAEP.

    Создаёт:
        <basename>.enc   — зашифрованный файл (QRC1 || nonce || ciphertext+tag)
        <basename>.key1  — AES-ключ, зашифрованный RSA публичным ключом

    Возвращает пути (.enc, .key1).
    """
    aes_key = token_bytes(32)
    nonce = token_bytes(12)

    with open(file_path, "rb") as f:
        plaintext = f.read()
    ciphertext = AESGCM(aes_key).encrypt(nonce, plaintext, None)

    base = os.path.basename(file_path)
    dest = output_dir or os.path.dirname(file_path) or "."
    os.makedirs(dest, exist_ok=True)

    enc_path = _non_conflicting_path(os.path.join(dest, base + ".enc"))
    with open(enc_path, "wb") as f:
        f.write(FORMAT_MAGIC + nonce + ciphertext)

    # RSA-encrypt AES key
    encrypted_key = public_key.encrypt(
        aes_key,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )
    key1_path = _non_conflicting_path(os.path.join(dest, base + ".key1"))
    with open(key1_path, "wb") as f:
        f.write(encrypted_key)

    return enc_path, key1_path


# ---------------------------------------------------------------------------
# Decryption
# ---------------------------------------------------------------------------

def decrypt_file_with_key(
    enc_path: str,
    key1_path: str,
    private_key_path: str,
    output_dir: str | None = None,
) -> str:
    """Расшифровывает .enc файл с помощью .key1 и private_key.pem.

    Возвращает путь к расшифрованному файлу.
    """
    # Load private key
    with open(private_key_path, "rb") as f:
        private_key = serialization.load_pem_private_key(
            f.read(),
            password=None,
            backend=default_backend(),
        )

    # Decrypt AES key
    with open(key1_path, "rb") as f:
        encrypted_key = f.read()
    aes_key = private_key.decrypt(
        encrypted_key,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )

    # Decrypt file. New files use AES-GCM with QRC1 header; legacy files used
    # AES-CFB with IV as the first 16 bytes and no integrity protection.
    with open(enc_path, "rb") as f:
        encrypted_data = f.read()

    if encrypted_data.startswith(FORMAT_MAGIC):
        nonce = encrypted_data[4:16]
        ciphertext = encrypted_data[16:]
        plaintext = AESGCM(aes_key).decrypt(nonce, ciphertext, None)
    else:
        iv = encrypted_data[:16]
        ciphertext = encrypted_data[16:]
        cipher = Cipher(algorithms.AES(aes_key), modes.CFB(iv), backend=default_backend())
        decryptor = cipher.decryptor()
        plaintext = decryptor.update(ciphertext) + decryptor.finalize()

    base = os.path.basename(enc_path)
    # Strip .enc suffix
    if base.endswith(".enc"):
        out_name = base[:-4]
    else:
        out_name = base + ".dec"

    dest = output_dir or os.path.dirname(enc_path) or "."
    os.makedirs(dest, exist_ok=True)
    out_path = _non_conflicting_path(os.path.join(dest, out_name))

    with open(out_path, "wb") as f:
        f.write(plaintext)

    return out_path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description=f"{APP_NAME} v{APP_VERSION} — шифрование/расшифровка файлов (AES+RSA) с QR-ключами.",
    )
    parser.add_argument("--version", action="version", version=f"{APP_NAME} {APP_VERSION}")
    parser.add_argument("-f", "--file", help="Путь к файлу для шифрования/расшифровки")
    parser.add_argument("-enc", "--encrypt", action="store_true", help="Зашифровать файл")
    parser.add_argument("-dec", "--decrypt", action="store_true", help="Расшифровать файл")
    parser.add_argument("-key1", help="Путь к .key1 (для расшифровки)")
    parser.add_argument("-keyfile", help="Путь к private_key.pem (для расшифровки)")
    parser.add_argument(
        "-o", "--output-dir",
        help="Каталог для выходных файлов (по умолчанию — рядом с исходным)",
    )
    args = parser.parse_args()

    if args.encrypt and args.file:
        private_key, public_key = generate_keys()
        enc_path, key1_path = encrypt_file(args.file, public_key, args.output_dir)
        keys_dir = args.output_dir or os.path.dirname(args.file) or "."
        prefix = os.path.splitext(os.path.basename(args.file))[0]
        save_keys(private_key, public_key, keys_dir, prefix=prefix)
        print(f"Зашифровано: {enc_path}")
        print(f"Ключ AES:    {key1_path}")
        print(f"RSA-ключи сохранены в: {keys_dir}")

    elif args.decrypt and args.file and args.key1 and args.keyfile:
        out_path = decrypt_file_with_key(args.file, args.key1, args.keyfile, args.output_dir)
        print(f"Расшифровано: {out_path}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
