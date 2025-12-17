# Gemini Project Context: TeraShell

This document provides a comprehensive overview of the TeraShell project for instructional context.

## 1. Project Overview

TeraShell is a modern, cross-platform command-line shell designed for developer productivity and a user-friendly experience. It is primarily written in Python, with plans for Rust integration for performance-critical components.

The shell's architecture is modular, with distinct components for handling core logic, user input, commands, background tasks, and advanced autocompletion. Its main goal is to provide a superior interactive experience with features not commonly found in standard shells like bash or cmd.

**Key Technologies:**
*   **Python 3**: The core language of the application.
*   **prompt_toolkit**: A powerful Python library used for building interactive command-line interfaces. It is the foundation for TeraShell's syntax highlighting, autocompletion, and input handling.
*   **psutil**: Used for process management and statistics in the background task manager.
*   **prettytable**: Used to display formatted tables for background task listings.
*   **Rust**: A `rust` directory with a `Cargo.toml` file exists, indicating a planned integration, likely using `pyo3` for creating Python bindings.

## 2. Building and Running

### Dependencies

*   Python dependencies are managed in `requirements.txt`. Install them using:
    ```sh
    pip install -r requirements.txt
    ```
*   Rust dependencies are in `rust/Cargo.toml`. Build the Rust component with:
    ```sh
    cd rust && cargo build && cd ..
    ```

### Running the Shell

*   **For Development**: The shell can be run directly for development and testing purposes:
    ```sh
    python3 src/TeraShell.py
    ```
*   **Installation**: The project has installation scripts for easy setup.
    *   **Unix (Linux/macOS)**: `sudo sh ./scripts/install.sh`
    *   **Windows**: `.\\scripts\\install.bat`
    These scripts create a virtual environment, install dependencies, and set up a system-wide command (`terashell-shell`) to launch the shell.

### Testing

*   **Status**: The project currently **lacks a formal automated testing suite**.
*   **TODO**: A testing framework like `pytest` should be implemented. Unit and integration tests need to be written for the core components (`commands.py`, `background.py`, `shell.py`, etc.) to ensure stability and prevent regressions.

## 3. Development Conventions

*   **Modular Architecture**: The codebase is organized into modules within the `src/` directory, each with a specific responsibility:
    *   `TeraShell.py`: Main application entry point, error handling, and lifecycle management.
    *   `shell.py`: Contains the core `TeraShell` class, the main input loop, and command dispatching logic.
    *   `input.py`: Manages all user-facing interactive features, including the `prompt_toolkit` session, syntax highlighting (`ShellLexer`), and autocompletion (`CommandCompleter`).
    *   `commands.py`: Defines all built-in shell commands (e.g., `t?`, `map`, `bg`, `instr`).
    *   `indexer.py`: Implements the powerful `map` feature, which parses the `--help` output of other tools to generate detailed autocompletion trees.
    *   `background.py`: Manages background processes, using `psutil` for detailed monitoring.
    *   `config.py`: A central place for application settings and constants.
*   **Code Style**: The code generally follows standard Python conventions (PEP 8).
*   **Error Handling**: The shell features a robust startup wrapper (`TeraShell.py`) that can catch critical errors, restart the shell, and even fall back to a standard system shell to prevent the user from being locked out.
*   **Current Priorities**: The `project_info/todo-0.3.0.md` file outlines the active development tasks. Key priorities include implementing user configuration, improving background task status reporting, and enhancing the autocompleter to support compound commands.
