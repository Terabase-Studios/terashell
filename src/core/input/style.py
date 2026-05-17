from prompt_toolkit.styles import Style


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

    # Bottom toolbar
    "bottom-toolbar": "noreverse bg:#1a1a1a",
    "cpu.low":    "noreverse fg:#4FC3F7",
    "cpu.medium": "noreverse fg:#FFB74D",
    "cpu.high":   "noreverse fg:#EF5350 bold",

    "ram.low":    "noreverse fg:#4FC3F7",
    "ram.medium": "noreverse fg:#FFB74D",
    "ram.high":   "noreverse fg:#EF5350 bold",

    "ai.off": "noreverse fg:#737d84",
    "ai.idle": "noreverse fg:#69aa71",
    "ai.work": "noreverse fg:#c4b5fd bold",
    "git.branch": "fg:#aaaaaa",
    "git.plus": "fg:#2ecc71",
    "git.minus": "fg:#e74c3c",
}


style = Style.from_dict(style_dict)