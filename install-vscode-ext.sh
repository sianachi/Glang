#!/usr/bin/env bash
set -euo pipefail

# ---------------------------------------------------------------------------
# install-vscode-ext.sh
# Installs the Glang VS Code extension for macOS and Linux.
# Run from anywhere — the script locates vscode-glang/ relative to itself.
# ---------------------------------------------------------------------------

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXT_SRC="$SCRIPT_DIR/vscode-glang"
EXT_NAME="glang-0.1.0"

# --- sanity check -----------------------------------------------------------

if [[ ! -d "$EXT_SRC" ]]; then
  echo "error: extension source not found at $EXT_SRC" >&2
  echo "  Make sure you run this script from the Glang project root." >&2
  exit 1
fi

# --- detect OS --------------------------------------------------------------

OS="$(uname -s)"
case "$OS" in
  Darwin)
    PLATFORM="macOS"
    RELOAD_KEY="Cmd+Shift+P"
    ;;
  Linux)
    PLATFORM="Linux"
    RELOAD_KEY="Ctrl+Shift+P"
    ;;
  *)
    echo "error: unsupported platform '$OS'" >&2
    echo "  This script supports macOS and Linux only." >&2
    exit 1
    ;;
esac

echo "Platform : $PLATFORM"

# --- locate extensions directory --------------------------------------------
# Both macOS and Linux store extensions under ~/.vscode/extensions.
# VS Code Insiders uses ~/.vscode-insiders/extensions.

EXT_DIR="$HOME/.vscode/extensions"

if [[ ! -d "$EXT_DIR" ]]; then
  echo "warning: $EXT_DIR does not exist — creating it."
  echo "  (VS Code may not be installed, or has never been opened.)"
  mkdir -p "$EXT_DIR"
fi

DEST="$EXT_DIR/$EXT_NAME"

# --- install ----------------------------------------------------------------

if [[ -d "$DEST" ]]; then
  echo "Removing old installation at $DEST ..."
  rm -rf "$DEST"
fi

echo "Installing to $DEST ..."
cp -r "$EXT_SRC" "$DEST"

# --- done -------------------------------------------------------------------

echo ""
echo "Installation complete."
echo ""
echo "To activate the extension, reload VS Code:"
echo "  $RELOAD_KEY  →  Developer: Reload Window"
echo ""
echo "If you use VS Code Insiders or Cursor, re-run with EXT_DIR overridden:"
echo "  EXT_DIR=~/.vscode-insiders/extensions bash install-vscode-ext.sh"
echo "  EXT_DIR=~/.cursor/extensions          bash install-vscode-ext.sh"
