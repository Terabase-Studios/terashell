import os

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.history import FileHistory
from prompt_toolkit.lexers import Lexer
from prompt_toolkit.styles import Style

from config import AUTO_COMPLETE, HISTORY_FILE, PROMPT_HIGHLIGHTING, ALWAYS_SUGGEST_HISTORY, \
    COMPLETE_PATH, COMPLETE_ARGS, COMPLETE_HISTORY, COMMAND_LINKING_SYMBOLS
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

    # -------------------- Path completion -------------------- #
    def complete_path(self, text_before_cursor, working_dir=None):
        text_expanded = os.path.expanduser(text_before_cursor)
        dir_part, file_part = os.path.split(text_expanded)

        # Handle Windows drive letters
        if len(dir_part) == 2 and dir_part[1] == ":":
            dir_part += os.sep

        # Resolve relative paths
        if not os.path.isabs(dir_part):
            dir_part = os.path.join(working_dir or os.getcwd(), dir_part)
        dir_part = os.path.abspath(dir_part)

        if not os.path.isdir(dir_part):
            return

        try:
            entries = os.listdir(dir_part)
        except (FileNotFoundError, PermissionError):
            entries = []

        for entry in entries:
            if self.ignore_case:
                match = entry.lower().startswith(file_part.lower())
            else:
                match = entry.startswith(file_part)
            if match:
                full_path = os.path.join(dir_part, entry)
                if os.path.isdir(full_path):
                    full_path += os.sep
                yield Completion(self._format_path(full_path, working_dir), start_position=-len(file_part))


    def _format_path(self, path, working_dir):
        """Clean up path for display, adding quotes if necessary."""
        no_quotes = path.strip("\"\'")
        # Only remove prefix if it's actually relative to the working dir
        if working_dir and no_quotes.startswith(working_dir):
            no_quotes = no_quotes.removeprefix(working_dir).lstrip("\\/")
        if any(ch in no_quotes for ch in ' \t\n"\''):
            return f'"{no_quotes}"'
        return no_quotes

    # -------------------- Command completion -------------------- #
    def _complete_command(self, text):
        for cmd in self.commands:
            cmd_name = cmd.split(".")[0]  # top-level only
            if self.ignore_case:
                if cmd_name.lower().startswith(text.lower()):
                    yield Completion(cmd_name, start_position=-len(text))
            else:
                if cmd_name.startswith(text):
                    yield Completion(cmd_name, start_position=-len(text))

    # -------------------- Subcommand / flag completion -------------------- #
    def _complete_deterministic(self, last_token, text_before_cursor):
        found = False

        # HelpIndexer suggestions
        if COMPLETE_ARGS:
            suggested = self.help_indexer.help_indexer.get_suggested(text_before_cursor)
            suggestions = suggested.get("suggestions", [])

            partial = suggested.get("partial", True)

            for s in suggestions:
                if partial:
                    yield Completion(s, start_position=-len(last_token))
                else:
                    yield Completion(s, start_position=0)

        # Path completions
        if COMPLETE_PATH:
            for c in self.complete_path(last_token, self.input_handler.shell.working_dir):
                found = True
                yield Completion(c.text, start_position=-len(last_token))

        # History completions (only after previous token)
        if not found and COMPLETE_HISTORY:
            prev_token_len = len(last_token)
            seen_tails = set()
            for entry in reversed(self.input_handler.get_history()):
                words = entry.split()
                if not words:
                    continue
                tail = words[-1]
                if tail in seen_tails:
                    continue
                if self._matches_token(tail, last_token):
                    yield Completion(tail, start_position=-prev_token_len)
                    seen_tails.add(tail)
    # -------------------- Subcommand / flag completion -------------------- #
    def _complete_personalized(self, last_token, text_before_cursor):
        return

    # -------------------- Utility -------------------- #
    def _matches_token(self, candidate, token):
        if self.ignore_case:
            return candidate.lower().startswith(token.lower())
        return candidate.startswith(token)

    # -------------------- Main entry -------------------- #
    def get_completions(self, document, complete_event):
        text_before_cursor = document.text_before_cursor
        tokens = text_before_cursor.split()

        # No tokens: suggest top-level commands
        if not tokens:
            for c in self._complete_command(""):
                yield c
            return

        # Guess Tool
        tool_offset = tokens[0].strip() == "sudo"
        tool_index = 0 if not tool_offset else 1
        if len(tokens) == tool_index + 1 and not text_before_cursor.endswith(" "):
            first_word = tokens[tool_index]
            for c in self._complete_command(first_word):
                yield c
            if COMPLETE_PATH:
                for c in self.complete_path(first_word, self.input_handler.shell.working_dir):
                    yield Completion(c.text, start_position=-len(first_word))
            return

        # Guess deterministically
        last_token = tokens[-1]
        for c in self._complete_deterministic(last_token, text_before_cursor.removeprefix("sudo")):
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
    'command': 'bold ansiyellow',
    'sudo': 'bold ansired',
    'link': 'bold ansiyellow',
    'arg': '#D0D0D0',
    'digit': 'ansiyellow',
    'optional': '#808080',
    'path': 'ansicyan',
    'file': 'ansiwhite',
    'path_complete': 'underline ansicyan',
    'file_complete': 'underline ansiwhite',
    'env_var': 'ansigreen',
    'built_in': 'ansigreen',
    'error': 'ansired',
    'quotes': 'italic ansicyan'
})

# Shell input
class ShellInput:
    def __init__(self, shell, cmd_prefix="NoPrefixFound!> ", history_file=HISTORY_FILE):
        self.shell = shell
        self.indexer = CommandIndexer(index_path=AUTO_COMPLETE)

        # Use FileHistory for persistent history
        self.history = FileHistory(history_file)

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
        del self.history
        open(HISTORY_FILE, "w").close()

        # rebuild the session
        self.history = FileHistory(HISTORY_FILE)

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
