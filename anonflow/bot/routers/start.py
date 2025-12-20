from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from anonflow.translator import Translator


class StartRouter(Router):
    def __init__(self, translator: Translator):
        super().__init__()

        self.translator = translator

        self._register_handlers()

    def _register_handlers(self):
        @self.message(CommandStart())
        async def on_start(message: Message):
            _ = self.translator.get()
            await message.answer(_("messages.command.start", message=message))
