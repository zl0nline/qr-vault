import argparse
import os
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import qrcode
from secrets import token_bytes

def generate_keys():
    """Генерация пары RSA ключей."""
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )
    public_key = private_key.public_key()
    return private_key, public_key

def save_keys_to_qr_and_text(private_key, public_key):
    """Сохранение ключей в текст и QR."""
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    
    # Сохранение в текстовые файлы
    with open("private_key.pem", "wb") as priv_file:
        priv_file.write(private_pem)
    with open("public_key.pem", "wb") as pub_file:
        pub_file.write(public_pem)
    
    # Генерация QR кодов
    qr_private = qrcode.make(private_pem.decode())
    qr_public = qrcode.make(public_pem.decode())
    qr_private.save("private_key_qr.png")
    qr_public.save("public_key_qr.png")

def encrypt_file(file_path, public_key):
    """Шифрование файла с использованием AES и RSA."""
    # Генерация случайного AES-ключа
    aes_key = token_bytes(32)
    iv = token_bytes(16)

    # Шифрование файла с использованием AES
    cipher = Cipher(algorithms.AES(aes_key), modes.CFB(iv), backend=default_backend())
    encryptor = cipher.encryptor()

    with open(file_path, 'rb') as file:
        plaintext = file.read()
        ciphertext = encryptor.update(plaintext) + encryptor.finalize()

    # Сохранение зашифрованного файла
    with open(file_path + '.enc', 'wb') as enc_file:
        enc_file.write(iv + ciphertext)

    # Шифрование AES-ключа публичным RSA-ключом
    encrypted_key = public_key.encrypt(
        aes_key,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )

    # Сохранение зашифрованного AES-ключа
    with open(file_path + '.key1', 'wb') as key_file1:
        key_file1.write(encrypted_key)

    print(f"Файл {file_path} зашифрован и сохранен как {file_path}.enc")

def decrypt_file_with_key(file_path, key1_path, private_key_path):
    """Расшифровка файла с одним RSA-ключом и AES."""
    # Загрузка приватного ключа
    with open(private_key_path, 'rb') as priv_key_file:
        private_key = serialization.load_pem_private_key(
            priv_key_file.read(),
            password=None,
            backend=default_backend()
        )

    # Загрузка зашифрованного AES-ключа
    with open(key1_path, 'rb') as key_file1:
        encrypted_key = key_file1.read()

    # Расшифровка AES-ключа
    aes_key = private_key.decrypt(
        encrypted_key,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )

    # Расшифровка файла
    with open(file_path, 'rb') as enc_file:
        iv = enc_file.read(16)
        ciphertext = enc_file.read()

    cipher = Cipher(algorithms.AES(aes_key), modes.CFB(iv), backend=default_backend())
    decryptor = cipher.decryptor()
    plaintext = decryptor.update(ciphertext) + decryptor.finalize()

    # Сохранение расшифрованного файла
    output_file = file_path.replace('.enc', '')
    with open(output_file, 'wb') as dec_file:
        dec_file.write(plaintext)

    print(f"Файл {file_path} успешно расшифрован и сохранен как {output_file}")

def main():
    parser = argparse.ArgumentParser(description="Шифрование и дешифрование файлов с использованием AES и RSA.")
    parser.add_argument('-f', '--file', help="Путь к файлу для шифрования/расшифровки")
    parser.add_argument('-enc', '--encrypt', action='store_true', help="Шифровать файл")
    parser.add_argument('-dec', '--decrypt', action='store_true', help="Расшифровать файл")
    parser.add_argument('-key1', help="Ключ дешифровки (путь к текстовому файлу)")
    parser.add_argument('-keyfile', help="Приватный ключ для дешифровки (путь к файлу)")
    args = parser.parse_args()

    if args.encrypt and args.file:
        # Генерация пары ключей
        private_key, public_key = generate_keys()
        
        encrypt_file(args.file, public_key)
        save_keys_to_qr_and_text(private_key, public_key)

    elif args.decrypt and args.file and args.key1 and args.keyfile:
        decrypt_file_with_key(args.file, args.key1, args.keyfile)
    else:
        print("Неверный набор аргументов. Используйте -h для справки.")

if __name__ == "__main__":
    main()

