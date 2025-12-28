from typing import List

from aiogram import BaseMiddleware
from aiogram.enums import ChatMemberStatus, ChatType
from aiogram.types import ChatIdUnion, Message

from anonflow.translator import Translator

from .utils import extract_message


class SubscriptionMiddleware(BaseMiddleware):
    def __init__(self, channel_ids: List[ChatIdUnion], translator: Translator):
        super().__init__()

        self.channel_ids = channel_ids
        self.translator = translator

    async def __call__(self, handler, event, data):
        _ = self.translator.get()

        message = extract_message(event)

        if isinstance(message, Message) and message.chat.type == ChatType.PRIVATE:
            user_id = message.from_user.id # type: ignore
            for channel_id in self.channel_ids:
                member = await message.bot.get_chat_member(channel_id, user_id) # type: ignore
                if member.status in (ChatMemberStatus.KICKED, ChatMemberStatus.LEFT):
                    await message.answer(_("messages.user.subscription_required", message=message))
                    return

        return await handler(event, data)
