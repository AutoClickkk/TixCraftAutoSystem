from typing import Optional, Self
from datetime import datetime


class LogUtils:
    _instance: Optional[Self] = None

    def __new__(cls) -> Self:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def _get_now(self) -> str:
        return datetime.now().strftime("%Y/%m/%d-%H:%M:%S")

    def info(self, text: str) -> None:
        now = self._get_now()
        print(f"[INFO] {now} {text}")
    
    def error(self, text: str) -> None:
        now = self._get_now()
        print(f"[ERROR] {now} {text}")
