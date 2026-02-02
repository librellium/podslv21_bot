from typing import Optional

from aiogram import F, Router
from aiogram.enums import ChatType
from aiogram.types import Message

from anonflow.bot.messaging.events import BotMessagePreparedEvent, ModerationDecisionEvent
from anonflow.bot.messaging.message_sender import MessageSender
from anonflow.database import Database
from anonflow.config import Config
from anonflow.moderation import ModerationExecutor
from anonflow.translator import Translator


class TextRouter(Router):
    def __init__(
        self,
        config: Config,
        database: Database,
        translator: Translator,
        message_sender: MessageSender,
        moderation_executor: Optional[ModerationExecutor] = None,
    ):
        super().__init__()

        self.config = config
        self.database = database
        self.translator = translator
        self.message_sender = message_sender
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
                        await self.message_sender.dispatch(event, message)

                _ = self.translator.get()
                await self.message_sender.dispatch(
                    BotMessagePreparedEvent(
                        _("messages.channel.text", message=message),
                        moderation_approved
                    ),
                    message
                )
