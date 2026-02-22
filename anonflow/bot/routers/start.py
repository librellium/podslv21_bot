from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from anonflow.services import MessageRouter, UserService
from anonflow.services.transport.results import CommandStartResult


class StartRouter(Router):
    def __init__(self, message_router: MessageRouter, user_service: UserService):
        super().__init__()
        self.message_router = message_router
        self.user_service = user_service

    def setup(self):
        @self.message(CommandStart())
        async def on_start(message: Message):
            if message.from_user:
                await self.user_service.add(message.from_user.id)
            await self.message_router.dispatch(
                CommandStartResult(),
                message
            )
