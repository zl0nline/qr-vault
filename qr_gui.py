import os
import sys

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gio, GLib

# Load crypto helpers from the CLI script located next to this GUI file
WORKSPACE_DIR = os.path.dirname(os.path.abspath(__file__))

def _locate_cli_script() -> str | None:
    candidate = os.path.join(WORKSPACE_DIR, "qr_2025_v.0.5.py")
    return candidate if os.path.isfile(candidate) else None

def _load_cli_impl():
    import importlib.util
    script_path = _locate_cli_script()
    if not script_path:
        raise FileNotFoundError(
            "Не найден файл qr_2025_v.0.5.py рядом с приложением или по ожидаемому пути. "
            "Поместите файл рядом с qr_gui.py или обновите путь в функции _locate_cli_script()."
        )
    spec = importlib.util.spec_from_file_location("qr_cli_impl", script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)  # type: ignore
    return module

_cli = _load_cli_impl()
generate_keys = _cli.generate_keys
save_keys_to_qr_and_text = _cli.save_keys_to_qr_and_text
encrypt_file = _cli.encrypt_file
decrypt_file_with_key = _cli.decrypt_file_with_key


class QRApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="com.example.qrcrypto")

    def do_activate(self):
        window = Gtk.ApplicationWindow(application=self)
        window.set_title("QR Vault")
        window.set_default_size(620, 340)

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        outer.set_margin_top(12)
        outer.set_margin_bottom(12)
        outer.set_margin_start(12)
        outer.set_margin_end(12)

        # File chooser for input file
        input_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        input_row.set_hexpand(True)
        input_entry = Gtk.Entry()
        input_entry.set_hexpand(True)
        input_entry.set_placeholder_text("Путь к файлу")
        input_btn = Gtk.Button(label="Выбрать файл…")
        input_row.append(input_entry)
        input_row.append(input_btn)

        # Key1 chooser (for decrypt)
        key1_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        key1_row.set_hexpand(True)
        key1_entry = Gtk.Entry()
        key1_entry.set_hexpand(True)
        key1_entry.set_placeholder_text("Путь к .key1 (для расшифровки)")
        key1_btn = Gtk.Button(label="Выбрать .key1…")
        key1_row.append(key1_entry)
        key1_row.append(key1_btn)

        # Private key chooser (for decrypt)
        priv_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        priv_row.set_hexpand(True)
        priv_entry = Gtk.Entry()
        priv_entry.set_hexpand(True)
        priv_entry.set_placeholder_text("Путь к private_key.pem (для расшифровки)")
        priv_btn = Gtk.Button(label="Выбрать ключ…")
        priv_row.append(priv_entry)
        priv_row.append(priv_btn)

        # Action buttons
        actions_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        enc_btn = Gtk.Button(label="Зашифровать")
        enc_btn.set_hexpand(False)
        dec_btn = Gtk.Button(label="Расшифровать")
        dec_btn.set_hexpand(False)
        actions_row.append(spacer)
        actions_row.append(enc_btn)
        actions_row.append(dec_btn)

        # Log area
        log_view = Gtk.TextView()
        log_view.set_editable(False)
        log_view.set_monospace(True)
        log_buf = log_view.get_buffer()

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_child(log_view)
        scrolled.set_vexpand(True)

        outer.append(input_row)
        outer.append(key1_row)
        outer.append(priv_row)
        outer.append(actions_row)
        outer.append(scrolled)

        window.set_child(outer)

        def append_log(text: str):
            end_iter = log_buf.get_end_iter()
            log_buf.insert(end_iter, text + "\n")

        def choose_file(target_entry: Gtk.Entry, pattern: str | None = None):
            dialog = Gtk.FileDialog()
            if pattern:
                f = Gtk.FileFilter()
                f.set_name(pattern)
                f.add_pattern(pattern)
                dialog.set_default_filter(f)

            def on_selected(dialog_obj, result):
                try:
                    file = dialog_obj.open_finish(result)
                    if file is not None:
                        path = file.get_path()
                        if path:
                            target_entry.set_text(path)
                            # move cursor to end so the file name is visible
                            target_entry.set_position(-1)
                except Exception as e:
                    append_log(f"Ошибка выбора файла: {e}")

            dialog.open(window, None, on_selected)

        input_btn.connect("clicked", lambda _b: choose_file(input_entry))
        key1_btn.connect("clicked", lambda _b: choose_file(key1_entry, "*.key1"))
        priv_btn.connect("clicked", lambda _b: choose_file(priv_entry, "*.pem"))

        def on_encrypt(_b):
            path = input_entry.get_text().strip()
            if not path:
                append_log("Укажите файл для шифрования")
                return
            if not os.path.isfile(path):
                append_log("Файл не найден")
                return
            append_log(f"Шифрование: {path}")
            try:
                private_key, public_key = generate_keys()
                encrypt_file(path, public_key)
                save_keys_to_qr_and_text(private_key, public_key)
                append_log("Готово: создан .enc, .key1 и QR/PEM ключи рядом с приложением")
            except Exception as e:
                append_log(f"Ошибка шифрования: {e}")

        def on_decrypt(_b):
            path = input_entry.get_text().strip()
            key1_path = key1_entry.get_text().strip()
            priv_path = priv_entry.get_text().strip()
            if not path or not key1_path or not priv_path:
                append_log("Укажите файл, .key1 и private_key.pem")
                return
            if not os.path.isfile(path):
                append_log("Файл не найден")
                return
            if not os.path.isfile(key1_path):
                append_log(".key1 не найден")
                return
            if not os.path.isfile(priv_path):
                append_log("Ключ не найден")
                return
            append_log(f"Расшифровка: {path}")
            try:
                decrypt_file_with_key(path, key1_path, priv_path)
                append_log("Готово: файл расшифрован")
            except Exception as e:
                append_log(f"Ошибка расшифровки: {e}")

        enc_btn.connect("clicked", on_encrypt)
        dec_btn.connect("clicked", on_decrypt)

        window.present()


def main():
    app = QRApp()
    app.run(sys.argv)


if __name__ == "__main__":
    main()


