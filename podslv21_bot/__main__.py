import asyncio
import logging

from aiogram import Bot, Dispatcher

from simpleforward.bot import MessageManager, build
from simpleforward.config import Config
from simpleforward.moderation import AsyncModerator, RuleManager

from . import paths


async def main():
    if not paths.CONFIG_FILE.exists():
        Config().save(paths.CONFIG_FILE)

    config = Config.load(paths.CONFIG_FILE)

    logging.basicConfig(format=config.logging.fmt,
                        datefmt=config.logging.date_fmt,
                        level=config.logging.level)

    bot = Bot(token=config.bot.token.get_secret_value())
    dispatcher = Dispatcher()

    message_manager = MessageManager()

    moderator = None
    if config.moderation.enabled:
        rule_manager = RuleManager(paths.RULES_DIR)
        moderator = AsyncModerator(config, rule_manager)

    dispatcher.include_router(
        build(config, message_manager, moderator)
    )

    await dispatcher.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())