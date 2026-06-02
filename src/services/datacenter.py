from __future__ import annotations
from typing import Optional, Dict, Any
from typing_extensions import Self
import json
from pathlib import Path

from ..utils import paths


Config = Dict[str, Any]


DEFAULT_CONFIG: Config = {
    "sleep": {"max_seconds": 0.5, "min_seconds": 0.2},
    "game_id": "",
    "number_of_ticket": 2,
    "open_for_purchase_datetime": None,
    "show_time_text_contains": None,
    "area_price_text_contains": None,
    "presale_code": None,
    "notification_emails": [],
}


class DataCenter:
    _instance: Optional[Self] = None

    def __new__(cls) -> Self:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._config = None
            cls._instance._path = None
        return cls._instance

    @property
    def path(self) -> Path:
        if self._path is None:
            self._path = paths.config_path()
        return self._path

    def set_path(self, path: str | Path) -> None:
        self._path = Path(path)
        self._config = None

    def get_config(self, reload: bool = False) -> Config:
        if self._config is None or reload:
            self._config = self._load()
        return self._config

    def set_config(self, config: Config) -> None:
        self._config = dict(config)

    def save(self, config: Optional[Config] = None) -> None:
        if config is not None:
            self._config = dict(config)
        if self._config is None:
            raise RuntimeError("No config loaded; nothing to save.")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self._config, f, indent=2, ensure_ascii=False)

    def _load(self) -> Config:
        if not self.path.exists():
            return dict(DEFAULT_CONFIG)
        with open(self.path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {**DEFAULT_CONFIG, **data}
