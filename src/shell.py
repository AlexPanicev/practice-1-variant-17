"""Разбор и выполнение команд эмулятора."""

import shlex
from dataclasses import dataclass

from src.listing import Listing
from src.vfs import Node, VFS


@dataclass
class Result:
    """Текст ответа и признак завершения сеанса."""

    output: str = ""
    exit_requested: bool = False


class Shell:
    """Оболочка с текущим каталогом и командами для VFS."""

    def __init__(self, vfs: VFS | None = None) -> None:
        """Начать сеанс в корне заданной виртуальной файловой системы."""
        self.vfs = vfs
        self.cwd = "/"

    def execute(self, line: str, comments: bool = False) -> Result:
        """Разобрать одну строку и вернуть результат команды."""
        try:
            words = shlex.split(line, comments=comments)
        except ValueError as error:
            return Result(f"Ошибка синтаксиса: {error}")
        if not words:
            return Result()
        command, *arguments = words
        if command == "exit":
            if arguments:
                return Result("exit: аргументы не поддерживаются")
            return Result(exit_requested=True)
        commands = {
            "ls": self._ls,
            "cd": self._cd,
            "wc": self._wc,
            "tree": self._tree,
            "touch": self._touch,
        }
        if command not in commands:
            return Result(f"{command}: команда не найдена")
        if self.vfs is None:
            return Result(f"{command}: VFS не загружена")
        try:
            return Result(commands[command](arguments))
        except (FileNotFoundError, NotADirectoryError,
                IsADirectoryError, ValueError) as error:
            return Result(f"{command}: {error}")

    def _ls(self, arguments: list[str]) -> str:
        """Вывести имена или виртуальные метаданные с ключами ls."""
        assert self.vfs is not None
        return Listing(self.vfs).execute(arguments, self.cwd)

    def _cd(self, arguments: list[str]) -> str:
        """Изменить текущий виртуальный каталог."""
        assert self.vfs is not None
        if len(arguments) > 1:
            raise ValueError("слишком много аргументов")
        path = arguments[0] if arguments else "/"
        node = self.vfs.get(path, self.cwd)
        if not node.is_dir:
            raise ValueError(f"не каталог: {path}")
        self.cwd = self.vfs.normalize(path, self.cwd)
        return ""

    def _wc(self, arguments: list[str]) -> str:
        """Посчитать строки, слова и байты указанных файлов."""
        assert self.vfs is not None
        flags = self._wc_flags(arguments)
        if not arguments:
            raise ValueError("укажите хотя бы один файл")
        totals = [0, 0, 0]
        rows = []
        for path in arguments:
            node = self.vfs.get(path, self.cwd)
            if node.is_dir:
                raise ValueError(f"не файл: {path}")
            data = node.content
            counts = [data.count(b"\n"), len(data.split()), len(data)]
            totals = [left + right for left, right in zip(totals, counts)]
            rows.append(self._format_counts(counts, flags, path))
        if len(arguments) > 1:
            rows.append(self._format_counts(totals, flags, "итого"))
        return "\n".join(rows)

    @staticmethod
    def _wc_flags(arguments: list[str]) -> str:
        """Извлечь и проверить необязательные ключи команды wc."""
        if not arguments or not arguments[0].startswith("-"):
            return "lwc"
        flags = arguments.pop(0)[1:]
        if not flags or any(flag not in "lwc" for flag in flags):
            raise ValueError("допустимы только ключи -l, -w, -c")
        return flags

    @staticmethod
    def _format_counts(counts: list[int], flags: str, label: str) -> str:
        """Сформировать одну строку вывода wc."""
        values = [str(counts[index]) for index, flag in
                  enumerate("lwc") if flag in flags]
        return " ".join(values + [label])

    def _tree(self, arguments: list[str]) -> str:
        """Вывести дерево каталога и число объектов."""
        assert self.vfs is not None
        if len(arguments) > 1:
            raise ValueError("слишком много аргументов")
        path = arguments[0] if arguments else "."
        node = self.vfs.get(path, self.cwd)
        lines = [path]
        directories, files = self._tree_lines(node, "", lines)
        if not node.is_dir:
            files = 1
        lines.append(f"{directories} каталогов, {files} файлов")
        return "\n".join(lines)

    def _tree_lines(
        self, node: Node, prefix: str, lines: list[str]
    ) -> tuple[int, int]:
        """Рекурсивно добавить потомков каталога в вывод tree."""
        directories = files = 0
        children = sorted(node.children.values(), key=lambda item: item.name)
        for index, child in enumerate(children):
            last = index == len(children) - 1
            lines.append(prefix + ("└── " if last else "├── ") + child.name)
            if child.is_dir:
                directories += 1
                continuation = "    " if last else "│   "
                found_dirs, found_files = self._tree_lines(
                    child, prefix + continuation, lines
                )
                directories += found_dirs
                files += found_files
            else:
                files += 1
        return directories, files

    def _touch(self, arguments: list[str]) -> str:
        """Создать или обновить объекты VFS без записи в XML."""
        assert self.vfs is not None
        if not arguments:
            raise ValueError("укажите хотя бы один путь")
        for path in arguments:
            self.vfs.touch(path, self.cwd)
        return ""
