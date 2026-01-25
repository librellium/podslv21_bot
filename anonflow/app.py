import logging

from aiogram import Bot, Dispatcher
from aiogram.client.bot import DefaultBotProperties

from anonflow.bot import (
    MessageSender,
    BlockedMiddleware,
    PrePostMiddleware,
    RegisteredMiddleware,
    SubscriptionMiddleware,
    ThrottlingMiddleware,
    build
)
from anonflow.config import Config
from anonflow.database import (
    Database,
    UserRepository
)
from anonflow.moderation import (
    ModerationExecutor,
    ModerationPlanner,
    RuleManager
)
from anonflow.translator import Translator

from . import paths


class NotInitializedError(Exception): ...


class Application:
    def __init__(self):
        self.bot = None
        self.dispatcher = None
        self.config = None
        self.database = None
        self.user_repository = None
        self.translator = None
        self.executor = None
        self.event_handler = None

    _essential_components = frozenset({
        "bot",
        "dispatcher",
        "config",
        "database",
        "user_repository",
        "translator",
        "event_handler",
    })
    def __getattribute__(self, name: str, /):
        if name in object.__getattribute__(self, "_essential_components"):
            obj = object.__getattribute__(self, name)
            if obj is None:
                raise NotInitializedError(name)
            return obj

        return object.__getattribute__(self, name)

    def _init_config(self):
        config_filepath = paths.CONFIG_FILEPATH

        if not config_filepath.exists():
            Config().save(config_filepath)

        self.config = Config.load(config_filepath)

    async def _init_database(self):
        config = self.config

        self.database = Database(config.get_database_url()) # type: ignore
        await self.database.init()

        self.user_repository = UserRepository(
            self.database,
            config.database.repositories.user.cache_size, # type: ignore
            config.database.repositories.user.cache_ttl # type: ignore
        )

    def _init_logging(self):
        config = self.config

        logging.basicConfig(
            format=config.logging.fmt, # type: ignore
            datefmt=config.logging.date_fmt, # type: ignore
            level=config.logging.level, # type: ignore
        )

    def _init_bot(self):
        config = self.config

        bot_token = config.bot.token # type: ignore
        if not bot_token:
            raise ValueError("bot.token is required and cannot be empty")

        self.bot = Bot(
            token=bot_token.get_secret_value(),
            default=DefaultBotProperties(parse_mode="HTML")
        )
        self.dispatcher = Dispatcher()

    async def _init_translator(self):
        self.translator = Translator()
        await self.translator.init(self.bot)

    def _postinit_bot(self):
        dispatcher, config, translator, user_repository = (
            self.dispatcher,
            self.config,
            self.translator,
            self.user_repository
        )

        dispatcher.update.middleware( # type: ignore
            BlockedMiddleware(
                user_repository=user_repository, # type: ignore
                translator=translator, # type: ignore
            )
        )

        if config.behavior.subscription_requirement.enabled: # type: ignore
            dispatcher.update.middleware( # type: ignore
                SubscriptionMiddleware(
                    channel_ids=config.forwarding.publication_channel_ids, # type: ignore
                    translator=translator # type: ignore
                )
            )

        dispatcher.update.middleware( # type: ignore
            RegisteredMiddleware(
                user_repository=user_repository, # type: ignore
                translator=translator, # type: ignore
            )
        )

        if config.behavior.throttling.enabled: # type: ignore
            dispatcher.update.middleware( # type: ignore
                ThrottlingMiddleware(
                    delay=config.behavior.throttling.delay, # type: ignore
                    translator=translator, # type: ignore
                    allowed_chat_ids=config.forwarding.moderation_chat_ids # type: ignore
                )
            )

        dispatcher.update.middleware( # type: ignore
            PrePostMiddleware()
        )

    def _init_message_sender(self):
        bot, config, translator = (
            self.bot,
            self.config,
            self.translator
        )

        self.message_sender = MessageSender(bot=bot, config=config, translator=translator) # type: ignore

    def _init_moderation(self):
        bot, config = (
            self.bot,
            self.config
        )

        if config.moderation.enabled: # type: ignore
            self.rule_manager = RuleManager(rules_dir=paths.RULES_DIR)
            self.rule_manager.reload()

            self.planner = ModerationPlanner(config=config, rule_manager=self.rule_manager) # type: ignore
            self.executor = ModerationExecutor(
                config=config, # type: ignore
                bot=bot, # type: ignore
                planner=self.planner
            )

    async def init(self):
        self._init_config()
        await self._init_database()
        self._init_logging()
        self._init_bot()
        await self._init_translator()
        self._postinit_bot()
        self._init_message_sender()
        self._init_moderation()

    async def run(self):
        await self.init()

        bot, dispatcher, config, database, user_repository, translator, message_sender = (
            self.bot,
            self.dispatcher,
            self.config,
            self.database,
            self.user_repository,
            self.translator,
            self.message_sender
        )

        dispatcher.include_router( # type: ignore
            build(
                config=config, # type: ignore
                database=database, # type: ignore
                user_repository=user_repository, # type: ignore
                translator=translator, # type: ignore
                message_sender=message_sender, # type: ignore
                executor=self.executor,
            )
        )

        try:
            await dispatcher.start_polling(bot) # type: ignore
        finally:
            await bot.session.close() # type: ignore
            await database.close() # type: ignore
