from pathlib import Path

import yaml
from pydantic import BaseModel, SecretStr

from .models import *


class Config(BaseModel):
    bot: Bot = Bot()
    forwarding: Forwarding = Forwarding()
    openai: OpenAI = OpenAI()
    moderation: Moderation = Moderation()
    logging: Logging = Logging()

    @classmethod
    def _serialize(cls, obj):
        if isinstance(obj, SecretStr):
            return obj.get_secret_value()
        elif isinstance(obj, dict):
            return {key: cls._serialize(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [cls._serialize(value) for value in obj]

        return obj

    @classmethod
    def load(cls, filepath: Path):
        filepath = Path(filepath)
        filepath.parent.mkdir(parents = True, exist_ok = True)

        config = cls()

        if filepath.exists():
            with filepath.open(encoding = "utf-8") as f:
                config = cls(**yaml.safe_load(f))

        return config

    def save(self, filepath: Path):
        filepath.parent.mkdir(parents = True, exist_ok = True)

        with filepath.open("w", encoding="utf-8") as config_file:
            yaml.dump(self._serialize(self.model_dump()), config_file, width = float("inf"), sort_keys = False)