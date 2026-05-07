#!/usr/bin/env bash
set -euo pipefail

# Resolve script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Use system Python to ensure access to system PyGObject (python3-gi)
PY_BIN="/usr/bin/python3"
if [ ! -x "$PY_BIN" ]; then
  PY_BIN="python3"
fi

# Check GTK bindings availability
if ! "$PY_BIN" - <<'PY'
import sys
try:
    import gi
    gi.require_version("Gtk", "4.0")
except Exception as e:
    print(e)
    sys.exit(2)
PY
then
  echo "Не найден модуль gi (PyGObject/GTK4). Установите пакеты и повторите:"
  echo "  sudo apt update"
  echo "  sudo apt install -y python3-gi gir1.2-gtk-4.0 libgtk-4-dev"
  exit 1
fi

exec "$PY_BIN" "$SCRIPT_DIR/qr_gui.py" "$@"

