from aiogram.types import Message


def extract_message(event):
    if isinstance(event, Message):
        return event

    msg = getattr(event, "message", None)
    if isinstance(msg, Message):
        return msg

    return None
