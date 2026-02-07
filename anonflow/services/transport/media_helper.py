from aiogram.types import InputMediaPhoto, InputMediaVideo

from .content import ContentMediaItem, MediaType

def wrap_media(item: ContentMediaItem):
    if item.type == MediaType.PHOTO:
        return InputMediaPhoto(media=item.file_id, caption=item.caption)
    elif item.type == MediaType.VIDEO:
        return InputMediaVideo(media=item.file_id, caption=item.caption)
    else:
        raise ValueError("Media item type is invalid.")
