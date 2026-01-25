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

from . import utils


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
        self.executor = moderation_executor

    def setup(self):
        @self.message(F.text)
        async def on_text(message: Message, is_post: bool):
            moderation = self.config.moderation.enabled
            moderation_approved = not moderation

            if (
                message.chat.type == ChatType.PRIVATE
                and "text" in self.config.forwarding.types
            ):
                msg = utils.strip_post_command(message)
                if moderation and is_post:
                    async for event in self.executor.process_message(msg): # type: ignore
                        if isinstance(event, ModerationDecisionEvent):
                            moderation_approved = event.approved
                        await self.message_sender.dispatch(event, msg)

                _ = self.translator.get()
                content = _("messages.channel.text", message=msg) if is_post else (msg.text or "")
                await self.message_sender.dispatch(
                    BotMessagePreparedEvent(content, is_post, moderation_approved),
                    msg
                )
