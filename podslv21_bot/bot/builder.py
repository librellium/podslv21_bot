from typing import Optional

from aiogram import Router

from podslv21_bot.config import Config
from podslv21_bot.moderation import ModerationExecutor

from .message_manager import MessageManager
from .routers.media import MediaRouter
from .routers.start import StartRouter
from .routers.text import TextRouter


def build(config: Config,
          message_manager: MessageManager,
          executor: Optional[ModerationExecutor] = None):
    main_router = Router()

    main_router.include_routers(
        StartRouter(),
        TextRouter(
            config, message_manager, executor
        ),
        MediaRouter(
            config, message_manager, executor
        )
    )

    return main_router