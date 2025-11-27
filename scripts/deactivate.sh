#!/bin/sh
set -e

TARGET_DIR="/usr/local/bin/terashell"
WRAPPER="/usr/local/bin/terashell-shell"
BASH_PATH="/bin/bash"

CURRENT_USER="$(whoami)"

echo "[*] Deactivating TeraShell for user $CURRENT_USER..."

# Switch back to bash for this user
chsh -s "$BASH_PATH" "$CURRENT_USER" || echo "[!] Could not switch shell automatically, run 'chsh -s $BASH_PATH' manually"

# Optionally remove configs
printf "Remove your ~/.terashell folder? [y/N]: "
read remove_config
REMOVE_CONFIG=$(echo "$remove_config" | tr '[:upper:]' '[:lower:]')

if [ "$REMOVE_CONFIG" = "y" ]; then
    rm -rf "$HOME/.terashell"
    echo "[*] Removed $HOME/.terashell"
else
    echo "[*] Preserved $HOME/.terashell"
fi

echo "[*] Deactivation complete. Your shell is now $BASH_PATH."
