from typing import Optional

from aiogram import Bot, F, Router
from aiogram.enums import ChatType
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.types import Message

from anonflow.bot.utils.event_handler import EventHandler
from anonflow.bot.utils.message_manager import MessageManager
from anonflow.config import Config
from anonflow.moderation import ModerationDecisionEvent, ModerationExecutor
from anonflow.translator import Translator


class TextRouter(Router):
    def __init__(
        self,
        config: Config,
        message_manager: MessageManager,
        translator: Translator,
        moderation_executor: Optional[ModerationExecutor] = None,
        event_handler: Optional[EventHandler] = None,
    ):
        super().__init__()

        self.config = config
        self.message_manager = message_manager
        self.translator = translator
        self.executor = moderation_executor
        self.event_handler = event_handler

        self._register_handlers()

    def _register_handlers(self):
        @self.message(F.text)
        async def on_text(message: Message, bot: Bot):
            reply_to_message = message.reply_to_message

            _ = self.translator.get()

            moderation = self.config.moderation.enabled
            moderation_passed = not moderation

            moderation_chat_ids = self.config.forwarding.moderation_chat_ids
            publication_channel_ids = self.config.forwarding.publication_channel_ids

            if (
                message.chat.id in moderation_chat_ids
                and reply_to_message
                and reply_to_message.from_user.is_bot
            ):
                result = self.message_manager.get(reply_to_message.message_id)

                if result:
                    reply_to_message_id, chat_id = result
                    try:
                        await bot.send_message(
                            chat_id,
                            message.text,
                            reply_to_message_id=reply_to_message_id,
                        )
                        await message.answer(_("messages.user.send_success", message=message))
                    except (TelegramBadRequest, TelegramForbiddenError) as e:
                        await message.answer(
                            _(
                                "messages.user.send_failure",
                                message=message,
                                exception=e,
                            )
                        )
            elif (
                message.chat.type == ChatType.PRIVATE
                and "text" in self.config.forwarding.types
            ):
                try:
                    group_message_id = None

                    targets = {}
                    if moderation_chat_ids:
                        for chat_id in moderation_chat_ids:
                            targets[chat_id] = True

                    if moderation:
                        async for event in self.executor.process_message(message):
                            if isinstance(event, ModerationDecisionEvent):
                                moderation_passed = event.approved
                            await self.event_handler.handle(event, message)

                    if publication_channel_ids and moderation_passed:
                        for channel_id in publication_channel_ids:
                            targets[channel_id] = False

                    for target, save_message_id in targets.items():
                        reply_to_message_id = message.message_id
                        msg = await bot.send_message(
                            target,
                            _("messages.channel.text", message=message)
                        )

                        if save_message_id:
                            group_message_id = msg.message_id

                    self.message_manager.add(
                        reply_to_message_id, group_message_id, message.chat.id
                    )
                except (TelegramBadRequest, TelegramForbiddenError) as e:
                    await message.answer(
                        _(
                            "messages.user.send_failure",
                            message=message,
                            exception=e,
                        )
                    )
