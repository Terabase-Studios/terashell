import subprocess
import time
from collections import deque

import psutil

import ai
import config

_cpu_history = deque([0, 0, 0, 0, 0, 0, 0, 0, 0, 0], maxlen=10)
_last_update = 0
_cached_cpu = 0


BLOCKS = "▁▂▃▄▅▆▇█"

def make_graph(history):
    blocks = "▁▂▃▄▅▆▇█"

    if not history:
        return ""

    max_v = max(history) or 1

    graph = ""
    for v in history:
        idx = int((v / 100) * (len(blocks) - 1))
        graph += blocks[idx]

    return graph


def get_cpu():
    global _last_update, _cached_cpu

    now = time.time()

    if now - _last_update > 0.5:
        _cached_cpu = psutil.cpu_percent(interval=None)
        _cpu_history.append(_cached_cpu)
        _last_update = now

    return _cached_cpu


def get_git_info():
    try:
        branch = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            stderr=subprocess.DEVNULL
        ).decode().strip()

        diff = subprocess.check_output(
            ["git", "diff", "--shortstat"],
            stderr=subprocess.DEVNULL
        ).decode().strip()

        additions = 0
        deletions = 0

        if diff:
            # example: "2 files changed, 10 insertions(+), 3 deletions(-)"
            parts = diff.split(",")

            for p in parts:
                p = p.strip()
                if "insertion" in p:
                    additions = int(p.split()[0])
                elif "deletion" in p:
                    deletions = int(p.split()[0])

        return branch, additions, deletions

    except Exception:
        return None, 0, 0


def bottom_toolbar():
    parts = []

    cpu = get_cpu()
    cpu_graph = make_graph(_cpu_history)


    cpu_style = (
        "class:cpu.high" if cpu > 80
        else "class:cpu.medium" if cpu > 50
        else "class:cpu.low"
    )

    parts.append((cpu_style, f"CPU {cpu:3.0f}% {cpu_graph}"))

    parts.append(("", " │ "))

    # RAM
    mem = psutil.virtual_memory()
    mem_percent = mem.percent

    used_gb = mem.used / (1024 ** 3)
    total_gb = mem.total / (1024 ** 3)

    mem_style = (
        "class:ram.high" if mem_percent > 80
        else "class:ram.medium" if mem_percent > 50
        else "class:ram.low"
    )

    parts.append((
        mem_style,
        f"RAM {mem_percent:3.0f}% {used_gb:.1f}/{total_gb:.1f}GB"
    ))

    parts.append(("", " │ "))

    # AI state (unchanged but cleaner)
    ai_enabled = config.AI_ENABLED and ai.AI_INTERFACE

    if not ai_enabled:
        ai_style = "class:ai.off"
        ai_state = "OFF"
    elif ai.is_working():
        ai_style = "class:ai.work"
        ai_state = "BUSY"
    else:
        ai_style = "class:ai.idle"
        ai_state = "IDLE"

    parts.append((ai_style, f"AI {ai_state}"))


    branch, adds, dels = get_git_info()


    if branch:
        parts.append(("", " │ "))
        parts.append(("class:git.branch", f"{branch} "))
        parts.append(("class:git.plus", f"+{adds} "))
        parts.append(("class:git.minus", f"-{dels}"))

    return parts