import os
from pkgutil import walk_packages

from prompt_toolkit import PromptSession
from prompt_toolkit.lexers import Lexer
from prompt_toolkit.styles import Style
from prompt_toolkit.completion import Completer, Completion, WordCompleter
from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.formatted_text import ANSI


from indexer import CommandIndexer

class CommandCompleter(Completer):
    """
    Completes only the first word (command) in the input.
    """
    def __init__(self, words, ignore_case=True):
        self.words = sorted(words)
        self.ignore_case = ignore_case

    def get_completions(self, document, complete_event):
        text_before_cursor = document.text_before_cursor
        if " " in text_before_cursor:
            # Only complete if the cursor is in the first word
            first_word = text_before_cursor.split()[0]
            if document.cursor_position <= len(first_word):
                for word in self.words:
                    if word.lower().startswith(first_word.lower()):
                        yield Completion(word, start_position=-len(first_word))
        else:
            # No space yet, complete normally
            for word in self.words:
                if word.lower().startswith(text_before_cursor.lower()):
                    yield Completion(word, start_position=-len(text_before_cursor))


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

                # Partial path exists check: highlight even if only partially typed
                if os.path.exists(full_path) or any(
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
})

# Shell input
class ShellInput:
    def __init__(self, shell, cmd_prefix="NoPrefixFound!> "):
        self.shell = shell
        self.indexer = CommandIndexer()
        self.history = InMemoryHistory()  # <-- Add history here
        self.session = PromptSession(
            lexer=ShellLexer(shell),
            style=style,
            completer=CommandCompleter(self.indexer.get_commands() + self.shell.command_handler.get_commands(), ignore_case=True),
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