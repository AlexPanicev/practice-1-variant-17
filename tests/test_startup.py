"""Проверки сценариев интерфейса без создания графического окна."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from src.main import Emulator
from src.shell import Shell


class DialogStub:
    """Подставить память вместо виджетов, сохранив методы интерфейса."""

    run_command = Emulator.run_command
    run_startup = Emulator.run_startup

    def __init__(self) -> None:
        """Подготовить оболочку и наблюдение за выводом и закрытием."""
        self.user = "test"
        self.host = "test"
        self.shell = Mock(wraps=Shell())
        self.write = Mock()
        self.destroy = Mock()


class StartupTests(unittest.TestCase):
    """Проверить завершение сценария, комментарии и ошибки чтения."""

    def setUp(self) -> None:
        """Создать временный сценарий и диалог без Tk-окна."""
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / "startup.txt"
        self.dialog = DialogStub()

    def test_exit_stops_script(self) -> None:
        """Не выполнять строки сценария после закрытия сеанса."""
        self.path.write_text("exit\nunknown\n", encoding="utf-8")
        self.dialog.run_startup(self.path)
        self.dialog.destroy.assert_called_once()
        self.dialog.shell.execute.assert_called_once_with(
            "exit", comments=True
        )

    def test_invalid_exit_continues(self) -> None:
        """После ошибочного exit продолжить до корректного завершения."""
        self.path.write_text("exit now\nexit\n", encoding="utf-8")
        self.dialog.run_startup(self.path)
        self.dialog.destroy.assert_called_once()
        commands = [call.args[0] for call in
                    self.dialog.shell.execute.call_args_list]
        self.assertEqual(commands, ["exit now", "exit"])

    def test_comments_and_command_error(self) -> None:
        """Пропустить пустые строки и комментарии, показать ошибку команды."""
        self.path.write_text("\n # note\nunknown # note\n", encoding="utf-8")
        self.dialog.run_startup(self.path)
        self.dialog.shell.execute.assert_called_once_with(
            "unknown # note", comments=True
        )
        self.dialog.write.assert_any_call("unknown: команда не найдена")
        self.dialog.destroy.assert_not_called()

    def test_missing_script(self) -> None:
        """Показать ошибку чтения отсутствующего стартового сценария."""
        self.dialog.run_startup(self.path)
        self.dialog.write.assert_called_once()
        self.dialog.shell.execute.assert_not_called()


if __name__ == "__main__":
    unittest.main()
