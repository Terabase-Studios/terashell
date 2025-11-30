import os.path
import sys
from os import makedirs

SHELL_NAME = "TeraShell"

# Cache files
APP_DIR = os.path.expanduser(f"~/.{SHELL_NAME}")
makedirs(APP_DIR, exist_ok=True)
HISTORY_FILE = os.path.join(APP_DIR, "history")
HELP_FILE = os.path.join(APP_DIR, "cmd_help.json")
INSTANCE_FILE = os.path.join(APP_DIR, "instances.json")
INSTR_FILE = os.path.join(APP_DIR, "instructions.json")

# Waved warning files
DISABLED_WARN_DIR = os.path.join(APP_DIR, "disabled_warn_files")
makedirs(DISABLED_WARN_DIR, exist_ok=True)
MAP_WARN_DISABLED_FILE = os.path.join(DISABLED_WARN_DIR, "map_warn_disabled.txt")

# For Auto Complete and highlighting
AUTO_COMPLETE = True
ONE_FLAG_PER_GROUP = True
ALWAYS_SUGGEST_HISTORY = False
PROMPT_HIGHLIGHTING = True

# For Indexing
PATH_INDEXING = True
HELP_FLAGS = ["-h", "--help", "/?", "help"]  # common help flags

#Other
SHOW_USER = True
INDIVIDUAL_INSTR_FOR_EACH_INSTANCE = True

# Get os
IS_WINDOWS = sys.platform.startswith("win")
IS_LINUX = sys.platform.startswith("linux")
IS_MAC = sys.platform.startswith("darwin")
IS_UNIX = IS_LINUX or IS_MAC