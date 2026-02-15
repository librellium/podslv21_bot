from typing import Tuple

from aiogram.types import ChatIdUnion

from anonflow.services import (
    MessageRouter,
    ModeratorService,
    UserService
)

from .blocked import BlockedMiddleware
from .not_registered import NotRegisteredMiddleware
from .subscription import SubscriptionMiddleware
from .throttling import ThrottlingMiddleware

def build(
    message_router: MessageRouter,
    user_service: UserService,
    moderator_service: ModeratorService,

    subscription_requirement: bool,
    subscription_channel_ids: Tuple[ChatIdUnion],

    throttling: bool,
    throttling_delay: float,
    throttling_allowed_chat_ids: Tuple[ChatIdUnion]
):
    middlewares = []

    middlewares.append(
        BlockedMiddleware(
            message_router=message_router,
            moderator_service=moderator_service
        )
    )

    if subscription_requirement:
        middlewares.append(
            SubscriptionMiddleware(
                channel_ids=subscription_channel_ids,
                message_router=message_router
            )
        )

    middlewares.append(
        NotRegisteredMiddleware(
            message_router=message_router,
            user_service=user_service
        )
    )

    if throttling:
        middlewares.append(
            ThrottlingMiddleware(
                message_router=message_router,
                delay=throttling_delay,
                allowed_chat_ids=throttling_allowed_chat_ids
            )
        )

    return middlewares
