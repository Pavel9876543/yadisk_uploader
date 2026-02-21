"""
Централизованный логгер приложения.
"""

import logging
import sys

logger = logging.getLogger("yadisk_uploader")
logger.setLevel(logging.DEBUG)

formatter = logging.Formatter(
    "[%(asctime)s] %(levelname)s | %(name)s | %(message)s"
)

# 🔹 В консоль
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(formatter)

logger.addHandler(console_handler)