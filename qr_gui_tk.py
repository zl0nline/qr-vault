"""
QR Vault — кроссплатформенный GUI (tkinter).

Работает на Linux, macOS, Windows без внешних GUI-зависимостей.
Требует только: cryptography, qrcode, Pillow (для QR в tkinter).
"""

import os
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import qr_crypto


TEXTS = {
    "ru": {
        "title": "QR Vault",
        "language": "Язык:",
        "file": "Файл:",
        "key1": ".key1:",
        "private_key": "Приватный ключ:",
        "browse": "Выбрать…",
        "encrypt": "🔐 Зашифровать",
        "decrypt": "🔓 Расшифровать",
        "help": "? Инструкция",
        "log": "Лог:",
        "select_file": "Выберите файл",
        "select_key1": "Выберите .key1",
        "select_private": "Выберите приватный ключ",
        "error": "Ошибка",
        "missing_encrypt_file": "Укажите существующий файл для шифрования",
        "missing_decrypt_inputs": "Укажите .enc файл, .key1 и private_key.pem",
        "enc_not_found": ".enc файл не найден",
        "key1_not_found": ".key1 файл не найден",
        "private_not_found": "Приватный ключ не найден",
        "encrypting": "Шифрование:",
        "decrypting": "Расшифровка:",
        "encrypted": "✅ Зашифровано:",
        "aes_key": "   AES-ключ:",
        "rsa_keys": "   RSA-ключи:",
        "decrypted": "✅ Расшифровано:",
        "failure": "❌ Ошибка:",
        "help_title": "Как пользоваться QR Vault",
        "help_text": """QR Vault шифрует файл и создаёт ключи для расшифровки. Всё происходит локально на вашем компьютере.\n\nЗАШИФРОВАТЬ ФАЙЛ\n1. Нажмите «Выбрать…» в строке «Файл».\n2. Выберите документ, который хотите зашифровать.\n3. Нажмите «Зашифровать».\n4. Рядом с исходным файлом появятся:\n   • файл .enc — зашифрованный документ;\n   • файл .key1 — зашифрованный AES-ключ;\n   • private_key.pem и private_key_qr.png — приватный ключ;\n   • public_key.pem и public_key_qr.png — публичный ключ.\n\nВАЖНО\nprivate_key.pem и private_key_qr.png — это главный секрет. Любой, у кого есть приватный ключ, .enc и .key1, сможет расшифровать документ. Храните приватный ключ отдельно: например, распечатайте QR и положите в сейф.\n\nРАСШИФРОВАТЬ ФАЙЛ\n1. В строке «Файл» выберите файл .enc.\n2. В строке «.key1» выберите соответствующий файл .key1.\n3. В строке «Приватный ключ» выберите private_key.pem.\n4. Нажмите «Расшифровать».\n5. Расшифрованный файл появится рядом с .enc. Если файл с таким именем уже есть, будет создана нумерованная копия.\n\nСОВЕТ\nПеред тем как полагаться на архив, обязательно сделайте пробное шифрование и расшифровку на тестовом файле.""",
    },
    "en": {
        "title": "QR Vault",
        "language": "Language:",
        "file": "File:",
        "key1": ".key1:",
        "private_key": "Private key:",
        "browse": "Browse…",
        "encrypt": "🔐 Encrypt",
        "decrypt": "🔓 Decrypt",
        "help": "? Help",
        "log": "Log:",
        "select_file": "Choose file",
        "select_key1": "Choose .key1",
        "select_private": "Choose private key",
        "error": "Error",
        "missing_encrypt_file": "Choose an existing file to encrypt",
        "missing_decrypt_inputs": "Choose the .enc file, .key1 file, and private_key.pem",
        "enc_not_found": ".enc file not found",
        "key1_not_found": ".key1 file not found",
        "private_not_found": "Private key not found",
        "encrypting": "Encrypting:",
        "decrypting": "Decrypting:",
        "encrypted": "✅ Encrypted:",
        "aes_key": "   AES key:",
        "rsa_keys": "   RSA keys:",
        "decrypted": "✅ Decrypted:",
        "failure": "❌ Error:",
        "help_title": "How to use QR Vault",
        "help_text": """QR Vault encrypts a file and creates the keys needed to decrypt it. Everything happens locally on your computer.\n\nENCRYPT A FILE\n1. Click “Browse…” in the “File” row.\n2. Choose the document you want to encrypt.\n3. Click “Encrypt”.\n4. Next to the original file you will get:\n   • .enc — the encrypted document;\n   • .key1 — the encrypted AES key;\n   • private_key.pem and private_key_qr.png — the private key;\n   • public_key.pem and public_key_qr.png — the public key.\n\nIMPORTANT\nprivate_key.pem and private_key_qr.png are the main secret. Anyone who has the private key, the .enc file, and the .key1 file can decrypt the document. Store the private key separately: for example, print the QR code and keep it in a safe.\n\nDECRYPT A FILE\n1. In the “File” row, choose the .enc file.\n2. In the “.key1” row, choose the matching .key1 file.\n3. In the “Private key” row, choose private_key.pem.\n4. Click “Decrypt”.\n5. The decrypted file will appear next to the .enc file. If a file with the same name already exists, a numbered copy will be created.\n\nTIP\nBefore relying on an archive, always run a test encryption and decryption on a harmless test file.""",
    },
}


class QRApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.lang = tk.StringVar(value="ru")
        self.root.geometry("720x520")
        self.root.minsize(620, 430)
        self._set_window_icon()

        # ── Variables ──
        self.file_path = tk.StringVar()
        self.key1_path = tk.StringVar()
        self.priv_path = tk.StringVar()
        self.widgets = {}

        self._build_ui()
        self._apply_language()

    def t(self, key: str) -> str:
        return TEXTS[self.lang.get()][key]

    def _resource_path(self, relative_path: str) -> str:
        base_dir = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base_dir, relative_path)

    def _set_window_icon(self):
        icon_path = self._resource_path(os.path.join("assets", "app_icon.png"))
        try:
            self._icon_image = tk.PhotoImage(file=icon_path)
            self.root.iconphoto(True, self._icon_image)
        except Exception:
            # Icon loading is cosmetic; never block the encryption UI because of it.
            self._icon_image = None

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _build_ui(self):
        pad = {"padx": 8, "pady": 4}

        # --- Top row ---
        row_top = ttk.Frame(self.root)
        row_top.pack(fill="x", **pad)
        self.widgets["language_label"] = ttk.Label(row_top)
        self.widgets["language_label"].pack(side="left")
        # macOS Aqua ttk.Combobox can lag intermittently when opened from a
        # background-launched Python.app. Plain tk.Radiobuttons are boring,
        # but they switch immediately and do not create/drop a popup window.
        self.widgets["ru_radio"] = tk.Radiobutton(
            row_top,
            text="RU",
            variable=self.lang,
            value="ru",
            indicatoron=False,
            width=5,
            command=lambda: self._set_language("ru"),
        )
        self.widgets["ru_radio"].pack(side="left", padx=(4, 2))
        self.widgets["en_radio"] = tk.Radiobutton(
            row_top,
            text="EN",
            variable=self.lang,
            value="en",
            indicatoron=False,
            width=5,
            command=lambda: self._set_language("en"),
        )
        self.widgets["en_radio"].pack(side="left", padx=(2, 12))
        self.widgets["help_button"] = ttk.Button(row_top, command=self._show_help)
        self.widgets["help_button"].pack(side="right")

        # --- File row ---
        row_file = ttk.Frame(self.root)
        row_file.pack(fill="x", **pad)
        self.widgets["file_label"] = ttk.Label(row_file, width=15)
        self.widgets["file_label"].pack(side="left")
        ttk.Entry(row_file, textvariable=self.file_path).pack(
            side="left", fill="x", expand=True, padx=(4, 4)
        )
        self.widgets["browse_file"] = ttk.Button(row_file, command=self._browse_file)
        self.widgets["browse_file"].pack(side="right")

        # --- Key1 row ---
        row_key1 = ttk.Frame(self.root)
        row_key1.pack(fill="x", **pad)
        self.widgets["key1_label"] = ttk.Label(row_key1, width=15)
        self.widgets["key1_label"].pack(side="left")
        ttk.Entry(row_key1, textvariable=self.key1_path).pack(
            side="left", fill="x", expand=True, padx=(4, 4)
        )
        self.widgets["browse_key1"] = ttk.Button(row_key1, command=self._browse_key1)
        self.widgets["browse_key1"].pack(side="right")

        # --- Private key row ---
        row_priv = ttk.Frame(self.root)
        row_priv.pack(fill="x", **pad)
        self.widgets["private_label"] = ttk.Label(row_priv, width=15)
        self.widgets["private_label"].pack(side="left")
        ttk.Entry(row_priv, textvariable=self.priv_path).pack(
            side="left", fill="x", expand=True, padx=(4, 4)
        )
        self.widgets["browse_private"] = ttk.Button(row_priv, command=self._browse_priv)
        self.widgets["browse_private"].pack(side="right")

        # --- Buttons ---
        row_btn = ttk.Frame(self.root)
        row_btn.pack(fill="x", **pad)
        self.widgets["encrypt_button"] = ttk.Button(row_btn, command=self._on_encrypt)
        self.widgets["encrypt_button"].pack(side="left", expand=True, fill="x", padx=2)
        self.widgets["decrypt_button"] = ttk.Button(row_btn, command=self._on_decrypt)
        self.widgets["decrypt_button"].pack(side="left", expand=True, fill="x", padx=2)

        # --- Log ---
        ttk.Separator(self.root, orient="horizontal").pack(fill="x", pady=6)
        self.widgets["log_label"] = ttk.Label(self.root)
        self.widgets["log_label"].pack(anchor="w", padx=8)
        self.log = tk.Text(self.root, height=12, state="disabled", font=("Monospace", 9))
        self.log.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    def _set_language(self, lang: str):
        if lang not in TEXTS:
            lang = "ru"
        if self.lang.get() != lang:
            self.lang.set(lang)
        self._apply_language()

    def _apply_language(self):
        self.root.title(self.t("title"))
        self.widgets["language_label"].config(text=self.t("language"))
        self.widgets["ru_radio"].config(relief="sunken" if self.lang.get() == "ru" else "raised")
        self.widgets["en_radio"].config(relief="sunken" if self.lang.get() == "en" else "raised")
        self.widgets["help_button"].config(text=self.t("help"))
        self.widgets["file_label"].config(text=self.t("file"))
        self.widgets["key1_label"].config(text=self.t("key1"))
        self.widgets["private_label"].config(text=self.t("private_key"))
        self.widgets["browse_file"].config(text=self.t("browse"))
        self.widgets["browse_key1"].config(text=self.t("browse"))
        self.widgets["browse_private"].config(text=self.t("browse"))
        self.widgets["encrypt_button"].config(text=self.t("encrypt"))
        self.widgets["decrypt_button"].config(text=self.t("decrypt"))
        self.widgets["log_label"].config(text=self.t("log"))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _append_log(self, text: str):
        self.log.config(state="normal")
        self.log.insert("end", text + "\n")
        self.log.see("end")
        self.log.config(state="disabled")

    def _log(self, text: str):
        if threading.current_thread() is threading.main_thread():
            self._append_log(text)
        else:
            self.root.after(0, self._append_log, text)

    def _show_help(self):
        win = tk.Toplevel(self.root)
        win.title(self.t("help_title"))
        win.geometry("640x560")
        win.minsize(520, 420)
        win.transient(self.root)

        frame = ttk.Frame(win, padding=10)
        frame.pack(fill="both", expand=True)

        text = tk.Text(frame, wrap="word", font=("TkDefaultFont", 10))
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=text.yview)
        text.configure(yscrollcommand=scrollbar.set)
        text.insert("1.0", self.t("help_text"))
        text.config(state="disabled")
        text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def _browse_file(self):
        p = filedialog.askopenfilename(title=self.t("select_file"))
        if p:
            self.file_path.set(p)

    def _browse_key1(self):
        p = filedialog.askopenfilename(
            title=self.t("select_key1"), filetypes=[("Key1 files", "*.key1"), ("All", "*.*")]
        )
        if p:
            self.key1_path.set(p)

    def _browse_priv(self):
        p = filedialog.askopenfilename(
            title=self.t("select_private"),
            filetypes=[("PEM files", "*.pem"), ("All", "*.*")],
        )
        if p:
            self.priv_path.set(p)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def _on_encrypt(self):
        path = self.file_path.get().strip()
        if not path or not os.path.isfile(path):
            messagebox.showerror(self.t("error"), self.t("missing_encrypt_file"))
            return

        labels = {
            "encrypting": self.t("encrypting"),
            "encrypted": self.t("encrypted"),
            "aes_key": self.t("aes_key"),
            "rsa_keys": self.t("rsa_keys"),
            "failure": self.t("failure"),
        }
        self._log(f"{labels['encrypting']} {path}")
        self.root.config(cursor="watch")

        def worker():
            try:
                private_key, public_key = qr_crypto.generate_keys()
                enc_path, key1_path = qr_crypto.encrypt_file(path, public_key)
                keys_dir = os.path.dirname(path) or "."
                prefix = os.path.splitext(os.path.basename(path))[0]
                qr_crypto.save_keys(private_key, public_key, keys_dir, prefix=prefix)
                self._log(f"{labels['encrypted']} {enc_path}")
                self._log(f"{labels['aes_key']}  {key1_path}")
                self._log(f"{labels['rsa_keys']} {keys_dir}")
            except Exception as e:
                self._log(f"{labels['failure']} {e}")
            finally:
                self.root.after(0, lambda: self.root.config(cursor=""))

        threading.Thread(target=worker, daemon=True).start()

    def _on_decrypt(self):
        enc = self.file_path.get().strip()
        key1 = self.key1_path.get().strip()
        priv = self.priv_path.get().strip()

        if not enc or not key1 or not priv:
            messagebox.showerror(self.t("error"), self.t("missing_decrypt_inputs"))
            return
        if not os.path.isfile(enc):
            messagebox.showerror(self.t("error"), self.t("enc_not_found"))
            return
        if not os.path.isfile(key1):
            messagebox.showerror(self.t("error"), self.t("key1_not_found"))
            return
        if not os.path.isfile(priv):
            messagebox.showerror(self.t("error"), self.t("private_not_found"))
            return

        labels = {
            "decrypting": self.t("decrypting"),
            "decrypted": self.t("decrypted"),
            "failure": self.t("failure"),
        }
        self._log(f"{labels['decrypting']} {enc}")
        self.root.config(cursor="watch")

        def worker():
            try:
                out = qr_crypto.decrypt_file_with_key(enc, key1, priv)
                self._log(f"{labels['decrypted']} {out}")
            except Exception as e:
                self._log(f"{labels['failure']} {e}")
            finally:
                self.root.after(0, lambda: self.root.config(cursor=""))

        threading.Thread(target=worker, daemon=True).start()


def main():
    root = tk.Tk()
    QRApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
