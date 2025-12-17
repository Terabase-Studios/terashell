import json
import os
import sys
import traceback

from yaspin import yaspin

from config import SHELL_NAME, MAP_WARN_DISABLED_FILE, HELP_FLAGS, IS_WINDOWS, INSTANCE_FILE, INSTR_FILE, \
    INDIVIDUAL_INSTR_FOR_EACH_INSTANCE
from instructions import InstructionHelper

RED = "\033[91m"
BOLD = "\033[1m"
RESET = "\033[0m"

class ShellCommands:
    def __init__(self, shell):
        self.shell = shell

        self.commands = {
            "t?": self._cmd_help,
            "f": self._cmd_critical,
            "exit": self._cmd_exit,
            "cd": self._cmd_cd,
            "map": self._cmd_map,
            "history": self._cmd_history,
            "history clear": self._cmd_history,
            "activate": self._cmd_activate,
            "deactivate": self._cmd_deactivate,
        #    "nest list": self._cmd_nest,
        #    "nest": self._cmd_nest,
            "instr add": self._cmd_instr,
            "instr remove": self._cmd_instr,
            "instr list": self._cmd_instr,
            "instr save": self._cmd_instr,
            "instr clear": self._cmd_instr,
            "instr add-last": self._cmd_instr,
            "instr": self._cmd_instr,
            "bg tasks": self._cmd_bg,
            "bg output": self._cmd_bg,
            "bg kill": self._cmd_bg,
            "bg": self._cmd_bg,
        }

        self.help_simple = {
            "t?": f"See {SHELL_NAME} commands.",
            "t? /all": f"See {SHELL_NAME} commands and subcommands.",
            "f": f"Fall back to another shell on Unix. Restart on Windows",
            "exit": f"Exit the current {SHELL_NAME} instance.",
            "map": f"Run a tool and its commands recursively and add/update autocompletion.",
            "history": "Managed stored inputs.",
            "activate": "Usage: \"activate <venv>\" Activate a Python virtual environment.",
            "deactivate": "Deactivate the current virtual environment.",
        #    "nest": "Usage: Manage shell sub-instances with different saved data",
            "instr": f"Create an instruction list within {SHELL_NAME}.",
            "bg": "Manage background tasks. Create a background task with the \'&\' arg.",
        }

        self.help = {
            "t?": f"See {SHELL_NAME} commands.",
            "t? /all": f"See {SHELL_NAME} commands and subcommands.",
            "f": f"Fall back to another shell on Unix. Restart on Windows",
            "exit": f"Exit the current {SHELL_NAME} instance.",
            "map": f"Run a tool and its commands recursively and add/update autocompletion.",
            "history": "See all previous inputs.",
            "history Clear": "Clear input history.",
            "activate": "Usage: \"activate <venv>\" Activate a Python virtual environment.",
            "deactivate": "Deactivate the current virtual environment.",
        #    "nest": "Usage: \"nest <shell>\" Open a shell sub-instance with different saved data",
        #    "nest list": "List all shell sub-instances",
            "instr add": "Add a new instruction step.",
            "instr add-last": "Save the last executed command as an instruction.",
            "instr list": "List all instruction steps.",
            "instr save": "Usage: \"instr save <file>\" Save instructions to a markdown file.",
            "instr remove": "Remove the most recent instruction step.",
            "instr clear": "Clear all instruction steps.",
            "bg tasks": "List all background tasks.",
            "bg output": "Usage: \"bg output <id>\"see a task's output",
            "bg kill": "Usage: \"bg kill <id>\"send a kill signal to a task",
        }

        self.command_list = list(self.commands.keys())

    def get_commands(self):
        return self.command_list

    def handle_command(self, line):
        parts = line.split()
        cmd = parts[0]
        args = parts[1:]

        func = self.commands.get(cmd)
        if func is None:
            return False  # tell the main shell to execute normally

        try:
            func(args)
        except Exception as e:
            if str(e) == "Forced Critical Error":
                raise e
            else:
                print(f"{SHELL_NAME} command error:")
                traceback.print_exception(e)

        return True

    # --- built-ins ---
    def _cmd_help(self, args):
        if len(args) != 0 and args[0] == "/all":
            help = self.help
        else:
            help = self.help_simple
        header = f" {SHELL_NAME} Commands:"
        print(header, "\n", "-" * len(header))
        width = max(len(cmd) for cmd in help)

        for cmd, desc in help.items():
            print(f"\t{cmd.ljust(width)} : {desc}")
        print()
        header = f" Modified commands:"
        print(header, "\n", "-" * len(header))
        print(" ", ", ".join([i for i in self.get_commands() if i not in list(help.keys())]))


    def _cmd_exit(self, args):
        self.shell.running = False

    def _cmd_cd(self, args):
        previous_dir = self.shell.working_dir
        try:
            if not args:
                # default to home directory
                new_dir = os.path.expanduser("~")
            else:
                new_dir = os.path.join(self.shell.working_dir, " ".join(args).strip("\"\'"))

            if os.path.isdir(new_dir):
                self.shell.working_dir = os.path.abspath(new_dir)
                os.chdir(self.shell.working_dir)  # update Python process cwd
            else:
                dir = " ".join(args).strip("\"\'")
                print(f"{SHELL_NAME}: cd: no such directory: {dir}")
        except Exception as e:
            self.shell.working_dir = previous_dir
            print(e)

    def _cmd_map(self, args):
        if not os.path.exists(MAP_WARN_DISABLED_FILE):
            print(f"Warning: This will execute the command and its subcommands with {HELP_FLAGS}!")
            choice = input("Proceed? [y/N] (Type 'a' to never show this again) ").strip().lower()
            if choice == "a":
                with open(MAP_WARN_DISABLED_FILE, "w") as f:
                    f.write("disabled")
            elif choice != "y":
                print("Aborted.")
                return

        # execute the original behavior
        with yaspin(text=f"Mapping: {args[0]}...", color="green", ) as spinner:
            self.shell.input_handler.indexer.help_indexer.map_tool(args[0], spinner=spinner)

    def _cmd_history(self, args):
        if not args:
            self.shell.input_handler.print_history()
        elif args[0] == "clear":
            self.shell.input_handler.clear_history()

    def _cmd_activate(self, args):
        if not args:
            print("Usage: activate <path>")
            return

        path = os.path.abspath(args[0])

        # figure out bin/Scripts
        if IS_WINDOWS:
            bindir = os.path.join(path, "Scripts")
            python_exe = os.path.join(bindir, "python.exe")
        else:
            bindir = os.path.join(path, "bin")
            python_exe = os.path.join(bindir, "python")

        if not os.path.exists(python_exe):
            print(f"{BOLD}{RED}Did not find a valid virtual environment: {path}{RESET}\n"
                  f"{RED}Could not find python in {python_exe}{RESET}\n"
                  "Please provide path to root of venv directory.\n"
                  "Example: activate venv")
            return

        # update environment
        os.environ["VIRTUAL_ENV"] = path
        os.environ["PATH"] = bindir + os.pathsep + os.environ["PATH"]

        # store it in shell instance
        self.shell.active_venv = os.path.basename(path)

        # get Python version inside venv
        try:
            import subprocess
            result = subprocess.run([python_exe, "--version"], capture_output=True, text=True)
            version =  result.stdout.strip() if result.stdout else result.stderr.strip()
            self.shell.active_venv_version = version.removeprefix("Python ") if  "3." in version else None
        except Exception as e:
            self.shell.active_venv_version = "unknown"

    def _cmd_deactivate(self, args):
        if "VIRTUAL_ENV" not in os.environ:
            print("No active venv to deactivate")
            return

        venv = os.environ.pop("VIRTUAL_ENV")

        # Remove venv bin path from PATH
        if os.name == "nt":
            bindir = os.path.join(venv, "Scripts")
        else:
            bindir = os.path.join(venv, "bin")

        paths = os.environ["PATH"].split(os.pathsep)
        paths = [p for p in paths if p != bindir]
        os.environ["PATH"] = os.pathsep.join(paths)

        self.shell.active_venv = None

    def _cmd_nest(self, args):
        if not args:
            print("Usage: nest <shell>")
            return

        if " ".join(args).strip() == "list":
            try:
                instances = json.load(open(INSTANCE_FILE))
            except Exception:
                return
            for i, instance in enumerate(instances):
                print(f"{i + 1}: {instance}")
            return

        instance = " ".join(args)
        self.shell.run(f"{sys.executable} {self.shell.shell_file} --instance {instance}")

    def _cmd_instr(self, args):
        if not args:
            print("Usage: instr <cmd>")
            return
        sub = args[0]
        if not hasattr(self, "instr_helper"):
            from shell import instance_file
            file = instance_file(self.shell.instance, INSTR_FILE) if INDIVIDUAL_INSTR_FOR_EACH_INSTANCE else INSTR_FILE
            self.instr_helper = InstructionHelper(file)

        if sub == "add":
            text = " ".join(args[1:])
            if text:
                self.instr_helper.add(text)
                print(f"Added step: {text}")

        if sub == "remove":
            text = self.instr_helper.remove()
            print(f"Removed step: {text}")

        elif sub == "list":
            print(self.instr_helper.list())

        elif sub == "save":
            filename = args[1]
            filename = os.path.expanduser(os.path.expandvars(filename))
            if not os.path.isabs(filename):
                filename = os.path.join(self.shell.working_dir, filename)
            filename = os.path.normpath(filename)
            success = self.instr_helper.save_markdown(filename)
            if success:
                print(f"Saved to {filename}")
            else:
                print(f"Failed to save to {filename}")

        elif sub == "clear":
            self.instr_helper.clear()
            print("Cleared instructions")

        elif sub == "add-last":
            last = self.shell.input_handler.get_history()[-1]

            if not last:
                print("No last command to save")
            else:
                last = f"run: {last}"
                self.instr_helper.add(f"{last}\n")
                print(f"Saved last command as instruction:\n{last}")

    def _cmd_critical(self, args):
        main = sys.modules["__main__"]
        main.times_critical = 999999
        main.warn = False
        raise Exception("Forced Critical Error")

    def _cmd_bg(self, args):
        if len(args) == 0:
            print("Usage: bg <command>")
            return
        command = args[0]
        args = args[1:]
        match command:
            case "output":
                if len(args) != 1 or not args[0].isdigit():
                    print("Usage: bg output <id>")
                    return
                self.shell.btm.show_output(int(args[0]))
            case "kill":
                if len(args) != 1 or not args[0].isdigit():
                    print("Usage: kill <id>")
                    return
                self.shell.btm.kill(int(args[0]))
            case "tasks":
                self.shell.btm.task_table()
            case _:
                print("Usage: bg <command>")