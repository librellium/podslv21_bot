from typing import List, Literal, Optional, TypeAlias

from pydantic import BaseModel, SecretStr

ForwardingMode: TypeAlias = Literal["both", "moderation", "publication"]
ForwardingType: TypeAlias = Literal["text", "photo", "video"]
ModerationType: TypeAlias = Literal["gpt"]
LoggingLevel: TypeAlias = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

class Bot(BaseModel):
    token: Optional[SecretStr] = None
    timeout: int = 10

class Forwarding(BaseModel):
    mode: Optional[ForwardingMode] = "both"
    moderation_chat_id: Optional[int] = None
    publication_chat_id: Optional[int] = None
    message_template: str = "🔔 У вас новое сообщение!\n\n<blockquote>{text}</blockquote>"
    types: List[ForwardingType] = ["text", "photo", "video"]

class OpenAI(BaseModel):
    api_key: Optional[SecretStr] = None
    timeout: int = 10
    max_retries: int = 0

class Moderation(BaseModel):
    enabled: bool = True
    model: str = "gpt-5-mini"
    types: List[ModerationType] = ["gpt"]

class Logging(BaseModel):
    level: LoggingLevel = "INFO"
    fmt: Optional[str] = "%(asctime)s.%(msecs)03d %(levelname)s [%(name)s] %(message)s"
    date_fmt: Optional[str] = "%Y-%m-%d %H:%M:%S"