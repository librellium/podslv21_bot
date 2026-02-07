from dataclasses import dataclass
from typing import TypeAlias, Union

from .content import ContentTextItem, ContentMediaGroup, ContentMediaItem


@dataclass(frozen=True)
class Event:
    pass

@dataclass(frozen=True)
class PostPreparedEvent(Event):
    content: Union[ContentTextItem, ContentMediaItem, ContentMediaGroup]
    moderation_approved: bool

@dataclass(frozen=True)
class ModerationDecisionEvent(Event):
    approved: bool
    reason: str

@dataclass(frozen=True)
class ModerationStartedEvent(Event):
    pass

Events: TypeAlias = Union[PostPreparedEvent, ModerationDecisionEvent, ModerationStartedEvent]
