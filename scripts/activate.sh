#!/bin/sh
set -e

# -------------------------
# Configuration
# -------------------------
TARGET_DIR="/usr/local/bin/terashell"
WRAPPER="/usr/local/bin/terashell-shell"
BASH_PATH="/bin/bash"
CURRENT_USER="$(whoami)"

# -------------------------
# Check if TeraShell is installed
# -------------------------
if [ ! -x "$WRAPPER" ]; then
    echo "[!] TeraShell wrapper not found at $WRAPPER"
    echo "[!] Please install TeraShell first."
    exit 1
fi

# -------------------------
# Ask user to confirm activation
# -------------------------
echo ""
echo "Activate TeraShell for user $CURRENT_USER? This will change your login shell."
printf "[y/N]: "
read confirm
CONFIRM=$(echo "$confirm" | tr '[:upper:]' '[:lower:]')

if [ "$CONFIRM" != "y" ]; then
    echo "[*] Activation cancelled."
    exit 0
fi

# -------------------------
# Activate TeraShell for current user
# -------------------------
# This does not need sudo because it uses chsh for the current user
if command -v chsh >/dev/null 2>&1; then
    chsh -s "$WRAPPER" "$CURRENT_USER" || {
        echo "[!] Failed to change shell for $CURRENT_USER."
        exit 1
    }
    echo "[*] TeraShell activated for $CURRENT_USER!"
    echo "Log out and back in to start using TeraShell."
else
    echo "[!] 'chsh' command not found. Cannot change shell."
    exit 1
fi
