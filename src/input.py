import os
import hashlib
import json
import time
import datetime
from collections import defaultdict

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.history import FileHistory
from prompt_toolkit.lexers import Lexer
from prompt_toolkit.styles import Style

from config import AUTO_COMPLETE, HISTORY_FILE, PROMPT_HIGHLIGHTING, ALWAYS_SUGGEST_HISTORY, \
    COMPLETE_PATH, COMPLETE_ARGS, COMPLETE_HISTORY, COMMAND_LINKING_SYMBOLS, IGNORE_SPACE
from indexer import CommandIndexer


class CommandCompleter(Completer):
    """
    Two-mode command completer:
    1. First word: top-level commands.
    2. Body: subcommands, flags, paths, and history after the last token.
    """

    def __init__(self, input_handler, extra_commands=None, ignore_case=True):
        self.input_handler = input_handler
        self.help_indexer = input_handler.indexer
        self.ignore_case = ignore_case
        self.commands = sorted(self.help_indexer.get_commands() + (extra_commands or []))

    # -------------------- Dedupe Gate -------------------- #
    def _dedupe(self, completions):
        seen = set()
        for c in completions:
            key = (
                c.text.lower() if self.ignore_case else c.text,
                c.start_position,
            )
            if key in seen:
                continue
            seen.add(key)
            yield c

    # -------------------- Path completion -------------------- #
    def complete_path(self, text_before_cursor, working_dir=None):
        text_expanded = os.path.expanduser(text_before_cursor)
        dir_part, file_part = os.path.split(text_expanded)

        if len(dir_part) == 2 and dir_part[1] == ":":
            dir_part += os.sep

        if not os.path.isabs(dir_part):
            dir_part = os.path.join(working_dir or os.getcwd(), dir_part)
        dir_part = os.path.abspath(dir_part)

        if not os.path.isdir(dir_part):
            return []

        try:
            entries = os.listdir(dir_part)
        except (FileNotFoundError, PermissionError):
            return []

        out = []
        for entry in entries:
            match = entry.lower().startswith(file_part.lower()) if self.ignore_case else entry.startswith(file_part)
            if not match:
                continue

            full_path = os.path.join(dir_part, entry)
            if os.path.isdir(full_path):
                full_path += os.sep

            out.append(
                Completion(
                    self._format_path(full_path, working_dir),
                    start_position=-len(file_part),
                )
            )
        return out

    def _format_path(self, path, working_dir):
        no_quotes = path.strip("\"\'")
        if working_dir and no_quotes.startswith(working_dir):
            no_quotes = no_quotes.removeprefix(working_dir).lstrip("\\/")
        if any(ch in no_quotes for ch in ' \t\n"\''):
            return f'"{no_quotes}"'
        return no_quotes

    # -------------------- Command completion -------------------- #
    def _complete_command(self, text):
        out = []
        for cmd in self.commands:
            cmd_name = cmd.split(".")[0]
            match = cmd_name.lower().startswith(text.lower()) if self.ignore_case else cmd_name.startswith(text)
            if match:
                out.append(Completion(cmd_name, start_position=-len(text)))
        return out

    # -------------------- Deterministic completion -------------------- #
    def _complete_deterministic(self, last_token, text_before_cursor, token_index, tool_index):
        out = []
        found_path = False

        if COMPLETE_ARGS:
            suggested = self.help_indexer.help_indexer.get_suggested(text_before_cursor)
            suggestions = suggested.get("suggestions", [])
            partial = suggested.get("partial", True)

            for s in suggestions:
                out.append(
                    Completion(
                        s,
                        start_position=-len(last_token) if partial else 0,
                    )
                )

        if COMPLETE_PATH:
            paths = self.complete_path(last_token, self.input_handler.shell.working_dir)
            if paths:
                found_path = True
                out.extend(paths)

        if (not found_path or ALWAYS_SUGGEST_HISTORY) and COMPLETE_HISTORY:
            if token_index == tool_index:
                return out

            seen = set()
            for entry in reversed(self.input_handler.get_history()):
                words = entry.split()
                if len(words) <= token_index:
                    continue

                candidate = words[token_index]
                key = candidate.lower() if self.ignore_case else candidate
                if key in seen:
                    continue

                if self._matches_token(candidate, last_token):
                    out.append(Completion(candidate, start_position=-len(last_token)))
                    seen.add(key)

        return out

    # -------------------- Utility -------------------- #
    def _matches_token(self, candidate, token):
        return candidate.lower().startswith(token.lower()) if self.ignore_case else candidate.startswith(token)

    # -------------------- Main entry -------------------- #
    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        tokens = text.split()
        candidates = []

        if not tokens:
            candidates.extend(self._complete_command(""))
            for c in self._dedupe(candidates):
                yield c
            return

        tool_offset = tokens[0] == "sudo"
        tool_index = 1 if tool_offset else 0

        if len(tokens) == tool_index + 1 and not text.endswith(" "):
            first = tokens[tool_index]
            candidates.extend(self._complete_command(first))
            if COMPLETE_PATH:
                candidates.extend(
                    self.complete_path(first, self.input_handler.shell.working_dir)
                )
            for c in self._dedupe(candidates):
                yield c
            return

        last_token = tokens[-1]
        candidates.extend(
            self._complete_deterministic(
                last_token,
                text.removeprefix("sudo "),
                token_index=len(tokens) - 1,
                tool_index=tool_index,
            )
        )

        for c in self._dedupe(candidates):
            yield c


