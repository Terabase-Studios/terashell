import asyncio
import json
import os
import shlex
import socket
import subprocess
import sys

from prompt_toolkit.formatted_text import ANSI

from background import create_btm
from commands import ShellCommands
from config import HISTORY_FILE, INSTANCE_FILE
from config import SHELL_NAME, SHOW_USER, IS_UNIX, VERSION
from input import ShellInput

try:
    import colorama
    colorama.init()
except ImportError:
    pass


INITIAL_PRINT = f"""
Welcome to Terashell!
type 't?' to see a list of added commands!
Shell Version: {VERSION}
"""

RED_BACKGROUND = "\033[41m"
BOLD = "\033[1m"

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

def instance_file(instance, file):
    return file.replace(os.path.basename(file), os.path.basename(file)+f"-{instance}") if instance else file


class TeraShell:
    def __init__(self, instance=None, shell_file=None):
        self.running = True
        self.command_handler = ShellCommands(self)
        self.btm = create_btm()
        history_file = instance_file(instance, HISTORY_FILE)

        self.input_handler = ShellInput(self, cmd_prefix=f"NO_PROMPT_DEFINED> ", history_file=history_file)
        self.working_dir = os.getcwd()
        self.active_venv = None
        self.active_venv_version = None
        self.instance = instance
        self.shell_file = shell_file
        self.cmd_check = None

        if "VIRTUAL_ENV" in os.environ:
            self.command_handler._cmd_activate([os.environ.get("VIRTUAL_ENV")])

    def run(self, command: str):
        try:
            result = subprocess.run(command, shell=True, stdout=sys.stdout, stderr=sys.stderr, env={**os.environ, "FORCE_COLOR": "1"},)
            self.input_handler.history.set_last_exit_code(result.returncode)

        except Exception as e:
            print(f"{SHELL_NAME} error: {e}")

    def start(self):
        print(INITIAL_PRINT)
        while self.running:
            try:
                user = get_current_user()
                MAIN_COLOR = CYAN if user != "root" else RED
                BACK_COLOR = BRIGHT_BLACK if user != "root" else DARK_RED
                instance = f"[{MAIN_COLOR}{self.instance}{RESET}]{BACK_COLOR}-{RESET}" if self.instance else ""
                venv_version = f"{self.active_venv_version}@" if self.active_venv_version else ""
                venv = f"[{MAIN_COLOR}{venv_version}{self.active_venv}{RESET}]{BACK_COLOR}-{RESET}" if self.active_venv else ""
                user = f"[{MAIN_COLOR}{user}@{socket.gethostname()}{BACK_COLOR}{RESET}]{BACK_COLOR}-{RESET}" if SHOW_USER else ""
                prefix = ANSI(f"{BACK_COLOR}TS-{RESET}{instance}{venv}{user}[{MAIN_COLOR}{self.working_dir}{RESET}]{BACK_COLOR}\n"
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
                    try:
                        # Use shlex for robust parsing, respecting quotes
                        parts = shlex.split(line)
                    except ValueError:
                        # Fallback to simple split if shlex fails (e.g., unclosed quotes)
                        parts = line.split()

                    if parts and parts[-1] == '&':
                        # Rejoin the command without the final '&'
                        # This preserves command chains (&&, ||) for the background shell
                        cmd_to_run = ' '.join(parts[:-1])
                        asyncio.run(self.btm.run_bg(cmd_to_run))
                    else:
                        # It's a normal foreground command
                        self.run(line)
                print()

            except KeyboardInterrupt:
                print()


def handle_instance():
    args = sys.argv
    instance = None
    if "--instance" in args:
        try:
            instance = args.pop(args.index("--instance") + 1)
        except:
            pass

    try:
        instances = json.load(open(INSTANCE_FILE))
    except:
        instances = []
    if instance and instance not in instances:
        instances.append(instance)
        with open(INSTANCE_FILE, "w") as f:
            f.write(json.dumps(instances))
    return instance