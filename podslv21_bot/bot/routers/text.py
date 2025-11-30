from typing import Optional

from aiogram import Bot, F, Router
from aiogram.enums import ChatType
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.types import Message

from simpleforward.bot.message_manager import MessageManager
from simpleforward.config import Config
from simpleforward.moderation import AsyncModerator


class TextRouter(Router):
    def __init__(self,
                 config: Config,
                 message_manager: MessageManager,
                 moderator: Optional[AsyncModerator] = None):
        super().__init__()

        self.config = config
        self.message_manager = message_manager
        self.moderator = moderator

        self._register_handlers()

    def _register_handlers(self):
        @self.message(F.text)
        async def on_text(message: Message, bot: Bot):
            reply_to_message = message.reply_to_message

            if message.chat.id == self.config.forwarding.target_chat_id\
                and reply_to_message and reply_to_message.from_user.is_bot:
                    result = self.message_manager.get(reply_to_message.message_id)

                    if result:
                        reply_to_message_id, chat_id = result
                        try:
                            await bot.send_message(chat_id, message.text, reply_to_message_id=reply_to_message_id)
                            await message.answer("✅ Ответ успешно отправлен!")
                        except (TelegramBadRequest, TelegramForbiddenError) as e:
                            await message.answer(f'❌ Не удалось отправить ответ: "{e}"')
            elif message.chat.type == ChatType.PRIVATE and "text" in self.config.forwarding.types:
                try:
                    reply_to_message_id = message.message_id
                    group_message_id = (await bot.send_message(
                        self.config.forwarding.target_chat_id,
                        self.config.forwarding.message_template.format(text=message.text),
                        parse_mode="HTML"
                    )).message_id

                    self.message_manager.add(reply_to_message_id, group_message_id, message.chat.id)
                    await message.answer("✅ Сообщение успешно отправлено!")
                except (TelegramBadRequest, TelegramForbiddenError) as e:
                    await message.answer(f'❌ Не удалось отправить сообщение: "{e}"')