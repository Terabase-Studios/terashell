# TeraShell Testing Development Plan

This document outlines the strategy for expanding the automated testing suite for TeraShell to ensure its stability, reliability, and maintainability. The plan is divided into phases, starting with the most critical components.

---

## Phase 1: Core Command Reliability

This phase focuses on ensuring that all built-in shell commands located in `src/commands.py` are thoroughly tested. These commands are fundamental to the user experience.

*   **Priority**: High
*   **Affected Files**: `tests/test_commands.py`

### Test Cases:
1.  **`cd` Command**:
    *   `cd` (no arguments) should change to the user's home directory.
    *   `cd <existing_directory>` should change to the specified directory.
    *   `cd <non_existent_directory>` should report an error and not change the directory.
    *   `cd ~` and `cd ~/subdir` should correctly expand the home directory path.
    *   `cd -` (if implemented) to go to the previous directory.

2.  **`history` Command**:
    *   `history` should correctly display the command history.
    *   `history clear` should wipe the history.

3.  **`activate` / `deactivate` Commands**:
    *   `activate <venv_path>` should correctly set the `VIRTUAL_ENV` and update the `PATH` environment variables.
    *   `deactivate` should restore the environment variables to their previous state.

4.  **`bg` Command Suite**:
    *   `bg tasks` should correctly display the list of background processes.
    *   `bg kill <id>` should call the `kill` method on the correct background task.
    *   `bg output <id>` should correctly retrieve the output of a specific task.

5.  **`instr` Command Suite**:
    *   Test adding, removing, listing, saving, and clearing instructions.

---

## Phase 2: Advanced Feature Verification

This phase targets the more complex and unique features of TeraShell, such as the command indexer and advanced autocompletion logic.

*   **Priority**: Medium
*   **Affected Files**: `tests/test_indexer.py`, `tests/test_input.py`

### Test Cases:
1.  **Command Indexer (`map` command)**:
    *   Write a test for the `map_tool` function in `src/indexer.py`.
    *   This will involve creating a mock command that produces fake `--help` output and asserting that the indexer correctly parses it into a command tree.

2.  **Path Completion**:
    *   Expand `tests/test_input.py` to include dedicated tests for path completion.
    *   Create a temporary directory structure and test completion for absolute paths, relative paths, and partial file/directory names.

---

## Phase 3: Integration and User Experience

This phase focuses on end-to-end interactive tests to ensure that all components work together seamlessly from a user's perspective.

*   **Priority**: Medium
*   **Affected Files**: `tests/test_terashell.py` (and other integration test files)

### Test Cases:
1.  **Command Chains**:
    *   Using `pexpect`, test running commands linked by `&&` and `||` to verify correct execution order and logic.

2.  **Environment Variable Expansion**:
    *   Write an interactive test that sets an environment variable and then uses it in a subsequent command (e.g., `my_var="hello"; echo $my_var`).

3.  **Input/Output Redirection**:
    *   If redirection features (`>`, `<`, `2>`) are implemented, write `pexpect` tests to verify that files are created and written to correctly.

4.  **Complex Interactive Scenarios**:
    *   Test for edge cases like unclosed quotes, special characters in input, and long-running commands.
