import json
from pathlib import Path

from utils.logger import logger

CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "config.json"

DEFAULT_CONFIG = {
    "local_paths": {
        "processed_photos": "",
        "raw_photos": "",
        "processed_video": "",
        "raw_video": "",
    },
    "yadisk_paths": {
        "processed_photos": "/Медиатека/Богослужения",
        "raw_photos": "/Медиатека/Богослужения",
        "processed_video": "/Медиатека/Богослужения",
        "raw_video": "/Медиатека/Богослужения",
    }
}


def _default_config():
    return {
        "local_paths": DEFAULT_CONFIG["local_paths"].copy(),
        "yadisk_paths": DEFAULT_CONFIG["yadisk_paths"].copy(),
    }


class ConfigService:
    def load(self):
        if not CONFIG_PATH.exists():
            return _default_config()

        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Не удалось прочитать config.json: %s", exc)
            return _default_config()

        if not isinstance(data, dict):
            logger.error("Некорректный config.json: корневой объект не является словарём")
            return _default_config()

        config = _default_config()

        local_paths = data.get("local_paths")
        if isinstance(local_paths, dict):
            config["local_paths"].update(local_paths)

        yadisk_paths = data.get("yadisk_paths")
        if isinstance(yadisk_paths, dict):
            config["yadisk_paths"].update(yadisk_paths)

        return config

    def save(self, data):
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
