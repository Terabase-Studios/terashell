import os
import re
import pytest
from collections import Counter
from input import ShellLexer, style

# ---------- Prepare formating ----------
# Map basic colors to ANSI codes
basic_colors = {
    'ansiblack': 30, 'ansired': 31, 'ansigreen': 32, 'ansiyellow': 33,
    'ansiblue': 34, 'ansimagenta': 35, 'ansicyan': 36, 'ansiwhite': 97,  # <- bright white
    'ansigray': 92
}

def parse_style_string(s):
    """Convert PTK style string to ANSI escape codes."""
    codes = []
    if not s:
        return ''
    for part in s.split():
        part = part.lower()
        if part == 'bold':
            codes.append('1')
        elif part == 'underline':
            codes.append('4')
        elif part == 'italic':
            codes.append('3')
        elif part.startswith('#') and re.match(r'^#[0-9a-f]{6}$', part):
            r = int(part[1:3], 16)
            g = int(part[3:5], 16)
            b = int(part[5:7], 16)
            codes.append(f'38;2;{r};{g};{b}')
        elif part in basic_colors:
            codes.append(str(basic_colors[part]))
    return ';'.join(codes)

# Build ANSI mapping from the style object
ansi_mapping = {cls: parse_style_string(s) for cls, s in style.style_rules}

def style_to_ansi(cls, text):
    """Wrap text with ANSI escape codes from style."""
    code = ansi_mapping.get(cls.replace("class:", ""), '')
    reset = '\033[0m'
    return f'\033[{code}m{text}{reset}' if code else text
# ---------------------------------------


@pytest.fixture
def fake_fs(tmp_path):
    """
    Creates all files and directories necessary for the test command:
    'sudo ls -l file.txt /home/user && echo $USER 123 unknowncmd "quoted text" ./partial /dev/nu file.txt/'
    """
    workdir = tmp_path / "workdir"
    workdir.mkdir()

    # File for 'file.txt' and 'error/' (path_complete)
    (workdir / "file_complete.txt").write_text("test")
    (workdir / "permission_denied").write_text("error")

    # Subdirectory to simulate /home/user
    home_dir = workdir / "home" / "complete_dir"
    home_dir.mkdir(parents=True)
    (home_dir / "dummy.txt").write_text("dummy")  # so /home/user is not empty

    # Partial match for 'file_partia'
    (workdir / "file_partial.txt").write_text("partial content")

    # /dev/nu directory/file
    dev_dir = workdir / "dev"
    dev_dir.mkdir()
    (dev_dir / "partial_dir").write_text("")

    print("\n[lexer test] working dir tree:")
    for root, dirs, files in os.walk(workdir):
        level = root.replace(str(workdir), "").count(os.sep)
        indent = "  " * level
        print(f"{indent}{os.path.basename(root)}/")
        for f in files:
            print(f"{indent}  {f}")

    return workdir


class FakeDocument:
    def __init__(self, text):
        self.text = text

class FakeShell:
    class FakeCommandHandler:
        def __init__(self):
            pass
        def get_commands(self):
            return {"builtin"}
    def __init__(self, working_dir="c:\\"):
        self.working_dir = working_dir
        self.command_handler = self.FakeCommandHandler()


@pytest.fixture
def shell(fake_fs):
    """Fixture to create a ShellCommands instance with a mock shell."""
    return FakeShell(working_dir=fake_fs)


def test_shell_lexing(shell, capsys):
    """
    Ensures every lexer token type is produced exactly once.
    """
    print("\n[test_shell_lexing] --- Running Lexer Test ---")

    lexer = ShellLexer(shell)

    # Command engineered to trigger EVERY token type once
    command = (
        'sudo builtin "quoted text" --optional file_partia file_complete.txt'
        '&& tool $ENV_VAR 123 '
        'subcommand '
        'dev/partial_di  home/complete_dir/ permission_denied/'
        ''
    )

    print("[test_shell_lexing] --- Command Before Lexing ---")
    print(command)

    document = FakeDocument(command)
    get_line = lexer.lex_document(document)
    tokens = get_line(0)

    normalized = [(cls.replace("class:", ""), val) for cls, val in tokens if cls]

    print("[test_shell_lexing] --- Tokens After Lexing ---")
    for cls, val in normalized:
        print(f"[test_shell_lexing] {cls:15} {repr(val)}")

    # Count token occurrences
    token_counts = Counter(cls for cls, _ in normalized)

    expected_tokens = {
        "command",
        "sudo",
        "link",
        "arg",
        "digit",
        "optional",
        "path",
        "file",
        "path_complete",
        "file_complete",
        "env_var",
        "built_in",
        "error",
        "quotes",
    }

    # Check for missing tokens
    missing = expected_tokens - set(token_counts.keys())
    if missing:
        print("[test_shell_lexing] --- Missing Token Types ---")
        for m in sorted(missing):
            print(f"[test_shell_lexing] {m}")

    # Check for duplicates
    duplicates = {cls: count for cls, count in token_counts.items() if count > 1}
    if duplicates:
        print("[test_shell_lexing] --- Duplicate Token Types ---")
        for cls, count in duplicates.items():
            print(f"[test_shell_lexing] {cls}: {count}")

    # Print colored output
    colored_output = "".join(style_to_ansi(cls, val) + " " for cls, val in normalized)
    print("[test_shell_lexing] --- Colored Lexed Output ---")
    print(colored_output)

    # Assert no missing or duplicate tokens
    assert not missing, f"Lexer did not produce tokens: {missing}"
    assert not duplicates, f"Lexer produced duplicate tokens: {duplicates}"
