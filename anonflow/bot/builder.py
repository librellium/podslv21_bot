from typing import Optional

from aiogram import Router

from anonflow.config import Config
from anonflow.moderation import ModerationExecutor
from anonflow.translator import Translator

from .events import EventHandler
from .routers import InfoRouter, MediaRouter, StartRouter, TextRouter


def build(
    config: Config,
    translator: Translator,
    event_handler: EventHandler,
    executor: Optional[ModerationExecutor] = None,
):
    main_router = Router()

    main_router.include_routers(
        StartRouter(translator=translator),
        InfoRouter(translator=translator),
        TextRouter(
            config=config,
            translator=translator,
            event_handler=event_handler,
            moderation_executor=executor,
        ),
        MediaRouter(
            config=config,
            translator=translator,
            event_handler=event_handler,
            moderation_executor=executor,
        ),
    )

    return main_router
