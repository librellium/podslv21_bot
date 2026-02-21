import logging
from contextlib import contextmanager
from typing import Any, Generator, Optional

from aiogram import Bot, Dispatcher
from aiogram.client.bot import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from anonflow import __version_str__
from anonflow.bot.builders.middleware import build as build_middleware
from anonflow.bot.builders.routers import build as build_routers
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


class NotInitializedError(RuntimeError): ...

@contextmanager
def require(obj, *names) -> Generator[Any, Any, None]:
    values = []
    for name in names:
        value = getattr(obj, name, None)
        if value is None:
            raise NotInitializedError(name)
        values.append(value)

    if len(values) == 1:
        yield values[0]
    else:
        yield tuple(values)

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
        self.moderation_planner: Optional[ModerationPlanner] = None
        self.moderation_executor: Optional[ModerationExecutor] = None
        self.message_router: Optional[MessageRouter] = None

    def _init_config(self):
        config_filepath = paths.CONFIG_FILEPATH

        if not config_filepath.exists():
            Config().save(config_filepath)
            raise RuntimeError("Config file was just created. Please fill it out and restart the application.")

        self.config = Config.load(config_filepath)

    def _init_logging(self):
        with require(self, "config") as config:
            logging.basicConfig(
                format=config.logging.fmt,
                datefmt=config.logging.date_fmt,
                level=config.logging.level,
            )

    async def _init_database(self):
        with require(self, "config") as config:
            self.database = Database(config.get_database_url())
            await self.database.init()

            self.moderator_service = ModeratorService(
                self.database,
                BanRepository(),
                ModeratorRepository()
            )
            self.user_service = UserService(
                self.database,
                UserRepository()
            )

    def _init_bot(self):
        with require(self, "config") as config:
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
        with require(
            self, "bot", "config", "user_service", "moderator_service", "translator"
        ) as (bot, config, user_service, moderator_service, translator):
            self.message_router = MessageRouter(
                moderation_chat_ids=config.forwarding.moderation_chat_ids,
                publication_channel_ids=config.forwarding.publication_channel_ids,
                delivery_service=DeliveryService(bot),
                user_service=user_service,
                moderator_service=moderator_service,
                translator=translator
            )

    def _init_middleware(self):
        with require(
            self, "dispatcher", "config", "message_router", "user_service", "moderator_service"
        ) as (dispatcher, config, message_router, user_service, moderator_service):
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
        with require(self, "config") as config:
            self.rule_manager = RuleManager(rules_dir=paths.RULES_DIR)
            self.rule_manager.reload()

            api_key = config.openai.api_key
            if not api_key and config.moderation.enabled:
                raise ValueError("openai.api_key is required and cannot be empty")

            base_url = config.openai.base_url
            proxy = config.openai.proxy

            self.moderation_planner = ModerationPlanner(
                api_key=api_key.get_secret_value() if api_key else None,
                gpt_model=config.moderation.model,
                backends=config.moderation.backends,
                rule_manager=self.rule_manager,
                base_url=str(base_url) if base_url else None,
                proxy=str(proxy) if proxy else None,
                timeout=config.openai.timeout,
                max_retries=config.openai.max_retries
            )
            self.moderation_planner.set_enabled(config.moderation.enabled)
            self.moderation_executor = ModerationExecutor(planner=self.moderation_planner)

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
        try:
            await self.init()
        except Exception:
            if self.bot:
                await self.bot.session.close()
            if self.database:
                await self.database.close()
            if self.moderation_planner:
                await self.moderation_planner.close()
            raise

        self._logger.info(f"Anonflow v{__version_str__} has been successfully initialized.")

        with require(
            self, "bot", "dispatcher", "config", "database", "message_router", "moderation_planner", "moderation_executor"
        ) as (bot, dispatcher, config, database, message_router, moderation_planner, moderation_executor):
            dispatcher.include_router(
                build_routers(
                    config=config,
                    message_router=message_router,
                    moderation_executor=moderation_executor,
                )
            )

            try:
                await dispatcher.start_polling(bot)
            finally:
                self._logger.info("Shutting down Anonflow...")
                await bot.session.close()
                await database.close()
                await moderation_planner.close()
