import os
import json
from collections import defaultdict

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.history import FileHistory
from prompt_toolkit.lexers import Lexer
from prompt_toolkit.styles import Style
from prompt_toolkit.shortcuts import CompleteStyle


from config import AUTO_COMPLETE, HISTORY_FILE, PROMPT_HIGHLIGHTING, COMPLETE_COMMAND, \
    COMPLETE_PATHS, COMPLETE_ARGS, COMPLETE_HISTORY, COMMAND_LINKING_SYMBOLS, IGNORE_SPACE
from indexer import CommandIndexer
from prompt_toolkit.key_binding import KeyBindings

kb = KeyBindings()

@kb.add("enter")
def accept_path_completion_or_submit(event):
    buffer = event.app.current_buffer
    state = buffer.complete_state
    text = buffer.document.text_before_cursor
    tokens = text.split()

    # Determine last token
    last_token = tokens[-1] if tokens else ""

    # Only trigger special Enter behavior if last token looks like a path
    is_path_token = (
        last_token.startswith(("~", "/", "\\"))  # starts like Unix/Windows path
        or "\\" in last_token                    # contains backslash
        or "/" in last_token                     # contains forward slash
    )

    if state and state.completions and state.complete_index is not None and is_path_token:
        # Accept highlighted completion
        buffer.apply_completion(state.current_completion)
        buffer.complete_state = None  # Close menu
        # Regenerate completions for the new path
        buffer.start_completion(select_first=True)
    else:
        # Normal Enter behavior
        buffer.validate_and_handle()



