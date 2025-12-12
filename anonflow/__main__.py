import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.bot import DefaultBotProperties

from anonflow import __version_str__
from anonflow.bot import (
    EventHandler,
    MessageManager,
    GlobalSlowmodeMiddleware,
    SubscriptionMiddleware,
    UserSlowmodeMiddleware,
    TemplateRenderer,
    build
)
from anonflow.config import Config
from anonflow.moderation import (
    ModerationExecutor,
    ModerationPlanner,
    RuleManager
)

from . import paths


async def main():
    with open(".env", "w") as env_file:
        env_file.write(f"APP_VERSION={__version_str__}\n")

    if not paths.CONFIG_FILE.exists():
        Config().save(paths.CONFIG_FILE)

    config = Config.load(paths.CONFIG_FILE)

    logging.basicConfig(
        format=config.logging.fmt,
        datefmt=config.logging.date_fmt,
        level=config.logging.level,
    )

    bot = Bot(
        token=config.bot.token.get_secret_value(),
        default=DefaultBotProperties(parse_mode="HTML")
    )
    dispatcher = Dispatcher()

    message_manager = MessageManager()
    renderer = TemplateRenderer(config=config, templates_dir=paths.TEMPLATES_DIR)

    executor, event_handler = None, None
    if config.moderation.enabled:
        rule_manager = RuleManager(rules_dir=paths.RULES_DIR)
        rule_manager.reload()

        planner = ModerationPlanner(config=config, rule_manager=rule_manager)
        executor = ModerationExecutor(
            config=config,
            bot=bot,
            template_renderer=renderer,
            planner=planner
        )
        event_handler = EventHandler(bot=bot, config=config, template_renderer=renderer)

    if config.behavior.subscription_requirement.enabled:
        dispatcher.update.middleware(
            SubscriptionMiddleware(
                channel_ids=config.forwarding.publication_channel_ids,
                template_renderer=renderer
            )
        )

    if config.behavior.slowmode.enabled:
        slowmode_map = {
            "global": GlobalSlowmodeMiddleware,
            "user": UserSlowmodeMiddleware
        }
        dispatcher.update.middleware(
            slowmode_map[config.behavior.slowmode.mode](
                delay=config.behavior.slowmode.delay,
                template_renderer=renderer,
                allowed_chat_ids=config.forwarding.moderation_chat_ids
            )
        )

    dispatcher.include_router(
        build(
            config=config,
            message_manager=message_manager,
            template_renderer=renderer,
            executor=executor,
            event_handler=event_handler
        )
    )

    await dispatcher.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
