from typing import FrozenSet

from aiogram import F, Router
from aiogram.enums import ChatType
from aiogram.types import Message

from anonflow.config.models import ForwardingType
from anonflow.moderation import ModerationExecutor
from anonflow.services.transport import MessageRouter
from anonflow.services.transport.content import ContentTextItem
from anonflow.services.transport.results import (
    ModerationDecisionResult,
    PostPreparedResult
)


class TextRouter(Router):
    def __init__(
        self,
        message_router: MessageRouter,
        forwarding_types: FrozenSet[ForwardingType],
        moderation_executor: ModerationExecutor,
    ):
        super().__init__()

        self.message_router = message_router
        self.forwarding_types = forwarding_types
        self.moderation_executor = moderation_executor

    def setup(self):
        @self.message(F.text)
        async def on_text(message: Message):
            if (
                message.chat.type == ChatType.PRIVATE
                and "text" in self.forwarding_types
            ):
                moderation_approved = False

                async for result in self.moderation_executor.process_message(message):
                    if isinstance(result, ModerationDecisionResult):
                        moderation_approved = result.is_approved
                    await self.message_router.dispatch(result, message)

                await self.message_router.dispatch(
                    PostPreparedResult(
                        ContentTextItem(message.text or ""),
                        moderation_approved
                    ),
                    message
                )
