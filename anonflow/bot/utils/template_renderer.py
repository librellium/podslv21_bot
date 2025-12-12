import logging
from pathlib import Path
from typing import Optional

from aiogram.types import Message
from jinja2 import Environment, FileSystemLoader, TemplateNotFound

from anonflow import __version_str__
from anonflow.config import Config


class TemplateRenderer:
    def __init__(self, config: Config, templates_dir: Path):
        self._logger = logging.getLogger(__name__)

        self.config = config

        self._env = Environment(
            loader=FileSystemLoader(templates_dir), enable_async=True
        )

    async def _get_context(self, message: Message):
        bot = await message.bot.get_me()
        user = message.from_user

        return {
            "first_name": user.first_name,
            "last_name": user.last_name,
            "username": user.username,
            "bot_first_name": bot.first_name,
            "bot_last_name": bot.last_name,
            "bot_username": bot.username,
            "bot_version": __version_str__,
            "config": self.config,
        }

    async def render(self, template_name: str, *, message: Optional[Message] = None, **extra_context):
        try:
            template = self._env.get_template(template_name)
            context = await self._get_context(message) if message else {}

            return await template.render_async(
                **{**context, **extra_context, "message": message}
            )
        except TemplateNotFound:
            self._logger.warning(f"Template {template_name} not found.")
            return f"Шаблон не найден для {template_name}"
