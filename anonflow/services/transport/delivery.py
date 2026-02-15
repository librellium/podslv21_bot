from typing import Optional, Union

from aiogram import Bot
from aiogram.client.bot import Default
from aiogram.types import (
    ChatIdUnion,
    InputMediaPhoto,
    InputMediaVideo,
    ReplyMarkupUnion
)

from .content import ContentMediaGroup, ContentMediaItem, MediaType


class DeliveryService:
    def __init__(self, bot: Bot):
        self._bot = bot

    @staticmethod
    def _wrap_media(item: ContentMediaItem):
        if item.type == MediaType.PHOTO:
            return InputMediaPhoto(media=item.file_id, caption=item.caption)
        elif item.type == MediaType.VIDEO:
            return InputMediaVideo(media=item.file_id, caption=item.caption)
        else:
            raise ValueError("Media item type is invalid.")

    async def send_media(
        self,
        chat_id: ChatIdUnion,
        media_item: ContentMediaItem,
        parse_mode: Optional[Union[str, Default]] = Default("parse_mode"),
        reply_markup: Optional[ReplyMarkupUnion] = None
    ):
        media = self._wrap_media(media_item)
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
        media_group: ContentMediaGroup,
    ):
        await self._bot.send_media_group(
            chat_id=chat_id,
            media=[
                self._wrap_media(item)
                for item in media_group.items
            ]
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
