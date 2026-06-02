from __future__ import annotations
from typing import Optional, Callable, List
from typing_extensions import Self
from datetime import datetime
from threading import Lock


LogHandler = Callable[[str, str], None]  # (level, formatted_line)


class LogUtils:
    _instance: Optional[Self] = None
    _handlers: List[LogHandler] = []
    _lock = Lock()

    def __new__(cls) -> Self:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def add_handler(self, handler: LogHandler) -> None:
        with self._lock:
            if handler not in self._handlers:
                self._handlers.append(handler)

    def remove_handler(self, handler: LogHandler) -> None:
        with self._lock:
            if handler in self._handlers:
                self._handlers.remove(handler)

    def _get_now(self) -> str:
        return datetime.now().strftime("%Y/%m/%d-%H:%M:%S")

    def _emit(self, level: str, text: str) -> None:
        line = f"[{level}] {self._get_now()} {text}"
        print(line, flush=True)
        with self._lock:
            handlers = list(self._handlers)
        for h in handlers:
            try:
                h(level, line)
            except Exception:
                pass

    def info(self, text: str) -> None:
        self._emit("INFO", text)

    def error(self, text: str) -> None:
        self._emit("ERROR", text)

    def warn(self, text: str) -> None:
        self._emit("WARN", text)
