from aiogram import BaseMiddleware
from aiogram.types import Message

from anonflow.services import MessageRouter, ModeratorService
from anonflow.services.transport.results import UserBlockedResult


class BlockedMiddleware(BaseMiddleware):
    def __init__(self, message_router: MessageRouter, moderator_service: ModeratorService):
        super().__init__()

        self.message_router = message_router
        self.moderator_service = moderator_service

    async def __call__(self, handler, event, data):
        message = getattr(event, "message", None)
        if isinstance(message, Message):
            if await self.moderator_service.is_banned(message.chat.id):
                await self.message_router.dispatch(UserBlockedResult(), message)
                return

        return await handler(event, data)
