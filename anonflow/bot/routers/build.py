from typing import Optional

from aiogram import Router

from anonflow.config import Config
from anonflow.moderation import ModerationExecutor
from anonflow.services import MessageRouter

from .info import InfoRouter
from .media import MediaRouter
from .start import StartRouter
from .text import TextRouter

def build(
    config: Config,
    message_router: MessageRouter,
    moderation_executor: Optional[ModerationExecutor] = None,
) -> Router:
    main_router = Router()

    routers = [
        StartRouter(message_router=message_router),
        InfoRouter(message_router=message_router),
        TextRouter(
            config=config,
            message_router=message_router,
            moderation_executor=moderation_executor
        ),
        MediaRouter(
            config=config,
            message_router=message_router,
            moderation_executor=moderation_executor
        ),
    ]

    for router in routers:
        router.setup()

    main_router.include_routers(*routers)
    return main_router
