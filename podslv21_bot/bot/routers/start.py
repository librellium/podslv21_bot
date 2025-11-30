from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message


class StartRouter(Router):
    def __init__(self):
        super().__init__()
        self._register_handlers()

    def _register_handlers(self):
        @self.message(CommandStart())
        async def on_start(message: Message):
            await message.answer(f"👋 Привет {message.from_user.username}!\nТы можешь отправить мне "
                                 "сообщение, и я передам его в Подслушано 21 школы, не раскрывая твою личность.\n\n"
                                 "[Исходный код](https://github.com/librellium/podslv21_bot/) "
                                 "открыт и находится под лицензией "
                                 "[MIT](https://github.com/librellium/podslv21_bot/blob/main/LICENSE)",
                                 parse_mode="Markdown")