from typing import Optional

from aiogram import Router

from simpleforward.config import Config
from simpleforward.moderation import AsyncModerator

from .message_manager import MessageManager
from .routers.media import MediaRouter
from .routers.start import StartRouter
from .routers.text import TextRouter


def build(config: Config,
          message_manager: MessageManager,
          moderator: Optional[AsyncModerator] = None):
    main_router = Router()

    main_router.include_routers(
        StartRouter(),
        TextRouter(
            config, message_manager, moderator
        ),
        MediaRouter(
            config, message_manager, moderator
        )
    )

    return main_router