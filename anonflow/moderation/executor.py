import asyncio
import base64
import logging
import textwrap
from io import BytesIO
from typing import AsyncGenerator, Literal

from aiogram import Bot
from aiogram.types import Message

from anonflow.services.transport.events import (
    Events,
    ModerationDecisionEvent,
    ModerationStartedEvent
)
from anonflow.config import Config

from .planner import ModerationPlanner


class ModerationExecutor:
    def __init__(
        self,
        bot: Bot,
        config: Config,
        planner: ModerationPlanner,
    ):
        self._logger = logging.getLogger(__name__)

        self.bot = bot
        self.config = config

        self.planner = planner
        self.planner.set_functions(self.moderation_decision)

    def moderation_decision(self, status: Literal["approve", "reject"], reason: str):
        moderation_map = {"approve": True, "reject": False}
        return ModerationDecisionEvent(approved=moderation_map.get(status.lower(), False), reason=reason)
    moderation_decision.description = textwrap.dedent( # type: ignore
        """
        Processes a message with a moderation decision by status and explanation.
        This function must be called whenever there is no exact user request or no other available function
        matching the user's intent. Status must be either "APPROVE" if the message is allowed, or "REJECT" if it should be blocked.
        """
    ).strip()

    async def _get_b64image(self, message: Message):
        if message.photo:
            photo = message.photo[-1]
            file = await self.bot.get_file(photo.file_id)
            if file:
                buffer = BytesIO()
                await self.bot.download(file, buffer)
                buffer.seek(0)
                return (base64.b64encode(buffer.read())).decode()

    async def process_message(self, message: Message) -> AsyncGenerator[Events, None]:
        yield ModerationStartedEvent()

        image = await self._get_b64image(message)
        functions = await self.planner.plan(
            (message.text or message.caption),
            f"data:image/jpeg;base64,{image}" if image else None
        )
        function_names = self.planner.get_function_names()

        for func in functions:
            func_name = func.get("name", "")
            func_args = func.get("args", {})

            method = getattr(self, func_name, None)

            if method is None or func_name not in function_names:
                self._logger.warning("Function %s not found, skipping.", func_name)
                continue

            self._logger.info("Executing %s.", func_name)
            try:
                if asyncio.iscoroutinefunction(method):
                    yield await method(**func_args)
                else:
                    yield await asyncio.to_thread(method, **func_args)
            except Exception:
                self._logger.exception("Failed to execute %s.", func_name)
