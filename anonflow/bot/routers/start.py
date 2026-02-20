from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from anonflow.services import MessageRouter
from anonflow.services.transport.results import CommandStartResult


class StartRouter(Router):
    def __init__(self, message_router: MessageRouter):
        super().__init__()
        self.message_router = message_router

    def setup(self):
        @self.message(CommandStart())
        async def on_start(message: Message):
            if message.from_user:
                await self.message_router.dispatch(
                    CommandStartResult(message.from_user.id),
                    message
                )
