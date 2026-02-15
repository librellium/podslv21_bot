from itertools import chain
from typing import Any, Callable, Dict, Tuple

from aiogram.types import ChatIdUnion, Message

from anonflow.services.accounts import UserService, ModeratorService
from anonflow.translator import Translator

from .content import ContentMediaGroup, ContentTextItem
from .delivery import DeliveryService
from .events import (
    Events,
    CommandInfoEvent,
    CommandStartEvent,
    ModerationDecisionEvent,
    ModerationStartedEvent,
    PostPreparedEvent,
    UserBlockedEvent,
    UserNotRegisteredEvent,
    UserSubscriptionRequiredEvent,
    UserThrottledEvent
)


class MessageRouter:
    def __init__(
        self,
        moderation_chat_ids: Tuple[ChatIdUnion],
        publication_channel_ids: Tuple[ChatIdUnion],
        delivery_service: DeliveryService,
        user_service: UserService,
        moderator_service: ModeratorService,
        translator: Translator
    ):
        self.moderation_chat_ids = moderation_chat_ids
        self.publication_channel_ids = publication_channel_ids
        self.delivery_service = delivery_service
        self.user_service = user_service
        self.moderator_service = moderator_service
        self.translator = translator

        self._handlers: Dict[Any, Callable] = {
            CommandInfoEvent: self._handle_command_info,
            CommandStartEvent: self._handle_command_start,
            PostPreparedEvent: self._handle_post_prepared,
            ModerationStartedEvent: self._handle_moderation_started,
            ModerationDecisionEvent: self._handle_moderation_decision,
            UserBlockedEvent: self._handle_user_blocked,
            UserNotRegisteredEvent: self._handle_user_not_registered,
            UserSubscriptionRequiredEvent: self._handle_user_subscription_required,
            UserThrottledEvent: self._handle_user_throttled
        }

    async def _handle_command_info(self, event: CommandInfoEvent, message: Message, _):
        await self.delivery_service.send_text(message.chat.id, _("messages.user.command_info", message=message))

    async def _handle_command_start(self, event: CommandStartEvent, message: Message, _):
        await self.user_service.add(event.user_id)
        await self.delivery_service.send_text(message.chat.id, _("messages.user.command_start", message=message))

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
                    await self.delivery_service.send_media_group(chat_id, content)
                elif len(items) == 1:
                    await self.delivery_service.send_media(chat_id, items[0])

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

    async def _handle_user_blocked(self, event: UserBlockedEvent, message: Message, _):
        await self.delivery_service.send_text(message.chat.id, _("messages.user.blocked", message))

    async def _handle_user_not_registered(self, event: UserNotRegisteredEvent, message: Message, _):
        await self.delivery_service.send_text(message.chat.id, _("messages.user.start_required", message))

    async def _handle_user_subscription_required(self, event: UserSubscriptionRequiredEvent, message: Message, _):
        await self.delivery_service.send_text(message.chat.id, _("messages.user.subscription_required", message))

    async def _handle_user_throttled(self, event: UserThrottledEvent, message: Message, _):
        await self.delivery_service.send_text(
            message.chat.id,
            _(
                "messages.user.send_busy",
                message,
                remaining=event.remaining_time
            )
        )

    async def dispatch(self, event: Events, message: Message):
        _ = self.translator.get()

        handler = self._handlers.get(type(event))
        if handler is None:
            return

        await handler(event, message, _)
