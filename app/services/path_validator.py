from pathlib import Path


class PathValidator:
    @staticmethod
    def validate_local_path(path: str) -> bool:
        if not path:
            return False
        return Path(path).exists() and Path(path).is_dir()