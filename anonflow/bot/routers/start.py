from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from anonflow.database import UserRepository
from anonflow.translator import Translator


class StartRouter(Router):
    def __init__(self, translator: Translator, user_repository: UserRepository):
        super().__init__()

        self.translator = translator
        self.user_repository = user_repository

    def setup(self):
        @self.message(CommandStart())
        async def on_start(message: Message):
            await self.user_repository.add(message.chat.id)
            _ = self.translator.get()
            await message.answer(_("messages.command.start", message=message))
