import os
import sys
import json
import re
from pathlib import Path

class CommandIndexer:
    BUILTINS = {
        "win": ["cd", "dir", "echo", "type", "copy", "move", "del", "cls"],
        "unix": ["cd", "ls", "echo", "cat", "cp", "mv", "rm", "clear"]
    }

    ARG_HINTS = {
        # Optional static argument hints
        "ls": ["-a", "-l", "-h", "--color"],
        "dir": ["/A", "/B", "/S"],
        "copy": ["/Y", "/V"],
        "rm": ["-f", "-r", "-i"]
    }

    def __init__(self):
        self.commands = self._get_all_commands()
        self.index = self._build_index()

    def _get_all_commands(self):
        paths = os.environ.get("PATH", "").split(os.pathsep)
        commands = set()

        if sys.platform.startswith("win"):
            exts = os.environ.get("PATHEXT", ".EXE;.BAT;.CMD;.COM").split(";")
            exts = [e.lower() for e in exts]
            for path in paths:
                if not os.path.isdir(path):
                    continue
                for f in os.listdir(path):
                    full_path = os.path.join(path, f)
                    _, ext = os.path.splitext(f)
                    if os.path.isfile(full_path) and ext.lower() in exts:
                        commands.add(os.path.splitext(f)[0])
            commands.update(self.BUILTINS["win"])
        else:
            for path in paths:
                if not os.path.isdir(path):
                    continue
                for f in os.listdir(path):
                    full_path = os.path.join(path, f)
                    if os.path.isfile(full_path) and os.access(full_path, os.X_OK):
                        commands.add(f)
            commands.update(self.BUILTINS["unix"])

        return sorted(commands)

    def _build_index(self):
        index = {}
        for cmd in self.commands:
            index[cmd] = self.ARG_HINTS.get(cmd, [])
        return index

    def get_commands(self):
        """Return list of all commands"""
        return self.commands

    def get_index(self):
        """Return command -> argument list mapping"""
        return self.index

    def get_args(self, command):
        """Return argument hints for a given command"""
        return self.index.get(command, [])


