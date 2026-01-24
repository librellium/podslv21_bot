from aiogram import BaseMiddleware
from aiogram.types import Message

from anonflow.database import UserRepository
from anonflow.translator import Translator

from .utils import extract_message


class BlockedMiddleware(BaseMiddleware):
    def __init__(self, user_repository: UserRepository, translator: Translator):
        super().__init__()

        self.user_repository = user_repository
        self.translator = translator

    async def __call__(self, handler, event, data):
        _ = self.translator.get()

        message = extract_message(event)
        if isinstance(message, Message):
            user = await self.user_repository.get(message.chat.id)

            if user and user.is_blocked:
                await message.answer(_("messages.user.blocked", message))
                return

        return await handler(event, data)
