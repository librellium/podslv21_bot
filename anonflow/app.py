import logging

from aiogram import Bot, Dispatcher
from aiogram.client.bot import DefaultBotProperties

from anonflow.bot import (
    EventHandler,
    MessageManager,
    GlobalSlowmodeMiddleware,
    SubscriptionMiddleware,
    UserSlowmodeMiddleware,
    build
)
from anonflow.config import Config
from anonflow.moderation import (
    ModerationExecutor,
    ModerationPlanner,
    RuleManager
)
from anonflow.translator import Translator

from . import paths


class NotInitializedError(Exception): ...
class BotNotInitializedError(NotInitializedError): ...
class ConfigNotInitializedError(NotInitializedError): ...
class TranslatorNotInitializedError(NotInitializedError): ...
class ModerationNotInitializedError(NotInitializedError): ...


class Application:
    def __init__(self):
        self.bot = None
        self.dispatcher = None
        self.message_manager = None
        self.config = None
        self.translator = None
        self.executor = None
        self.event_handler = None

    def get_bot(self):
        if self.bot is None:
            raise BotNotInitializedError()

        return self.bot

    def get_dispatcher(self):
        if self.dispatcher is None:
            raise BotNotInitializedError()

        return self.dispatcher

    def get_message_manager(self):
        if self.message_manager is None:
            raise BotNotInitializedError()

        return self.message_manager

    def get_config(self):
        if self.config is None:
            raise ConfigNotInitializedError()

        return self.config

    def get_translator(self):
        if self.translator is None:
            raise TranslatorNotInitializedError()

        return self.translator

    def _init_config(self):
        config_filepath = paths.CONFIG_FILEPATH

        if not config_filepath.exists():
            Config().save(config_filepath)

        self.config = Config.load(config_filepath)

    def _init_logging(self):
        config = self.get_config()

        logging.basicConfig(
            format=config.logging.fmt,
            datefmt=config.logging.date_fmt,
            level=config.logging.level,
        )

    def _init_bot(self):
        config = self.get_config()

        if not config.bot.token:
            raise ValueError()

        self.bot = Bot(
            token=config.bot.token.get_secret_value(),
            default=DefaultBotProperties(parse_mode="HTML")
        )
        self.dispatcher = Dispatcher()

        self.message_manager = MessageManager()

    def _postinit_bot(self):
        dispatcher, config, translator = (
            self.get_dispatcher(),
            self.get_config(),
            self.get_translator()
        )

        if config.behavior.subscription_requirement.enabled:
            dispatcher.update.middleware(
                SubscriptionMiddleware(
                    channel_ids=config.forwarding.publication_channel_ids,
                    translator=translator
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
                    translator=translator,
                    allowed_chat_ids=config.forwarding.moderation_chat_ids
                )
            )

    async def _init_translator(self):
        self.translator = Translator()
        await self.translator.init(self.bot)

    def _init_moderation(self):
        bot = self.get_bot()
        config = self.get_config()
        translator = self.get_translator()

        if config.moderation.enabled:
            self.rule_manager = RuleManager(rules_dir=paths.RULES_DIR)
            self.rule_manager.reload()

            self.planner = ModerationPlanner(config=config, rule_manager=self.rule_manager)
            self.executor = ModerationExecutor(
                config=config,
                bot=bot,
                planner=self.planner
            )
            self.event_handler = EventHandler(bot=bot, config=config, translator=translator)

    async def init(self):
        self._init_config()
        self._init_logging()
        self._init_bot()
        await self._init_translator()
        self._init_moderation()

    async def run(self):
        await self.init()

        bot, dispatcher, config, translator, message_manager = (
            self.get_bot(),
            self.get_dispatcher(),
            self.get_config(),
            self.get_translator(),
            self.get_message_manager()
        )

        dispatcher.include_router(
            build(
                config=config,
                message_manager=message_manager,
                translator=translator,
                executor=self.executor,
                event_handler=self.event_handler
            )
        )

        await dispatcher.start_polling(bot)
