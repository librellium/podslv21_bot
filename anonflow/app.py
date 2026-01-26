import logging
from typing import TypeVar, Optional

from aiogram import Bot, Dispatcher
from aiogram.client.bot import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from anonflow import __version_str__
from anonflow.bot import (
    MessageSender,
    BlockedMiddleware,
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

T = TypeVar("T")
def req(name: str, value: T | None) -> T:
    if value is None:
        raise NotInitializedError(name)
    return value

class Application:
    def __init__(self):
        self._logger = logging.getLogger(__name__)

        self.bot: Optional[Bot] = None
        self.dispatcher: Optional[Dispatcher] = None
        self.config: Optional[Config] = None
        self.database: Optional[Database] = None
        self.user_repository: Optional[UserRepository] = None
        self.translator: Optional[Translator] = None
        self.moderation_executor: Optional[ModerationExecutor] = None
        self.message_sender: Optional[MessageSender] = None

    def _init_config(self):
        config_filepath = paths.CONFIG_FILEPATH

        if not config_filepath.exists():
            Config().save(config_filepath)
            raise RuntimeError("Config file was just created. Please fill it out and restart the application.")

        self.config = Config.load(config_filepath)

    async def _init_database(self):
        config = req("config", self.config)

        self.database = Database(config.get_database_url())
        await self.database.init()

        self.user_repository = UserRepository(
            self.database,
            config.database.repositories.user.cache_size,
            config.database.repositories.user.cache_ttl
        )

    def _init_logging(self):
        config = req("config", self.config)

        logging.basicConfig(
            format=config.logging.fmt,
            datefmt=config.logging.date_fmt,
            level=config.logging.level,
        )

    def _init_bot(self):
        config = req("config", self.config)

        bot_token = config.bot.token
        if not bot_token:
            raise ValueError("bot.token is required and cannot be empty")

        self.bot = Bot(
            token=bot_token.get_secret_value(),
            default=DefaultBotProperties(parse_mode="HTML")
        )
        self.dispatcher = Dispatcher(storage=MemoryStorage())

    async def _init_translator(self):
        self.translator = Translator()
        await self.translator.init(self.bot)

    def _postinit_bot(self):
        dispatcher = req("dispatcher", self.dispatcher)
        config = req("config", self.config)
        translator = req("translator", self.translator)
        user_repository = req("user_repository", self.user_repository)

        dispatcher.update.middleware(
            BlockedMiddleware(
                user_repository=user_repository,
                translator=translator,
            )
        )

        if config.behavior.subscription_requirement.enabled:
            dispatcher.update.middleware(
                SubscriptionMiddleware(
                    channel_ids=config.forwarding.publication_channel_ids,
                    translator=translator
                )
            )

        dispatcher.update.middleware(
            RegisteredMiddleware(
                user_repository=user_repository,
                translator=translator,
            )
        )

        if config.behavior.throttling.enabled:
            dispatcher.update.middleware(
                ThrottlingMiddleware(
                    delay=config.behavior.throttling.delay,
                    translator=translator,
                    allowed_chat_ids=config.forwarding.moderation_chat_ids
                )
            )

    def _init_message_sender(self):
        bot = req("bot", self.bot)
        config = req("config", self.config)
        translator = req("translator", self.translator)

        self.message_sender = MessageSender(
            bot=bot,
            config=config,
            translator=translator
        )

    def _init_moderation(self):
        bot = req("bot", self.bot)
        config = req("config", self.config)

        if config.moderation.enabled:
            self.rule_manager = RuleManager(rules_dir=paths.RULES_DIR)
            self.rule_manager.reload()

            self.planner = ModerationPlanner(config=config, rule_manager=self.rule_manager)
            self.moderation_executor = ModerationExecutor(
                config=config,
                bot=bot,
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

        self._logger.info(f"Anonflow v{__version_str__} has been successfully initialized.")

        bot = req("bot", self.bot)
        dispatcher = req("dispatcher", self.dispatcher)
        config = req("config", self.config)
        database = req("database", self.database)
        user_repository = req("user_repository", self.user_repository)
        translator = req("translator", self.translator)
        message_sender = req("message_sender", self.message_sender)

        dispatcher.include_router(
            build(
                config=config,
                database=database,
                user_repository=user_repository,
                translator=translator,
                message_sender=message_sender,
                moderation_executor=self.moderation_executor,
            )
        )

        try:
            await dispatcher.start_polling(bot)
        finally:
            self._logger.info("Shutting down Anonflow...")
            await bot.session.close()
            await database.close()
