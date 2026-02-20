from dataclasses import dataclass
from typing import TypeAlias, Union

from .content import ContentMediaGroup, ContentMediaItem, ContentTextItem


@dataclass(frozen=True)
class Result:
    pass

@dataclass(frozen=True)
class CommandInfoResult(Result):
    pass

@dataclass(frozen=True)
class CommandStartResult(Result):
    user_id: int

@dataclass(frozen=True)
class PostPreparedResult(Result):
    content: Union[ContentTextItem, ContentMediaItem, ContentMediaGroup]
    moderation_approved: bool

@dataclass(frozen=True)
class ModerationDecisionResult(Result):
    is_approved: bool
    reason: str

@dataclass(frozen=True)
class ModerationStartedResult(Result):
    pass

@dataclass(frozen=True)
class UserBlockedResult(Result):
    pass

@dataclass(frozen=True)
class UserSubscriptionRequiredResult(Result):
    pass

@dataclass(frozen=True)
class UserThrottledResult(Result):
    remaining_time: int

@dataclass(frozen=True)
class UserNotRegisteredResult(Result):
    pass

Results: TypeAlias = Union[
    CommandInfoResult,
    CommandStartResult,
    PostPreparedResult,
    ModerationDecisionResult,
    ModerationStartedResult,
    UserBlockedResult,
    UserSubscriptionRequiredResult,
    UserThrottledResult,
    UserNotRegisteredResult
]
