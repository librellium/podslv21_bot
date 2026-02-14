import gettext
from collections import defaultdict
from functools import lru_cache
from typing import Optional, Literal

from aiogram import Bot
from aiogram.types import Message

from anonflow import __version_str__, paths




class Translator:
    def __init__(self):
        self.bot = None

    @staticmethod
    @lru_cache
    def _get_translator(lang: str):
        translator = gettext.translation(
            "messages",
            paths.TRANSLATIONS_DIR,
            languages=[lang],
            fallback=True
        )
        return translator

    def format(self, s: str, message: Optional[Message], **extra):
        bot = self.bot

        msg_context = {}
        if isinstance(message, Message):
            user = message.from_user
            chat = message.chat

            first_name = getattr(user, "first_name", "")
            last_name = getattr(user, "last_name", "")

            msg_context = {
                "chat_id": getattr(chat, "id", ""),
                "user_id": getattr(user, "id", ""),
                "first_name": first_name,
                "last_name": last_name,
                "full_name": " ".join(filter(None, (first_name, last_name))),
                "username": getattr(user, "username", ""),
                "bot_first_name": getattr(bot, "first_name", ""),
                "bot_last_name": getattr(bot, "last_name", ""),
                "bot_username": getattr(bot, "username", ""),
                "bot_version": __version_str__
            }

        return s.format_map(
            defaultdict(
                str,
                msg_context | extra
            )
        )

    def get(self, lang: Literal["ru"] = "ru"):
        translator = self._get_translator(lang)

        def _(msgid: str, message: Optional[Message] = None, **extra):
            return self.format(
                translator.gettext(msgid),
                message=message,
                **extra
            )

        return _

    async def init(self, bot: Optional[Bot]):
        if bot: self.bot = await bot.get_me()
