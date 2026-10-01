"""Графический интерфейс эмулятора."""

import getpass
import socket
import tkinter as tk
from tkinter import scrolledtext

from src.config import Config, parse_args
from src.shell import Shell
from src.vfs import VFS


class Emulator(tk.Tk):
    """Окно с историей диалога и строкой ввода."""

    def __init__(self, config: Config) -> None:
        """Создать окно и загрузить конфигурацию сеанса."""
        super().__init__()
        self.user = getpass.getuser()
        self.host = socket.gethostname()
        self.title(f"Эмулятор - [{self.user}@{self.host}]")
        self.geometry("760x480")
        self.shell = Shell()
        self.history = scrolledtext.ScrolledText(
            self, state="disabled", font=("Menlo", 12), wrap="word"
        )
        self.entry = tk.Entry(self, font=("Menlo", 12))
        self.entry.pack(side="bottom", fill="x", padx=8, pady=(0, 8))
        self.history.pack(fill="both", expand=True, padx=8, pady=8)
        self.entry.bind("<Return>", self.submit)
        self.entry.focus_set()
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.write(f"Параметр --vfs: {config.vfs or '(не задан)'}")
        self.write(f"Параметр --startup: {config.startup or '(не задан)'}")
        if config.vfs:
            try:
                self.vfs = VFS.load(config.vfs)
                self.write("VFS загружена в память")
                self.write(
                    "Корень VFS: "
                    + ", ".join(sorted(self.vfs.root.children))
                )
            except ValueError as error:
                self.write(str(error))
        if config.startup:
            self.after(0, lambda: self.run_startup(config.startup))

    def run_startup(self, path) -> None:
        """Показать команды скрипта и результаты в истории диалога."""
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError as error:
            self.write(f"Стартовый скрипт: {error}")
            return
        for line in lines:
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            if not self.run_command(line, comments=True):
                break

    def write(self, message: str) -> None:
        """Добавить текст в историю диалога."""
        self.history.configure(state="normal")
        self.history.insert("end", message + "\n")
        self.history.see("end")
        self.history.configure(state="disabled")

    def submit(self, _event: tk.Event) -> None:
        """Выполнить содержимое строки ввода."""
        line = self.entry.get()
        self.entry.delete(0, "end")
        self.run_command(line)

    def run_command(self, line: str, comments: bool = False) -> bool:
        """Выполнить команду и вернуть признак продолжения сеанса."""
        self.write(f"{self.user}@{self.host}$ {line}")
        result = self.shell.execute(line, comments=comments)
        if result.output:
            self.write(result.output)
        if result.exit_requested:
            self.destroy()
            return False
        return True


def main() -> None:
    """Запустить интерфейс."""
    Emulator(parse_args()).mainloop()


if __name__ == "__main__":
    main()
