import os

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.history import FileHistory
from prompt_toolkit.lexers import Lexer
from prompt_toolkit.styles import Style

from config import AUTO_COMPLETE, HISTORY_FILE, PROMPT_HIGHLIGHTING, ALWAYS_SUGGEST_HISTORY
from indexer import CommandIndexer


def clean_path(path, working_dir):
    no_quotes = path.strip("\"\'")
    no_long_path = no_quotes.removeprefix(working_dir)
    if not no_long_path == no_quotes:
        no_starting_slash = no_long_path.lstrip("\\/")
    else:
        no_starting_slash = no_long_path

    if any(ch in no_starting_slash for ch in ' \t\n"\''):
        proper_path = f"\"{no_starting_slash}\""
    else:
        proper_path = no_starting_slash
    return proper_path

def complete_path(text_before_cursor, ignore_case=False, working_dir=None):
    text_expanded = os.path.expanduser(text_before_cursor)

    # Split into directory and file prefix
    dir_part, file_part = os.path.split(text_expanded)

    # Handle Windows drive letters
    if len(dir_part) == 2 and dir_part[1] == ":":
        dir_part += os.sep

    # If relative, join with shell working dir
    if not os.path.isabs(dir_part):
        if working_dir:
            dir_part = os.path.join(working_dir, dir_part)
        else:
            dir_part = os.path.abspath(dir_part)

    # Only try to list if dir exists
    if not os.path.isdir(dir_part):
        return

    try:
        entries = os.listdir(dir_part)
    except (FileNotFoundError, PermissionError):
        entries = []

    for entry in entries:
        if ignore_case:
            match = entry.lower().startswith(file_part.lower())
        else:
            match = entry.startswith(file_part)
        if match:
            completion_path = os.path.join(dir_part, entry)
            if os.path.isdir(completion_path):
                completion_path += os.sep
            yield Completion(clean_path(completion_path, working_dir), start_position=-len(file_part))


class CommandCompleter(Completer):
    """
    Completes the first word (command) separately,
    then uses HelpIndexer for subcommands and flags.
    """

    def __init__(self, input_handler, extra_commands = [], ignore_case=True):
        self.input_handler = input_handler
        self.help_indexer = input_handler.indexer
        self.ignore_case = ignore_case
        self.commands = sorted(self.help_indexer.get_commands() + extra_commands)  # top-level commands

    def get_completions(self, document, complete_event):
        text_before_cursor = document.text_before_cursor
        tokens = text_before_cursor.split()

        if not tokens:
            return

        # --- First word: command completion ---
        if len(tokens) == 1 and text_before_cursor[-1] != " ":
            first_word = tokens[0]
            start_pos = -len(first_word)
            for cmd in self.commands:
                cmd_name = cmd.split(".")[0]  # only top-level
                if self.ignore_case:
                    if cmd_name.lower().startswith(first_word.lower()):
                        yield Completion(cmd_name, start_position=start_pos)
                else:
                    if cmd_name.startswith(first_word):
                        yield Completion(cmd_name, start_position=start_pos)
            # --- Add filesystem path completion ---
            for c in complete_path(text_before_cursor, ignore_case=self.ignore_case,
                                   working_dir=self.input_handler.shell.working_dir):
                yield Completion(c.text, start_position=start_pos)
            return  # don't try subcommands/flags yet

        # --- Subcommands/flags completion ---
        # Use HelpIndexer for suggestions
        suggested = self.help_indexer.help_indexer.get_suggested(text_before_cursor)
        suggestions = suggested.get("suggestions", [])

        last_token = tokens[-1]
        start_pos = -len(last_token)
        found_suggestion = False

        # --- Add filesystem path completion ---
        last_token = tokens[-1]
        start_pos = -len(last_token)
        for c in complete_path(last_token, ignore_case=self.ignore_case,
                               working_dir=self.input_handler.shell.working_dir):
            found_suggestion = True
            yield Completion(c.text, start_position=start_pos)

        for s in suggestions:
            if self.ignore_case:
                if s.lower().startswith(last_token.lower()):
                    found_suggestion = True
                    yield Completion(s, start_position=start_pos)
            else:
                if s.startswith(last_token):
                    found_suggestion = True
                    yield Completion(s, start_position=start_pos)

        for s in self.input_handler.shell.command_handler.get_commands():
            if self.ignore_case:
                if s.lower().startswith(text_before_cursor.lower()):
                    found_suggestion = True
                    yield Completion(s, start_position=-len(text_before_cursor))
            else:
                if s.startswith(text_before_cursor):
                    found_suggestion = True
                    yield Completion(s, start_position=-len(text_before_cursor))

        if not found_suggestion or ALWAYS_SUGGEST_HISTORY:
            for s in list(set(self.input_handler.get_history())):
                # Handle case-insensitive option
                if self.ignore_case:
                    if s.lower().startswith(text_before_cursor.lower()):
                        # Replace everything typed so far
                        yield Completion(s, start_position=-len(text_before_cursor))
                else:
                    if s.startswith(text_before_cursor):
                        yield Completion(s, start_position=-len(text_before_cursor))

# Lexer with live path highlighting
class ShellLexer(Lexer):
    def __init__(self, shell):
        self.shell = shell

    def lex_document(self, document):
        text = document.text
        cwd = os.path.expanduser(self.shell.working_dir)

        def get_line(lineno):
            tokens = []
            current = []
            in_quotes = False

            words = text.split(" ")

            for i, word in enumerate(words):
                if word.startswith(("'", '"')) and not in_quotes:
                    in_quotes = True
                    current.append(word)
                    continue
                if in_quotes:
                    current.append(word)
                    # check if this word ends with a quote (same type as opening)
                    if word.endswith(("'", '"')):
                        tokens.append(('class:quotes', ' '.join(current)))
                        current = []
                        in_quotes = False
                    continue

                # Expand ~ and resolve relative paths
                full_path = os.path.expanduser(word.strip("\'\""))
                if not os.path.isabs(full_path):
                    full_path = os.path.join(cwd, full_path)
                try:
                    path_exists = os.path.exists(full_path)
                    path_partial = (path_exists or any(
                        f.startswith(os.path.basename(full_path))
                        for f in (os.listdir(os.path.dirname(full_path)) if os.path.exists(os.path.dirname(full_path)) else [])
                    ))

                    if word.startswith("$"):
                        tokens.append(('class:env_var', word))
                    # Partial path exists check: highlight even if only partially typed
                    elif path_exists or path_partial:
                        if '\\' in word or '/' in word:
                            if path_exists:
                                tokens.append(('class:path_complete', word))
                            else:
                                tokens.append(('class:path', word))
                        else:
                            if path_exists and word != "." and word != "..":
                                tokens.append(('class:file_complete', word))
                            else:
                                tokens.append(('class:file', word))
                    elif word.replace(".", "").isdigit():
                        tokens.append(('class:digit', word))
                    elif word.startswith('-'):
                        tokens.append(('class:optional', word))
                    elif i == 0:
                        if word in self.shell.command_handler.get_commands():
                            tokens.append(('class:built_in', word))
                        else:
                            tokens.append(('class:command', word))
                    else:
                        tokens.append(('class:arg', word))
                except Exception:
                    tokens.append(('class:error', word))
                tokens.append(('', ' '))  # add space back
            if current:
                tokens.append(('class:quotes', ' '.join(current)))
            return tokens

        return get_line

# Style for colors
style = Style.from_dict({
    'command': 'bold ansiyellow',
    'arg': 'ansigray',
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
