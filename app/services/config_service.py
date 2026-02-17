import json
from pathlib import Path

CONFIG_PATH = Path("config/config.json")


class ConfigService:
    def load(self):
        if not CONFIG_PATH.exists():
            return {
                "local_paths": {},
                "yadisk_paths": {}
            }
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)

    def save(self, data):
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
