"""Вывод ls с виртуальными Unix-метаданными и ключами -l, -a, -h."""

from dataclasses import dataclass, field
from datetime import timezone

from src.vfs import Node, VFS


SIZE_BASE = 1024
SIZE_UNITS = ("", "K", "M", "G", "T", "P", "E")
VIRTUAL_OWNER = "vfs"
VIRTUAL_GROUP = "vfs"
DIRECTORY_LINKS = 2
DIRECTORY_MODE = "drwxr-xr-x"
FILE_MODE = "-rw-r--r--"


@dataclass
class Options:
    """Ключи ls и пути после разбора аргументов."""

    flags: set[str] = field(default_factory=set)
    paths: list[str] = field(default_factory=list)

    @classmethod
    def parse(cls, arguments: list[str]) -> "Options":
        """Прочитать короткие ключи до разделителя -- без изменения ввода."""
        result = cls()
        options_enabled = True
        for argument in arguments:
            if options_enabled and argument == "--":
                options_enabled = False
            elif options_enabled and argument.startswith("-"):
                if argument == "-":
                    result.paths.append(argument)
                    continue
                flags = argument[1:]
                unknown = set(flags) - set("lah")
                if unknown:
                    raise ValueError(
                        "неизвестные ключи: " + ", ".join(sorted(unknown))
                        + "; допустимы -l, -a, -h"
                    )
                result.flags.update(flags)
            else:
                result.paths.append(argument)
        return result


def readable_size(size: int) -> str:
    """Вернуть байты или число с одним десятичным знаком и суффиксом."""
    value = float(size)
    for unit in SIZE_UNITS:
        if round(value, 1) < SIZE_BASE or unit == SIZE_UNITS[-1]:
            return str(size) if not unit else f"{value:.1f}{unit}"
        value /= SIZE_BASE
    return str(size)


class Listing:
    """Сформировать ls с синтетическими правами и владельцем vfs."""

    def __init__(self, vfs: VFS) -> None:
        """Сохранить виртуальное дерево без обращения к реальным файлам."""
        self.vfs = vfs

    def execute(self, arguments: list[str], cwd: str) -> str:
        """Вывести указанные пути с заголовками для нескольких аргументов."""
        options = Options.parse(arguments)
        paths = options.paths or ["."]
        output = []
        for path in paths:
            node = self.vfs.get(path, cwd)
            if len(paths) > 1:
                output.append(f"{path}:")
            for name, item in self._entries(node, path, cwd, options):
                output.append(self._format(name, item, options))
        return "\n".join(output)

    def _entries(
        self, node: Node, path: str, cwd: str, options: Options
    ) -> list[tuple[str, Node]]:
        """Отфильтровать скрытые имена и при -a добавить . и .. ."""
        if not node.is_dir:
            return [(node.name, node)]
        entries = []
        if "a" in options.flags:
            absolute = self.vfs.normalize(path, cwd)
            parent = self.vfs.get("..", absolute)
            entries.extend([(".", node), ("..", parent)])
        entries.extend(
            (name, child) for name, child in sorted(node.children.items())
            if "a" in options.flags or not name.startswith(".")
        )
        return entries

    @staticmethod
    def _format(name: str, node: Node, options: Options) -> str:
        """Вывести имя или права, ссылки, владельца, размер и время UTC."""
        if "l" not in options.flags:
            return name
        mode = DIRECTORY_MODE if node.is_dir else FILE_MODE
        links = 1
        if node.is_dir:
            links = DIRECTORY_LINKS + sum(
                child.is_dir for child in node.children.values()
            )
        size = 0 if node.is_dir else len(node.content)
        size_text = readable_size(size) if "h" in options.flags else str(size)
        date = node.modified_at.astimezone(timezone.utc).strftime(
            "%Y-%m-%d %H:%M"
        )
        return (f"{mode} {links} {VIRTUAL_OWNER} {VIRTUAL_GROUP} "
                f"{size_text} {date} {name}")
