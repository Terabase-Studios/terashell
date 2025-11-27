import os
import subprocess
import sys
import traceback
import socket

from prompt_toolkit.formatted_text import ANSI

from commands import ShellCommands
from config import SHELL_NAME, SHOW_USER
from input import ShellInput

try:
    import colorama
    colorama.init()
except ImportError:
    pass


INITIAL_PRINT = """
Welcome to Terashell!
type 't?' to see a list of added commands!
"""


class MiniShell:
    def __init__(self):
        self.running = True
        self.command_handler = ShellCommands(self)
        self.input_handler = ShellInput(self, cmd_prefix=f"TS [ACTIVEDIR]:\n└> ")
        self.working_dir = os.getcwd()
        self.active_venv = None

        if "VIRTUAL_ENV" in os.environ:
            self.command_handler._cmd_activate([os.environ.get("VIRTUAL_ENV")])

    def run(self, command: str):
        try:
            subprocess.run(command, shell=True, stdout=sys.stdout, stderr=sys.stderr, env={**os.environ, "FORCE_COLOR": "1"},
)
        except Exception as e:
            print(f"{SHELL_NAME} error: {e}")

    def start(self):
        print(INITIAL_PRINT)
        while self.running:
            try:
                venv = f"[\033[36m{self.active_venv}\033[90m\033[0m]\033[90m-\033[0m" if self.active_venv else ""
                user = f"[\033[36m{os.getlogin()}@{socket.gethostname()}\033[90m\033[0m]\033[90m-\033[0m" if SHOW_USER else ""
                prefix = ANSI(f"\033[90mTS-\033[0m{venv}{user}[\033[36m{self.working_dir}\033[0m]\033[90m\n└> \033[0m")
                line = self.input_handler.input(cmd_prefix=prefix)
            except KeyboardInterrupt:
                print()
                continue
            except EOFError:
                break

            if not line:
                continue

            try:
                print()
                handled = self.command_handler.handle_command(line)
                if not handled:
                    self.run(line)
                print()

            except KeyboardInterrupt:
                print()


if __name__ == "__main__":
    shell = MiniShell()
    try:
        shell.start()
    except Exception as ex:
        print(f"{SHELL_NAME} unhandled error:\n{traceback.print_exception(ex)}")