import json
import os.path
import sys
from os import makedirs

from platformdirs import user_cache_dir

try:
    from compatability.migrate_cache import migrate_legacy_cache
except ImportError:
    from .compatability.migrate_cache import migrate_legacy_cache

SHELL_NAME = "TeraShell"
VERSION = "0.7.0"

# Cache files
LEGACY_APP_DIR = os.path.expanduser(f"~/.{SHELL_NAME}")
APP_DIR = user_cache_dir(SHELL_NAME, appauthor=False)
migrate_legacy_cache(LEGACY_APP_DIR, APP_DIR)
makedirs(APP_DIR, exist_ok=True)
HISTORY_FILE = os.path.join(APP_DIR, "history.txt")
HELP_FILE = os.path.join(APP_DIR, "cmd_help.json")
INSTANCE_FILE = os.path.join(APP_DIR, "instances.json")
INSTR_FILE = os.path.join(APP_DIR, "instructions.json")
SETTINGS_FILE = os.path.join(APP_DIR, "settings.json")

# For history
IGNORE_SPACE = True

# Waved warning files
DISABLED_WARN_DIR = os.path.join(APP_DIR, "disabled_warn_files")
makedirs(DISABLED_WARN_DIR, exist_ok=True)
MAP_WARN_DISABLED_FILE = os.path.join(DISABLED_WARN_DIR, "map_warn_disabled.txt")

# For Auto Complete and highlighting
AUTO_COMPLETE = True
ONE_FLAG_PER_GROUP = True
COMPLETE_COMMAND = True
COMPLETE_PATHS = True
COMPLETE_ARGS = True
COMPLETE_HISTORY = True

PROMPT_HIGHLIGHTING = True

# For Indexing
PATH_INDEXING = True
PATH_INDEXING_EXCLUDE = ["/mnt/c"]  # paths to exclude from indexing
HELP_FLAGS = ["-h", "--help", "/?", "help"]  # common help flags

# Command Linking Symbols
COMMAND_LINKING_SYMBOLS = ["&&", "||", "|", ">", ">>", "<", "2>", "&>"]

# AI
AI_ENABLED = False
AI_SERVER_IP = "http://localhost:11434"
AI_API_KEY = ""
AI_MODEL = "none"

# Other
SHOW_USER = True
INDIVIDUAL_INSTR_FOR_EACH_INSTANCE = True

DEFAULT_SETTINGS = {
    "history": {
        "IGNORE_SPACE": IGNORE_SPACE,
    },
    "autocomplete": {
        "AUTO_COMPLETE": AUTO_COMPLETE,
        "ONE_FLAG_PER_GROUP": ONE_FLAG_PER_GROUP,
        "COMPLETE_COMMAND": COMPLETE_COMMAND,
        "COMPLETE_PATHS": COMPLETE_PATHS,
        "COMPLETE_ARGS": COMPLETE_ARGS,
        "COMPLETE_HISTORY": COMPLETE_HISTORY,
    },
    "prompt": {
        "PROMPT_HIGHLIGHTING": PROMPT_HIGHLIGHTING,
        "SHOW_USER": SHOW_USER,
    },
    "indexing": {
        "PATH_INDEXING": PATH_INDEXING,
        "PATH_INDEXING_EXCLUDE": PATH_INDEXING_EXCLUDE,
        "HELP_FLAGS": HELP_FLAGS,
    },
    "commands": {
        "COMMAND_LINKING_SYMBOLS": COMMAND_LINKING_SYMBOLS,
    },
    "ai": {
        "AI_ENABLED": AI_ENABLED,
        "AI_SERVER_IP": AI_SERVER_IP,
        "AI_API_KEY": AI_API_KEY,
        "AI_MODEL": AI_MODEL,
    },
    "other": {
        "INDIVIDUAL_INSTR_FOR_EACH_INSTANCE": INDIVIDUAL_INSTR_FOR_EACH_INSTANCE,
    },
}

FLAT_DEFAULT_SETTINGS = {
    key: value
    for category in DEFAULT_SETTINGS.values()
    for key, value in category.items()
}


def _write_settings(settings):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as settings_file:
        json.dump(settings, settings_file, indent=4)
        settings_file.write("\n")


def _flatten_settings(settings):
    flat_settings = {}

    for key, value in settings.items():
        if key in FLAT_DEFAULT_SETTINGS:
            flat_settings[key] = value
        elif isinstance(value, dict):
            flat_settings.update(
                {
                    setting_name: setting_value
                    for setting_name, setting_value in value.items()
                    if setting_name in FLAT_DEFAULT_SETTINGS
                }
            )

    return flat_settings


def _categorize_settings(flat_settings):
    return {
        category: {
            key: flat_settings.get(key, default_value)
            for key, default_value in category_settings.items()
        }
        for category, category_settings in DEFAULT_SETTINGS.items()
    }


def _load_settings():
    if not os.path.exists(SETTINGS_FILE):
        _write_settings(DEFAULT_SETTINGS)
        return FLAT_DEFAULT_SETTINGS.copy()

    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as settings_file:
            settings = json.load(settings_file)
    except (OSError, json.JSONDecodeError):
        settings = {}

    if not isinstance(settings, dict):
        settings = {}

    merged_settings = FLAT_DEFAULT_SETTINGS.copy()
    merged_settings.update(_flatten_settings(settings))
    categorized_settings = _categorize_settings(merged_settings)

    if categorized_settings != settings:
        _write_settings(categorized_settings)

    return merged_settings


def save_settings(**updates):
    settings = _load_settings()
    settings.update({key: value for key, value in updates.items() if key in FLAT_DEFAULT_SETTINGS})
    _write_settings(_categorize_settings(settings))

    for key, value in updates.items():
        if key in FLAT_DEFAULT_SETTINGS:
            globals()[key] = value


def reset_settings():
    _write_settings(DEFAULT_SETTINGS)

    for key, value in FLAT_DEFAULT_SETTINGS.items():
        globals()[key] = value


for _setting_name, _setting_value in _load_settings().items():
    globals()[_setting_name] = _setting_value

del _setting_name, _setting_value

# Get os
PLATFORM = sys.platform
IS_WINDOWS = PLATFORM.startswith("win")
IS_LINUX = PLATFORM.startswith("linux")
IS_MAC = PLATFORM.startswith("darwin")
IS_UNIX = IS_LINUX or IS_MAC
