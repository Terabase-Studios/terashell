import os
import shutil
from pathlib import Path

from platformdirs import user_cache_dir


SHELL_NAME = "TeraShell"


def migrate_legacy_cache(legacy_dir=None, cache_dir=None):
    legacy_path = Path(legacy_dir or os.path.expanduser(f"~/.{SHELL_NAME}"))
    cache_path = Path(cache_dir or user_cache_dir(SHELL_NAME, appauthor=False))

    if not legacy_path.exists() or legacy_path.resolve() == cache_path.resolve():
        return False

    cache_path.mkdir(parents=True, exist_ok=True)
    migrated = False

    for item in legacy_path.iterdir():
        target = cache_path / item.name
        if target.exists():
            continue

        shutil.move(str(item), str(target))
        migrated = True

    try:
        legacy_path.rmdir()
    except OSError:
        pass

    return migrated


if __name__ == "__main__":
    migrated_cache = migrate_legacy_cache()
    print("Migrated legacy cache." if migrated_cache else "No legacy cache migrated.")
