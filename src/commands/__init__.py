import json
import os
import sys
import traceback
from dataclasses import dataclass, field
from typing import Callable

from yaspin import yaspin

from commands.instructions import InstructionHelper
from config import SHELL_NAME, MAP_WARN_DISABLED_FILE, HELP_FLAGS, IS_WINDOWS, INSTANCE_FILE, \
    INDIVIDUAL_INSTR_FOR_EACH_INSTANCE, INSTR_FILE

RED = "\033[91m"
BOLD = "\033[1m"
RESET = "\033[0m"


@dataclass
class CommandNode:
    handler: Callable | None = None
    help: str | None = None
    simple_help: str | None = None
    children: dict[str, "CommandNode"] = field(default_factory=dict)


class ShellCommands:
    def __init__(self, shell):
        self.shell = shell

        self.command_tree = CommandNode()
        self._register_commands()
        self._refresh_indexes()

    def _register_commands(self):
        self.register("t?", self._cmd_help, f"See {SHELL_NAME} commands.")
        self.register("t? /all", help=f"See {SHELL_NAME} commands and subcommands.")
        self.register("f", self._cmd_critical, "Fall back to another shell on Unix. Restart on Windows")
        self.register("exit", self._cmd_exit, f"Exit the current {SHELL_NAME} instance.")
        self.register("cd", self._cmd_cd)
        self.register("map", self._cmd_map, "Run a tool and its commands recursively and add/update autocompletion.")
        self.register("ai", self._cmd_ai, "Connect to the configured AI service and enable AI tools.")
        self.register("history", self._cmd_history, "See all previous inputs.", simple_help="Managed stored inputs.")
        self.register("history clear", help="Clear input history.")
        self.register("activate", self._cmd_activate, 'Usage: "activate <venv>" Activate a Python virtual environment.')
        self.register("deactivate", self._cmd_deactivate, "Deactivate the current virtual environment.")
        # self.register("nest", self._cmd_nest, 'Usage: "nest <shell>" Open a shell sub-instance with different saved data')
        # self.register("nest list", help="List all shell sub-instances")
        self.register("instr", self._cmd_instr, f"Create an instruction list within {SHELL_NAME}.")
        self.register("instr add", help="Add a new instruction step.")
        self.register("instr add-last", help="Save the last executed command as an instruction.")
        self.register("instr list", help="List all instruction steps.")
        self.register("instr save", help='Usage: "instr save <file>" Save instructions to a markdown file.')
        self.register("instr remove", help="Remove the most recent instruction step.")
        self.register("instr clear", help="Clear all instruction steps.")
        self.register("bg", self._cmd_bg, "Manage background tasks. Create a background task with the '&' arg.")
        self.register("bg tasks", help="List all background tasks.")
        self.register("bg output", help="Usage: \"bg output <id>\" see a task's output")
        self.register("bg kill", help="Usage: \"bg kill <id>\" send a kill signal to a task")

    def register(self, command, handler=None, help=None, simple_help=None):
        node = self.command_tree
        for part in command.split():
            node = node.children.setdefault(part, CommandNode())
        node.handler = handler or node.handler
        node.help = help if help is not None else node.help
        node.simple_help = simple_help if simple_help is not None else node.simple_help
        self._refresh_indexes()

    def _refresh_indexes(self):
        self.commands = self._flatten_handlers()
        self.help_simple = self._flatten_help(simple=True)
        self.help = self._flatten_help(simple=False)
        self.command_list = list(self._flatten_command_paths())

    def _flatten_command_paths(self):
        yield from self._walk_command_paths(include_all=True)

    def _flatten_handlers(self):
        handlers = {}
        for path, node in self._walk_nodes():
            if node.handler is not None:
                handlers[path] = node.handler
        return handlers

    def _flatten_help(self, simple):
        help_items = {}
        for path, node in self._walk_nodes():
            description = node.simple_help if simple else node.help
            if description is None and simple and node.handler is not None:
                description = node.help
            if description is not None:
                help_items[path] = description
        return help_items

    def _walk_command_paths(self, include_all=False):
        for path, node in self._walk_nodes():
            if include_all or node.handler is not None:
                yield path

    def _walk_nodes(self):
        def walk(node, parts):
            for name, child in node.children.items():
                child_parts = parts + [name]
                yield " ".join(child_parts), child
                yield from walk(child, child_parts)

        yield from walk(self.command_tree, [])

    def _resolve_command(self, parts):
        node = self.command_tree
        best_handler = None
        best_depth = 0

        for index, part in enumerate(parts):
            node = node.children.get(part)
            if node is None:
                break
            if node.handler is not None:
                best_handler = node.handler
                best_depth = index + 1

        if best_handler is None:
            return None, []

        return best_handler, parts[best_depth:]

    def get_commands(self):
        return self.command_list

    def handle_command(self, line):
        parts = line.split()
        if not parts:
            return False

        func, args = self._resolve_command(parts)
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
        #header = f" Modified commands:"
        #print(header, "\n", "-" * len(header))
        #print(" ", ", ".join([i for i in self.get_commands() if i not in list(help.keys())]))

    def _cmd_exit(self, args):
        self.shell.running = False

    def _cmd_cd(self, args):
        previous_dir = self.shell.working_dir
        try:
            if not args:
                # default to home directory
                new_dir = os.path.expanduser("~")
            else:
                path_arg = " ".join(args).strip("\"\'")
                # Expand user (~), and resolve relative paths (., ..)
                # This handles absolute and relative paths correctly.
                new_dir = os.path.abspath(os.path.expanduser(path_arg))

            if os.path.isdir(new_dir):
                self.shell.working_dir = new_dir
                os.chdir(self.shell.working_dir)  # update Python process cwd
            else:
                dir_name = " ".join(args).strip("\"\'")
                print(f"{SHELL_NAME}: cd: no such directory: {dir_name}")
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

    def _cmd_ai(self, args):
        import ai
        ai.init()

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
            version = result.stdout.strip() if result.stdout else result.stderr.strip()
            self.shell.active_venv_version = version.removeprefix("Python ") if "3." in version else None
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
        self.shell.active_venv_version = None

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
            from core.shell import instance_file
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
        if command == "output":
            if len(args) != 1 or not args[0].isdigit():
                print("Usage: bg output <id>")
                return
            self.shell.btm.show_output(int(args[0]))
        elif command == "kill":
            if len(args) != 1 or not args[0].isdigit():
                print("Usage: kill <id>")
                return
            self.shell.btm.kill(int(args[0]))
        elif command == "tasks":
            self.shell.btm.task_table()
        else:
            print("Usage: bg <command>")
