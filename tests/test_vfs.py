"""Проверки загрузки и навигации по XML VFS."""

import tempfile
import unittest
from pathlib import Path

from src.vfs import VFS


ROOT = Path(__file__).resolve().parents[1]


class VFSTests(unittest.TestCase):
    """Чтение трех вариантов виртуальной файловой системы."""

    def test_minimal(self) -> None:
        """Загрузить минимальную структуру с пустым каталогом."""
        vfs = VFS.load(ROOT / "vfs/minimal.xml")
        self.assertEqual(list(vfs.root.children), ["empty"])

    def test_text_and_binary(self) -> None:
        """Прочитать текстовый файл и точные двоичные данные."""
        vfs = VFS.load(ROOT / "vfs/files.xml")
        self.assertIn(b"Hello", vfs.get("/readme.txt").content)
        self.assertEqual(
            vfs.get("/logo.bin").content, b"\x00\x01\x02\x03\xff\xfe"
        )

    def test_deep_path(self) -> None:
        """Найти вложенный файл по пути с родительским каталогом."""
        vfs = VFS.load(ROOT / "vfs/deep.xml")
        node = vfs.get("../projects/hello.txt", "/home/student/tmp")
        self.assertIn("Привет".encode(), node.content)

    def test_missing_path(self) -> None:
        """Отклонить обращение к отсутствующему объекту."""
        vfs = VFS.load(ROOT / "vfs/minimal.xml")
        with self.assertRaises(FileNotFoundError):
            vfs.get("/missing")


class VFSValidationTests(unittest.TestCase):
    """Проверки некорректного XML на временных файлах."""

    def setUp(self) -> None:
        """Создать изолированную папку с автоматической очисткой."""
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.xml_path = Path(directory.name) / "input.xml"

    def _load_xml(self, source: str) -> VFS:
        """Записать временный XML и загрузить его в память."""
        self.xml_path.write_text(source, encoding="utf-8")
        return VFS.load(self.xml_path)

    def test_unreadable_and_malformed_xml(self) -> None:
        """Отказать при отсутствующем файле и поврежденном XML."""
        with self.assertRaisesRegex(ValueError, "не удалось прочитать XML"):
            VFS.load(self.xml_path)
        with self.assertRaisesRegex(ValueError, "не удалось прочитать XML"):
            self._load_xml("<vfs>")

    def test_wrong_root(self) -> None:
        """Требовать корневой элемент vfs."""
        with self.assertRaisesRegex(ValueError, "корневой элемент"):
            self._load_xml("<root/>")

    def test_invalid_names(self) -> None:
        """Отказать при отсутствующем имени и специальных компонентах."""
        for name in ("", ".", "..", "a/b"):
            with self.subTest(name=name):
                source = f'<vfs><file name="{name}"/></vfs>'
                with self.assertRaisesRegex(ValueError, "недопустимое имя"):
                    self._load_xml(source)
        with self.assertRaisesRegex(ValueError, "недопустимое имя"):
            self._load_xml("<vfs><directory/></vfs>")

    def test_duplicate_names(self) -> None:
        """Отклонить одинаковые имена файла и каталога в одной папке."""
        source = (
            '<vfs><file name="same"/><directory name="same"/></vfs>'
        )
        with self.assertRaisesRegex(ValueError, "повторяющееся имя"):
            self._load_xml(source)

    def test_invalid_elements(self) -> None:
        """Отклонить неизвестный тег и вложенные элементы внутри файла."""
        sources = (
            '<vfs><unknown name="x"/></vfs>',
            '<vfs><file name="x"><file name="y"/></file></vfs>',
        )
        for source in sources:
            with self.subTest(source=source):
                with self.assertRaisesRegex(
                    ValueError, "недопустимый элемент"
                ):
                    self._load_xml(source)

    def test_invalid_encodings(self) -> None:
        """Сообщить об ошибочном base64 и неизвестной кодировке."""
        cases = (
            ('<file name="x" encoding="base64">???</file>', "неверный base64"),
            ('<file name="x" encoding="ascii"/>', "неизвестная кодировка"),
        )
        for element, message in cases:
            with self.subTest(message=message):
                with self.assertRaisesRegex(ValueError, message):
                    self._load_xml(f"<vfs>{element}</vfs>")

    def test_empty_files_and_scoped_names(self) -> None:
        """Разрешить пустые файлы и одинаковые имена в разных каталогах."""
        source = (
            '<vfs><file name="x"/>'
            '<directory name="dir">'
            '<file name="x" encoding="base64"/>'
            '</directory></vfs>'
        )
        vfs = self._load_xml(source)
        self.assertEqual(vfs.get("/x").content, b"")
        self.assertEqual(vfs.get("/dir/x").content, b"")
        with self.assertRaises(FileNotFoundError):
            vfs.get("/x/child")
        self.assertEqual(VFS.normalize("../../..", "/dir"), "/")
        self.assertEqual(self.xml_path.read_text(encoding="utf-8"), source)


if __name__ == "__main__":
    unittest.main()
