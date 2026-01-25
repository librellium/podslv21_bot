from dataclasses import dataclass
from typing import List, Union

from aiogram.types import MediaUnion


@dataclass
class BotMessagePreparedEvent:
    content: Union[str, List[MediaUnion]]
    is_post: bool
    moderation_approved: bool


@dataclass
class ModerationDecisionEvent:
    approved: bool
    reason: str


@dataclass
class ModerationStartedEvent:
    pass


Events = Union[BotMessagePreparedEvent, ModerationDecisionEvent, ModerationStartedEvent]
