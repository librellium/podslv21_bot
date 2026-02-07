from typing import Optional

from aiogram import F, Router
from aiogram.enums import ChatType
from aiogram.types import Message

from anonflow.config import Config
from anonflow.moderation import ModerationExecutor
from anonflow.services.transport import MessageRouter
from anonflow.services.transport.content import ContentTextItem
from anonflow.services.transport.events import PostPreparedEvent, ModerationDecisionEvent


class TextRouter(Router):
    def __init__(
        self,
        config: Config,
        message_router: MessageRouter,
        moderation_executor: Optional[ModerationExecutor] = None,
    ):
        super().__init__()

        self.config = config
        self.message_router = message_router
        self.moderation_executor = moderation_executor

    def setup(self):
        @self.message(F.text)
        async def on_text(message: Message):
            moderation = self.config.moderation.enabled
            moderation_approved = not moderation

            if (
                message.chat.type == ChatType.PRIVATE
                and "text" in self.config.forwarding.types
            ):
                executor = self.moderation_executor
                if moderation and executor:
                    async for event in executor.process_message(message):
                        if isinstance(event, ModerationDecisionEvent):
                            moderation_approved = event.approved
                        await self.message_router.dispatch(event, message)

                await self.message_router.dispatch(
                    PostPreparedEvent(
                        ContentTextItem(message.text or ""),
                        moderation_approved
                    ),
                    message
                )
