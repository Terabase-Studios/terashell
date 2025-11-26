import os
import sys
import json
import re
from copy import deepcopy
from pathlib import Path
import subprocess
from yaspin import yaspin
import traceback

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
                    timeout=2
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
        print("""
        The preceding output is a fuzzy command representation; 
        it may be inaccurate but should somewhat work for autocomplete.
        
        If you don't see anything after the tool name then 
        the shell was unable to parse its help message."
        
        """)


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


    def parse_help(
                self,
                text: str,
                extra_headers: list[str] = None,
                extra_positional_headers: list[str] = None,
                extra_flag_headers: list[str] = None,
                extra_subcommand_headers: list[str] = None,
        ) -> dict:
            positional = []
            optional = []
            subcommands = []
            sections = {}

            lines = [line.rstrip() for line in text.splitlines()]

            # Default headers
            positional_headers = ["positional arguments"] + (extra_positional_headers or [])
            subcommand_headers = ["commands", "command"] + (extra_subcommand_headers or [])
            flag_headers = [
                               "options",
                               "optional arguments",
                               "general options",
                               "options (and corresponding environment variables)"
                           ] + (extra_flag_headers or [])

            all_headers = positional_headers + subcommand_headers + flag_headers

            # Collect lines under each header
            current_header = None

            # Escape headers for regex
            escaped_headers = [re.escape(h) for h in all_headers]

            for line in lines:
                match = re.match(rf'\s*({"|".join(escaped_headers)}):', line, flags=re.I)
                if match:
                    current_header = match.group(1).strip()
                    sections[current_header.lower()] = []
                elif current_header:
                    sections[current_header.lower()].append(line)

            # Parse positional arguments
            pos_section = next((sections[h.lower()] for h in positional_headers if h.lower() in sections), [])
            for line in pos_section:
                if "available commands" in line.lower():
                    continue
                m = re.match(r'\s*([a-zA-Z0-9_-]+)\s{2,}(.+)', line)
                if m:
                    name, _ = m.groups()
                    positional.append(name)

            # Parse subcommands
            for section_lines in sections.values():
                for line in section_lines:
                    m = re.match(r'\s{2,}([a-zA-Z0-9_-]+)\s{2,}(.+)', line)
                    if m:
                        name, desc = m.groups()
                        if "available commands" not in desc.lower():
                            subcommands.append({"name": name, "desc": desc.strip()})

            # Parse optional flags
            for header, lines in sections.items():
                if any(header.startswith(h.lower()) for h in flag_headers):
                    current_option = None
                    for line in lines:
                        line = line.rstrip()

                        m = re.match(
                            r'\s*([-\w][-\w, ]*?)'  # flag blob: one or more flags separated by comma or space
                            r'(?:\s+([A-Z0-9_<>-]+))?'  # optional metavar (captured separately)
                            r'\s*:\s*(.*)',  # description starts after the first colon
                            line
                        )

                        if m:
                            flag_blob, metavar, desc = m.groups()
                            flags = [f.strip().split(" ")[0] for f in flag_blob.split(',') if f.strip() and f.strip() != '-']
                            if flags:
                                opt = {"flags": flags, "desc": desc.strip()}
                                if metavar:
                                    opt["metavar"] = metavar
                                optional.append(opt)
                                current_option = opt
                        else:
                            # continuation line
                            if current_option and line.strip():
                                current_option["desc"] += " " + line.strip()
                            else:
                                current_option = None

            # Filter invalid optional flags and positional duplicates
            optional = [o for o in optional if o["flags"] and o["flags"][0].startswith("-")]
            positional = [p for p in positional if p not in {s["name"] for s in subcommands}]

            return {
                "positional": positional,
                "optional": optional,
                "subcommands": subcommands,
                "sections": sections
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