import json
import os
import re
import subprocess
import sys
import traceback
from copy import deepcopy
from itertools import combinations
from pathlib import Path

from yaspin import yaspin

from config import HELP_FILE, HELP_FLAGS, PATH_INDEXING, ONE_FLAG_PER_GROUP, IS_UNIX


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

    def __init__(self, index_path=True):
        self.index_path = index_path and PATH_INDEXING
        self.commands = self._get_all_commands()
        self.index = self._build_index()
        self.help_indexer = HelpIndexer()

    def _get_all_commands(self):
        if not self.index_path:
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

    def _get_help(self, base_cmd, flag):
        cmd_list = base_cmd + [flag]

        if IS_UNIX:
            # Use pty to emulate a terminal for programs that detect TTY
            import pty
            master_fd, slave_fd = pty.openpty()
            try:
                proc = subprocess.Popen(
                    cmd_list,
                    stdout=slave_fd,
                    stderr=subprocess.STDOUT,
                    env={**os.environ, "FORCE_COLOR": "1"},
                    text=True
                )
                os.close(slave_fd)
                output = b""
                while True:
                    try:
                        data = os.read(master_fd, 1024)
                        if not data:
                            break
                        output += data
                    except OSError:
                        break
                proc.wait(timeout=2)
                return output.decode(errors="ignore")
            finally:
                os.close(master_fd)

        else:
            # Windows or other non-UNIX systems
            result = subprocess.run(
                cmd_list,
                capture_output=True,
                text=True,
                timeout=2
            )
            return result.stdout if result.stdout else None



    # ============================================================
    # Auto-generate help by running the tool
    # ============================================================
    def map_tool(self, tool_name, base_cmd=None, recursive_depth=4, main=True, previous_help=None):
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

        if recursive_depth and len(base_cmd) >= recursive_depth:
            return None, None

        collected_help = ""
        for flag in HELP_FLAGS:
            try:
                collected_help = self._get_help(base_cmd, flag)
                if collected_help and len(collected_help.splitlines()) > 5:
                    break
            except FileNotFoundError:
                result = subprocess.run(
                    base_cmd + [flag],
                    shell=True,
                    stdout=sys.stdout,
                    stderr=sys.stderr,
                    env={**os.environ, "FORCE_COLOR": "1"},
                )
                return None, None
            except Exception as e:
                print(traceback.format_exception(e))
                continue  # skip flags that fail

        if (not collected_help) or len(collected_help.splitlines()) < 1:
            if main:
                print(f"Unable to find help for \"{tool_name}\"\nThe tool did not return any help text.")
            return None, None # no help found


        if not collected_help or len(collected_help.splitlines()) <= 5 or previous_help == collected_help:
            return None, None



        dict = self._parse_help(collected_help)
        potential_commands = list(set(dict.get("potential_subcommands", [])))
        options = dict.get("optional", [])

        main_branch = {"command": base_cmd, "options": options, "subcommands": [], "branches": {}}
        commands = []
        #print(potential_commands)
        for command in potential_commands:
            if command in base_cmd:
                continue
            branch, subcommand_help = self.map_tool(command, base_cmd=base_cmd+[command], recursive_depth=recursive_depth, main=False, previous_help=collected_help)
            if branch and collected_help != subcommand_help:
                main_branch["branches"][command] = branch
                commands.append(command)

        main_branch["subcommands"] = commands

        if not main:
            return main_branch, collected_help

        def print_block(text):
            # Normalize text to lines
            lines = text.rstrip("\n").split("\n")
            width = max(len(line) for line in lines)
            border = "-" * width

            print(border)
            for line in lines:
                print(line)
            print(border)

        print("\n")

        if commands or options:
            content = []
            content.append("Command Tree:\n")
            display_branch = deepcopy(main_branch)
            display_branch["command"] = base_cmd + ["+"]
            content.append(
                self.get_ascii_tree(display_branch))  # you need a method returning the tree as a string
            block_text = "\n".join(content)

            print_block(block_text)
            print("\nThe above output is a fuzzy command representation\nand may not be accurate or complete.")
            self.data[tool_name] = main_branch
            self._save()
        else:
            print_block("Main Help Page Found:\n\n" + collected_help.rstrip("\n"))

            print("\nThe shell could not parse the above output")
        return main_branch, collected_help

    def get_ascii_tree(self, node, prefix="", is_last=True):
        lines = []

        # Build connector
        connector = "└── " if is_last else "├── "

        cmd_path = " ".join(node.get("command", []))
        options = node.get("options")
        if options:
            opts_str = ", ".join([", ".join(opt) for opt in options])
            line = f"{cmd_path} [{opts_str}]"
        else:
            line = cmd_path

        if prefix:
            lines.append(f"{prefix}{connector}{line}")
        else:
            lines.append(line)

        child_prefix = prefix + ("    " if is_last else "│   ")

        branches = list(node.get("branches", {}).values())
        for i, child in enumerate(branches):
            child_str = self.get_ascii_tree(
                child,
                prefix=child_prefix,
                is_last=(i == len(branches) - 1)
            )
            lines.append(child_str)

        return "\n".join(lines)

    def _parse_subcommands(self, text: str) -> list:
        def flatten_set(text, indent="    "):
            # Extract the contents inside the braces
            match = re.search(r'\{(.*)\}', text, re.DOTALL)
            if not match:
                return text  # no braces found, return original

            content = match.group(1)

            # Split by | and remove whitespace/newlines
            items = [item.strip() for item in content.split('|') if item.strip()]

            # Reconstruct as an indented list
            flattened = "\n".join(f"{indent}{item}" for item in items).replace("{", "\n\t")
            return flattened + text

        subcommands = []

        # Format help:
        lines = []

        for raw_line in flatten_set(text).splitlines():
            cleaned_line = re.sub(r'[^\x20-\x7E]', '', raw_line)
            no_meta_line = cleaned_line.replace("=", " ").replace(":", " ")
            lines.append(no_meta_line)

        for line in lines:
            if line.startswith(" "):
                no_tab_line = line.replace("\t", "").strip(" ")
                # filter opt args or fragments
                if no_tab_line.startswith("-") or no_tab_line.startswith("--") or no_tab_line.startswith("/") or no_tab_line.startswith("//") or no_tab_line.startswith("[") or no_tab_line.startswith("{"):
                    continue
                try:
                    subcommand = no_tab_line.split()[0]
                except IndexError:
                    subcommand = no_tab_line
                subcommands.append(subcommand)

        return subcommands

    def _merge_option_groups(self, option_groups):
        groups = [set(g) for g in option_groups]
        merged = True

        while merged:
            merged = False
            new_groups = []
            skip = set()
            for i, j in combinations(range(len(groups)), 2):
                if i in skip or j in skip:
                    continue
                if groups[i] & groups[j]:  # if they share any flag
                    groups[i] |= groups[j]  # merge
                    skip.add(j)
                    merged = True
            # Rebuild list removing skipped groups
            groups = [g for idx, g in enumerate(groups) if idx not in skip]

        # Convert sets back to sorted lists
        return [sorted(list(g)) for g in groups]

    def _parse_optional(self, text: str):
        optional = []

        # Format help:
        lines = []
        for raw_line in text.splitlines():
            cleaned_line = re.sub(r'[^\x20-\x7E]', '', raw_line)
            flat_usage_line = cleaned_line.replace("[", "\n").replace("]", "").replace(" |", ",")
            no_tab_line = flat_usage_line.replace("\t", "").strip(" ")
            no_meta_line = no_tab_line.replace("=", " ").replace(":", " ")
            less_fake_line = no_meta_line.replace("[-]", "")
            sterilized_line = less_fake_line.rstrip()
            lines.extend(sterilized_line.split("\n"))

        # Parse optional flags
        for line in lines:
            stripped = line.strip()

            # Must start with -, --, or /
            if not (stripped.startswith("-") or stripped.startswith("--") or stripped.startswith("/")):
                continue

            # print(line)

            tokens = stripped.split()
            flag_tokens = []
            for tok in tokens:
                if tok.startswith("-") or tok.startswith("--") or tok.startswith("/"):
                    # Strip trailing commas
                    cleaned = tok.rstrip(",")
                    flag_tokens.append(cleaned)
                else:
                    break

            grouped_flags = []
            for tok in flag_tokens:
                for f in tok.split(","):
                    f = f.strip()
                    if f:
                        grouped_flags.append(f)
            optional.append(grouped_flags)

        return self._merge_option_groups(optional)

    def _parse_help(self, text: str) -> dict:
        return {
            "potential_subcommands": self._parse_subcommands(text),
            "optional": self._parse_optional(text)
        }

    def _save(self):
        self.json_path.write_text(json.dumps(self.data, indent=2))

    def get_suggested(self, line):
        tokens = line.strip().split()
        if not tokens:
            return {"command": None, "suggestions": []}

        tool = tokens[0]

        if tool not in self.data:
            return {"command": tool, "suggestions": [], "error": "Unknown command"}

        entry = self.data[tool]
        typed_sub = None

        # Recursively walk down subcommands
        current_entry = entry
        for token in tokens[1:]:
            if token in current_entry.get("subcommands", []):
                typed_sub = token
                current_entry = current_entry.get("branches", {}).get(token, current_entry)
            else:
                break

        suggestions = []

        # Suggest next subcommands if none typed yet at this level
        if not typed_sub or tokens[-1] not in current_entry.get("subcommands", []):
            suggestions.extend(current_entry.get("subcommands", []))

        # Build a set of flags already used in the line
        used_flags = set(tokens[1:])

        # Suggest options per group
        for group in current_entry.get("options", []):
            # Only suggest group if none of its flags are used
            if not any(flag in used_flags for flag in group) or not ONE_FLAG_PER_GROUP:
                suggestions.extend(group)

        # Filter suggestions by prefix of last token if partial and make sure no duplicate flags if ONE_FLAG_PER_GROUP is False
        last_token = tokens[-1]
        if last_token not in (tool, typed_sub):
            suggestions = [s for s in suggestions if s.startswith(last_token) and s not in used_flags]

        # Deduplicate and sort (shorter flags first)
        suggestions = sorted(set(suggestions), key=lambda x: (len(x), x), reverse=True)

        return {
            "command": tool,
            "subcommand": typed_sub,
            "suggestions": suggestions
        }