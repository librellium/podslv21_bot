from typing import Literal, Optional, Tuple, TypeAlias

from pydantic import BaseModel, SecretStr

SlowmodeMode: TypeAlias = Literal["global", "user"]
ForwardingType: TypeAlias = Literal["text", "photo", "video"]
ModerationType: TypeAlias = Literal["omni", "gpt"]
LoggingLevel: TypeAlias = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


class Bot(BaseModel):
    token: Optional[SecretStr] = None
    timeout: int = 10
    model_config = {"frozen": True}


class BehaviorSlowmode(BaseModel):
    enabled: bool = True
    mode: SlowmodeMode = "user"
    delay: float = 120
    model_config = {"frozen": True}


class BehaviorSubscriptionRequirement(BaseModel):
    enabled: bool = True
    channel_ids: Optional[Tuple[int]] = None
    model_config = {"frozen": True}


class Behavior(BaseModel):
    slowmode: BehaviorSlowmode = BehaviorSlowmode()
    subscription_requirement: BehaviorSubscriptionRequirement = BehaviorSubscriptionRequirement()
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
