import os
from pathlib import Path

from dotenv import dotenv_values, set_key
import yadisk


ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
TOKEN_KEY = "YANDEX_TOKEN"


class EnvService:
    def __init__(self, env_path: Path = ENV_PATH):
        self.env_path = Path(env_path)

    def load_token(self) -> str:
        if self.env_path.exists():
            token = dotenv_values(self.env_path).get(TOKEN_KEY)
            if token:
                token = token.strip()
                os.environ[TOKEN_KEY] = token
                return token

        return os.getenv(TOKEN_KEY, "").strip()

    def save_token(self, token: str) -> Path:
        token = token.strip()
        if not token:
            raise ValueError("Токен Яндекс.Диска не указан")

        self.env_path.parent.mkdir(parents=True, exist_ok=True)
        self.env_path.touch(mode=0o600, exist_ok=True)
        set_key(
            self.env_path.as_posix(),
            TOKEN_KEY,
            token,
            quote_mode="never",
        )
        os.environ[TOKEN_KEY] = token
        return self.env_path

    def check_token(self, token: str) -> bool:
        token = token.strip()
        if not token:
            raise RuntimeError("Не найден токен Яндекс.Диска (.env)")

        try:
            return bool(yadisk.YaDisk(token=token).check_token())
        except Exception as exc:
            raise RuntimeError(str(exc)) from exc
