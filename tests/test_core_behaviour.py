import json
import sys
import unittest
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

import yadisk
from requests.exceptions import Timeout

from integrations.yadisk_client import YadiskClient
from services import config_service
from services.config_service import ConfigService
from services.yadisk_path_builder import build_yadisk_path
from utils.error_translator import translate_exception


class FakeDisk:
    def __init__(self):
        self.paths = {"/"}
        self.uploaded = []
        self.existing_files = set()

    def exists(self, path):
        return path in self.paths or path in self.existing_files

    def mkdir(self, path):
        self.paths.add(path)

    def upload(self, local, remote, overwrite=False):
        self.uploaded.append((Path(local).name, remote, overwrite))
        self.existing_files.add(remote)


class PathBuilderTest(unittest.TestCase):
    def test_builds_category_path_with_date(self):
        result = build_yadisk_path(
            base_path="/Медиатека/Богослужения",
            category="raw_video",
            now=datetime(2026, 7, 17),
        )

        self.assertEqual(
            result,
            "/Медиатека/Богослужения/2026/2026.07.17/Исходники/Видео",
        )


class ConfigServiceTest(unittest.TestCase):
    def setUp(self):
        self.original_config_path = config_service.CONFIG_PATH

    def tearDown(self):
        config_service.CONFIG_PATH = self.original_config_path

    def test_missing_config_returns_defaults(self):
        with TemporaryDirectory() as tmp:
            config_service.CONFIG_PATH = Path(tmp) / "config.json"

            config = ConfigService().load()

        self.assertIn("processed_photos", config["local_paths"])
        self.assertEqual(
            config["yadisk_paths"]["processed_photos"],
            "/Медиатека/Богослужения",
        )

    def test_invalid_config_returns_defaults(self):
        with TemporaryDirectory() as tmp:
            config_service.CONFIG_PATH = Path(tmp) / "config.json"
            config_service.CONFIG_PATH.write_text("{bad json", encoding="utf-8")

            config = ConfigService().load()

        self.assertEqual(config["local_paths"]["raw_photos"], "")

    def test_partial_config_is_merged_with_defaults(self):
        with TemporaryDirectory() as tmp:
            config_service.CONFIG_PATH = Path(tmp) / "config.json"
            config_service.CONFIG_PATH.write_text(
                json.dumps({
                    "local_paths": {"raw_photos": "/tmp/raw"},
                    "yadisk_paths": {"raw_photos": "/Custom/Base"},
                }),
                encoding="utf-8",
            )

            config = ConfigService().load()

        self.assertEqual(config["local_paths"]["raw_photos"], "/tmp/raw")
        self.assertEqual(config["yadisk_paths"]["raw_photos"], "/Custom/Base")
        self.assertIn("processed_video", config["local_paths"])


class YadiskClientTest(unittest.TestCase):
    def test_upload_folder_preserves_nested_paths_and_counts_skips(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a" / "b").mkdir(parents=True)
            (root / "a" / "b" / "file.jpg").write_bytes(b"123")
            (root / "skip.txt").write_bytes(b"12")

            client = object.__new__(YadiskClient)
            client.disk = FakeDisk()
            client.disk.existing_files.add("/disk/root/skip.txt")

            progress = []
            skipped = []
            client.upload_folder(
                root,
                "/disk/root",
                on_progress=lambda done, total: progress.append((done, total)),
                on_skip=skipped.append,
            )

        self.assertIn(("file.jpg", "/disk/root/a/b/file.jpg", False), client.disk.uploaded)
        self.assertIn("/disk/root/a/b", client.disk.paths)
        self.assertEqual([path.name for path in skipped], ["skip.txt"])
        self.assertEqual(progress[-1], (5, 5))


class ErrorTranslatorTest(unittest.TestCase):
    def test_uses_wrapped_yadisk_error(self):
        exc = RuntimeError("Ошибка загрузки файла:\nvideo.mp4")
        exc.__cause__ = yadisk.exceptions.ForbiddenError("forbidden")

        self.assertIn("Недостаточно прав", translate_exception(exc))

    def test_uses_wrapped_network_error(self):
        exc = RuntimeError("Ошибка загрузки файла:\nvideo.mp4")
        exc.__cause__ = Timeout("timeout")

        self.assertIn("интернет", translate_exception(exc))

    def test_translates_common_runtime_messages(self):
        self.assertIn(
            "Не найден токен",
            translate_exception(RuntimeError("Не найден токен Яндекс.Диска (.env)")),
        )
        self.assertIn(
            "Не указан путь",
            translate_exception(RuntimeError("Не указан путь на Яндекс.Диске")),
        )
        self.assertIn(
            "прервана",
            translate_exception(RuntimeError("Загрузка прервана пользователем")),
        )


if __name__ == "__main__":
    unittest.main()
