# TeraShell Project Summary

## Project Goal
TeraShell is an ambitious project to create a modern, user-friendly, and powerful cross-platform shell for both Windows and Unix-like systems (Linux, macOS). It is designed with developer productivity in mind.

## Core Features & Architecture

1.  **Robustness and Stability:**
    *   The shell is designed to be a reliable system shell replacement. It has a fail-safe startup mechanism that catches errors, attempts to restart, and can fall back to a standard system shell (`bash`, `zsh`) or a minimal emergency shell to prevent locking the user out.

2.  **Advanced Interactive Experience:**
    *   **Syntax Highlighting:** It provides live, color-coded syntax highlighting for commands, paths, arguments, and more as you type.
    *   **Intelligent Autocompletion:** This is a standout feature. The shell can complete not only commands and paths but also arguments and flags for other command-line tools.
    *   **Command Mapping (`map` command):** TeraShell can "learn" a tool's command structure by running it with help flags (`--help`). It parses the output and builds a command tree, which is then used to provide highly accurate, context-aware suggestions.

3.  **Developer-Focused Tooling:**
    *   **Background Task Management (`bg` command):** It includes a powerful, built-in job manager. You can run processes in the background (`&`), view a detailed table of running tasks with CPU/memory usage, see their output, and kill them with descriptive statuses (`RUNNING`, `DONE`, `FAILED`, `KILLED`).
    *   **Python Virtual Environments (`activate`/`deactivate`):** It has first-class support for activating and deactivating Python virtual environments, displaying the active environment in the prompt.
    *   **Instruction Manager (`instr` command):** A built-in macro-like system that allows you to save, manage, and export sequences of shell commands, which is useful for remembering and running multi-step tasks.
    *   **Multi-Instance Support:** The shell can run in multiple named instances, allowing for different contexts with separate history and instruction lists.

## Technical Stack

*   **Primary Language:** Python.
*   **Key Libraries:**
    *   `prompt_toolkit`: Powers the entire interactive front-end, including autocompletion and syntax highlighting.
    *   `psutil`: Used for the advanced process monitoring in the background task manager.
    *   `prettytable`: For displaying the formatted list of background tasks.
*   **Rust Integration:** There is a `rust` directory with a `Cargo.toml` file, indicating plans to integrate Rust components (likely for performance), but this is not yet fully implemented.

## Current State & Recent Progress

*   **State:** The project is well-developed, with a rich and functional feature set. Its primary strengths are the intelligent autocompletion system (`map` command) and the robust background task manager.
*   **Recent Progress:** A significant recent milestone was the **implementation of a formal automated testing suite using `pytest`**. This addresses a major project need and provides a foundation for long-term stability. Development velocity has been high, with numerous bug fixes and enhancements being completed, including improved status reporting for background tasks, better `sudo` highlighting, and fixes for path autocompletion.

## Development Roadmap

### Immediate Priorities (0.3.0 Release)
The current development focus is on the 0.3.0 release, which includes the following key features and investigations:
*   **User Configuration:** Implementing a `config.toml` file to allow user customization of colors, prompts, and features.
*   **Enhanced Autocompletion:** Improving the engine to support compound commands (`&&`, `||`, `|`) and to be "adaptive" based on user history.
*   **Core Shell Features:** Adding support for environment variable expansion and a command `alias` system.
*   **Instruction Execution:** Building the `instr execute` command to run instruction files across different machine environments.
*   **Theming:** Expanding configuration to allow for full theming of the shell.
*   **Compatibility:** Investigating and resolving an issue with the Cockpit web-based monitoring tool.

### Long-Term Vision (Towards 1.0)
A production-ready 1.0 release is a long-term goal. Reaching it will require work on major, large-scale features after the 0.3.0 release is complete. Key items on this long-term roadmap include:
*   **Complete Rust Integration:** Fully realizing the plan to integrate Rust for performance-critical components.
*   **Plugin and Extension API:** Creating a stable API for users to extend the shell's functionality.
*   **Comprehensive Documentation & Testing:** Expanding test coverage significantly and writing detailed user and developer documentation.