import json
import os
import threading
from pathlib import Path


class Config:
    def __init__(self):
        self.config_dir  = Path(os.environ.get("APPDATA", Path.home())) / "GamePill"
        self.config_file = self.config_dir / "config.json"
        self._data: dict = {}
        self._lock = threading.Lock()
        self._load()

    def _load(self):
        if self.config_file.exists():
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    self._data = json.load(f)
            except (json.JSONDecodeError, IOError):
                self._data = {}

    def _save(self):
        self.config_dir.mkdir(parents=True, exist_ok=True)
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)

    def get(self, key, default=None):
        with self._lock:
            return self._data.get(key, default)

    def set(self, key, value):
        with self._lock:
            self._data[key] = value
            self._save()

    @property
    def is_first_launch(self):
        return not self.config_file.exists() or not self._data
