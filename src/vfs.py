"""Виртуальная файловая система, загружаемая из XML в память."""

import base64
import binascii
from xml.etree import ElementTree
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class Node:
    """Каталог или файл виртуальной файловой системы."""

    name: str
    is_dir: bool
    content: bytes = b""
    children: dict[str, "Node"] = field(default_factory=dict)
    modified_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class VFS:
    """Дерево XML, операции над которым выполняются только в памяти."""

    def __init__(self, root: Node) -> None:
        """Сохранить корень независимого дерева в памяти."""
        self.root = root

    @classmethod
    def load(cls, path: Path) -> "VFS":
        """Прочитать XML и создать независимое дерево объектов."""
        try:
            document = ElementTree.parse(path)
        except (OSError, ElementTree.ParseError) as error:
            message = f"VFS: не удалось прочитать XML: {error}"
            raise ValueError(message) from error
        if document.getroot().tag != "vfs":
            raise ValueError("VFS: корневой элемент должен быть <vfs>")
        root = Node("", True)
        for element in document.getroot():
            cls._add_element(root, element)
        return cls(root)

    @classmethod
    def _add_element(cls, parent: Node, element: ElementTree.Element) -> None:
        """Добавить XML-элемент в дерево после проверки имени и типа."""
        name = cls._validate_name(parent, element)
        if element.tag == "directory":
            node = Node(name, True)
            parent.children[name] = node
            for child in element:
                cls._add_element(node, child)
            return
        if element.tag != "file" or len(element):
            raise ValueError(f"VFS: недопустимый элемент: {element.tag}")
        content = cls._decode_content(element)
        parent.children[name] = Node(name, False, content)

    @staticmethod
    def _validate_name(parent: Node, element: ElementTree.Element) -> str:
        """Отклонить пустое, некорректное или повторяющееся имя."""
        name = element.get("name", "")
        if not name or name in (".", "..") or "/" in name:
            raise ValueError(f"VFS: недопустимое имя: {name!r}")
        if name in parent.children:
            raise ValueError(f"VFS: повторяющееся имя: {name}")
        return name

    @staticmethod
    def _decode_content(element: ElementTree.Element) -> bytes:
        """Прочитать текст или строго декодировать двоичные данные."""
        name = element.get("name", "")
        encoding = element.get("encoding", "utf-8")
        raw = element.text or ""
        if encoding == "base64":
            try:
                return base64.b64decode(raw.strip(), validate=True)
            except binascii.Error as error:
                raise ValueError(f"VFS: неверный base64: {name}") from error
        if encoding == "utf-8":
            return raw.encode("utf-8")
        raise ValueError(f"VFS: неизвестная кодировка: {encoding}")

    @staticmethod
    def normalize(path: str, cwd: str = "/") -> str:
        """Получить абсолютный путь с учетом точки и родительского каталога."""
        parts = [] if path.startswith("/") else cwd.strip("/").split("/")
        parts = [part for part in parts if part]
        for part in path.split("/"):
            if part == "..":
                if parts:
                    parts.pop()
            elif part and part != ".":
                parts.append(part)
        return "/" + "/".join(parts)

    def get(self, path: str, cwd: str = "/") -> Node:
        """Найти объект по абсолютному или относительному пути."""
        absolute = self.normalize(path, cwd)
        node = self.root
        for part in absolute.strip("/").split("/"):
            if not part:
                continue
            if not node.is_dir or part not in node.children:
                raise FileNotFoundError(absolute)
            node = node.children[part]
        return node

    def touch(self, path: str, cwd: str = "/") -> None:
        """Создать файл или обновить время объекта только в памяти."""
        absolute = self.normalize(path, cwd)
        if absolute == "/":
            self.root.modified_at = datetime.now(timezone.utc)
            return
        parent_path, _, name = absolute.rpartition("/")
        parent = self.get(parent_path or "/")
        if not parent.is_dir:
            raise NotADirectoryError(parent_path)
        if name in parent.children:
            parent.children[name].modified_at = datetime.now(timezone.utc)
            return
        if path.endswith("/"):
            raise ValueError(f"не каталог: {path}")
        parent.children[name] = Node(name, False)
