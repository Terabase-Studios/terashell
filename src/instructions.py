import os
import json
from sys import exception


class InstructionHelper:
    def __init__(self, filepath):
        self.filepath = filepath
        self.steps = []
        self._load()

    def _load(self):
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.steps = data.get("steps", [])
            except Exception:
                self.steps = []  # corrupted file? just reset =(

    def _save(self):
        try:
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump({"steps": self.steps}, f, indent=2)
        except Exception:
            pass  # silently ignore write failure =(

    def add(self, text):
        self.steps.append(text)
        self._save()

    def remove(self):
        removed = self.steps.pop(-1)
        self._save()
        return removed

    def list(self):
        return "\n".join(f"{i+1}. {step}" for i, step in enumerate(self.steps))

    def clear(self):
        self.steps = []
        self._save()

    def save_markdown(self, filename):
        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.write(self.list())
            return True
        except Exception as e:
            print("Failed to save file: ", e)
            return False
            