# Lexer with live path highlighting
class ShellLexer(Lexer):
    def __init__(self, shell):
        self.shell = shell

    def lex_document(self, document):
        text = document.text
        cwd = os.path.expanduser(self.shell.working_dir)

        def split_by_linkers(line: str):
            parts = []
            buf = ""
            i = 0
            in_quotes = False
            quote_char = None

            while i < len(line):
                ch = line[i]

                if ch in ("'", '"'):
                    if not in_quotes:
                        in_quotes = True
                        quote_char = ch
                    elif ch == quote_char:
                        in_quotes = False
                        quote_char = None
                    buf += ch
                    i += 1
                    continue

                if not in_quotes:
                    for sym in COMMAND_LINKING_SYMBOLS:
                        if line.startswith(sym, i):
                            if buf:
                                parts.append(("segment", buf))
                            parts.append(("link", sym))
                            buf = ""
                            i += len(sym)
                            break
                    else:
                        buf += ch
                        i += 1
                else:
                    buf += ch
                    i += 1

            if buf:
                parts.append(("segment", buf))

            return parts

        def parse_segment(segment):
            tokens = []
            current = ""
            in_quotes = False
            quote_char = None
            word_index = 0
            words = segment.strip().split()
            tool_index = 0 if words and words[0] != "sudo" else 1

            def flush_word(word, i, quoted=False):
                if not word:
                    return

                try:
                    # strip quotes only for path checking
                    full_path = os.path.expanduser(word.strip("'\""))
                    if not os.path.isabs(full_path):
                        full_path = os.path.join(cwd, full_path)

                    path_exists = os.path.exists(full_path)
                    dirname = os.path.dirname(full_path)
                    path_partial = (
                            path_exists or
                            (os.path.exists(dirname) and any(
                                f.startswith(os.path.basename(full_path))
                                for f in os.listdir(dirname)
                            ))
                    )

                    if quoted:
                        tokens.append(("class:quotes", word))  # <- key change
                    elif word.lower() == "sudo" and i == 0:
                        tokens.append(("class:sudo", word))
                    elif word.startswith("$"):
                        tokens.append(("class:env_var", word))
                    elif path_exists or path_partial:
                        if "/" in word or "\\" in word:
                            tokens.append((
                                "class:path_complete" if path_exists else "class:path",
                                word
                            ))
                        else:
                            tokens.append((
                                "class:file_complete" if path_exists else "class:file",
                                word
                            ))
                    elif word.replace(".", "").isdigit():
                        tokens.append(("class:digit", word))
                    elif word.startswith("-") or word.startswith("/"):
                        tokens.append(("class:optional", word))
                    elif i == tool_index:
                        if word in self.shell.command_handler.get_commands():
                            tokens.append(("class:built_in", word))
                        else:
                            tokens.append(("class:command", word))
                    else:
                        tokens.append(("class:arg", word))

                except Exception:
                    tokens.append(("class:error", word))

            i = 0
            while i < len(segment):
                ch = segment[i]

                if ch in ("'", '"'):
                    if not in_quotes:
                        in_quotes = True
                        quote_char = ch
                        current = ch  # start including quote
                    elif ch == quote_char:
                        in_quotes = False
                        current += ch
                        flush_word(current, word_index, quoted=True)
                        current = ""
                        word_index += 1
                        quote_char = None
                    i += 1
                    continue

                if ch == " " and not in_quotes:
                    flush_word(current, word_index)
                    if current:
                        word_index += 1
                    current = ""
                    tokens.append(("", " "))  # preserve real space
                    i += 1
                    continue

                current += ch
                i += 1

            # flush anything left (in case segment ends without space)
            if current:
                flush_word(current, word_index, quoted=in_quotes)

            return tokens

        def get_line(_lineno):
            tokens = []

            for kind, value in split_by_linkers(text):
                if kind == "link":
                    tokens.append(("class:link", value.strip()))
                else:
                    tokens.extend(parse_segment(value))

            return tokens

        return get_line


