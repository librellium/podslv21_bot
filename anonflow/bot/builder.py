from typing import Optional

from aiogram import Router

from anonflow.config import Config
from anonflow.moderation import ModerationExecutor

from .routers import InfoRouter, MediaRouter, StartRouter, TextRouter
from .utils import EventHandler, MessageManager, TemplateRenderer


def build(
    config: Config,
    message_manager: MessageManager,
    template_renderer: TemplateRenderer,
    executor: Optional[ModerationExecutor] = None,
    event_handler: Optional[EventHandler] = None
):
    main_router = Router()

    main_router.include_routers(
        StartRouter(template_renderer=template_renderer),
        InfoRouter(template_renderer=template_renderer),
        MediaRouter(
            config=config,
            message_manager=message_manager,
            template_renderer=template_renderer,
            moderation_executor=executor,
        ),
        TextRouter(
            config=config,
            message_manager=message_manager,
            template_renderer=template_renderer,
            moderation_executor=executor,
            event_handler=event_handler
        ),
    )

    return main_router
