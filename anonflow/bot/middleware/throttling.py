import asyncio
import time
from typing import Dict, List, Optional

from aiogram import BaseMiddleware
from aiogram.types import ChatIdUnion, Message

from anonflow.translator import Translator

from .utils import extract_message


class SlowmodeMiddleware(BaseMiddleware):
    def __init__(self, delay: float, translator: Translator, allowed_chat_ids: Optional[List[ChatIdUnion]] = []):
        super().__init__()

        self.delay = delay
        self.translator = translator
        self.allowed_chat_ids = allowed_chat_ids

        self.user_times: Dict[int, float] = {}
        self.user_locks: Dict[int, asyncio.Lock] = {}

        self.lock = asyncio.Lock()

    async def __call__(self, handler, event, data):
        _ = self.translator.get()

        message = extract_message(event)

        if isinstance(message, Message) and message.chat.id not in self.allowed_chat_ids:
            text = message.text or message.caption
            if text and text.startswith("/post"):
                async with self.lock:
                    user_lock = self.user_locks.setdefault(message.chat.id, asyncio.Lock())

                if user_lock.locked():
                    start_time = self.user_times.get(message.chat.id) or 0
                    current_time = time.monotonic()

                    await message.answer(
                        _(
                            "messages.user.send_busy",
                            message=message,
                            remaining=round(self.delay - (current_time - start_time)) if start_time else None
                        )
                    )
                    return

                async with user_lock:
                    self.user_times[message.chat.id] = time.monotonic()
                    result = await handler(event, data)
                    await asyncio.sleep(self.delay)

                async with self.lock:
                    self.user_locks.pop(message.chat.id)

                return result

        return await handler(event, data)
