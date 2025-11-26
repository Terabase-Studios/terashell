import os
import sys
import json
import re
from copy import deepcopy
from pathlib import Path
import subprocess
from yaspin import yaspin


from config import HELP_FILE, HELP_FLAGS, PATH_INDEXING, EXTRA_SUB_COMMAND_HEADERS, EXTRA_FLAG_HEADERS, EXTRA_POSITIONAL_HEADERS


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
        self.help_indexer = HelpIndexer()

    def _get_all_commands(self):
        if not PATH_INDEXING:
            return []
        with yaspin(text="Indexing path", color="yellow") as spinner:
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

    def __init__(self, json_path=HELP_FILE):
        self.json_path = Path(json_path)
        self.data = {}
        if self.json_path.exists():
            try:
                self.data = json.loads(self.json_path.read_text())
            except Exception:
                self.data = {}

    # ============================================================
    # Auto-generate help by running the tool
    # ============================================================
    def map_tool(self, tool_name, base_cmd=None, recursive_depth=1, _depth=0, main=True):
        """
        Runs the tool with multiple help flags and harvests its help text.
        Recursively processes subcommands.
        """
        if main:
            copy_tool_name = tool_name
            dict_copy = deepcopy(self.data)
            for entry in dict_copy:
                if entry.startswith(copy_tool_name):
                    del self.data[entry]
            tool_name = copy_tool_name

        if not base_cmd:
            base_cmd = [tool_name]

        collected_help = ""
        for flag in HELP_FLAGS:
            try:
                result = subprocess.run(
                    base_cmd + [flag],
                    capture_output=True,
                    text=True,
                    timeout=3
                )
                if result.returncode == 0 or result.stdout:
                    collected_help = result.stdout
                    break
            except FileNotFoundError:
                result = subprocess.run(
                    base_cmd + [flag],
                    shell=True,
                    stdout=sys.stdout,
                    stderr=sys.stderr,
                    env={**os.environ, "FORCE_COLOR": "1"},
                )
                return
            except Exception as e:
                import traceback
                print(traceback.format_exception(e))
                continue  # skip flags that fail

        if not collected_help:
            print(f"Unable to find help for \"{tool_name}\"")
            return  # no help found

        # Update JSON with parsed help
        full_key = ".".join(base_cmd)
        self.update_command(full_key, collected_help)

        entry = self.data.get(full_key)
        if not entry:
            print(f"Unable to update autocomplete for \"{tool_name}\"")
            return  # no help found

        if recursive_depth and _depth >= recursive_depth:
            return

        # Recursively process subcommands
        for sub in entry.get("subcommands", []):
            sub_name = sub["name"]
            sub_base_cmd = base_cmd + [sub_name]
            # only recurse if we haven't indexed it yet
            full_sub_key = ".".join(sub_base_cmd)
            if full_sub_key not in self.data:
                self.map_tool(tool_name, sub_base_cmd, recursive_depth=recursive_depth, _depth=_depth + 1, main=False)

        self.print_help(tool_name, recursive_depth=recursive_depth)
        print()
        print("The preceding output is a fuzzy command representation; it may be inaccurate but should work for autocomplete.")

    def print_help(self, key, indent=0, recursive_depth=1, _depth=0):
        """
        Pretty-print a help entry from the autocomplete JSON.
        data: dict containing all entries
        key: the specific command to print
        """
        if key not in self.data:
            print("[DISPLAY ERROR] Command not found:", key)
            return

        entry = self.data[key]
        spacer = "  " * indent
        name = key.split(".")[-1]

        # Print command header
        print(f"{spacer}{name}:\n{spacer}{"-"*(len(name)+1)}")

        # Positional arguments
        if entry.get("positional"):
            print(f"{spacer}Positional arguments:")
            for p in entry["positional"]:
                print(f"{spacer}  {p}")

        # Optional flags
        if entry.get("optional"):
            print(f"{spacer}Options:")
            for opt in entry["optional"]:
                flags = ", ".join(opt["flags"])
                desc = opt.get("desc", "")
                print(f"{spacer}  {flags:<20} {desc}")


        if entry.get("subcommands"):
            print(f"{spacer}Subcommands:")
            for sub in entry["subcommands"]:
                sub_name = sub["name"]
                sub_desc = sub.get("desc", "")
                print(f"{spacer}  {sub_name:<15} {sub_desc}")

        # Subcommands
        if _depth >= recursive_depth:
            return

        # Recurse into subcommands if they have their own entries
        for sub in entry.get("subcommands", []):
            sub_key = f"{key}.{sub['name']}"
            if sub_key in self.data:
                print()
                self.print_help(sub_key, indent=indent + 1, recursive_depth=recursive_depth, _depth=_depth + 1)



    # ============================================================
    # Core: Parse help text (your existing logic, embedded cleanly)
    # ============================================================
    def parse_help(self, text, extra_headers=None, extra_positional_headers=EXTRA_POSITIONAL_HEADERS, extra_flag_headers=EXTRA_FLAG_HEADERS, extra_subcommand_headers=EXTRA_SUB_COMMAND_HEADERS):
        """
        Parse help text into positional, optional, subcommands, and extra headers.
        extra_headers: list of additional section headers to capture
        """

        positional = []
        optional = []
        subcommands = []
        other_sections = {}

        lines = [ln.rstrip() for ln in text.splitlines()]

        # Default headers
        positional_headers = ["positional arguments"]
        if extra_subcommand_headers:
            positional_headers.extend(extra_positional_headers)

        subcommand_headers = ["commands", "command"]
        if extra_subcommand_headers:
            subcommand_headers.extend(extra_subcommand_headers)

        flag_headers = ["options", "optional arguments", "general options", "options (and corresponding environment variables)"]
        if extra_flag_headers:
            flag_headers.extend(extra_flag_headers)

        headers = positional_headers + subcommand_headers + flag_headers


        current = None
        for ln in lines:
            header = re.match(
                rf'\s*({"|".join(headers)}):',
                ln,
                flags=re.I
            )
            if header:
                current = header.group(1).strip()
                other_sections[current] = []
            elif current:
                other_sections[current].append(ln)

        # find the first positional header that exists in other_sections
        pos_section = None
        for header in positional_headers:
            if header.lower() in other_sections:
                pos_section = other_sections[header.lower()]
                break

        # parse the positional arguments
        if pos_section:
            for ln in pos_section:
                # skip lines that are like 'COMMAND   available commands:'
                if "available commands" in ln.lower():
                    continue
                m = re.match(r'\s*([a-zA-Z0-9_-]+)\s{2,}(.+)', ln)
                if m:
                    name, desc = m.groups()
                    positional.append(name)

        # collect subcommands from known headers + lines starting with spaces + name + description
        for section_name, lines in other_sections.items():
            for ln in lines:
                # match lines that look like subcommands (e.g., "  send   connect to...")
                m = re.match(r'\s{2,}([a-zA-Z0-9_-]+)\s{2,}(.+)', ln)
                if m:
                    name, desc = m.groups()
                    # ignore lines that are just the 'available commands:' text
                    if "available commands" not in desc.lower():
                        subcommands.append({"name": name, "desc": desc})

        # options
        for section_name, lines in other_sections.items():
            # match if the section_name starts with a known flag header (case-insensitive)
            if any(section_name.lower().startswith(hdr.lower()) for hdr in flag_headers):
                for ln in lines:
                    m = re.match(
                        r'\s*([-\w]+(?:,\s*[-\w]+)*)(?:\s+([A-Z0-9_<>]+))?\s{2,}(.*)',
                        ln
                    )
                    if not m:
                        continue
                    flag_blob, metavar, desc = m.groups()
                    flags = [f.strip() for f in flag_blob.split(',')]
                    optional.append({"flags": flags, "desc": desc.strip()})

        optional = [i for i in optional if i["flags"][0].startswith("-")]
        subcommand_names = [z['name'] for z in subcommands]
        positional = [x for x in positional if x not in subcommand_names]

        return {
            "positional": positional,
            "optional": optional,
            "subcommands": subcommands,
            "sections": other_sections  # extra headers are kept here
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

        self._save()
        return self.data[tool_name]

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

        if tool not in self.data:
            return {"command": tool, "suggestions": [], "error": "Unknown command"}

        entry = self.data[tool]
        typed_sub = None

        # Detect subcommand
        if len(tokens) > 1:
            candidate = tokens[1]
            for sub in entry.get("subcommands", []):
                if candidate == sub["name"]:
                    typed_sub = candidate
                    break

        # Switch to subcommand context if exists
        if typed_sub and f"{tool}.{typed_sub}" in self.data:
            entry = self.data[f"{tool}.{typed_sub}"]

        suggestions = []

        # Suggest subcommands if none typed yet
        if typed_sub is None:
            suggestions.extend([s["name"] for s in entry.get("subcommands", [])])

        # Suggest flags while keeping short flags behind long flags
        for opt in entry.get("optional", []):
            flags = opt["flags"]
            if len(flags) == 2 and flags[0].startswith("--") and flags[1].startswith("-"):
                # long flag first, short flag after
                suggestions.extend(flags)
            else:
                suggestions.extend(flags)

        # add positional arguments or subcommands
        suggestions.extend(i["name"] for i in entry.get("subcommands", []) if i["name"] not in line.split())

        # Prefix filtering
        pref = tokens[-1]
        if pref and pref != typed_sub and pref != tool:
            suggestions = list(set([s for s in suggestions if s.startswith(pref)]))

        return {
            "command": tool,
            "subcommand": typed_sub,
            "suggestions": suggestions
        }