class CommandCompleter(Completer):
    """
    Two-mode command completer:
    1. First word: top-level commands.
    2. Body: subcommands, flags, paths, and history after the last token.
    """

    def __init__(self, input_handler, extra_commands=None, ignore_case=True, completer_style = None):
        self.input_handler = input_handler
        self.help_indexer = input_handler.indexer
        self.ignore_case = ignore_case
        self.commands = sorted(self.help_indexer.get_commands() + (extra_commands or []))
        self.built_in_commands = input_handler.shell.command_handler.command_list
        if completer_style:
            self.style = completer_style

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
        if not text_before_cursor or text_before_cursor[-1] == " " or text_before_cursor[-1] == "~":
            return []

        text_before_cursor = text_before_cursor.split()[-1]

        text_before_expanded = text_before_cursor
        text_before_cursor = os.path.expanduser(text_before_cursor)
        expanded = not text_before_expanded == text_before_cursor

        # Find last slash of either type
        last_slash = max(text_before_cursor.rfind("/"), text_before_cursor.rfind("\\"))

        if last_slash != -1:
            # Split cleanly
            dir_part = text_before_cursor[:last_slash + 1]
            fragment = text_before_cursor[last_slash + 1:]

            # Extend working directory
            if working_dir:
                working_dir = os.path.normpath(os.path.join(working_dir, dir_part))
            else:
                working_dir = os.path.normpath(dir_part)

            text_before_cursor = fragment

        # TODO: This can cause problems so here it is for future me
        if "." in text_before_cursor:
            return []

        paths =  self.complete_path_raw(
                text_before_cursor,
                working_dir,
                ignore_case=self.ignore_case,
            )

        out = []
        dir_part, file_part = os.path.split(text_before_cursor)

        for path in paths:
            formatted_path, is_absolute = self._format_path(path, working_dir)

            quoted = formatted_path.startswith("\"") or formatted_path.startswith("\'")
            if quoted and expanded:
                continue

            out.append(
                Completion(
                    formatted_path,
                    start_position=(-len(file_part) - 1) if is_absolute else - len(text_before_cursor),
                    style="class:quotes" if quoted else "class:path"
                )
            )
        return out

    def complete_path_raw(
        self,
        text_before_cursor: str,
        working_dir: str | None = None,
        ignore_case: bool = False,
    ):
        text_expanded = os.path.expanduser(text_before_cursor)
        dir_part, file_part = os.path.split(text_expanded)

        # Windows drive edge case: "C:"
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

        results = []
        for entry in entries:
            match = (
                entry.lower().startswith(file_part.lower())
                if ignore_case
                else entry.startswith(file_part)
            )
            if not match:
                continue

            full_path = os.path.join(dir_part, entry)
            if os.path.isdir(full_path):
                full_path += os.sep

            results.append(full_path)

        return results

    def _format_path(self, path, working_dir):
        no_quotes = path.strip("\"\'")
        is_absolute = os.path.isabs(no_quotes)
        if working_dir and no_quotes.startswith(working_dir):
            no_quotes = no_quotes.removeprefix(working_dir).lstrip("\\/")
        if any(ch in no_quotes for ch in ' \t\n"\''):
            if is_absolute:
                return f'"\\{no_quotes}"', is_absolute
            else:
                return f'"{no_quotes}"', is_absolute
        return no_quotes, False

    # -------------------- Command completion -------------------- #
    def _complete_command(self, text, no_sudo=False, built_in_index = 0):
        out = []
        for cmd in self.commands:
            cmd_name = cmd.split(".")[0]
            match = cmd_name.lower().startswith(text.lower()) if self.ignore_case else cmd_name.startswith(text)

            if cmd_name == "sudo":
                if no_sudo:
                    continue
                color = "class:sudo"
            elif cmd_name in self.built_in_commands:
                color = "class:built_in"
            else:
                color = "class:command"

            if match:
                out.append(Completion(cmd_name.split()[0], start_position=-len(text), style=color))
        return out

    def _complete_build_in_arg(self, text, built_in_index=1):
        out = []
        text_tokens = text.split()
        text_arg = text_tokens[built_in_index] if built_in_index < len(text_tokens) else ""

        for cmd in self.built_in_commands:
            cmd_tokens = cmd.split()
            if built_in_index >= len(cmd_tokens):
                continue
            if cmd_tokens[0] != text_tokens[0]:
                continue
            cmd_arg = cmd_tokens[built_in_index]

            match = cmd_arg.lower().startswith(text_arg.lower()) if self.ignore_case else cmd_arg.startswith(text_arg)
            match = match or text.endswith(" ")

            if match:
                out.append(Completion(cmd_arg, start_position=-len(text_arg), style="class:arg"))
        return out

    # -------------------- Deterministic completion -------------------- #
    def _complete_deterministic(self, last_token, text_before_cursor, token_index, tool_index):
        out = []
        found_path = False

        if COMPLETE_ARGS:
            out += self._complete_build_in_arg(text_before_cursor.removeprefix("sudo"))
            suggested = self.help_indexer.help_indexer.get_suggested(text_before_cursor)
            command_suggestions = suggested.get("subcommand_suggestions", [])
            if text_before_cursor[-1] == " " or last_token.startswith("-") or last_token.startswith("--") or last_token.startswith("/"):
                optional_suggestions = suggested.get("option_suggestions", [])
            else:
                optional_suggestions = suggested.get("optional_suggestions", [])

            partial = suggested.get("partial", True)

            for s in command_suggestions:
                out.append(
                    Completion(
                        s,
                        start_position=-len(last_token) if partial else 0,
                        style="class:arg"
                    )
                )

            for s in optional_suggestions:
                out.append(
                    Completion(
                        s,
                        start_position=-len(last_token) if partial else 0,
                        style="class:optional"
                    )
                )

        if COMPLETE_PATHS:
            paths = self.complete_path(text_before_cursor, self.input_handler.shell.working_dir)
            if paths:
                found_path = True
                out.extend(paths)

        if COMPLETE_HISTORY:
            out = self._complete_history(text_before_cursor, tool_index, token_index, last_token, self.input_handler.shell.working_dir) + out

        return out

    def _complete_history(self, text_before_cursor, tool_index, token_index, last_token, working_dir):
        def _looks_like_path(token: str) -> bool:
            return (
                "/" in token
                or "\\" in token
                or token.startswith(".")
                or token.startswith("~")
                or (len(token) >= 2 and token[1] == ":")  # Windows drive
            )
        def _verify_path(token: str, working_dir: str | None) -> bool:
            expanded = os.path.expanduser(token)

            if not os.path.isabs(expanded) and working_dir:
                expanded = os.path.join(working_dir, expanded)

            # exact path exists
            if os.path.exists(expanded):
                return True

            # parent exists (user still typing filename)
            parent = os.path.dirname(expanded)
            return bool(parent) and os.path.isdir(parent)
        out = []
        seen = set()
        history = reversed(self.input_handler.get_history())

        tokens = text_before_cursor.split()

        if token_index == tool_index:
            return out

        prev_typed = tokens[token_index - 1] if token_index > 0 else None
        prev_typed_minus_one = tokens[token_index - 2] if token_index > 0 else None

        for entry in history:
            words = entry.split()
            if len(words) <= token_index:
                continue

            # context lock
            if token_index > tool_index:
                if text_before_cursor.endswith(" "):
                    if words[token_index - 1] != prev_typed:
                        continue
                else:
                    if words[token_index - 2] != prev_typed_minus_one:
                        continue

            candidate = words[token_index if text_before_cursor.endswith(" ") else token_index - 1 ]

            key = candidate.lower() if self.ignore_case else candidate
            if key in seen:
                continue

            if _looks_like_path(candidate):
                if not _verify_path(candidate, working_dir):
                    continue

            if self._matches_token(candidate, last_token) or text_before_cursor.endswith(" "):
                out.append(
                    Completion(
                        candidate,
                        start_position=-len(last_token) if not text_before_cursor.endswith(" ") else 0,
                        style="class:link",
                    )
                )
                seen.add(key)

        return out

    # -------------------- Utility -------------------- #
    def _matches_token(self, candidate, token):
        return candidate.lower().startswith(token.lower()) if self.ignore_case else candidate.startswith(token)

    def _yield_autocomplete_errors(self, messages=None):
        if messages is None:
            messages = ["NULL", "NULL", "NULL"]
        for message in messages:
            yield Completion(
                text="",
                display=f"{message}",
                start_position=0,
                style="class:error"
            )

    # -------------------- Main entry -------------------- #
    def get_completions(self, document, complete_event):
        try:
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
            start_whitespace = " " if text[0] == " " else ""
            end_whitespace = " " if text[-1] == " " else ""

            if len(tokens) == tool_index + 1 and not text.endswith(" "):
                first = tokens[tool_index]
                if COMPLETE_COMMAND:
                    candidates.extend(self._complete_command(first, no_sudo=tool_offset))
                if COMPLETE_PATHS:
                    candidates.extend(
                        self.complete_path(start_whitespace+first+end_whitespace, self.input_handler.shell.working_dir)
                    )
                for c in self._dedupe(candidates):
                    yield c
                return

            last_token = tokens[-1]
            candidates.extend(
                self._complete_deterministic(
                    last_token,
                    text,
                    token_index=len(tokens),
                    tool_index=tool_index,
                )
            )
            for c in self._dedupe(candidates):
                yield c
        except Exception as e:
            # Get the traceback object from the exception
            tb = e.__traceback__

            # Iterate through the traceback frames to find the last one (where the error occurred)
            last_frame = None
            while tb:
                last_frame = tb
                tb = tb.tb_next

            if last_frame:
                filename = last_frame.tb_frame.f_code.co_filename
                function_name = last_frame.tb_frame.f_code.co_name
                line_number = last_frame.tb_lineno


                messages = [str(e), str(function_name), str(line_number), "PLEASE REPORT"]
                yield from self._yield_autocomplete_errors(messages=messages)
                return

            yield from self._yield_autocomplete_errors()



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


