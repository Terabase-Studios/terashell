import os
import subprocess
import sys
import traceback
import socket
from prompt_toolkit.formatted_text import ANSI

from commands import ShellCommands
from config import SHELL_NAME, SHOW_USER, IS_UNIX
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

RESET = "\033[0m"
RED = "\033[31m"
CYAN = "\033[36m"
WHITE = "\033[37m"
BRIGHT_BLACK = "\033[90m"
DARK_RED = "\033[38;2;139;0;0m"

def get_current_user():
    if IS_UNIX:
        try:
            import pwd
            return pwd.getpwuid(os.geteuid()).pw_name
        except Exception:
            return os.environ.get("USER", "unknown")
    else:  # Windows
        return os.environ.get("USERNAME", "unknown")

class MiniShell:
    def __init__(self):
        self.running = True
        self.command_handler = ShellCommands(self)
        self.input_handler = ShellInput(self, cmd_prefix=f"TS [ACTIVEDIR]:\n└> ")
        self.working_dir = os.getcwd()
        self.active_venv = None
        self.active_venv_version = None

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
                user = get_current_user()
                MAIN_COLOR = CYAN if user != "root" else RED
                BACK_COLOR = BRIGHT_BLACK if user != "root" else DARK_RED
                venv = f"[{MAIN_COLOR}{self.active_venv_version}@{self.active_venv}{BACK_COLOR}{RESET}]{BACK_COLOR}-{RESET}" if self.active_venv else ""
                user = f"[{MAIN_COLOR}{user}@{socket.gethostname()}{BACK_COLOR}{RESET}]{BACK_COLOR}-{RESET}" if SHOW_USER else ""
                prefix = ANSI(f"{BACK_COLOR}TS-{RESET}{venv}{user}[{MAIN_COLOR}{self.working_dir}{RESET}]{BACK_COLOR}\n"
                              f"└> {RESET}")
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