from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from anonflow.translator import Translator


class InfoRouter(Router):
    def __init__(self, translator: Translator):
        super().__init__()

        self.translator = translator

    def setup(self):
        @self.message(Command("info"))
        async def on_start(message: Message):
            _ = self.translator.get()
            await message.answer(_("messages.command.info", message=message))
