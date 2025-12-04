import asyncio

from aiogram import BaseMiddleware
from aiogram.types import Message

from anonflow.bot.utils.template_renderer import TemplateRenderer


class GlobalSlowmodeMiddleware(BaseMiddleware):
    def __init__(self,
                 delay: float,
                 template_renderer: TemplateRenderer):
        super().__init__()

        self.delay = delay
        self.renderer = template_renderer

        self.lock = asyncio.Lock()

    def _extract_message(self, event):
        if isinstance(event, Message):
            return event
        
        msg = getattr(event, "message", None)
        if isinstance(msg, Message):
            return msg

        return None

    async def __call__(self, handler, event, data):
        message = self._extract_message(event)

        if message:
            text = message.text or message.caption
            if text and text.startswith("/"):
                return await handler(event, data)

            if self.lock.locked():
                await message.answer(
                    await self.renderer.render("messages/users/send/busy.j2", message=message)
                )
                return

            async with self.lock:
                result = await handler(event, data)

                await asyncio.sleep(self.delay)

                return result