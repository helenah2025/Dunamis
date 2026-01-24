"""
Dunamis IRC Bot - Logger

Copyright (C) 2026 Helenah, Helena Bolan <helenah2025@proton.me>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import logging
from pathlib import Path
from datetime import datetime


class Logger:
    _initialized = False
    _log_dir = Path("logs")

    @classmethod
    def setup(cls, log_dir: Path = Path("logs")):
        if cls._initialized:
            return

        cls._log_dir = log_dir
        cls._log_dir.mkdir(exist_ok=True)

        # Clear any existing handlers
        root_logger = logging.getLogger()
        root_logger.handlers.clear()

        # Set level
        root_logger.setLevel(logging.INFO)

        # Create formatter
        formatter = logging.Formatter('%(asctime)s:%(levelname)s: %(message)s')

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

        # File handler
        log_file = cls._log_dir / f"{datetime.now().strftime('%Y-%m-%d')}.log"
        file_handler = logging.FileHandler(log_file, mode='a')
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

        cls._initialized = True

    @staticmethod
    def info(message: str):
        logging.info(message)

    @staticmethod
    def warning(message: str):
        logging.warning(message)

    @staticmethod
    def error(message: str):
        logging.error(message)

    @staticmethod
    def debug(message: str):
        logging.debug(message)
