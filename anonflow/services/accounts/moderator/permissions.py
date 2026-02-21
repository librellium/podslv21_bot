from dataclasses import dataclass, asdict
from enum import Enum


@dataclass(frozen=True)
class ModeratorPermissions:
    can_approve_posts: bool = False
    can_manage_bans: bool = False
    can_manage_moderators: bool = False

    def to_dict(self):
        return asdict(self)

class ModeratorPermission(str, Enum):
    APPROVE_POSTS = "can_approve_posts"
    MANAGE_BANS = "can_manage_bans"
    MANAGE_MODERATORS = "can_manage_moderators"
