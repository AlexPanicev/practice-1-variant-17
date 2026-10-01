"""Проверки диалога и разбора команд."""

import unittest

from src.shell import Shell


class ShellTests(unittest.TestCase):
    """Базовые сценарии первого этапа."""

    def setUp(self) -> None:
        """Создать независимую оболочку перед каждой проверкой."""
        self.shell = Shell()

    def test_quoted_arguments(self) -> None:
        """Проверить аргумент с пробелом внутри кавычек."""
        self.assertEqual(
            self.shell.execute('ls "two words"').output,
            "ls: аргументы = ['two words']",
        )

    def test_syntax_and_unknown_command(self) -> None:
        """Проверить ошибки синтаксиса и неизвестной команды."""
        self.assertIn("Ошибка синтаксиса", self.shell.execute('ls "').output)
        self.assertEqual(
            self.shell.execute("missing").output,
            "missing: команда не найдена",
        )

    def test_exit(self) -> None:
        """Проверить завершение без аргументов и отказ с аргументом."""
        self.assertTrue(self.shell.execute("exit").exit_requested)
        self.assertFalse(self.shell.execute("exit now").exit_requested)


if __name__ == "__main__":
    unittest.main()
