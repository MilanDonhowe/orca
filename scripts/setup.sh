#!/usr/bin/env sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
PYTHON="$ROOT_DIR/.venv/bin/python"

if [ ! -x "$PYTHON" ]; then
  python3 -m venv "$ROOT_DIR/.venv"
fi

"$PYTHON" -m pip install --upgrade pip
"$PYTHON" -m pip install -e "$ROOT_DIR[dev]"

if command -v mosquitto >/dev/null 2>&1; then
  echo "Mosquitto already installed."
elif command -v brew >/dev/null 2>&1; then
  printf 'Install the optional local MQTT broker with Homebrew? [y/N] '
  read answer
  case "$answer" in y|Y) brew install mosquitto ;; esac
elif command -v apt-get >/dev/null 2>&1; then
  echo "Optional MQTT broker: sudo apt-get install mosquitto mosquitto-clients"
else
  echo "No supported package manager found; use --mqtt with an existing broker."
fi

echo "Ready. Try: $ROOT_DIR/.venv/bin/orca --camera demo"

