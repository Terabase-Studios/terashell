#!/bin/bash
set -e

# -----------------------------------------------------------------------------
# TeraShell Installer
#
# This script installs TeraShell. It defaults to a user-level installation,
# which does not require sudo privileges and is safer. A system-wide
# installation is available via the --system flag, but is not recommended.
#
# Modes:
#   - User (default): Installs to ~/.terashell, with a launcher in ~/.local/bin.
#   - System (--system): Installs to /usr/local/bin/terashell (requires sudo).
# -----------------------------------------------------------------------------

# --- Configuration ---
MIN_PYTHON_MAJOR=3
MIN_PYTHON_MINOR=8
SCRIPT_DIR="$(dirname "$(realpath "$0")")"
PROJECT_ROOT="$SCRIPT_DIR/.."
REQUIREMENTS="$PROJECT_ROOT/requirements.txt"
INSTALL_MODE="user"

# --- Helper Functions ---

# Function to print a formatted message
# Usage: log "level" "message"
# Example: log "INFO" "Starting installation..."
log() {
    local level="$1"
    local message="$2"
    local color_reset='\033[0m'
    local color_info='\033[36m'  # Cyan
    local color_warn='\033[33m'  # Yellow
    local color_error='\033[31m' # Red
    local color_success='\033[32m' # Green

    case "$level" in
        "INFO") printf "%b\n" "${color_info}[*] $message${color_reset}";;
        "SUCCESS") printf "%b\n" "${color_success}[+] $message${color_reset}";;
        "WARN") printf "%b\n" "${color_warn}[!] $message${color_reset}";;
        "ERROR") printf "%b\n" "${color_error}[X] $message${color_reset}";;
        *) printf "%s\n" "[-] $message";;
    esac
}

# Check Python version
check_python_version() {
    log "INFO" "Checking Python version..."
    if ! python3 -c "import sys; sys.exit(0 if sys.version_info >= ($MIN_PYTHON_MAJOR, $MIN_PYTHON_MINOR) else 1)" >/dev/null 2>&1; then
        log "ERROR" "Python $MIN_PYTHON_MAJOR.$MIN_PYTHON_MINOR+ is required. Please install it and ensure 'python3' is in your PATH."
        exit 1
    fi
    local py_version
    py_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')")
    log "SUCCESS" "Python version $py_version is compatible."
}

# --- Installation Logic ---

