from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import qr_crypto


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        plain = work / "secret.txt"
        original = "hello наследство\n".encode("utf-8")
        plain.write_bytes(original)

        private_key, public_key = qr_crypto.generate_keys()
        enc_path, key1_path = qr_crypto.encrypt_file(str(plain), public_key, str(work / "out"))
        priv_path, _ = qr_crypto.save_keys(private_key, public_key, str(work / "keys"), prefix="secret")

        plain.unlink()
        out_path = qr_crypto.decrypt_file_with_key(enc_path, key1_path, priv_path, str(work / "dec"))
        assert Path(out_path).read_bytes() == original

    print("smoke ok")


if __name__ == "__main__":
    main()
