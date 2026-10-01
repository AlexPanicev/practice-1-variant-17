"""Разбор и выполнение команд эмулятора."""

import shlex
from dataclasses import dataclass


@dataclass
class Result:
    """Текст ответа и признак завершения сеанса."""

    output: str = ""
    exit_requested: bool = False


class Shell:
    """Диалоговая оболочка первого этапа."""

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
        if command in ("ls", "cd"):
            return Result(f"{command}: аргументы = {arguments!r}")
        return Result(f"{command}: команда не найдена")
