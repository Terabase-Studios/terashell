#!/bin/bash
set -e

# -----------------------------------------------------------------------------
# TeraShell Uninstaller & Deactivator
#
# This script safely deactivates and uninstalls TeraShell.
# 1. It reverts any shell modifications ('exec' lines or 'chsh' changes).
# 2. It removes all application files.
# -----------------------------------------------------------------------------

# --- Configuration ---
USER_INSTALL_DIR="$HOME/.terashell"
USER_BIN_PATH="$HOME/.local/bin/terashell"
SYSTEM_INSTALL_DIR="/usr/local/lib/terashell"
SYSTEM_WRAPPER_PATH="/usr/local/bin/terashell"

# --- Helper Functions ---
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

# Removes modifications from a given shell profile file
remove_profile_modifications() {
    local profile_path="$1"
    local terashell_path_fragment="terashell" # Generic fragment to find exec/path lines

    if [ ! -f "$1" ]; then
        return
    fi

    # Check if file contains any terashell modifications
    if grep -q "$terashell_path_fragment" "$1"; then
        log "INFO" "Detected modifications in '$1'. Cleaning up..."
        
        # Escape paths for sed
        local escaped_user_bin_path=$(echo "$USER_BIN_PATH" | sed 's/\//\\\//g')
        local escaped_home_local_bin=$(echo "$HOME/.local/bin" | sed 's/\//\\\//g')

        # Remove 'exec terashell' line and its comment
        sed -i.bak '/# Activate TeraShell/d' "$1"
        sed -i.bak "/exec $escaped_user_bin_path/d" "$1"

        # Remove PATH export line and its comment
        sed -i.bak '/# Add ~\/.local\/bin to PATH for TeraShell/d' "$1"
        sed -i.bak "/export PATH=\"$escaped_home_local_bin:\$PATH\"/d" "$1"
        
        log "SUCCESS" "Cleaned up '$1'."
    fi
}

# Deactivates by changing the login shell if it was set to terashell
deactivate_chsh_method() {
    local terashell_exec_path="$1"
    local current_user
    current_user=$(whoami)
    local login_shell
    login_shell=$(getent passwd "$current_user" | cut -d: -f7)

    if [ "$login_shell" = "$1" ]; then
        log "WARN" "Detected TeraShell is set as your login shell via 'chsh'."
        
        local default_shell="/bin/bash"
        if [ ! -x "$default_shell" ]; then default_shell="/bin/sh"; fi

        printf "%b" "Do you want to switch it back to '$default_shell'? [Y/n]: "
        read -r confirm
        case "$confirm" in
            [nN])
                log "WARN" "Deactivation of login shell cancelled. Please change it manually via 'chsh'."
                return
                ;;
            *)
                # Proceed
                ;;
        esac

        if ! chsh -s "$default_shell" "$current_user"; then
            log "ERROR" "Failed to change shell. You may need to run 'chsh -s $default_shell' manually."
            return
        fi
        log "SUCCESS" "Login shell has been reverted to '$default_shell'."
        log "INFO" "You must log out and log back in for this to take effect."
    fi
}

# --- Main Uninstallation Logic ---
uninstall_and_deactivate() {
    local install_dir="$1"
    local bin_path="$2"
    local scope_name="$3"
    
    log "INFO" "Starting $scope_name deactivation and uninstallation..."

    # 1. Deactivate shell modifications
    log "INFO" "Step 1: Deactivating shell configurations..."
    if [ "$scope_name" = "user-level" ]; then
        deactivate_chsh_method "$bin_path"
        remove_profile_modifications "$HOME/.bashrc"
        remove_profile_modifications "$HOME/.zshrc"
        remove_profile_modifications "$HOME/.profile"
    else
        log "INFO" "System-wide deactivation involves checking user shells manually."
    fi

    # 2. Confirm and remove files
    log "INFO" "Step 2: Removing application files..."
    printf "%b" "Are you sure you want to PERMANENTLY remove all TeraShell files from '$install_dir'? [y/N]: "
    read -r confirmation
    
    case "$confirmation" in
        [yY] | [yY][eE][sS])
            # Proceed with file removal
            ;;
        *)
            log "WARN" "File removal cancelled."
            exit 0
            ;;
    esac
    
    if [ -d "$install_dir" ]; then
        log "INFO" "Removing directory: $install_dir"
        rm -rf "$install_dir"
    fi

    if [ -f "$bin_path" ]; then
        log "INFO" "Removing launcher: $bin_path"
        rm -f "$bin_path"
    fi
    
    if [ "$scope_name" = "system-wide" ]; then
        if grep -Fxq "$bin_path" /etc/shells; then
            log "INFO" "Removing TeraShell from /etc/shells..."
            local escaped_bin_path=$(echo "$bin_path" | sed 's/\//\\\//g')
            sed -i.bak "/$escaped_bin_path/d" /etc/shells
        fi
    fi

    log "SUCCESS" "TeraShell files have been removed."
    log "INFO" "Please restart your terminal for all changes to take effect."
}

# --- Main Execution ---
log "INFO" "Searching for TeraShell installation..."

if [ -d "$USER_INSTALL_DIR" ] || [ -f "$USER_BIN_PATH" ]; then
    uninstall_and_deactivate "$USER_INSTALL_DIR" "$USER_BIN_PATH" "user-level"
elif [ -d "$SYSTEM_INSTALL_DIR" ] || [ -f "$SYSTEM_WRAPPER_PATH" ]; then
    if [ "$(id -u)" -ne 0 ]; then
        log "ERROR" "A system-wide installation was detected. Please run with 'sudo $0'."
        exit 1
    fi
    uninstall_and_deactivate "$SYSTEM_INSTALL_DIR" "$SYSTEM_WRAPPER_PATH" "system-wide"
else
    log "INFO" "TeraShell does not appear to be installed."
fi

