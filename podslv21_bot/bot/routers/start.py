from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from podslv21_bot.bot.utils.template_renderer import TemplateRenderer


class StartRouter(Router):
    def __init__(self, template_renderer: TemplateRenderer):
        super().__init__()

        self.renderer = template_renderer

        self._register_handlers()

    def _register_handlers(self):
        @self.message(CommandStart())
        async def on_start(message: Message):
            await message.answer(
                await self.renderer.render("commands/start.j2", message)
            )