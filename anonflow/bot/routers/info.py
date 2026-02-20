from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from anonflow.services import MessageRouter
from anonflow.services.transport.results import CommandInfoResult


class InfoRouter(Router):
    def __init__(self, message_router: MessageRouter):
        super().__init__()
        self.message_router = message_router

    def setup(self):
        @self.message(Command("info"))
        async def on_info(message: Message):
            await self.message_router.dispatch(CommandInfoResult(), message)
