# Changelog

All notable changes to QR Vault are documented here.

## v0.3 — 2026-05-07

### Added
- Project renamed and prepared as **QR Vault**.
- Cross-platform tkinter GUI with fast RU/EN language toggle using simple radiobutton controls.
- In-app RU/EN help window with step-by-step usage instructions.
- Application icon assets: PNG, ICNS, and ICO.
- GitHub Actions CI for Linux, macOS, and Windows.
- GitHub Actions PyInstaller release build with QR Vault bundle name and platform icons.
- README in English and Russian with GUI preview and digital inheritance scenario.

### Changed
- New encryption flow uses AES-256-GCM for authenticated encryption.
- RSA key files and QR images are saved next to the source file with a source-based prefix.
- Output files no longer silently overwrite existing files; numbered copies are created instead.
- `requirements.txt` now stays focused on the recommended tkinter app dependencies; GTK dependencies live in `requirements-gtk.txt`.

### Compatibility
- Legacy decrypt support remains for older AES-256-CFB encrypted files produced by the original script.

### Security notes
- Private keys are still stored unencrypted by default. Keep `*_private_key.pem` and `*_private_key_qr.png` offline and separate from `.enc` + `.key1`.
- No independent cryptographic audit has been performed yet.
