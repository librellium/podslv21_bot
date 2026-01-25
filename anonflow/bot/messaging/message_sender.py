from contextlib import suppress
from typing import Callable, Dict

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import ChatIdUnion, Message, InputMediaPhoto, InputMediaVideo

from anonflow.config import Config
from anonflow.translator import Translator

from .events import (
    BotMessagePreparedEvent,
    Events,
    ModerationDecisionEvent,
    ModerationStartedEvent
)


class MessageSender:
    def __init__(self, bot: Bot, config: Config, translator: Translator):
        self.bot = bot
        self.config = config
        self.translator = translator

        self._messages: Dict[ChatIdUnion, Message] = {}
        self._handlers: Dict[Events, Callable] = {
            BotMessagePreparedEvent: self._handle_bot_message_prepared,
            ModerationStartedEvent: self._handle_moderation_started,
            ModerationDecisionEvent: self._handle_moderation_decision
        }

    async def _handle_bot_message_prepared(self, event: BotMessagePreparedEvent, message: Message, _):
        moderation_chat_ids = self.config.forwarding.moderation_chat_ids or ()
        publication_channel_ids = self.config.forwarding.publication_channel_ids or ()

        chat_ids = moderation_chat_ids
        if event.moderation_approved and event.is_post:
            chat_ids += publication_channel_ids

        for chat_id in chat_ids:
            content = event.content
            if isinstance(content, str):
                await self.bot.send_message(chat_id, content)
            if isinstance(content, list):
                if len(content) > 1:
                    await self.bot.send_media_group(chat_id, content)
                else:
                    input_media = content[0]
                    if isinstance(input_media, InputMediaPhoto):
                        await self.bot.send_photo(
                            chat_id,
                            input_media.media,
                            caption=input_media.caption
                        )
                    elif isinstance(input_media, InputMediaVideo):
                        await self.bot.send_video(
                            chat_id,
                            input_media.media,
                            caption=input_media.caption
                        )

        if event.moderation_approved or not event.is_post:
            await message.answer(_("messages.user.send_success", message=message))

    async def _handle_moderation_started(self, event: ModerationStartedEvent, message: Message, _):
        self._messages[message.chat.id] = await message.answer(
            _("messages.user.moderation_pending", message=message)
        )

    async def _handle_moderation_decision(self, event: ModerationDecisionEvent, message: Message, _):
        moderation_chat_ids = self.config.forwarding.moderation_chat_ids or ()

        for chat_id in moderation_chat_ids:
            if event.approved:
                await self.bot.send_message(
                    chat_id,
                    _(
                        "messages.staff.moderation_approved",
                        message=message,
                        explanation=event.reason,
                    )
                )
            else:
                await self.bot.send_message(
                    chat_id,
                    _(
                        "messages.staff.moderation_rejected",
                        message=message,
                        explanation=event.reason,
                    )
                )

        with suppress(TelegramBadRequest):
            msg = self._messages.get(message.chat.id)
            if isinstance(msg, Message):
                await msg.delete()

        if not event.approved:
            await message.answer(_("messages.user.moderation_rejected", message=message))

    async def dispatch(self, event: Events, message: Message):
        _ = self.translator.get()

        handler = self._handlers.get(type(event))
        if handler is None:
            return

        await handler(event, message, _)
