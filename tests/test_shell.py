"""Проверки диалога и разбора команд."""

import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from src.shell import Shell
from src.vfs import VFS


class ShellTests(unittest.TestCase):
    """Базовые сценарии первого этапа."""

    def setUp(self) -> None:
        """Создать независимый сеанс перед каждой проверкой."""
        path = Path(__file__).resolve().parents[1] / "vfs/deep.xml"
        self.shell = Shell(VFS.load(path))

    def test_quoted_arguments(self) -> None:
        """Передать имя с пробелами как один аргумент."""
        self.assertEqual(
            self.shell.execute('ls "/home/student/todo list.txt"').output,
            "todo list.txt",
        )

    def test_syntax_and_unknown_command(self) -> None:
        """Сообщить о незакрытой кавычке и неизвестной команде."""
        self.assertIn("Ошибка синтаксиса", self.shell.execute('ls "').output)
        self.assertEqual(
            self.shell.execute("missing").output,
            "missing: команда не найдена",
        )

    def test_exit(self) -> None:
        """Завершить сеанс только при корректной команде exit."""
        self.assertTrue(self.shell.execute("exit").exit_requested)
        self.assertFalse(self.shell.execute("exit now").exit_requested)

    def test_script_comment(self) -> None:
        """Игнорировать комментарий после команды стартового скрипта."""
        self.assertEqual(
            self.shell.execute(
                'ls "/home/student/todo list.txt" # note',
                comments=True,
            ).output,
            "todo list.txt",
        )

    def test_cd_and_tree(self) -> None:
        """Перейти в каталог и проверить дерево с итогами."""
        self.assertEqual(self.shell.execute("cd home/student").output, "")
        self.assertEqual(self.shell.cwd, "/home/student")
        self.assertIn("projects", self.shell.execute("tree .").output)
        self.assertIn("1 каталогов, 2 файлов",
                      self.shell.execute("tree .").output)

    def test_wc(self) -> None:
        """Посчитать строки, слова и байты текстового файла."""
        self.shell.execute("cd /home/student/projects")
        output = self.shell.execute("wc hello.txt").output
        self.assertTrue(output.startswith("2 4 "))
        self.assertEqual(self.shell.execute("wc -l hello.txt").output,
                         "2 hello.txt")

    def test_command_errors(self) -> None:
        """Отклонить отсутствующий путь и неверный тип объекта."""
        self.assertIn("missing", self.shell.execute("ls missing").output)
        self.assertIn("не каталог", self.shell.execute(
            'cd "/home/student/todo list.txt"').output)
        self.assertIn("не файл", self.shell.execute("wc /home").output)

    def test_touch_and_persistence(self) -> None:
        """Создать пустой файл в памяти без изменения исходного XML."""
        source = Path(__file__).resolve().parents[1] / "vfs/deep.xml"
        original = source.read_bytes()
        self.shell.execute("cd /home/student/projects")
        self.assertEqual(self.shell.execute('touch "new file.txt"').output,
                         "")
        self.assertIn("new file.txt", self.shell.execute("ls").output)
        self.assertEqual(self.shell.execute('wc "new file.txt"').output,
                         "0 0 0 new file.txt")
        self.assertEqual(source.read_bytes(), original)
        fresh = VFS.load(source)
        with self.assertRaises(FileNotFoundError):
            fresh.get("/home/student/projects/new file.txt")

    def test_touch_errors(self) -> None:
        """Отклонить отсутствие аргумента и родительского каталога."""
        self.assertIn("укажите", self.shell.execute("touch").output)
        self.assertIn("missing", self.shell.execute(
            "touch /missing/new.txt").output)

    def test_wc_modes_and_totals(self) -> None:
        """Проверить ключи wc и общий итог для нескольких файлов."""
        self.shell.execute("cd /home/student/projects")
        expected = {
            "wc -w hello.txt": "4 hello.txt",
            "wc -c hello.txt": "49 hello.txt",
            "wc -lc hello.txt": "2 49 hello.txt",
            "wc hello.txt hello.txt": (
                "2 4 49 hello.txt\n2 4 49 hello.txt\n4 8 98 итого"
            ),
        }
        for command, output in expected.items():
            with self.subTest(command=command):
                self.assertEqual(self.shell.execute(command).output, output)

    def test_wc_invalid_arguments(self) -> None:
        """Отклонить неизвестный ключ и отсутствие имени файла."""
        for command in ("wc", "wc -l", "wc -", "wc -z /missing"):
            with self.subTest(command=command):
                self.assertTrue(self.shell.execute(command).output)

    def test_ls_multiple_paths_and_tree_file(self) -> None:
        """Показать несколько каталогов и дерево отдельного файла."""
        self.assertEqual(self.shell.execute("ls /tmp /home").output,
                         "/tmp:\n/home:\nstudent")
        self.assertEqual(
            self.shell.execute("tree /home/student/projects/hello.txt").output,
            "/home/student/projects/hello.txt\n0 каталогов, 1 файлов",
        )

    def test_touch_updates_timestamp(self) -> None:
        """Обновить время файла и каталогов без потери содержимого."""
        expected = datetime(2026, 10, 8, tzinfo=timezone.utc)
        path = "/home/student/projects/hello.txt"
        original = self.shell.vfs.get(path).content
        with patch("src.vfs.datetime") as clock:
            clock.now.return_value = expected
            self.shell.execute(f"touch {path} /home /")
        for name in (path, "/home", "/"):
            self.assertEqual(self.shell.vfs.get(name).modified_at, expected)
        self.assertEqual(self.shell.vfs.get(path).content, original)


if __name__ == "__main__":
    unittest.main()
