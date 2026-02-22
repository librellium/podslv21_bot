from itertools import chain
from typing import Any, Callable, Dict, Tuple

from aiogram.types import ChatIdUnion, Message

from anonflow.translator import Translator

from .content import ContentMediaGroup, ContentTextItem
from .delivery import DeliveryService
from .results import (
    Results,
    CommandInfoResult,
    CommandStartResult,
    ModerationDecisionResult,
    ModerationStartedResult,
    PostPreparedResult,
    UserBannedResult,
    UserNotRegisteredResult,
    UserSubscriptionRequiredResult,
    UserThrottledResult
)


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
            CommandInfoResult: self._handle_command_info,
            CommandStartResult: self._handle_command_start,
            PostPreparedResult: self._handle_post_prepared,
            ModerationStartedResult: self._handle_moderation_started,
            ModerationDecisionResult: self._handle_moderation_decision,
            UserBannedResult: self._handle_user_banned,
            UserNotRegisteredResult: self._handle_user_not_registered,
            UserSubscriptionRequiredResult: self._handle_user_subscription_required,
            UserThrottledResult: self._handle_user_throttled
        }

    async def _handle_command_info(self, result: CommandInfoResult, message: Message, _):
        await self.delivery_service.send_text(message.chat.id, _("messages.user.command_info", message=message))

    async def _handle_command_start(self, result: CommandStartResult, message: Message, _):
        await self.delivery_service.send_text(message.chat.id, _("messages.user.command_start", message=message))

    async def _handle_post_prepared(self, result: PostPreparedResult, message: Message, _):
        chat_ids = (
            chain(self.moderation_chat_ids, self.publication_channel_ids)
            if result.moderation_approved
            else iter(self.moderation_chat_ids)
        )

        content = result.content
        for chat_id in chat_ids:
            if isinstance(content, ContentTextItem):
                await self.delivery_service.send_text(chat_id, _("messages.channel.text", text=content.text))
            elif isinstance(content, ContentMediaGroup):
                items = content.items
                if len(items) > 1:
                    await self.delivery_service.send_media_group(chat_id, content)
                elif len(items) == 1:
                    await self.delivery_service.send_media(chat_id, items[0])

        if result.moderation_approved:
            await message.answer(_("messages.user.moderation_approved", message=message))

    async def _handle_moderation_started(self, result: ModerationStartedResult, message: Message, _):
        await self.delivery_service.send_text(
            message.chat.id,
            _("messages.user.moderation_started", message=message)
        )

    async def _handle_moderation_decision(self, result: ModerationDecisionResult, message: Message, _):
        for chat_id in self.moderation_chat_ids:
            if result.is_approved:
                await self.delivery_service.send_text(
                    chat_id,
                    _(
                        "messages.staff.moderation_approved",
                        message=message,
                        explanation=result.reason,
                    )
                )
            else:
                await self.delivery_service.send_text(
                    chat_id,
                    _(
                        "messages.staff.moderation_rejected",
                        message=message,
                        explanation=result.reason,
                    )
                )

        if not result.is_approved:
            await self.delivery_service.send_text(
                message.chat.id,
                _("messages.user.moderation_rejected", message=message)
            )

    async def _handle_user_banned(self, result: UserBannedResult, message: Message, _):
        await self.delivery_service.send_text(message.chat.id, _("messages.user.banned", message))

    async def _handle_user_not_registered(self, result: UserNotRegisteredResult, message: Message, _):
        await self.delivery_service.send_text(message.chat.id, _("messages.user.not_registered", message))

    async def _handle_user_subscription_required(self, result: UserSubscriptionRequiredResult, message: Message, _):
        await self.delivery_service.send_text(message.chat.id, _("messages.user.subscription_required", message))

    async def _handle_user_throttled(self, result: UserThrottledResult, message: Message, _):
        await self.delivery_service.send_text(
            message.chat.id,
            _(
                "messages.user.throttled",
                message,
                remaining=result.remaining_time
            )
        )

    async def dispatch(self, result: Results, message: Message):
        _ = self.translator.get()

        handler = self._handlers.get(type(result))
        if handler is None:
            return

        await handler(result, message, _)
