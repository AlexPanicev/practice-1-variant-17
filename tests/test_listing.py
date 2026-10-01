"""Проверки ключей ls на независимой файловой системе в памяти."""

import unittest
from datetime import datetime, timezone

from src.listing import Options, readable_size
from src.shell import Shell
from src.vfs import Node, VFS


FIXED_TIME = datetime(2026, 10, 2, 12, 30, tzinfo=timezone.utc)


class ListingTests(unittest.TestCase):
    """Обычный и подробный вывод, скрытые файлы и разбор ключей."""

    def setUp(self) -> None:
        """Создать дерево с фиксированными датами без записи на диск."""
        root = Node("", True, modified_at=FIXED_TIME)
        folder = Node("folder", True, modified_at=FIXED_TIME)
        folder.children["nested"] = Node(
            "nested", True, modified_at=FIXED_TIME
        )
        folder.children["inside.txt"] = Node(
            "inside.txt", False, b"a", modified_at=FIXED_TIME
        )
        root.children["folder"] = folder
        for name, content in (
            (".hidden", b"secret"), ("-dash", b"d"),
            ("large.txt", b"x" * 1536), ("two words.txt", b"abc"),
        ):
            root.children[name] = Node(
                name, False, content, modified_at=FIXED_TIME
            )
        self.shell = Shell(VFS(root))

    def test_plain_and_h_without_l(self) -> None:
        """Сохранить обычный вывод и применять -h только вместе с -l."""
        expected = "-dash\nfolder\nlarge.txt\ntwo words.txt"
        for command in ("ls", "ls /", "ls -h", "ls -hh"):
            with self.subTest(command=command):
                self.assertEqual(self.shell.execute(command).output, expected)

    def test_all_includes_dots_and_hidden(self) -> None:
        """При -a показать . и .., скрытые имена и обычные объекты."""
        expected = ".\n..\n-dash\n.hidden\nfolder\nlarge.txt\ntwo words.txt"
        self.assertEqual(self.shell.execute("ls -a").output, expected)

    def test_explicit_hidden_and_quoted_path(self) -> None:
        """Показывать явно выбранный скрытый файл и путь в кавычках."""
        self.assertEqual(self.shell.execute("ls /.hidden").output, ".hidden")
        self.assertEqual(self.shell.execute('ls "two words.txt"').output,
                         "two words.txt")
        self.assertEqual(self.shell.execute('ls -l "two words.txt"').output,
                         "-rw-r--r-- 1 vfs vfs 3 2026-10-02 12:30 "
                         "two words.txt")

    def test_long_columns_and_directory_defaults(self) -> None:
        """Проверить виртуальные права, ссылки, владельца, размер и UTC."""
        expected = (
            "-rw-r--r-- 1 vfs vfs 1 2026-10-02 12:30 inside.txt\n"
            "drwxr-xr-x 2 vfs vfs 0 2026-10-02 12:30 nested"
        )
        self.assertEqual(self.shell.execute("ls -l folder").output, expected)
        rows = self.shell.execute("ls -la folder").output.splitlines()
        self.assertIn("drwxr-xr-x 3 vfs vfs 0 2026-10-02 12:30 .", rows)
        self.assertIn("drwxr-xr-x 3 vfs vfs 0 2026-10-02 12:30 ..", rows)

    def test_human_readable_long_output(self) -> None:
        """Отличать размер в байтах от размера с суффиксом K."""
        self.assertEqual(self.shell.execute("ls -l large.txt").output,
                         "-rw-r--r-- 1 vfs vfs 1536 2026-10-02 12:30 "
                         "large.txt")
        self.assertEqual(self.shell.execute("ls -lh large.txt").output,
                         "-rw-r--r-- 1 vfs vfs 1.5K 2026-10-02 12:30 "
                         "large.txt")

    def test_grouped_separate_and_reordered_flags(self) -> None:
        """Разрешить объединённые, повторные и переставленные ключи."""
        expected = self.shell.execute("ls -lah /").output
        for command in (
            "ls -l -a -h /", "ls / -a -h -l", "ls -hal /",
            "ls -l / -ah", "ls -llaaahhh /",
        ):
            with self.subTest(command=command):
                self.assertEqual(self.shell.execute(command).output, expected)

    def test_separator_and_hyphen_filename(self) -> None:
        """Считать имена после -- путями, даже если они начинаются с - ."""
        self.assertEqual(self.shell.execute("ls -- -dash").output, "-dash")
        self.assertEqual(self.shell.execute("ls -l -- -dash").output,
                         "-rw-r--r-- 1 vfs vfs 1 2026-10-02 12:30 -dash")
        self.assertIn("неизвестные ключи",
                      self.shell.execute("ls -dash").output)
        self.assertIn("/-l", self.shell.execute("ls -- -l").output)

    def test_invalid_options(self) -> None:
        """Ясно отклонить неподдерживаемые короткие и длинные ключи."""
        for command in ("ls -z", "ls -lz", "ls --all"):
            with self.subTest(command=command):
                result = self.shell.execute(command).output
                self.assertTrue(result.startswith("ls: неизвестные ключи"))
                self.assertIn("допустимы -l, -a, -h", result)

    def test_dots_resolve_parent_metadata(self) -> None:
        """Показывать метаданные родителя через .. в текущем каталоге."""
        self.shell.execute("cd folder/nested")
        rows = self.shell.execute("ls -la").output.splitlines()
        self.assertEqual(rows, [
            "drwxr-xr-x 2 vfs vfs 0 2026-10-02 12:30 .",
            "drwxr-xr-x 3 vfs vfs 0 2026-10-02 12:30 ..",
        ])
        self.assertEqual(self.shell.execute("ls -a ../../..").output,
                         self.shell.execute("ls -a /").output)

    def test_multiple_paths_and_relative_resolution(self) -> None:
        """Сохранить заголовки нескольких путей и относительную навигацию."""
        self.assertEqual(self.shell.execute("ls folder large.txt").output,
                         "folder:\ninside.txt\nnested\nlarge.txt:\nlarge.txt")
        self.shell.execute("cd folder")
        self.assertEqual(self.shell.execute("ls ../large.txt -h").output,
                         "large.txt")

    def test_options_do_not_mutate_arguments_or_vfs(self) -> None:
        """Не изменять аргументы, содержимое и даты при перечислении."""
        arguments = ["-lah", "/"]
        Options.parse(arguments)
        self.assertEqual(arguments, ["-lah", "/"])
        node = self.shell.vfs.get("large.txt")
        original = (node.content, node.modified_at)
        self.shell.execute("ls -lah")
        self.assertEqual((node.content, node.modified_at), original)
        self.assertEqual(self.shell.cwd, "/")

    def test_readable_size_thresholds(self) -> None:
        """Проверить ноль, границы K/M и единый десятичный формат."""
        cases = {
            0: "0", 1023: "1023", 1024: "1.0K", 1536: "1.5K",
            1048575: "1.0M", 1048576: "1.0M", 1572864: "1.5M",
            1073741823: "1.0G", 1073741824: "1.0G",
        }
        for size, expected in cases.items():
            with self.subTest(size=size):
                self.assertEqual(readable_size(size), expected)


if __name__ == "__main__":
    unittest.main()
