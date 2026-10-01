"""Параметры запуска эмулятора."""

import argparse
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Config:
    """Пути к виртуальной файловой системе и стартовому скрипту."""

    vfs: Path | None
    startup: Path | None


def parse_args() -> Config:
    """Прочитать параметры командной строки."""
    parser = argparse.ArgumentParser(description="Эмулятор shell, вариант 17")
    parser.add_argument("--vfs", type=Path, help="путь к XML-файлу VFS")
    parser.add_argument(
        "--startup", type=Path, help="путь к стартовому скрипту"
    )
    options = parser.parse_args()
    return Config(options.vfs, options.startup)