# Background for autocomplete
autocomplete_bg = "#1a1a1a"

# Style for colors
style_dict = {
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

    # Menu background
    "completion-menu": f"bg:{autocomplete_bg}",
    "completion-menu.completion": f"bg:{autocomplete_bg}",
    "completion-menu.completion.current": f"bg:#444444",
    "scrollbar.background": f"bg:{autocomplete_bg}",
    "scrollbar.arrow": "bg:#444444",
}
style = Style.from_dict(style_dict)

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
        #print(self.cmd_meta)

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


# Shell input
class ShellInput:
    def __init__(self, shell, cmd_prefix="NoPrefixFound!> ", history_file=HISTORY_FILE):
        self.shell = shell
        self.indexer = CommandIndexer(index_path=AUTO_COMPLETE)

        # Use FileHistory for persistent history
        #self.history = ShellFileHistory(shell, history_file)
        self.history = FileHistory(history_file)

        if AUTO_COMPLETE:
            completer = CommandCompleter(
                self,
                extra_commands=self.shell.command_handler.get_commands(),
                ignore_case=True,
                completer_style=style
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
            history=self.history,
            complete_while_typing=True,
            complete_in_thread=True,
            complete_style = CompleteStyle.MULTI_COLUMN,
            key_bindings=kb
        )
        self.cmd_prefix = cmd_prefix

    def input(self, cmd_prefix=None):
        if cmd_prefix is None:
            cmd_prefix = self.cmd_prefix
        try:
            command = self.session.prompt(cmd_prefix, )
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
            history=self.history,
            complete_while_typing=True,
            complete_in_thread=True,
            complete_style = CompleteStyle.MULTI_COLUMN,
            key_bindings=kb
        )