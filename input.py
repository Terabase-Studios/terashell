import os
from pkgutil import walk_packages

from prompt_toolkit import PromptSession
from prompt_toolkit.lexers import Lexer
from prompt_toolkit.styles import Style
from prompt_toolkit.completion import Completer, Completion, WordCompleter
from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.formatted_text import ANSI

from config import AUTO_COMPLETE
from indexer import CommandIndexer


class CommandCompleter(Completer):
    """
    Completes the first word (command) separately,
    then uses HelpIndexer for subcommands and flags.
    """

    def __init__(self, command_indexer, extra_commands = [], ignore_case=True):
        self.help_indexer = command_indexer
        self.ignore_case = ignore_case
        self.commands = sorted(command_indexer.get_commands() + extra_commands)  # top-level commands

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
            return  # don't try subcommands/flags yet

        # --- Subcommands/flags completion ---
        # Use HelpIndexer for suggestions
        suggested = self.help_indexer.help_indexer.get_suggested(text_before_cursor)
        suggestions = suggested.get("suggestions", [])

        last_token = tokens[-1]
        start_pos = -len(last_token)

        for s in suggestions:
            if self.ignore_case:
                if s.lower().startswith(last_token.lower()):
                    yield Completion(s, start_position=start_pos)
            else:
                if s.startswith(last_token):
                    yield Completion(s, start_position=start_pos)


# Lexer with live path highlighting
class ShellLexer(Lexer):
    def __init__(self, shell):
        self.shell = shell

    def lex_document(self, document):
        text = document.text
        cwd = os.path.expanduser(self.shell.working_dir)

        def get_line(lineno):
            tokens = []
            words = text.split()

            for i, word in enumerate(words):
                # Expand ~ and resolve relative paths
                full_path = os.path.expanduser(word)
                if not os.path.isabs(full_path):
                    full_path = os.path.join(cwd, full_path)

                if word.startswith("$"):
                    tokens.append(('class:env_var', word))
                # Partial path exists check: highlight even if only partially typed
                elif os.path.exists(full_path) or any(
                    f.startswith(os.path.basename(full_path))
                    for f in (os.listdir(os.path.dirname(full_path)) if os.path.exists(os.path.dirname(full_path)) else [])
                ):
                    if '\\' in word or '/' in word:
                        tokens.append(('class:path', word))
                    else:
                        tokens.append(('class:file', word))
                elif word.isdigit():
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
                tokens.append(('', ' '))  # add space back
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
    'env_var': 'ansigreen',
    'built_in': 'ansigreen'
})

# Shell input
class ShellInput:
    def __init__(self, shell, cmd_prefix="NoPrefixFound!> "):
        self.shell = shell
        self.history = InMemoryHistory()
        self.indexer = CommandIndexer()

        if AUTO_COMPLETE:
            completer = CommandCompleter(self.indexer, extra_commands=self.shell.command_handler.get_commands(), ignore_case=True)
        else:
            completer = None

        self.session = PromptSession(
            lexer=ShellLexer(shell),
            style=style,
            completer=completer,
            history=self.history  # <-- pass it to the session
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