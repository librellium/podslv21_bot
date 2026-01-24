from pathlib import Path
from typing import Literal, Optional, Tuple, TypeAlias, Union

from pydantic import BaseModel, SecretStr

ForwardingType: TypeAlias = Literal["text", "photo", "video"]
ModerationType: TypeAlias = Literal["omni", "gpt"]
LoggingLevel: TypeAlias = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


class Bot(BaseModel):
    token: Optional[SecretStr] = None
    timeout: int = 10
    model_config = {"frozen": True}


class BehaviorThrottling(BaseModel):
    enabled: bool = True
    delay: float = 120
    model_config = {"frozen": True}


class BehaviorSubscriptionRequirement(BaseModel):
    enabled: bool = True
    channel_ids: Optional[Tuple[int]] = None
    model_config = {"frozen": True}


class Behavior(BaseModel):
    throttling: BehaviorThrottling = BehaviorThrottling()
    subscription_requirement: BehaviorSubscriptionRequirement = BehaviorSubscriptionRequirement()
    model_config = {"frozen": True}


class DatabaseRepositoriesUser(BaseModel):
    cache_size: int = 1024
    cache_ttl: int = 60
    model_config = {"frozen": True}


class DatabaseRepositories(BaseModel):
    user: DatabaseRepositoriesUser = DatabaseRepositoriesUser()
    model_config = {"frozen": True}


class DatabaseMigrations(BaseModel):
    backend: str = "sqlite"
    model_config = {"frozen": True}


class Database(BaseModel):
    backend: str = "sqlite+aiosqlite"
    name_or_path: Optional[Union[str, Path]] = None
    host: Optional[str] = None
    port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[SecretStr] = None
    repositories: DatabaseRepositories = DatabaseRepositories()
    migrations: DatabaseMigrations = DatabaseMigrations()
    model_config = {"frozen": True}


class Forwarding(BaseModel):
    moderation_chat_ids: Optional[Tuple[int]] = None
    publication_channel_ids: Optional[Tuple[int]] = None
    types: Tuple[ForwardingType, ...] = ("text", "photo", "video")
    model_config = {"frozen": True}


class OpenAI(BaseModel):
    api_key: Optional[SecretStr] = None
    timeout: int = 10
    max_retries: int = 0
    model_config = {"frozen": True}


class Moderation(BaseModel):
    enabled: bool = True
    model: str = "gpt-5-mini"
    types: Tuple[ModerationType, ...] = ("omni", "gpt")
    model_config = {"frozen": True}


class Logging(BaseModel):
    level: LoggingLevel = "INFO"
    fmt: Optional[str] = "%(asctime)s.%(msecs)03d %(levelname)s [%(name)s] %(message)s"
    date_fmt: Optional[str] = "%Y-%m-%d %H:%M:%S"
    model_config = {"frozen": True}
