"""Графический интерфейс эмулятора."""

import getpass
import socket
import tkinter as tk
from tkinter import scrolledtext

from src.shell import Shell


class Emulator(tk.Tk):
    """Окно с историей диалога и строкой ввода."""

    def __init__(self) -> None:
        """Создать окно с историей диалога и строкой ввода."""
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
        self.write(f"{self.user}@{self.host}$ {line}")
        result = self.shell.execute(line)
        if result.output:
            self.write(result.output)
        if result.exit_requested:
            self.destroy()


def main() -> None:
    """Запустить интерфейс."""
    Emulator().mainloop()


if __name__ == "__main__":
    main()
