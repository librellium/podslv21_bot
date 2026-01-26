from string import Template
from pathlib import Path

import yaml
from dotenv import dotenv_values
from sqlalchemy.engine import URL
from pydantic import BaseModel, SecretStr

from .models import Behavior, Bot, Database, Forwarding, Logging, Moderation, OpenAI


class Config(BaseModel):
    bot: Bot = Bot()
    behavior: Behavior = Behavior()
    database: Database = Database()
    forwarding: Forwarding = Forwarding()
    openai: OpenAI = OpenAI()
    moderation: Moderation = Moderation()
    logging: Logging = Logging()
    model_config = {"frozen": True}

    def get_database_url(self):
        password = None
        if self.database.password:
            password = (
                self.database.password.get_secret_value()
                if isinstance(self.database.password, SecretStr)
                else self.database.password
            )

        return URL.create(
            drivername=self.database.backend,
            username=self.database.username,
            password=password,
            host=self.database.host,
            port=self.database.port,
            database=str(self.database.name_or_path),
        )

    def get_migrations_url(self):
        password = None
        if self.database.password:
            password = (
                self.database.password.get_secret_value()
                if isinstance(self.database.password, SecretStr)
                else self.database.password
            )

        return URL.create(
            drivername=self.database.migrations.backend,
            username=self.database.username,
            password=password,
            host=self.database.host,
            port=self.database.port,
            database=str(self.database.name_or_path),
        )

    @classmethod
    def load(cls, filepath: Path):
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)

        if filepath.exists():
            with filepath.open(encoding="utf-8") as f:
                template = Template(f.read())
                rendered = template.safe_substitute(dotenv_values())
                data = yaml.safe_load(rendered) or {}
            return cls(**data) # type: ignore

        return cls()

    @classmethod
    def _prepare_for_save(cls, obj):
        if isinstance(obj, SecretStr):
            return obj.get_secret_value()
        elif isinstance(obj, dict):
            return {key: cls._prepare_for_save(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [cls._prepare_for_save(value) for value in obj]

        return obj

    def save(self, filepath: Path):
        filepath.parent.mkdir(parents=True, exist_ok=True)

        with filepath.open("w", encoding="utf-8") as config_file:
            yaml.dump(
                self._prepare_for_save(self.model_dump()),
                config_file,
                width=float("inf"),
                sort_keys=False,
                default_flow_style=False
            )
