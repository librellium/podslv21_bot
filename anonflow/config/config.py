from pathlib import Path

import yaml
from pydantic import BaseModel, SecretStr

from .models import Behavior, Bot, Forwarding, Logging, Moderation, OpenAI


class Config(BaseModel):
    bot: Bot = Bot()
    behavior: Behavior = Behavior()
    forwarding: Forwarding = Forwarding()
    openai: OpenAI = OpenAI()
    moderation: Moderation = Moderation()
    logging: Logging = Logging()
    model_config = {"frozen": True}

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
        filepath.parent.mkdir(parents=True, exist_ok=True)

        if filepath.exists():
            with filepath.open(encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            return cls(**data) # type: ignore

        return cls()

    def save(self, filepath: Path):
        filepath.parent.mkdir(parents=True, exist_ok=True)

        with filepath.open("w", encoding="utf-8") as config_file:
            yaml.dump(
                self._serialize(self.model_dump()),
                config_file,
                width=float("inf"),
                sort_keys=False,
                default_flow_style=False
            )
