import os.path
from os import makedirs

SHELL_NAME = "terashell"

APP_DIR = os.path.expanduser(f"~/.{SHELL_NAME}")
makedirs(APP_DIR, exist_ok=True)
HISTORY_FILE = os.path.join(APP_DIR, "history")
HELP_FILE = os.path.join(APP_DIR, "cmd_help.json")

# Waved warning files
DISABLED_WARN_DIR = os.path.join(APP_DIR, "disabled_warn_files")
makedirs(DISABLED_WARN_DIR, exist_ok=True)
MAP_WARN_DISABLED_FILE = os.path.join(DISABLED_WARN_DIR, "map_warn_disabled.txt")

AUTO_COMPLETE = True
PROMPT_HIGHLIGHTING = True

# For Indexing
PATH_INDEXING = True
HELP_FLAGS = ["-h", "--help", "/?", "help"]  # common help flags
EXTRA_POSITIONAL_HEADERS = []
EXTRA_SUB_COMMAND_HEADERS = []
EXTRA_FLAG_HEADERS = []