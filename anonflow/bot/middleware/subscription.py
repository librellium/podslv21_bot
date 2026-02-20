from typing import Tuple

from aiogram import BaseMiddleware
from aiogram.enums import ChatMemberStatus, ChatType
from aiogram.types import ChatIdUnion, Message

from anonflow.services import MessageRouter
from anonflow.services.transport.results import UserSubscriptionRequiredResult


class SubscriptionMiddleware(BaseMiddleware):
    def __init__(self, channel_ids: Tuple[ChatIdUnion], message_router: MessageRouter):
        super().__init__()

        self.channel_ids = channel_ids
        self.message_router = message_router

    async def __call__(self, handler, event, data):
        message = getattr(event, "message", None)
        if isinstance(message, Message) and message.chat.type == ChatType.PRIVATE:
            user_id = message.from_user.id # type: ignore
            for channel_id in self.channel_ids:
                member = await message.bot.get_chat_member(channel_id, user_id) # type: ignore
                if member.status in (ChatMemberStatus.KICKED, ChatMemberStatus.LEFT):
                    await self.message_router.dispatch(UserSubscriptionRequiredResult(), message)
                    return

        return await handler(event, data)
