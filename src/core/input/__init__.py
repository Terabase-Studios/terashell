from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.shortcuts import CompleteStyle
from prompt_toolkit.styles import Style

from config import AUTO_COMPLETE, HISTORY_FILE, PROMPT_HIGHLIGHTING
from core.indexer import CommandIndexer
from .completer import CommandCompleter
from .lexer import ShellLexer

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
            or "\\" in last_token  # contains backslash
            or "/" in last_token  # contains forward slash
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


# Lexer with live path highlighting


# Background for autocomplete
autocomplete_bg = "#1a1a1a"

# Style for colors
style_dict = {
    # commands & control
    "command": "bold #c98c6c",
    "built_in": "#69aa71",
    "sudo": "bold #db5d6b",
    "completion-ai": "bold #c4b5fd",

    # arguments & values
    "arg": "#D4D4D4",
    "digit": "#2aacb8",
    "optional": "#737d84",
    "quotes": "italic #69aa71",

    # filesystem
    "path": "#6f94dd",
    "file": "#EDEDED",
    "path_complete": "underline #6f94dd",
    "file_complete": "underline #EDEDED",
    "link": "#7b87b8",

    # environment & errors
    "env_var": "#5f826b",
    "error": "bold #db5d6b",

    # Menu background
    "completion-menu": f"bg:{autocomplete_bg}",
    "completion-menu.completion": f"bg:{autocomplete_bg}",
    "completion-menu.completion.current": f"bg:#444444",
    "scrollbar.background": f"bg:{autocomplete_bg}",
    "scrollbar.arrow": "bg:#444444",
}
style = Style.from_dict(style_dict)


# Shell input
class ShellInput:
    def __init__(self, shell, cmd_prefix="NoPrefixFound!> ", history_file=HISTORY_FILE):
        self.shell = shell
        self.indexer = CommandIndexer(index_path=AUTO_COMPLETE)

        # Use FileHistory for persistent history
        # self.history = ShellFileHistory(shell, history_file)
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
            complete_style=CompleteStyle.MULTI_COLUMN,
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
        for i, line in enumerate(self.history.get_strings()):
            print(f"{i + 1}: {line}")

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
            complete_style=CompleteStyle.MULTI_COLUMN,
            key_bindings=kb
        )
