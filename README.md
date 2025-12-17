# TeraShell

TeraShell is a modern, cross-platform command-line shell designed for developer productivity and a user-friendly experience. It combines a powerful interactive interface with advanced developer-focused tools to make working in the terminal faster and more intuitive.

![image](https://github.com/Terabase-Studios/TeraShell/assets/1925364/11d882a2-3023-424a-939e-4e4b785d9962)

## Features

*   **Intelligent Autocompletion**: TeraShell provides rich, context-aware suggestions for commands, arguments, flags, paths, and history.
*   **Live Syntax Highlighting**: Commands, arguments, and paths are colored and highlighted as you type, improving readability and reducing errors.
*   **Command Mapping**: A powerful `map` command that learns the CLI of other tools by parsing their help text, providing deep autocompletion for their subcommands and flags.
*   **Advanced Background Tasks**: Run processes in the background with `&` and manage them with the `bg` command. View a detailed table of running jobs with CPU/memory stats, see their output, and kill them.
*   **Python Virtual Environment Support**: First-class support for `activate` and `deactivate` commands, with the active venv displayed in the prompt.
*   **Instruction Manager**: A built-in `instr` command to create, manage, and save sequences of commands, acting as a simple macro system.
*   **Cross-Platform**: Designed to run on both Windows and Unix-like systems (Linux, macOS).
*   **Robust and Safe**: Features a fail-safe startup mechanism that falls back to a standard system shell in case of critical errors, so you're never locked out.

## Installation

### Linux & macOS

1.  Clone the repository:
    ```sh
    git clone https://github.com/Terabase-Studios/TeraShell.git
    cd TeraShell
    ```
2.  Run the installation script:
    ```sh
    sudo sh ./scripts/install.sh
    ```
3.  The script will guide you through the process, including an option to set TeraShell as your default shell. Log out and back in for the changes to take effect.

### Windows

1.  Clone the repository:
    ```sh
    git clone https://github.com/Terabase-Studios/TeraShell.git
    cd TeraShell
    ```
2.  Run the installation script:
    ```bat
    .\scripts\install.bat
    ```
3.  The script will prompt you to install for the current user or all users and will offer to add TeraShell to your PATH and create a Start Menu shortcut.

## Usage

Once inside TeraShell, you can use standard shell commands as well as the advanced features built into the shell.

*   **Get Help**: See a list of all custom TeraShell commands.
    ```sh
    t?
    ```
*   **Map a Tool**: Learn the command structure of a tool (e.g., `git`) to enable deep autocompletion.
    ```sh
    map git
    ```
*   **Manage Background Tasks**: Run a long process in the background and check its status.
    ```sh
    long_running_command &
    bg tasks
    ```
*   **Use Instructions**: Save a sequence of commands for later.
    ```sh
    instr add "echo First step"
    instr add "echo Second step"
    instr list
    ```

## Contributing

Contributions are welcome! Please feel free to submit a pull request or open an issue for any bugs or feature requests.

## License

This project is licensed under the terms of the [LICENSE](LICENSE) file.
