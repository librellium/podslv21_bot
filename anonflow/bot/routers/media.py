import asyncio
from asyncio import CancelledError
from typing import Dict, List, Optional, Tuple

from aiogram import F, Router
from aiogram.enums import ChatType
from aiogram.types import InputMediaPhoto, InputMediaVideo, Message

from anonflow.bot.messaging.events import BotMessagePreparedEvent, ModerationDecisionEvent
from anonflow.bot.messaging.message_sender import MessageSender
from anonflow.database import Database
from anonflow.config import Config
from anonflow.moderation import ModerationExecutor
from anonflow.translator import Translator


class MediaRouter(Router):
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

        self.media_groups: Dict[str, List[Message]] = {}
        self.media_groups_tasks: Dict[str, asyncio.Task] = {}
        self.media_groups_lock = asyncio.Lock()

    def setup(self):
        def can_send_media(msgs: List[Message]):
            forwarding_types = self.config.forwarding.types
            return any(
                (msg.photo and "photo" in forwarding_types) or
                (msg.video and "video" in forwarding_types)
                for msg in msgs
            )

        def get_media(message: Message, caption: Optional[str] = None):
            if message.photo and "photo" in self.config.forwarding.types:
                return InputMediaPhoto(media=message.photo[-1].file_id, caption=caption)
            elif message.video and "video" in self.config.forwarding.types:
                return InputMediaVideo(media=message.video.file_id, caption=caption)

        async def process_messages(messages: List[Message]):
            if not messages:
                return

            if can_send_media(messages):
                moderation = self.config.moderation.enabled
                moderation_approved = not moderation
                _ = self.translator.get()

                content = []
                executor = self.moderation_executor
                for index, message in enumerate(messages):
                    if moderation and executor:
                        async for event in executor.process_message(message):
                            if isinstance(event, ModerationDecisionEvent):
                                moderation_approved = event.approved
                            await self.message_sender.dispatch(event, message)

                    if index == 0:
                        caption = _("messages.channel.media", message=message)
                        content.append(get_media(message, caption))
                    else:
                        content.append(get_media(message))

                await self.message_sender.dispatch(
                    BotMessagePreparedEvent(content, moderation_approved),
                    messages[0]
                )

        @self.message(F.photo | F.video)
        async def on_photo(message: Message):
            if message.chat.type != ChatType.PRIVATE:
                return

            media_group_id = message.media_group_id

            async def await_media_group():
                try:
                    await asyncio.sleep(2)
                    async with self.media_groups_lock:
                        messages = self.media_groups.pop(media_group_id, []) # type: ignore
                        self.media_groups_tasks.pop(media_group_id, None) # type: ignore

                    await process_messages(messages)
                except CancelledError:
                    pass

            if media_group_id:
                async with self.media_groups_lock:
                    self.media_groups.setdefault(media_group_id, []).append(message)

                    task = self.media_groups_tasks.get(media_group_id)
                    if task:
                        task.cancel()

                    self.media_groups_tasks[media_group_id] = asyncio.create_task(
                        await_media_group()
                    )
                return

            await process_messages([message])
