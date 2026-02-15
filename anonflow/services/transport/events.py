from dataclasses import dataclass
from typing import TypeAlias, Union

from .content import ContentMediaGroup, ContentMediaItem, ContentTextItem


@dataclass(frozen=True)
class Event:
    pass

@dataclass(frozen=True)
class CommandInfoEvent(Event):
    pass

@dataclass(frozen=True)
class CommandStartEvent(Event):
    user_id: int

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

@dataclass(frozen=True)
class UserBlockedEvent(Event):
    pass

@dataclass(frozen=True)
class UserSubscriptionRequiredEvent(Event):
    pass

@dataclass(frozen=True)
class UserThrottledEvent(Event):
    remaining_time: int

@dataclass(frozen=True)
class UserNotRegisteredEvent(Event):
    pass

Events: TypeAlias = Union[
    CommandInfoEvent,
    CommandStartEvent,
    PostPreparedEvent,
    ModerationDecisionEvent,
    ModerationStartedEvent,
    UserBlockedEvent,
    UserSubscriptionRequiredEvent,
    UserThrottledEvent,
    UserNotRegisteredEvent
]
