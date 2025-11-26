import os.path
from os import makedirs

SHELL_NAME = "terashell"

APP_DIR = os.path.expanduser(f"~/.{SHELL_NAME}")
makedirs(APP_DIR, exist_ok=True)
HELP_FILE = os.path.join(APP_DIR, "cmd_help.json")

# For Indexing
AUTO_COMPLETE = True
PATH_INDEXING = True
HELP_FLAGS = ["-h", "--help", "/?", "help"]  # common help flags
EXTRA_POSITIONAL_HEADERS = []
EXTRA_SUB_COMMAND_HEADERS = []
EXTRA_FLAG_HEADERS = []