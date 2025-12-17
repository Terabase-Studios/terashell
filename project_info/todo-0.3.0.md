# TeraShell 0.3.0 Development Plan

This document outlines the development tasks required for the TeraShell 0.3.0 release. Each task includes its goal, estimated effort, affected files, and key considerations.

---
## Regressions and Clarifications

*   **1. Decouple `install.sh` PATH setup from Shell Application**
    *   **Goal**: The choice to add `terashell-shell` to the system PATH should be independent of setting it as a login shell for users. The installer should always register the shell wrapper in `/etc/shells`, but the wrapper's location will depend on the user's choice.
    *   **Affected Files**: `scripts/install.sh`.

*   **2. Refine Background Process Handling for Command Chains**
    *   **Goal [COMPLETED]**: Ensure that commands containing `&&` or `||` can still be run as background processes if the entire line ends with a standalone `&`. The parser should be robust, with a fallback if `shlex` fails.
    *   **Affected Files**: `src/shell.py`.

---

## 1. Implement User Configuration Management
*   **Goal**: Implement saving and loading user configuration from `~/.TeraShell/config.toml` (or similar file format) in TeraShell's `APP_DIR`. This will allow users to customize colors, prompt layout, and features without editing the source code.
*   **Estimated Time**: 4-6 hours.
*   **Affected Files**: `src/config.py`, potentially a new config parsing module.
*   **Important Info**:
    *   Need to decide on a configuration file format (e.g., TOML, YAML, JSON). TOML is often preferred for human-readable configuration.
    *   The configuration file should be located at `~/.TeraShell/config.toml`.
    *   Implement logic to load default settings and then override them with user-defined settings from the file.
    *   This will involve changes to how `src/config.py` currently defines settings.

## 2. Improve Background Task Status Reporting
*   **Goal [COMPLETED]**: Enhance the `bg tasks` command to provide more descriptive statuses based on how a task concludes.
*   **Estimated Time**: 2-3 hours.
*   **Affected Files**: `src/background.py`.
*   **Important Info**:
    *   The `status()` method in the `BackgroundTask` class needs to be updated.
    *   Implement the following statuses:
        *   `RUNNING`: The process is currently active.
        *   `COMPLETED`: The process finished with exit code 0.
        *   `FAILED`: The process finished with a non-zero exit code.
        *   `TERMINATED`: The process was manually stopped by the user via `bg kill`.

## 3. Implement Autocomplete for Compound Commands
*   **Goal**: Enhance the autocompletion engine to correctly provide suggestions after command separators like `&&`, `||`, and `|`.
*   **Estimated Time**: 5-8 hours.
*   **Affected Files**: `src/input.py` (`CommandCompleter` class).
*   **Important Info**:
    *   This requires the completer to recognize command separators and restart the completion logic for the new command segment.
    *   For example, after a user types `git pull && `, the completer should suggest a new set of commands, not arguments for `git pull`.
    *   This is a complex enhancement to the parsing logic within the completer.

## 4. Implement Proper Sudo Highlighting
*   **Goal**: Improve the syntax highlighter to correctly identify and style the actual command being run when `sudo` is used.
*   **Estimated Time**: 2-4 hours.
*   **Affected Files**: `src/input.py` (`ShellLexer` class).
*   **Important Info**:
    *   Currently, if `sudo` is used, the highlighting for the subsequent command token may not be applied correctly.
    *   The lexer needs to be updated to recognize `sudo` as a prefix and then apply its normal command highlighting logic to the *next* token.

## 5. Enhance `install.sh` with PATH Prompt

*   **Goal**: Modify the Unix installer (`install.sh`) to explicitly ask the user if they want to add TeraShell to the system PATH, mirroring the functionality of the Windows `install.bat` script. This gives users more control over their environment.
*   **Estimated Time**: 1-2 hours.
*   **Affected Files**: `scripts/install.sh`.
*   **Important Info**:
    *   The script currently creates a wrapper in `/usr/local/bin`, which is typically in the user's PATH by default.
    *   The enhancement should involve adding a shell prompt (`read -p`) to ask the user.
    *   The logic for creating the symbolic link or wrapper script in a standard PATH directory should be made conditional based on the user's choice.

## 6. Fix Global Install Behavior in `install.sh`

