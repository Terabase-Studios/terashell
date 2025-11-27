import os
import traceback

from config import SHELL_NAME, MAP_WARN_DISABLED_FILE, HELP_FLAGS


class ShellCommands:
    def __init__(self, shell):
        self.shell = shell

        self.commands = {
            "t?": self._cmd_help,
            "exit": self._cmd_exit,
            "cd": self._cmd_cd,
            "map": self._cmd_map,
            "history": self._cmd_history,
            "history clear": self._cmd_history,
        }

        self.help = {
            "t?": f"See {SHELL_NAME} commands.",
            "exit": f"Exit {SHELL_NAME} and return to original command line.",
            "map": f"Run a tool and its commands recursively and add/update autocompletion.",
            "history": "See all previous inputs.",
            "history clear": "Clear input history.",
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
            print(f"{SHELL_NAME} command error:\n{traceback.format_exc(e)}")

        return True

    # --- built-ins ---
    def _cmd_help(self, args):
        header = f" {SHELL_NAME} Commands:"
        print(header, "\n", "-" * len(header))
        width = max(len(cmd) for cmd in self.help)

        for cmd, desc in self.help.items():
            print(f"\t{cmd.ljust(width)} : {desc}")
        print()
        header = f" Modified commands:"
        print(header, "\n", "-" * len(header))
        print("\t", ", ".join([i for i in self.get_commands() if i not in list(self.help.keys())]))


    def _cmd_exit(self, args):
        self.shell.running = False

    def _cmd_cd(self, args):
        if not args:
            # default to home directory
            new_dir = os.path.expanduser("~")
        else:
            new_dir = os.path.join(self.shell.working_dir, args[0])

        if os.path.isdir(new_dir):
            self.shell.working_dir = os.path.abspath(new_dir)
            os.chdir(self.shell.working_dir)  # update Python process cwd
        else:
            print(f"{SHELL_NAME}: cd: no such directory: {args[0]}")

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
        self.shell.input_handler.indexer.help_indexer.map_tool(args[0])

    def _cmd_history(self, args):
        if not args:
            self.shell.input_handler.print_history()
        elif args[0] == "clear":
            self.shell.input_handler.clear_history()
