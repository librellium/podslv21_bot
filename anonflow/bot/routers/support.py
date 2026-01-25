from aiogram import Router
from aiogram.enums import ChatType
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from anonflow.bot.states import SupportStates
from anonflow.translator import Translator


class SupportRouter(Router):
    def __init__(self, translator: Translator):
        super().__init__()

        self.translator = translator

    def setup(self):
        @self.message(Command("support"))
        async def on_support(message: Message, state: FSMContext):
            if message.chat.type == ChatType.PRIVATE:
                await state.set_state(SupportStates.in_support)
                _ = self.translator.get()
                await message.answer(_("messages.command.support", message=message))

        @self.message(Command("end_support"))
        async def on_end_support(message: Message, state: FSMContext):
            if message.chat.type == ChatType.PRIVATE:
                await state.clear()
                _ = self.translator.get()
                await message.answer(_("messages.command.end_support", message=message))