# Style for colors
style = Style.from_dict({
    # commands & control
    "command":        "bold #c98c6c",
    "built_in":       "#69aa71",
    "sudo":           "bold #db5d6b",

    # arguments & values
    "arg":            "#D4D4D4",
    "digit":          "#2aacb8",
    "optional":       "#737d84",
    "quotes":         "italic #69aa71",

    # filesystem
    "path":           "#6f94dd",
    "file":           "#EDEDED",
    "path_complete":  "underline #6f94dd",
    "file_complete":  "underline #EDEDED",
    "link":           "#7b87b8",

    # environment & errors
    "env_var":        "#5f826b",
    "error":          "bold #db5d6b",
})


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

    def set_last_valid(self, value: bool):
        """
        Sets the 'valid' field for the last command to the given value.
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
            last_meta['valid'] = value
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
            self.cmd_meta[last_cmd][-1]['valid'] = value

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
        meta = {"cwd": cwd, "venv": venv, "ts": time.time(), "valid": None}

        # Append metadata
        with open(self.meta_filename, "a", encoding="utf-8") as f:
            f.write(json.dumps(meta) + "\n")

        # Update in-memory
        self.cmd_meta[text].append(meta)
        super().append_string(text)


# Shell input
class ShellInput:
    def __init__(self, shell, cmd_prefix="NoPrefixFound!> ", history_file=HISTORY_FILE):
        self.shell = shell
        self.indexer = CommandIndexer(index_path=AUTO_COMPLETE)

        # Use FileHistory for persistent history
        self.history = ShellFileHistory(shell, history_file)

        if AUTO_COMPLETE:
            completer = CommandCompleter(
                self,
                extra_commands=self.shell.command_handler.get_commands(),
                ignore_case=True
            )
        else:
            completer = None

        if PROMPT_HIGHLIGHTING:
            lexer = ShellLexer(self.shell)
        else:
            lexer = None

        self.session = PromptSession(
            lexer=lexer,
            style=style,
            completer=completer,
            history=self.history
        )
        self.cmd_prefix = cmd_prefix

    def input(self, cmd_prefix=None):
        if cmd_prefix is None:
            cmd_prefix = self.cmd_prefix
        try:
            command = self.session.prompt(cmd_prefix)
        except EOFError:
            return None

        if not command.strip():
            return None

        return command

    def print_history(self):
        for i, line  in enumerate(self.history.get_strings()):
            print(f"{i+1}: {line}")

    def get_history(self):
        return self.history.get_strings()

    def clear_history(self):
        # wipe the file
        filename = self.history.filename
        del self.history
        open(filename, "w").close()

        # rebuild the session
        self.history = FileHistory(filename)

        if AUTO_COMPLETE:
            completer = CommandCompleter(
                self,
                extra_commands=self.shell.command_handler.get_commands(),
                ignore_case=True
            )
        else:
            completer = None

        self.session = PromptSession(
            lexer=ShellLexer(self.shell),
            style=style,
            completer=completer,
            history=self.history
        )
