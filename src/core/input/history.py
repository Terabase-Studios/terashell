import json
import os
from collections import defaultdict

from prompt_toolkit.history import FileHistory

from config import IGNORE_SPACE


class ShellFileHistory(FileHistory):
    """
    Stores command history in standard prompt_toolkit format.
    Metadata stored separately.
    """

    def __init__(self, shell, filename):
        super().__init__(filename)
        self.shell = shell
        self.meta_filename = filename + ".meta"
        self.cmd_meta: dict[str, list[dict]] = defaultdict(list)
        self.rebuild_cmd_meta()
        # print(self.cmd_meta)

    def set_last_exit_code(self, value: int):
        """
        Sets the 'exit_code' field for the last command to the given value.
        """
        if not os.path.exists(self.filename) or not os.path.exists(self.meta_filename):
            return

        # Read all metadata lines
        with open(self.meta_filename, "r", encoding="utf-8") as f:
            meta_lines = f.readlines()

        if not meta_lines:
            return

        # Update last line
        try:
            last_meta = json.loads(meta_lines[-1])
            last_meta['exit_codes'] = value
            meta_lines[-1] = json.dumps(last_meta) + "\n"
        except Exception:
            return

        # Write back all metadata
        with open(self.meta_filename, "w", encoding="utf-8") as f:
            f.writelines(meta_lines)

        # Update in-memory cmd_meta
        last_cmd = None
        # Find last command by reading history file
        with open(self.filename, "r", encoding="utf-8") as f:
            for line in f:
                line = line.rstrip("\n")
                if line.startswith("+"):
                    last_cmd = line[1:]

        if last_cmd and self.cmd_meta.get(last_cmd):
            self.cmd_meta[last_cmd][-1]['exit_codes'] = value

    def rebuild_cmd_meta(self):
        self.cmd_meta.clear()
        if not os.path.exists(self.filename) or not os.path.exists(self.meta_filename):
            return

        try:
            with open(self.filename, "r", encoding="utf-8") as f_cmd, \
                    open(self.meta_filename, "r", encoding="utf-8") as f_meta:
                for line_cmd, line_meta in zip(f_cmd, f_meta):
                    cmd = line_cmd.rstrip("\n").lstrip("+")
                    try:
                        meta = json.loads(line_meta)
                    except Exception:
                        meta = {}
                    self.cmd_meta[cmd].append(meta)
        except Exception:
            pass

    def append_string(self, text):
        if not text or (IGNORE_SPACE and text.startswith(" ")):
            return

        import json, time
        cwd = getattr(self.shell, "working_dir", None)
        venv = getattr(self.shell, "active_venv", None)
        meta = {"cwd": cwd, "venv": venv, "ts": time.time(), "exit_codes": None}

        # Append metadata
        with open(self.meta_filename, "a", encoding="utf-8") as f:
            f.write(json.dumps(meta) + "\n")

        # Update in-memory
        self.cmd_meta[text].append(meta)
        super().append_string(text)
