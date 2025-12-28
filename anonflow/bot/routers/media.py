import asyncio
from asyncio import CancelledError
from typing import Dict, List, Optional

from aiogram import F, Router
from aiogram.enums import ChatType
from aiogram.types import InputMediaPhoto, InputMediaVideo, Message

from anonflow.bot.events.models import BotMessagePreparedEvent, ModerationDecisionEvent
from anonflow.bot.events.event_handler import EventHandler
from anonflow.config import Config
from anonflow.moderation import ModerationExecutor
from anonflow.translator import Translator


class MediaRouter(Router):
    def __init__(
        self,
        config: Config,
        translator: Translator,
        event_handler: EventHandler,
        moderation_executor: Optional[ModerationExecutor] = None,
    ):
        super().__init__()

        self.config = config
        self.translator = translator
        self.event_handler = event_handler
        self.executor = moderation_executor

        self.media_groups: Dict[str, List[Message]] = {}
        self.media_groups_tasks: Dict[str, asyncio.Task] = {}
        self.media_groups_lock = asyncio.Lock()

        self._register_handlers()

    def _register_handlers(self):
        @self.message(F.photo | F.video)
        async def on_photo(message: Message):
            if message.chat.type != ChatType.PRIVATE:
                return

            def can_send_media(msgs: List[Message]):
                photos = len([msg for msg in msgs if msg.photo])
                videos = len([msg for msg in msgs if msg.video])

                return (
                    photos and "photo" in self.config.forwarding.types
                ) or (
                    videos and "video" in self.config.forwarding.types
                )

            async def get_media(msg: Message):
                _ = self.translator.get()

                caption = _("messages.channel.media", message=msg)

                if msg.photo and "photo" in self.config.forwarding.types:
                    return InputMediaPhoto(media=msg.photo[-1].file_id, caption=caption)
                elif msg.video and "video" in self.config.forwarding.types:
                    return InputMediaVideo(media=msg.video.file_id, caption=caption)

            async def process_messages(messages: list[Message]):
                if not messages:
                    return

                _ = self.translator.get()

                if can_send_media(messages):
                    moderation = self.config.moderation.enabled
                    moderation_passed = not moderation

                    media = []
                    for msg in messages:
                        if moderation and msg.caption:
                            async for event in self.executor.process_message(msg):
                                if isinstance(event, ModerationDecisionEvent):
                                    moderation_passed = event.approved
                                await self.event_handler.handle(event, message)

                        media.append(await get_media(msg))

                    if moderation_passed:
                        await self.event_handler.handle(BotMessagePreparedEvent(media), messages[0])

            media_group_id = message.media_group_id

            async def await_media_group():
                try:
                    await asyncio.sleep(2)
                    async with self.media_groups_lock:
                        messages = self.media_groups.pop(media_group_id, [])
                        self.media_groups_tasks.pop(media_group_id, None)
                    await process_messages(messages)
                except CancelledError:
                    pass

            if media_group_id:
                self.media_groups.setdefault(media_group_id, []).append(message)

                task = self.media_groups_tasks.get(media_group_id)
                if task:
                    task.cancel()

                self.media_groups_tasks[media_group_id] = asyncio.create_task(
                    await_media_group()
                )
                return

            await process_messages([message])
