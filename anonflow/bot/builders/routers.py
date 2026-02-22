from aiogram import Router

from anonflow.config import Config
from anonflow.moderation import ModerationExecutor
from anonflow.services import MessageRouter, ModeratorService, UserService

from anonflow.bot.routers import (
    InfoRouter,
    MediaRouter,
    StartRouter,
    TextRouter
)

def build(
    config: Config,
    message_router: MessageRouter,
    user_service: UserService,
    moderator_service: ModeratorService,
    moderation_executor: ModerationExecutor,
) -> Router:
    main_router = Router()

    routers = [
        StartRouter(
            message_router=message_router,
            user_service=user_service
        ),
        InfoRouter(message_router=message_router),
        TextRouter(
            message_router=message_router,
            forwarding_types=config.forwarding.types,
            moderation_executor=moderation_executor
        ),
        MediaRouter(
            message_router=message_router,
            forwarding_types=config.forwarding.types,
            moderation_executor=moderation_executor
        ),
    ]

    for router in routers:
        router.setup()

    main_router.include_routers(*routers)
    return main_router
