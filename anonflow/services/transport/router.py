from itertools import chain
from typing import Any, Callable, Dict, Tuple

from aiogram.types import ChatIdUnion, Message

from anonflow.translator import Translator

from .content import ContentTextItem, ContentMediaGroup
from .delivery import DeliveryService
from .events import (
    Events,
    ModerationDecisionEvent,
    ModerationStartedEvent,
    PostPreparedEvent
)
from .media_helper import wrap_media


class MessageRouter:
    def __init__(
        self,
        moderation_chat_ids: Tuple[ChatIdUnion],
        publication_channel_ids: Tuple[ChatIdUnion],
        delivery_service: DeliveryService,
        translator: Translator
    ):
        self.moderation_chat_ids = moderation_chat_ids
        self.publication_channel_ids = publication_channel_ids
        self.delivery_service = delivery_service
        self.translator = translator

        self._handlers: Dict[Any, Callable] = {
            PostPreparedEvent: self._handle_post_prepared,
            ModerationStartedEvent: self._handle_moderation_started,
            ModerationDecisionEvent: self._handle_moderation_decision
        }

    async def _handle_post_prepared(self, event: PostPreparedEvent, message: Message, _):
        chat_ids = (
            chain(self.moderation_chat_ids, self.publication_channel_ids)
            if event.moderation_approved
            else iter(self.moderation_chat_ids)
        )

        content = event.content
        for chat_id in chat_ids:
            if isinstance(content, ContentTextItem):
                await self.delivery_service.send_text(chat_id, _("messages.channel.text", text=content.text))
            elif isinstance(content, ContentMediaGroup):
                items = content.items
                if len(items) > 1:
                    await self.delivery_service.send_media_group(
                        chat_id,
                        [
                            wrap_media(item)
                            for item in items
                        ]
                    )
                elif len(items) == 1:
                    await self.delivery_service.send_media(
                        chat_id,
                        wrap_media(items[0])
                    )

        if event.moderation_approved:
            await message.answer(_("messages.user.send_success", message=message))

    async def _handle_moderation_started(self, event: ModerationStartedEvent, message: Message, _):
        await self.delivery_service.send_text(
            message.chat.id,
            _("messages.user.moderation_pending", message=message)
        )

    async def _handle_moderation_decision(self, event: ModerationDecisionEvent, message: Message, _):
        for chat_id in self.moderation_chat_ids:
            if event.approved:
                await self.delivery_service.send_text(
                    chat_id,
                    _(
                        "messages.staff.moderation_approved",
                        message=message,
                        explanation=event.reason,
                    )
                )
            else:
                await self.delivery_service.send_text(
                    chat_id,
                    _(
                        "messages.staff.moderation_rejected",
                        message=message,
                        explanation=event.reason,
                    )
                )

        if not event.approved:
            await self.delivery_service.send_text(
                message.chat.id,
                _("messages.user.moderation_rejected", message=message)
            )

    async def dispatch(self, event: Events, message: Message):
        _ = self.translator.get()

        handler = self._handlers.get(type(event))
        if handler is None:
            return

        await handler(event, message, _)
