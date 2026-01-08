import asyncio
from asyncio import CancelledError
from typing import Dict, List, Optional, Tuple

from aiogram import F, Router
from aiogram.enums import ChatType
from aiogram.types import InputMediaPhoto, InputMediaVideo, Message

from anonflow.bot.events.models import BotMessagePreparedEvent, ModerationDecisionEvent
from anonflow.bot.events.event_handler import EventHandler
from anonflow.database import Database
from anonflow.config import Config
from anonflow.moderation import ModerationExecutor
from anonflow.translator import Translator

from . import utils


class MediaRouter(Router):
    def __init__(
        self,
        config: Config,
        database: Database,
        translator: Translator,
        event_handler: EventHandler,
        moderation_executor: Optional[ModerationExecutor] = None,
    ):
        super().__init__()

        self.config = config
        self.database = database
        self.translator = translator
        self.event_handler = event_handler
        self.executor = moderation_executor

        self.media_groups: Dict[str, List[Tuple[Message, bool]]] = {}
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

        async def process_messages(messages: List[Message], is_post: bool):
            if not messages:
                return

            if can_send_media(messages):
                moderation = self.config.moderation.enabled
                moderation_approved = not moderation
                _ = self.translator.get()

                content = []
                for index, message in enumerate(messages):
                    msg = utils.strip_post_command(message)
                    if moderation and is_post:
                        async for event in self.executor.process_message(msg): # type: ignore
                            if isinstance(event, ModerationDecisionEvent):
                                moderation_approved = event.approved
                            await self.event_handler.handle(event, msg)

                    if index == 0:
                        caption = _("messages.channel.media", message=msg) if is_post else (msg.caption or "")
                        content.append(get_media(msg, caption))
                    else:
                        content.append(get_media(msg))

                await self.event_handler.handle(
                    BotMessagePreparedEvent(content, is_post, moderation_approved),
                    messages[0]
                )

        @self.message(F.photo | F.video)
        async def on_photo(message: Message, is_post: bool):
            if message.chat.type != ChatType.PRIVATE:
                return

            media_group_id = message.media_group_id

            async def await_media_group():
                try:
                    await asyncio.sleep(2)
                    async with self.media_groups_lock:
                        items = self.media_groups.pop(media_group_id, []) # type: ignore
                        self.media_groups_tasks.pop(media_group_id, None) # type: ignore

                        messages = []
                        final_is_post = False
                        for item in items:
                            messages.append(item[0])
                            final_is_post = final_is_post or item[1]

                    await process_messages(messages, final_is_post)
                except CancelledError:
                    pass

            if media_group_id:
                async with self.media_groups_lock:
                    self.media_groups.setdefault(media_group_id, []).append((message, is_post))

                    task = self.media_groups_tasks.get(media_group_id)
                    if task:
                        task.cancel()

                    self.media_groups_tasks[media_group_id] = asyncio.create_task(
                        await_media_group()
                    )
                return

            await process_messages([message], is_post)
