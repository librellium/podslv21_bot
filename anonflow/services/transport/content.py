from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List


class MediaType(str, Enum):
    PHOTO = "photo"
    VIDEO = "video"

@dataclass(frozen=True)
class ContentItem:
    pass

@dataclass(frozen=True)
class ContentGroup:
    pass

@dataclass(frozen=True)
class ContentTextItem(ContentItem):
    text: str

@dataclass(frozen=True)
class ContentMediaItem(ContentItem):
    type: MediaType
    file_id: str
    caption: Optional[str] = None

@dataclass(frozen=True)
class ContentMediaGroup(ContentGroup):
    items: List[ContentMediaItem] = field(default_factory=list)
