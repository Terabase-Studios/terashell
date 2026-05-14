import os

from prompt_toolkit.lexers import Lexer

from config import COMMAND_LINKING_SYMBOLS


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
            seen_command = False

            def flush_word(word, i, quoted=False):
                nonlocal seen_command
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
                        tokens.append(("class:quotes", word))
                    elif word.lower() == "sudo" and i == 0:
                        tokens.append(("class:sudo", word))
                    elif not seen_command:
                        seen_command = True
                        if word.strip() in self.shell.command_handler.get_commands():
                            tokens.append(("class:built_in", word))
                        else:
                            tokens.append(("class:command", word))
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