class HelpIndexer:
    def __init__(self, json_path="terashell_help.json"):
        self.json_path = Path(json_path)
        self.data = {}

        if self.json_path.exists():
            try:
                self.data = json.loads(self.json_path.read_text())
            except Exception:
                self.data = {}

    # ============================================================
    # Core: Parse help text (your existing logic, embedded cleanly)
    # ============================================================
    def parse_help(self, text):
        positional = []
        optional = []
        subcommands = []

        lines = [ln.rstrip() for ln in text.splitlines()]

        sections = {}
        current = None
        for ln in lines:
            header = re.match(
                r'\s*(positional arguments|options|optional arguments|arguments):',
                ln,
                flags=re.I
            )
            if header:
                current = header.group(1).lower()
                sections[current] = []
            elif current:
                sections[current].append(ln)

        # positional arguments
        pos_section = sections.get("positional arguments", []) or sections.get("arguments", [])
        for ln in pos_section:
            m = re.match(r'\s*([a-zA-Z0-9_-]+)\s{2,}(.+)', ln)
            if m:
                name, desc = m.groups()
                positional.append(name)

        # subcommands under COMMAND
        in_commands = False
        for ln in pos_section:
            if ln.strip().startswith("COMMAND"):
                in_commands = True
                continue
            if in_commands:
                m = re.match(r'\s{4,}([a-zA-Z0-9_-]+)\s{2,}(.+)', ln)
                if m:
                    subcommands.append({
                        'name': m.group(1),
                        'desc': m.group(2)
                    })
                else:
                    if ln.strip():
                        continue
                    break

        # options
        opt_section = sections.get("options", []) or sections.get("optional arguments", [])
        for ln in opt_section:
            m = re.match(
                r'\s*([-\w]+(?:,\s*[-\w]+)*)(?:\s+([A-Z0-9_<>]+))?\s{2,}(.*)',
                ln
            )
            if not m:
                continue

            flag_blob, metavar, desc = m.groups()
            flags = [f.strip() for f in flag_blob.split(',')]

            if metavar:
                flags[-1] += " " + metavar

            optional.append({
                'flags': flags,
                'desc': desc.strip()
            })

        return {
            "positional": positional,
            "optional": optional,
            "subcommands": subcommands
        }

    # ============================================================
    # Store or update help data
    # ============================================================
    def update_command(self, tool_name, help_text):
        parsed = self.parse_help(help_text)

        # Detect subcommand help based on tool syntax
        # Example tool_name: "fts.send"
        is_sub = "." in tool_name

        if is_sub:
            # Update only this subcommand entry
            self.data[tool_name] = parsed
            self._save()
            return

        # Parent command update
        parent = parsed

        # Merge with existing to avoid wiping known subcommands
        if tool_name not in self.data:
            self.data[tool_name] = parent
        else:
            existing = self.data[tool_name]

            # Merge optional flags
            # (avoid duplicates, handle new ones)
            opt_map = {tuple(o["flags"]): o for o in existing["optional"]}
            for o in parent["optional"]:
                opt_map[tuple(o["flags"])] = o
            existing["optional"] = list(opt_map.values())

            # Merge subcommands
            sub_map = {s["name"]: s for s in existing["subcommands"]}
            for s in parent["subcommands"]:
                if s["name"] not in sub_map:
                    sub_map[s["name"]] = s
            existing["subcommands"] = list(sub_map.values())

            # Positional rarely matters for root commands → ignore

    def _save(self):
        self.json_path.write_text(json.dumps(self.data, indent=2))

    # ============================================================
    # Suggestion engine
    # ============================================================
    def get_suggested(self, line):
        tokens = line.strip().split()
        if not tokens:
            return {"command": None, "suggestions": []}

        tool = tokens[0]

        # No entry at all
        if tool not in self.data:
            return {"command": tool, "suggestions": [], "error": "Unknown command"}

        base_entry = self.data[tool]
        entry = base_entry

        typed_sub = None
        if len(tokens) > 1:
            # Detect subcommand
            candidate = tokens[1]
            for sub in base_entry["subcommands"]:
                if candidate == sub["name"]:
                    typed_sub = candidate
                    break

        # If subcommand help exists → switch to it
        if typed_sub and f"{tool}.{typed_sub}" in self.data:
            entry = self.data[f"{tool}.{typed_sub}"]

        suggestions = []

        # If no subcommand typed yet → suggest subcommands
        if typed_sub is None:
            for s in base_entry["subcommands"]:
                suggestions.append(s["name"])

        # Always suggest flags for the current entry
        for opt in entry["optional"]:
            for flag in opt["flags"]:
                suggestions.append(flag)

        # Prefix filtering
        pref = tokens[-1]
        suggestions = [s for s in suggestions if s.startswith(pref)]

        return {
            "command": tool,
            "subcommand": typed_sub,
            "suggestions": sorted(set(suggestions))
        }


# ============================================================
# Example use
# ============================================================
if __name__ == "__main__":
    db = HelpIndexer()

    helptext = """

usage: fts send [-h] [-q | -v] [-log LOGFILE] [-n NAME] [-p PORT] [-l LIMIT] [--nocompress] [--progress] path ip

positional arguments:
  path                  path to the file being sent
  ip                    server IP to send to

options:
  -h, --help            show this help message and exit
  -q, --quiet           suppress non-critical output
  -v, --verbose         enable verbose debug output
  -log, --logfile LOGFILE
                        log output to a file
  -n, --name NAME       send file with this name
  -p, --port PORT       override port used (change to port an open server is running on)
  -l, --limit LIMIT     max sending speed (e.g. 500KB, 2MB, 1GB)
  --nocompress          Skip compression (use if fts is compressing an already compressed file)
  --progress            show progress bar for the transfer
"""

    db.update_command("fts", helptext)

    print(db.get_suggested("fts send "))
