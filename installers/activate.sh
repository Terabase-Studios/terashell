#!/bin/bash
set -e

# -----------------------------------------------------------------------------
# TeraShell Activator
#
# This script helps you start using TeraShell as your primary shell.
# It offers two methods:
#
#   1. Safe Activation (Recommended):
#      Adds 'exec terashell' to your shell profile (~/.bashrc, ~/.zshrc).
#      This is safe because you can easily comment it out if something
#      goes wrong.
#
#   2. Login Shell Activation (Risky):
#      Uses 'chsh' to change your system's default login shell. This is
#      DANGEROUS. If TeraShell fails, you may be unable to log in.
#
# -----------------------------------------------------------------------------

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

# --- Main Logic ---

# 1. Find the TeraShell executable
log "INFO" "Locating TeraShell executable..."
USER_BIN_PATH="$HOME/.local/bin/terashell"
SYSTEM_BIN_PATH="/usr/local/bin/terashell"
TERASHELL_EXEC=""

if [ -x "$USER_BIN_PATH" ]; then
    TERASHELL_EXEC="$USER_BIN_PATH"
    log "SUCCESS" "Found user-level installation at $TERASHELL_EXEC"
elif [ -x "$SYSTEM_BIN_PATH" ]; then
    TERASHELL_EXEC="$SYSTEM_BIN_PATH"
    log "SUCCESS" "Found system-level installation at $TERASHELL_EXEC"
else
    log "ERROR" "TeraShell executable not found."
    log "INFO" "Please run the install.sh script first."
    exit 1
fi

# 2. Present activation choices
printf "\n"
log "INFO" "How would you like to activate TeraShell?"
printf "%s\n" "  1) Safe Activation (exec from shell profile, recommended)"
printf "%s\n" "  2) Login Shell Activation (use chsh, risky)"
printf "%s\n" "  3) Cancel"
printf "\n"
printf "%b" "Your choice [1/2/3]: "
read -r choice

# 3. Execute chosen action
case "$choice" in
    1)
        # Safe Activation
        log "INFO" "Proceeding with Safe Activation..."
        
        shell_profile=""
        current_shell=$(basename "$SHELL")
        case "$current_shell" in
            bash)
                shell_profile="$HOME/.bashrc"
                ;;
            zsh)
                shell_profile="$HOME/.zshrc"
                ;;
            *)
                log "WARN" "Could not detect a standard shell profile (.bashrc or .zshrc)."
                log "INFO" "Please add 'exec $TERASHELL_EXEC' manually to your shell's startup file."
                exit 1
                ;;
        esac

        # Check if already activated
        if grep -Fxq "exec $TERASHELL_EXEC" "$shell_profile"; then
            log "SUCCESS" "TeraShell is already activated in $shell_profile."
            exit 0
        fi

        # Add exec to profile
        printf "\n" >> "$shell_profile"
        printf "%s\n" "# Activate TeraShell" >> "$shell_profile"
        printf "%s\n" "exec $TERASHELL_EXEC" >> "$shell_profile"
        
        log "SUCCESS" "TeraShell has been activated in '$shell_profile'."
        log "INFO" "The next time you open a new terminal, it will start with TeraShell."
        log "INFO" "To deactivate and uninstall, run 'sh ./installers/uninstall.sh'."
        ;;
    2)
        # Login Shell (chsh) Activation
        log "WARN" "This is a risky operation."
        printf "%b" "Are you absolutely sure you want to change your login shell? [y/N]: "
        read -r chsh_confirm
        
        case "$chsh_confirm" in
            [yY] | [yY][eE][sS])
                # Proceed with chsh
                ;;
            *)
                log "INFO" "Activation cancelled."
                exit 0
                ;;
        esac

        if ! command -v chsh >/dev/null 2>&1; then
            log "ERROR" "'chsh' command not found. Cannot change login shell."
            exit 1
        fi

        # For user-level installs, /etc/shells must be updated manually
        if [ "$TERASHELL_EXEC" = "$USER_BIN_PATH" ] && ! grep -Fxq "$TERASHELL_EXEC" /etc/shells; then
            log "ERROR" "TeraShell is not listed in /etc/shells."
            log "INFO" "To use 'chsh', the shell executable must be in that file."
            log "WARN" "Please run the following command to add it:"
            printf "\n  %s\n\n" "echo '$TERASHELL_EXEC' | sudo tee -a /etc/shells"
            log "INFO" "After running the command, please try activating again."
            exit 1
        fi

        # Add to /etc/shells if it's a system install and not present
        if [ "$TERASHELL_EXEC" = "$SYSTEM_BIN_PATH" ] && ! grep -Fxq "$TERASHELL_EXEC" /etc/shells; then
            log "INFO" "This seems to be a system install. 'chsh' requires an entry in /etc/shells."
            log "INFO" "You may need to run 'sudo echo $TERASHELL_EXEC >> /etc/shells' first."
        fi

        if ! chsh -s "$TERASHELL_EXEC" "$(whoami)"; then
            log "ERROR" "Failed to change shell using 'chsh'."
            log "INFO" "Please check your permissions or if the shell path is in /etc/shells."
            exit 1
        fi
        
        log "SUCCESS" "Login shell changed successfully."
        log "INFO" "You will need to log out and log back in for the change to take effect."
        log "WARN" "To deactivate, run: chsh -s $(command -v bash) or run 'sh ./installers/uninstall.sh'."
        ;;
    3)
        log "INFO" "Activation cancelled."
        ;;
    *)
        log "ERROR" "Invalid choice. No action taken."
        ;;
esac