*   **Goal [COMPLETED]**: The user reported that applying TeraShell globally via `install.sh` might be incorrectly launching the shell for the current user. This task is to investigate and rectify this behavior to ensure the script only sets the default shell for other users without affecting the current installation session.
*   **Estimated Time**: 2-4 hours.
*   **Affected Files**: `scripts/install.sh`.
*   **Important Info**:
    *   This is primarily an investigation task. The `chsh` command, used by the script, should not affect the current session, so the root cause needs to be identified.
    *   The problem might be related to how the script interacts with the environment when run by different shells.
    *   Testing on multiple Linux distributions (like Ubuntu and Fedora) would be beneficial to ensure consistent behavior.

## 7. Correct Background Process (`&`) Detection

*   **Goal [COMPLETED]**: Refine the command parser to prevent it from misinterpreting `&` or `&&` within command arguments (e.g., in a URL or as a logical AND) as a request to run a background process.
*   **Estimated Time**: 2-3 hours.
*   **Affected Files**: `src/shell.py`.
*   **Important Info**:
    *   The current implementation in the `TeraShell` class uses a simple string check (`"&" in args`).
    *   This should be replaced with more robust logic that only treats `&` as a background operator when it appears as a separate token at the end of the command line.
    *   Consider using Python's `shlex` module for more reliable parsing of command lines.

## 8. Investigate Cockpit Compatibility

*   **Goal**: The Cockpit web-based monitoring tool fails to work when TeraShell is set as the user's default shell. This task is to investigate the cause and implement a solution.
*   **Estimated Time**: 4-8 hours.
*   **Affected Files**: Potentially `src/TeraShell.py` and `src/shell.py`.
*   **Important Info**:
    *   This is a research-heavy task. Cockpit likely expects a POSIX-compliant shell for non-interactive command execution.
    *   The solution may involve detecting when TeraShell is run in a non-interactive session and either executing the command differently or passing it to a standard shell like `bash`.
    *   This could also be solved by making TeraShell's non-interactive mode more compliant with expected standard shell behaviors.

## 9. Implement Environment Variable Handling
*   **Goal**: Implement expansion of environment variables (e.g., `$HOME` on Unix, `%USERPROFILE%` on Windows) within the shell's command handling.
*   **Estimated Time**: 3-4 hours.
*   **Affected Files**: `src/shell.py`, `src/input.py`.
*   **Important Info**:
    *   The shell should be able to resolve variables like `echo $HOME`.
    *   This can be achieved using `os.path.expandvars` and `os.path.expanduser`.
    *   This needs to be integrated into the command execution flow.

## 10. Implement Adaptive Autocomplete

*   **Goal**: Add a third layer of autocompletion that provides predictive suggestions based on the user's command history and context, similar to the adaptive suggestions in JetBrains IDEs.
*   **Estimated Time**: 16-24 hours.
*   **Affected Files**: `src/input.py`, and likely a new file for the prediction logic (e.g., `src/predictor.py`).
*   **Important Info**:
    *   This is a major, complex feature.
    *   It would involve analyzing the command history to build a predictive model (e.g., what command most frequently follows `git status`?).
    *   The prediction logic needs to be integrated into the `CommandCompleter` in `src/input.py` to offer these suggestions in real-time.

---

## Suggested Additional Todos for Future Releases

*   **1. Implement a Formal Testing Suite**
    *   **Goal**: The project currently lacks automated tests. Integrating a framework like `pytest` and writing unit and integration tests is the highest priority for ensuring long-term stability and maintainability.
    *   **Estimated Time**: 20-30 hours (for initial setup and basic coverage).
    *   **Affected Files**: New `tests/` directory and test files (e.g., `tests/test_commands.py`).

*   **2. External User Configuration**
    *   **Goal**: Move settings from `src/config.py` to a user-editable file (e.g., `~/.TeraShell/config.toml`). This would allow users to easily customize colors, prompt layout, and features without editing the source code.
    *   **Estimated Time**: 4-6 hours.
    *   **Affected Files**: `src/config.py` and a new config parsing module.

*   **3. Alias and Function Support**
    *   **Goal**: Implement a built-in `alias` command to allow users to create and manage command aliases (e.g., `alias ll="ls -l"`). Support for shell functions could be a future extension.
    *   **Estimated Time**: 3-5 hours.
    *   **Affected Files**: `src/commands.py` and potentially `src/shell.py`.

*   **4. Improved Theming**
    *   **Goal**: Expand on the external configuration to allow for full theming of the shell, including all colors used in the syntax highlighting and prompt.
    *   **Estimated Time**: 2-4 hours.
    *   **Affected Files**: `src/input.py`, `src/shell.py`, and the new config module.