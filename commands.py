import os

from config import SHELL_NAME


class ShellCommands:
    def __init__(self, shell):
        self.shell = shell

        self.commands = {
            "t?": self._cmd_help,
            "exit": self._cmd_exit,
            "cd": self._cmd_cd,
            "map": self._cmd_map,
        }

        self.help = {
            "t?": f"See {SHELL_NAME} commands",
            "exit": f"exit {SHELL_NAME} and return to original command line",
            "map": f"run a tool and its commands recursively and add/update autocompletion",
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
            print(f"{SHELL_NAME} command error: {e}")

        return True

    # --- built-ins ---
    def _cmd_help(self, args):
        header = f"{SHELL_NAME} Commands:"
        print(header, "\n", "-" * len(header))
        for command in self.help:
            print(f"\t{command}: {self.help[command]}")
        print()
        header = f"Modified commands:"
        print(header, "\n", "-" * len(header))
        print(", ".join([i for i in self.get_commands() if i not in list(self.help.keys())]))


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
        self.shell.input_handler.indexer.help_indexer.map_tool(args[0])