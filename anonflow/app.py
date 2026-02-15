import logging
from typing import Optional, TypeVar

from aiogram import Bot, Dispatcher
from aiogram.client.bot import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from anonflow import __version_str__
from anonflow.bot.middleware import build as build_middleware
from anonflow.bot.routers import build as build_routers
from anonflow.config import Config
from anonflow.database import (
    BanRepository,
    Database,
    ModeratorRepository,
    UserRepository
)
from anonflow.moderation import (
    ModerationExecutor,
    ModerationPlanner,
    RuleManager
)
from anonflow.services import (
    DeliveryService,
    MessageRouter,
    ModeratorService,
    UserService
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
        self.moderator_service: Optional[ModeratorService] = None
        self.user_service: Optional[UserService] = None
        self.translator: Optional[Translator] = None
        self.moderation_executor: Optional[ModerationExecutor] = None
        self.message_router: Optional[MessageRouter] = None

    def _init_config(self):
        config_filepath = paths.CONFIG_FILEPATH

        if not config_filepath.exists():
            Config().save(config_filepath)
            raise RuntimeError("Config file was just created. Please fill it out and restart the application.")

        self.config = Config.load(config_filepath)

    def _init_logging(self):
        config = req("config", self.config)

        logging.basicConfig(
            format=config.logging.fmt,
            datefmt=config.logging.date_fmt,
            level=config.logging.level,
        )

    async def _init_database(self):
        config = req("config", self.config)

        self.database = Database(config.get_database_url())
        await self.database.init()

        self.user_service = UserService(
            self.database,
            UserRepository()
        )
        self.moderator_service = ModeratorService(
            self.database,
            BanRepository(),
            ModeratorRepository()
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
        self.translator = Translator(translations_dir=paths.TRANSLATIONS_DIR)
        await self.translator.init(self.bot)

    def _init_transport(self):
        bot = req("bot", self.bot)
        config = req("config", self.config)
        user_service = req("user_service", self.user_service)
        moderator_service = req("moderator_service", self.moderator_service)
        translator = req("translator", self.translator)

        self.message_router = MessageRouter(
            moderation_chat_ids=config.forwarding.moderation_chat_ids,
            publication_channel_ids=config.forwarding.publication_channel_ids,
            delivery_service=DeliveryService(bot),
            user_service=user_service,
            moderator_service=moderator_service,
            translator=translator
        )

    def _init_middleware(self):
        dispatcher = req("dispatcher", self.dispatcher)
        config = req("config", self.config)
        message_router = req("message_router", self.message_router)
        user_service = req("user_service", self.user_service)
        moderator_service = req("moderator_service", self.moderator_service)

        middlewares = build_middleware(
            message_router=message_router,
            user_service=user_service,
            moderator_service=moderator_service,
            subscription_requirement=config.behavior.subscription_requirement.enabled,
            subscription_channel_ids=config.behavior.subscription_requirement.channel_ids,
            throttling=config.behavior.throttling.enabled,
            throttling_delay=config.behavior.throttling.delay,
            throttling_allowed_chat_ids=config.forwarding.moderation_chat_ids
        )

        for middleware in middlewares:
            dispatcher.update.middleware(middleware)

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
        self._init_logging()
        await self._init_database()
        self._init_bot()
        await self._init_translator()
        self._init_transport()
        self._init_middleware()
        self._init_moderation()

    async def run(self):
        await self.init()

        self._logger.info(f"Anonflow v{__version_str__} has been successfully initialized.")

        bot = req("bot", self.bot)
        dispatcher = req("dispatcher", self.dispatcher)
        config = req("config", self.config)
        database = req("database", self.database)
        message_router = req("message_router", self.message_router)

        dispatcher.include_router(
            build_routers(
                config=config,
                message_router=message_router,
                moderation_executor=self.moderation_executor,
            )
        )

        try:
            await dispatcher.start_polling(bot)
        finally:
            self._logger.info("Shutting down Anonflow...")
            await bot.session.close()
            await database.close()
