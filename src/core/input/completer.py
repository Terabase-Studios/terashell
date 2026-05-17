import os

from prompt_toolkit.completion import Completer, Completion

import ai
import config
from ai.translation import translate_to_command
from config import COMPLETE_ARGS, COMPLETE_PATHS, COMPLETE_HISTORY

ai_mode = False

class CommandCompleter(Completer):
    """
    Two-mode command completer:
    1. First word: top-level commands.
    2. Body: subcommands, flags, paths, and history after the last token.
    """

    def __init__(self, input_handler, extra_commands=None, ignore_case=True, completer_style=None):
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
    def _complete_path(self, text_before_cursor, working_dir=None):
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

        # TODO: This can cause problems so here it is for future me, Later: okay but why?
        if "." in text_before_cursor:
            return []

        paths = self._complete_path_raw(
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
                    style="class:quotes" if quoted else "class:path",
                    display_meta="QUOTED PATH" if quoted else "PATH",
                )
            )
        return out

    @staticmethod
    def _complete_path_raw(
            text_before_cursor: str,
            working_dir = None,
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
    def _complete_command(self, text, no_sudo=False, built_in_index=0):
        sudo = []
        built_in = []
        command = []
        for cmd in self.commands:
            cmd_name = cmd.split(".")[0]
            match = cmd_name.lower().startswith(text.lower()) if self.ignore_case else cmd_name.startswith(text)
            if match:
                if cmd_name == "sudo":
                    if no_sudo:
                        continue
                    color = "class:sudo"
                    sudo.append(Completion(cmd_name.split()[0], start_position=-len(text), style=color, display_meta="SUDO",))

                elif cmd_name in self.built_in_commands:
                    color = "class:built_in"
                    built_in.append(Completion(cmd_name.split()[0], start_position=-len(text), style=color, display_meta="BUILT-IN",))

                else:
                    color = "class:command"
                    command.append(Completion(cmd_name.split()[0], start_position=-len(text), style=color, display_meta="INDEXED COMMAND",))

        return sudo + built_in + command

    def _complete_build_in_arg(self, text, built_in_index=1):
        out = []
        text_tokens = text.split()
        text_arg = text_tokens[built_in_index] if built_in_index < len(text_tokens) else ""
        if not text_tokens:
            return []
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
    def complete_deterministic(self, last_token, text_before_cursor, token_index, tool_index):
        out = []
        found_path = False

        if COMPLETE_ARGS:
            out += self._complete_build_in_arg(text_before_cursor.removeprefix("sudo"))
            suggested = self.help_indexer.help_indexer.get_suggested(text_before_cursor)
            command_suggestions = suggested.get("subcommand_suggestions", [])
            if text_before_cursor[-1] == " " or last_token.startswith("-") or last_token.startswith(
                    "--") or last_token.startswith("/"):
                optional_suggestions = suggested.get("option_suggestions", [])
            else:
                optional_suggestions = suggested.get("optional_suggestions", [])

            partial = suggested.get("partial", True)

            for s in command_suggestions:
                out.append(
                    Completion(
                        s,
                        start_position=-len(last_token) if partial else 0,
                        style="class:arg",
                        display_meta="MAP - ARGUMENT",
                    )
                )

            for s in optional_suggestions:
                out.append(
                    Completion(
                        s,
                        start_position=-len(last_token) if partial else 0,
                        style="class:optional",
                        display_meta="MAP - OPTIONAL",
                    )
                )

        if COMPLETE_PATHS:
            paths = self._complete_path(text_before_cursor, self.input_handler.shell.working_dir)
            if paths:
                found_path = True
                out.extend(paths)

        if COMPLETE_HISTORY:
            out = self._complete_history(text_before_cursor, tool_index, token_index, last_token,
                                         self.input_handler.shell.working_dir) + out

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

        def _verify_path(token: str, working_dir) -> bool:
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

            candidate = words[token_index if text_before_cursor.endswith(" ") else token_index - 1]

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
                        display_meta="HISTORY",
                    )
                )
                seen.add(key)

        return out

    @staticmethod
    def ellipsize_left(text: str, max_len: int) -> str:
        if len(text) <= max_len:
            return ""
        return ": ..." + text[-(max_len - 3):]

    # -------------------- AI -------------------- #
    @staticmethod
    def ai_limit_history(history, max_items=25):
        seen = set()
        out = []

        for item in history[::-1]:  # newest first
            if item in seen:
                continue
            seen.add(item)
            out.append(item)

            if len(out) >= max_items:
                break

        return out[::-1]


    @staticmethod
    def ai_get_nearby_files(cwd: str, prefix: str, limit: int = 30):
        try:
            items = os.listdir(cwd)
        except Exception:
            return []

        token = (prefix.split(" ")[-1] if prefix else "").lower()

        if token:
            filtered = [i for i in items if i.lower().startswith(token)]
        else:
            filtered = items

        return filtered[:limit]


    def complete_ai(self, text):
        out = []

        if config.AI_ENABLED and ai.AI_INTERFACE:
            current_os = config.PLATFORM
            cwd = self.input_handler.shell.working_dir
            nearby_files = self.ai_get_nearby_files(cwd, prefix=text)
            history = self.ai_limit_history(self.input_handler.get_history())
            history_text = ", ".join(history)
            nearby_files_text = ", ".join(nearby_files)

            ai_completions = [translate_to_command(text, os=current_os, cwd=cwd)]
            ai_completions.extend(
                ai.AI_INTERFACE.autocomplete
                (
                    text,
                    os=current_os,
                    cwd=cwd,
                    nearby_files=nearby_files_text,
                    history_text=history_text,
                )
            )

            for i, completion in enumerate(ai_completions):
                if not completion:
                    continue

                completion = completion.strip()

                insert_text = completion

                display = self.ellipsize_left(insert_text, 50)


                out.append(
                    Completion(
                        insert_text,
                        start_position=-len(text),
                        style="class:completion-ai",
                        display_meta=f"AI{display}" if i != 0 else f"AI (Natural -> Command){display}",
                    )
                )
        return out


    # -------------------- Utility -------------------- #
    def _matches_token(self, candidate, token):
        return candidate.lower().startswith(token.lower()) if self.ignore_case else candidate.startswith(token)

    @staticmethod
    def _yield_autocomplete_errors(messages=None):
        if messages is None:
            messages = ["NULL", "NULL", "NULL"]
        for message in messages:
            yield Completion(
                text="",
                display=f"{message}",
                start_position=0,
                style="class:error",
                display_meta="ERROR",
            )

    # -------------------- Main entry -------------------- #
    def get_completions(self, document, complete_event):
        global ai_mode
        try:

            text = document.text_before_cursor
            tokens = text.split()
            candidates = []

            # AI-only mode
            if ai_mode:
                completions = self.complete_ai(text)
                if len(completions) > 0:
                    for c in completions:
                        yield c
                else:
                    yield Completion(
                        "NO RESULT",
                        start_position=-len(text),
                        style="class:completion-ai",
                        display_meta="AI"
                    )
                ai_mode = False
                return

            if not tokens:
                candidates.extend(self._complete_command(""))
                for c in self._dedupe(candidates):
                    yield c
                return

            tool_offset = tokens[0] == "sudo"
            tool_index = 1 if tool_offset else 0
            start_whitespace = " " if text[0] == " " else ""
            end_whitespace = " " if text[-1] == " " else ""

            if text == "sudo ":
                candidates.extend(self._complete_command("", no_sudo=True))
                for c in self._dedupe(candidates):
                    yield c
                return

            last_token = tokens[-1]
            candidates.extend(
                self.complete_deterministic(
                    last_token,
                    text,
                    token_index=len(tokens),
                    tool_index=tool_index,
                )
            )

            if len(tokens) == 1 and not text.endswith(" "):
                candidates.extend(
                    self._complete_command(tokens[0])
                )
                for c in self._dedupe(candidates):
                    if not c.style == "class:arg":
                        yield c
            else:
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