# User-level installation
install_user() {
    log "INFO" "Starting user-level installation."
    local target_dir="$HOME/.terashell"
    local bin_dir="$HOME/.local/bin"
    local wrapper_path="$bin_dir/terashell"
    local shell_profile="$HOME/.profile" # Initialize shell_profile here

    # Determine shell profile
    if [ -n "$SHELL" ]; then
        case "$(basename "$SHELL")" in
            bash) shell_profile="$HOME/.bashrc" ;;
            zsh) shell_profile="$HOME/.zshrc" ;;
            fish) shell_profile="$HOME/.config/fish/config.fish" ;;
            *) # Default to .profile if shell not explicitly matched
               shell_profile="$HOME/.profile" ;;
        esac
    fi

    # 1. Create directories
    log "INFO" "Creating installation directories..."
    mkdir -p "$target_dir"
    mkdir -p "$bin_dir"
    log "SUCCESS" "Directories created at $target_dir and $bin_dir."

    # 2. Copy source files
    log "INFO" "Copying TeraShell source files..."
    cp -r "$PROJECT_ROOT/src"/* "$target_dir/"
    log "SUCCESS" "Source files copied."

    # 3. Create virtual environment and install dependencies
    log "INFO" "Creating Python virtual environment..."
    python3 -m venv "$target_dir/venv"
    log "INFO" "Installing dependencies from requirements.txt..."
    "$target_dir/venv/bin/pip" install --upgrade pip > /dev/null
    "$target_dir/venv/bin/pip" install -r "$REQUIREMENTS"
    log "SUCCESS" "Virtual environment and dependencies are set up."

    # 4. Create the wrapper script
    log "INFO" "Creating launcher script at $wrapper_path..."
    cat > "$wrapper_path" << EOF
#!/bin/sh
# This script launches TeraShell from the user installation.
exec "$target_dir/venv/bin/python" "$target_dir/TeraShell.py" "\$@"
EOF
    chmod +x "$wrapper_path"
    log "SUCCESS" "Launcher created."

    # 5. Check and update PATH
    # Use POSIX-compliant 'case' for path check
    case ":$PATH:" in
        *":$bin_dir:"*) 
            log "INFO" "PATH already includes $bin_dir. No modification needed."
            ;;
        *)
            log "WARN" "Your PATH does not include $bin_dir."
            log "INFO" "To run 'terashell', you need to add it to your PATH."
            
            printf "\n# Add ~/.local/bin to PATH for TeraShell\n" >> "$shell_profile"
            echo "export PATH=\"$bin_dir:\$PATH\"" >> "$shell_profile"
            log "SUCCESS" "Added PATH export to your '$shell_profile'. Please restart your terminal or run 'source $shell_profile'."
            ;;
    esac

    # 6. Final instructions
    echo ""
    log "SUCCESS" "TeraShell user-level installation is complete!"
    log "INFO" "You can now run 'terashell' from your terminal."
    log "WARN" "To make TeraShell your default login shell, you can run:"
    log "WARN" "  sh ./installers/activate.sh"
    log "WARN" "and select the 'Login Shell' option. This is risky."
    log "INFO" "For a safer alternative, run 'sh ./installers/activate.sh' and select 'Safe Activation'."
}

# System-wide installation
install_system() {
    if [ "$(id -u)" -ne 0 ]; then
        log "ERROR" "System-wide installation requires sudo privileges. Please run with 'sudo'."
        exit 1
    fi
    
    log "INFO" "Starting system-wide installation."
    local target_dir="/usr/local/lib/terashell"
    local wrapper_path="/usr/local/bin/terashell"

    # 1. Create directories
    log "INFO" "Creating installation directories..."
    mkdir -p "$target_dir"
    log "SUCCESS" "Directory created at $target_dir."

    # 2. Copy source files
    log "INFO" "Copying TeraShell source files..."
    cp -r "$PROJECT_ROOT/src"/* "$target_dir/"
    chmod -R 755 "$target_dir"
    log "SUCCESS" "Source files copied."

    # 3. Create virtual environment and install dependencies
    log "INFO" "Creating Python virtual environment..."
    python3 -m venv "$target_dir/venv"
    log "INFO" "Installing dependencies..."
    "$target_dir/venv/bin/pip" install --upgrade pip > /dev/null
    "$target_dir/venv/bin/pip" install -r "$REQUIREMENTS"
    log "SUCCESS" "Virtual environment and dependencies are set up."

    # 4. Create the wrapper script
    log "INFO" "Creating wrapper script at $wrapper_path..."
    cat > "$wrapper_path" << EOF
#!/bin/sh
# This script launches TeraShell from the system-wide installation.
exec "$target_dir/venv/bin/python" "$target_dir/TeraShell.py" "\$@"
EOF
    chmod +x "$wrapper_path"
    log "SUCCESS" "Wrapper script created."
    
    # 5. Add to /etc/shells
    if ! grep -Fxq "$wrapper_path" /etc/shells; then
        log "INFO" "Adding TeraShell to /etc/shells..."
        echo "$wrapper_path" >> /etc/shells
        log "SUCCESS" "Shell added."
    fi

    # 6. Final instructions
    echo ""
    log "SUCCESS" "TeraShell system-wide installation is complete!"
    log "INFO" "You can now run 'terashell' from your terminal."
    log "WARN" "If you wish to set TeraShell as the default shell for a user, run:"
    log "WARN" "  chsh -s $wrapper_path <username>"
    log "WARN" "This is risky and not recommended for critical users like 'root'."
}


# --- Main Execution ---

# Parse command-line arguments
if [ "$1" = "--system" ]; then
    INSTALL_MODE="system"
fi

# Run pre-flight checks
check_python_version

# Execute the chosen installation mode
if [ "$INSTALL_MODE" = "user" ]; then
    install_user
else
    # We don't automatically ask for sudo, the user must run the script with it.
    install_system
fi

echo ""
log "INFO" "For uninstallation, run 'sh $SCRIPT_DIR/uninstall.sh'."
