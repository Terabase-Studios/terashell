#!/bin/bash
set -e

# -------------------------
# Configuration
# -------------------------
MIN_PYTHON_MAJOR=3
MIN_PYTHON_MINOR=6

SCRIPT_DIR="$(dirname "$(realpath "$0")")"
PY_SRC_DIR="$SCRIPT_DIR/.."   # TeraShell root
TARGET_DIR="/usr/local/bin/terashell"
WRAPPER="/usr/local/bin/terashell-shell"
REQUIREMENTS="$PY_SRC_DIR/requirements.txt"
CURRENT_USER="$(whoami)"

# -------------------------
# Python Version Check
# -------------------------
check_python_version() {
    if ! command -v python3 >/dev/null 2>&1; then
        echo "[!] Python3 is missing. Need >= $MIN_PYTHON_MAJOR.$MIN_PYTHON_MINOR"
        exit 1
    fi

    PYTHON_VERSION=$(python3 - << 'EOF'
import sys
print(f"{sys.version_info.major}.{sys.version_info.minor}")
EOF
    )

    PY_MAJOR=${PYTHON_VERSION%.*}
    PY_MINOR=${PYTHON_VERSION#*.}

    if [ "$PY_MAJOR" -lt "$MIN_PYTHON_MAJOR" ] ||
       { [ "$PY_MAJOR" -eq "$MIN_PYTHON_MAJOR" ] && [ "$PY_MINOR" -lt "$MIN_PYTHON_MINOR" ]; }; then
        echo "[!] Python $PYTHON_VERSION found. Need >= $MIN_PYTHON_MAJOR.$MIN_PYTHON_MINOR"
        exit 1
    fi

    echo "[*] Python version OK: $PYTHON_VERSION"
}

check_python_version

echo "[*] Installing TeraShell..."


# -------------------------
# Copy TeraShell Files
# -------------------------
echo "[*] Copying source files..."
sudo mkdir -p "$TARGET_DIR"
sudo cp -r "$PY_SRC_DIR/src"/* "$TARGET_DIR/"
sudo chmod -R 755 "$TARGET_DIR"


# -------------------------
# Create Virtual Environment
# -------------------------
echo "[*] Creating virtual environment..."
sudo python3 -m venv "$TARGET_DIR/venv"
sudo chown -R "$CURRENT_USER" "$TARGET_DIR/venv"

if [ -f "$REQUIREMENTS" ]; then
    echo "[*] Installing dependencies..."
    "$TARGET_DIR/venv/bin/pip" install --upgrade pip
    "$TARGET_DIR/venv/bin/pip" install -r "$REQUIREMENTS"
fi


# -------------------------
# Create Wrapper Shell Entry
# -------------------------
echo "[*] Creating wrapper script..."
sudo tee "$WRAPPER" >/dev/null << EOF
#!/bin/sh
exec $TARGET_DIR/venv/bin/python $TARGET_DIR/TeraShell.py
EOF

sudo chmod +x "$WRAPPER"


# -------------------------
# Register Shell in /etc/shells
# -------------------------
if ! grep -Fxq "$WRAPPER" /etc/shells; then
    echo "[*] Adding wrapper to /etc/shells..."
    echo "$WRAPPER" | sudo tee -a /etc/shells >/dev/null
fi


# -------------------------
# Add 'terashell' to PATH
# -------------------------
echo ""
read -r -p "Do you want to add 'terashell-shell' to your PATH to launch the shell? [y/N]: " path_choice
case "$path_choice" in
    [yY][eE][sS]|[yY])
        echo "[*] Creating symlink for 'terashell-shell'..."
        sudo ln -sf "$WRAPPER" /usr/local/bin/terashell
        ;;
    *)
        echo "[*] Skipping PATH modification."
        ;;
esac


# -------------------------
# Shell Selection Prompt
# -------------------------
echo ""
echo "Choose how to apply TeraShell:"
echo "  1) Set as shell for *this user* ($CURRENT_USER)"
echo "  2) Apply semi-globally (all new and existing users accept root)"
echo "  3) Apply globally (all new users and existing including root) - Not recommended"
echo "  4) Do not automatically apply"
echo ""

read -r -p "Selection [1/2/3/4]: " choice

case "$choice" in
    1)
        echo "[*] Applying TeraShell for user $CURRENT_USER..."
        sudo chsh -s "$WRAPPER" "$CURRENT_USER" || echo "[!] Could not set shell"
        ;;
    2)
        echo "[*] Applying semi-globally..."

        # Apply to all existing users with home dirs
        for home in /home/*; do
            [ -d "$home" ] || continue       # skip non-directories
            u=$(basename "$home")
            sudo chsh -s "$WRAPPER" "$u" || echo "[!] Failed for user $u"
        done

        # Default login shell (for new accounts)
        if [ -f /etc/default/useradd ]; then
            sudo sed -i "s|SHELL=.*|SHELL=$WRAPPER|" /etc/default/useradd
        fi
        ;;
    3)
        echo "[*] Applying globally"

        # Apply to all existing non-root users with home dirs
        for home in /home/*; do
            [ -d "$home" ] || continue
            u=$(basename "$home")
            sudo chsh -s "$WRAPPER" "$u" || echo "[!] Failed for user $u"
        done

        # Apply to root explicitly
        sudo chsh -s "$WRAPPER" root || echo "[!] Failed for root"

        # Set default login shell for all *future* accounts
        if [ -f /etc/default/useradd ]; then
            sudo sed -i "s|SHELL=.*|SHELL=$WRAPPER|" /etc/default/useradd
        fi
        ;;
    4)
        echo "[*] Leaving system shells unchanged. You can switch manually with:"
        echo "    chsh -s $WRAPPER"
        ;;
    *)
        echo "[!] Invalid selection. No changes made."
        ;;
esac

echo ""
echo "[*] Installation complete"
echo "Log out and back in to start using TeraShell."

echo "Run 'sh $SCRIPT_DIR/activate.sh' to activate TeraShell for the instigating user"
echo "Run 'sh $SCRIPT_DIR/deactivate.sh' to deactivate TeraShell for the instigating user'"
echo "For a full TeraShell uninstall for ALL users, run 'sh $SCRIPT_DIR/uninstall.sh'"
