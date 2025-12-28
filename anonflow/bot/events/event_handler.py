from contextlib import suppress
from typing import Dict

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import ChatIdUnion, Message, InputMediaPhoto, InputMediaVideo

from anonflow.config import Config
from anonflow.translator import Translator

from .models import (
    BotMessagePreparedEvent,
    Events,
    ExecutorDeletionEvent,
    ModerationDecisionEvent,
    ModerationStartedEvent
)


class EventHandler:
    def __init__(self, bot: Bot, config: Config, translator: Translator):
        self.bot = bot
        self.config = config
        self.translator = translator

        self._messages: Dict[ChatIdUnion, Message] = {}

    async def handle(self, event: Events, message: Message):
        moderation_chat_ids = self.config.forwarding.moderation_chat_ids or ()
        publication_channel_ids = self.config.forwarding.publication_channel_ids or ()

        _ = self.translator.get()

        if isinstance(event, ModerationStartedEvent):
            self._messages[message.chat.id] = await message.answer(
                _("messages.user.moderation_pending", message=message)
            )
        elif isinstance(event, ModerationDecisionEvent):
            for chat_id in moderation_chat_ids:
                if event.approved:
                    await self.bot.send_message(
                        chat_id,
                        _(
                            "messages.staff.moderation_approved",
                            message=message,
                            explanation=event.explanation,
                        )
                    )
                else:
                    await self.bot.send_message(
                        chat_id,
                        _(
                            "messages.staff.moderation_rejected",
                            message=message,
                            explanation=event.explanation,
                        )
                    )

            with suppress(TelegramBadRequest):
                msg = self._messages.get(message.chat.id)
                if isinstance(msg, Message):
                    await msg.delete()

            if event.approved:
                await message.answer(_("messages.user.send_success", message=message))
            else:
                await message.answer(_("messages.user.moderation_rejected", message=message))
        elif isinstance(event, BotMessagePreparedEvent) and publication_channel_ids is not None:
            for chat_id in publication_channel_ids + moderation_chat_ids:
                content = event.content
                if isinstance(content, str):
                    await self.bot.send_message(
                        chat_id,
                        _("messages.channel.text", message=message)
                    )
                if isinstance(content, list):
                    if len(content) > 1:
                        await self.bot.send_media_group(
                            chat_id,
                            content
                        )
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
        elif isinstance(event, ExecutorDeletionEvent) and moderation_chat_ids:
            for chat_id in moderation_chat_ids:
                if event.success:
                    await self.bot.send_message(
                        chat_id,
                        _(
                            "messages.staff.deletion_success",
                            message=message,
                            message_id=event.message_id,
                        )
                    )
                else:
                    await self.bot.send_message(
                        chat_id,
                        _(
                            "messages.staff.deletion_failure",
                            message=message,
                            message_id=event.message_id,
                        )
                    )
