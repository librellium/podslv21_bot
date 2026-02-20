import asyncio
from asyncio import CancelledError
from contextlib import suppress
from typing import Dict, FrozenSet, List

from aiogram import F, Router
from aiogram.enums import ChatType
from aiogram.types import Message

from anonflow.config.models import ForwardingType
from anonflow.moderation import ModerationExecutor
from anonflow.services.transport import MessageRouter
from anonflow.services.transport.content import (
    ContentMediaGroup,
    ContentMediaItem,
    MediaType
)
from anonflow.services.transport.results import (
    ModerationDecisionResult,
    PostPreparedResult
)


class MediaRouter(Router):
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

        self.media_groups: Dict[str, List[Message]] = {}
        self.media_groups_tasks: Dict[str, asyncio.Task] = {}
        self.media_groups_lock = asyncio.Lock()

    def _can_send_media(self, msgs: List[Message]):
        return any(
            (msg.photo and "photo" in self.forwarding_types) or
            (msg.video and "video" in self.forwarding_types)
            for msg in msgs
        )

    def _get_media(self, message: Message):
        if message.photo and "photo" in self.forwarding_types:
            return {"type": MediaType.PHOTO, "file_id": message.photo[-1].file_id}
        elif message.video and "video" in self.forwarding_types:
            return {"type": MediaType.VIDEO, "file_id": message.video.file_id}

    def setup(self):
        async def process_messages(messages: List[Message]):
            if not messages:
                return

            if self._can_send_media(messages):
                moderation_approved = False

                content_group = ContentMediaGroup()
                caption = next((msg.caption for msg in messages if msg.caption), "")
                for message in messages:
                    async for result in self.moderation_executor.process_message(message):
                        if isinstance(result, ModerationDecisionResult):
                            moderation_approved = result.is_approved
                        await self.message_router.dispatch(result, message)

                    media = self._get_media(message)
                    if media:
                        content_group.items.append(ContentMediaItem(**media, caption=caption))

                await self.message_router.dispatch(
                    PostPreparedResult(content_group, moderation_approved),
                    messages[0]
                )

        @self.message(F.photo | F.video)
        async def on_photo(message: Message):
            if message.chat.type != ChatType.PRIVATE:
                return

            media_group_id = message.media_group_id

            async def await_media_group():
                with suppress(CancelledError):
                    await asyncio.sleep(2)
                    async with self.media_groups_lock:
                        messages = self.media_groups.pop(media_group_id, []) # type: ignore
                        self.media_groups_tasks.pop(media_group_id, None) # type: ignore

                    await process_messages(messages)

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
