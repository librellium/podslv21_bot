from typing import Optional

from aiogram import Router

from anonflow.config import Config
from anonflow.database import Database, UserRepository
from anonflow.moderation import ModerationExecutor
from anonflow.translator import Translator

from .messaging import MessageSender
from .routers import InfoRouter, MediaRouter, StartRouter, TextRouter


def build(
    config: Config,
    database: Database,
    user_repository: UserRepository,
    translator: Translator,
    message_sender: MessageSender,
    moderation_executor: Optional[ModerationExecutor] = None,
) -> Router:
    main_router = Router()

    routers = [
        StartRouter(
            translator=translator,
            user_repository=user_repository
        ),
        InfoRouter(translator=translator),
        TextRouter(
            config=config,
            database=database,
            translator=translator,
            message_sender=message_sender,
            moderation_executor=moderation_executor
        ),
        MediaRouter(
            config=config,
            database=database,
            translator=translator,
            message_sender=message_sender,
            moderation_executor=moderation_executor
        ),
    ]

    for router in routers:
        router.setup()

    main_router.include_routers(*routers)
    return main_router
