#!/bin/sh
set -e

TARGET_DIR="/usr/local/bin/terashell"
WRAPPER="/usr/local/bin/terashell-shell"
BASH_PATH="/bin/bash"

# Verify bash exists
if [ ! -x "$BASH_PATH" ]; then
    echo "[!] $BASH_PATH does not exist or is not executable!"
    echo "[!] Aborting uninstall to avoid breaking the system."
    exit 1
fi

echo "[*] Full TeraShell uninstall for ALL users..."

# Ask about configs
printf "Remove all users' .terashell configuration folders? [y/N]: "
read remove_configs
REMOVE_CONFIGS=$(echo "$remove_configs" | tr '[:upper:]' '[:lower:]')

# Determine all users (home dirs + root)
USERS="$(ls /home | tr '\n' ' ') root"

# Restore shells for all users
echo "[*] Restoring login shells to $BASH_PATH..."
for u in $USERS; do
    sudo chsh -s "$BASH_PATH" "$u" || echo "[!] Failed to restore shell for $u"
done

# Set default shell for future accounts
if [ -f /etc/default/useradd ]; then
    sudo sed -i "s|SHELL=.*|SHELL=$BASH_PATH|" /etc/default/useradd
fi

# Remove TeraShell files
echo "[*] Removing TeraShell files..."
sudo rm -rf "$TARGET_DIR"
sudo rm -f "$WRAPPER"

# Remove wrapper from /etc/shells
if grep -Fxq "$WRAPPER" /etc/shells; then
    sudo sed -i "\|$WRAPPER|d" /etc/shells
fi

# Remove user-specific configs
if [ "$REMOVE_CONFIGS" = "y" ]; then
    echo "[*] Removing all users' .terashell folders..."
    for u in $USERS; do
        HOME_DIR=$(eval echo "~$u")
        sudo rm -rf "$HOME_DIR/.terashell"
    done
else
    echo "[*] Preserving .terashell configuration folders"
fi

echo ""
echo "[*] TeraShell fully uninstalled for all users."
echo "[*] All login shells restored to $BASH_PATH, future accounts will default to $BASH_PATH."
if [ "$REMOVE_CONFIGS" = "y" ]; then
    echo "[*] All .terashell configuration folders were removed."
else
    echo "[*] Configuration folders were preserved."
fi
