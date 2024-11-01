from typing import Optional, Self, Dict, Any
import json


Config = Dict[str, Any]


class DataCenter:
    _instance: Optional[Self] = None

    def __new__(cls) -> Self:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def get_config(self) -> Config:
        config = None
        with open("./config.json", 'r', encoding="utf-8") as file:
            config = json.loads(file.read())
        return config
