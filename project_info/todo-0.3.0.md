# TeraShell 0.3.0 Development Plan

This document outlines the development tasks required for the TeraShell 0.3.0 release. Each task includes its goal, estimated effort, affected files, and key considerations.

---
## Regressions and Clarifications

*   **1. Decouple `install.sh` PATH setup from Shell Application**
    *   **Goal**: The choice to add `terashell-shell` to the system PATH should be independent of setting it as a login shell for users. The installer should always register the shell wrapper in `/etc/shells`, but the wrapper's location will depend on the user's choice.
    *   **Affected Files**: `scripts/install.sh`.

*   **2. Refine Background Process Handling for Command Chains**
    *   **Goal [COMPLETED]**: Ensure that commands containing `&&` or `||` can still be run as background processes if the entire line ends with a standalone `&`. The parser now uses `shlex.split` for more robust parsing, with a fallback to a simple split.
    *   **Affected Files**: `src/shell.py`.

---

## Patches

*   **1. Fix Global Install Behavior in `install.sh`**
    *   **Goal [COMPLETED]**: The user reported that applying TeraShell globally via `install.sh` might be incorrectly launching the shell for the current user. This task is to investigate and rectify this behavior to ensure the script only sets the default shell for other users without affecting the current installation session.
    *   **Affected Files**: `scripts/install.sh`.

*   **2. Correct Background Process (`&`) Detection**
    *   **Goal [COMPLETED]**: Refine the command parser to prevent it from misinterpreting `&` or `&&` within command arguments (e.g., in a URL or as a logical AND) as a request to run a background process.
    *   **Affected Files**: `src/shell.py`.

*   **3. Investigate Cockpit Compatibility**
    *   **Goal**: The Cockpit web-based monitoring tool fails to work when TeraShell is set as the user's default shell. This task is to investigate the cause and implement a solution.
    *   **Affected Files**: Potentially `src/TeraShell.py` and `src/shell.py`.

*   **4. Fix fallsafe command 'f'.**
    *   **Goal [COMPLETED]**: The `f` command was intended to force a critical error to engage the fallback shell, but the exception was being caught locally in `commands.py`. The fix ensures the exception propagates to the main shell loop in `TeraShell.py` by checking `str(e)` instead of the deprecated `e.message`.
    *   **Affected Files**: `src/commands.py`.

*   **5. Add option to prevent path indexing in c/WINDOWS for WSL compatibility**
    *   **Goal [COMPLETED]**: Added a `PATH_INDEXING_EXCLUDE` list to `config.py` to prevent the command indexer from scanning specified paths. This improves performance and prevents errors in WSL environments by checking if a path starts with any of the excluded prefixes.
    *   **Affected Files**: `src/config.py`, `src/indexer.py`.

*   **6. Improve Background Task Status Reporting**
    *   **Goal [COMPLETED]**: Enhance the `bg tasks` command to provide more descriptive statuses based on how a task concludes.
    *   **Affected Files**: `src/background.py`.
    *   **Important Info**:
        *   The `status()` method in the `BackgroundTask` class was updated.
        *   The implemented statuses are: `RUNNING`, `DONE`, `FAILED`, `KILLED`.

*   **7. Implement Proper Sudo Highlighting**
    *   **Goal [COMPLETED]**: Improve the syntax highlighter to correctly identify and style the actual command being run when `sudo` is used.
    *   **Affected Files**: `src/input.py` (`ShellLexer` class).

*   **8. Fix Absolute Path Autocorrect**
    *   **Goal [COMPLETED]**: Prevent the autocompletion from removing the leading slash on absolute paths.
    *   **Affected Files**: `src/input.py` (`_format_path` method).
    *   **Important Info**: The `lstrip` call in `_format_path` is too aggressive and needs to be adjusted to preserve the leading slash for absolute paths.

*   **9. Better Lexing Coloring**
    *   **Goal [COMPLETED]**: Improved the overall lexing coloring to enhance readability and user experience. This includes improvements such as proper sudo highlighting.
    *   **Affected Files**: `src/input.py` (`ShellLexer` class).

---

## New Features

*   **1. Implement User Configuration Management**
    *   **Goal**: Implement saving and loading user configuration from `~/.TeraShell/config.toml` (or similar file format) in TeraShell's `APP_DIR`. This will allow users to customize colors, prompt layout, and features without editing the source code.
    *   **Affected Files**: `src/config.py`, potentially a new config parsing module.

*   **2. Implement Autocomplete for Compound Commands**
    *   **Goal**: Enhance the autocompletion engine to correctly provide suggestions after command separators like `&&`, `||`, and `|`.
    *   **Affected Files**: `src/input.py` (`CommandCompleter` class).

*   **3. Enhance `install.sh` with PATH Prompt**
    *   **Goal [COMPLETED]**: Modify the Unix installer (`install.sh`) to explicitly ask the user if they want to add TeraShell to the system PATH. This provides a convenient way to launch the shell using the `terashell` command.
    *   **Affected Files**: `scripts/install.sh`.

*   **4. Implement Environment Variable Handling**
    *   **Goal**: Implement expansion of environment variables (e.g., `$HOME` on Unix, `%USERPROFILE%` on Windows) within the shell's command handling.
    *   **Affected Files**: `src/shell.py`, `src/input.py`.

*   **5. Implement Adaptive Autocomplete**
    *   **Goal**: Add a third layer of autocompletion that provides predictive suggestions based on the user's command history and context.
    *   **Affected Files**: `src/input.py`, and likely a new file for the prediction logic.

*   **6. Implement a Formal Testing Suite**
    *   **Goal [COMPLETED]**: The project currently lacks automated tests. Integrating a framework like `pytest` and writing unit and integration tests is the highest priority for ensuring long-term stability and maintainability.
    *   **Affected Files**: New `tests/` directory and test files.

*   **7. Alias and Function Support**
    *   **Goal**: Implement a built-in `alias` command to allow users to create and manage command aliases.
    *   **Affected Files**: `src/commands.py` and potentially `src/shell.py`.

*   **8. Improved Theming**
    *   **Goal**: Expand on the external configuration to allow for full theming of the shell.
    *   **Affected Files**: `src/input.py`, `src/shell.py`, and the new config module.

*   **9. Implement `instr` Execution Command**
    *   **Goal**: Allow TeraShell to execute instruction files, potentially accounting for differences between computers.
    *   **Affected Files**: `src/instructions.py`, `src/shell.py`.