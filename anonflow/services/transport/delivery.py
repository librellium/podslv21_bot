from typing import Optional, List, Union

from aiogram import Bot
from aiogram.client.bot import Default
from aiogram.types import (
    ChatIdUnion,
    InputMediaPhoto,
    InputMediaVideo,
    MediaUnion,
    ReplyMarkupUnion
)


class DeliveryService:
    def __init__(self, bot: Bot):
        self._bot = bot

    async def send_media(
        self,
        chat_id: ChatIdUnion,
        media: MediaUnion,
        parse_mode: Optional[Union[str, Default]] = Default("parse_mode"),
        reply_markup: Optional[ReplyMarkupUnion] = None
    ):
        if isinstance(media, InputMediaPhoto):
            await self._bot.send_photo(
                chat_id,
                media.media,
                caption=media.caption,
                parse_mode=parse_mode,
                reply_markup=reply_markup
            )
        elif isinstance(media, InputMediaVideo):
            await self._bot.send_video(
                chat_id,
                media.media,
                caption=media.caption,
                parse_mode=parse_mode,
                reply_markup=reply_markup
            )

    async def send_media_group(
        self,
        chat_id: ChatIdUnion,
        media: List[MediaUnion],
    ):
        await self._bot.send_media_group(
            chat_id=chat_id,
            media=media
        )

    async def send_text(
        self,
        chat_id: ChatIdUnion,
        text: str,
        parse_mode: Optional[Union[str, Default]] = Default("parse_mode"),
        reply_markup: Optional[ReplyMarkupUnion] = None
    ):
        await self._bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode=parse_mode,
            reply_markup=reply_markup
        )
