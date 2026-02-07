from typing import Optional

from aiogram import Router

from anonflow.config import Config
from anonflow.database import Database
from anonflow.moderation import ModerationExecutor
from anonflow.services import MessageRouter, ModeratorService, UserService
from anonflow.translator import Translator

from .routers import InfoRouter, MediaRouter, StartRouter, TextRouter


def build(
    config: Config,
    moderator_service: ModeratorService,
    user_service: UserService,
    translator: Translator,
    message_router: MessageRouter,
    moderation_executor: Optional[ModerationExecutor] = None,
) -> Router:
    main_router = Router()

    routers = [
        StartRouter(
            translator=translator,
            user_service=user_service
        ),
        InfoRouter(translator=translator),
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
