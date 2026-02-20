from aiogram import BaseMiddleware
from aiogram.enums import ChatType
from aiogram.types import Message

from anonflow.services import MessageRouter, UserService
from anonflow.services.transport.results import UserNotRegisteredResult


class NotRegisteredMiddleware(BaseMiddleware):
    def __init__(self, message_router: MessageRouter, user_service: UserService):
        super().__init__()

        self.message_router = message_router
        self.user_service = user_service

    async def __call__(self, handler, event, data):
        message = getattr(event, "message", None)
        if isinstance(message, Message) and message.chat.type == ChatType.PRIVATE:
            text = message.text or message.caption or ""

            is_user_exists = await self.user_service.has(message.chat.id)
            if not is_user_exists and not text.startswith("/start"):
                await self.message_router.dispatch(UserNotRegisteredResult(), message)
                return

        return await handler(event, data)
