import asyncio
from typing import Set

from aiogram import BaseMiddleware
from aiogram.enums import ChatType
from aiogram.types import Message

from .utils import extract_message


class PrePostMiddleware(BaseMiddleware):
    def __init__(self, ttl: float = 30):
        super().__init__()

        self.ttl = ttl

        self.media_groups: Set[str] = set()
        self.media_groups_lock = asyncio.Lock()

    async def __call__(self, handler, event, data):
        message = extract_message(event)

        is_post = False

        if isinstance(message, Message) and message.chat.type == ChatType.PRIVATE:
            source_text = message.text or message.caption or ""

            media_group_id = message.media_group_id
            if media_group_id:
                async with self.media_groups_lock:
                    is_post = media_group_id in self.media_groups

            parts = source_text.lstrip().split(maxsplit=1)

            if parts:
                cmd, *rest = parts

                post_text = rest[0] if rest else ""
                if message.text is not None and cmd == "/post" and not post_text:
                    return

                if not is_post and cmd == "/post":
                    is_post = True
                    if media_group_id:
                        async with self.media_groups_lock:
                            self.media_groups.add(media_group_id)
                        asyncio.create_task(self._cleanup_group(media_group_id))

        data["is_post"] = is_post
        return await handler(event, data)

    async def _cleanup_group(self, media_group_id: str):
        await asyncio.sleep(self.ttl)
        async with self.media_groups_lock:
            self.media_groups.discard(media_group_id)
