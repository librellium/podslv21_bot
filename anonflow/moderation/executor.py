import logging
from typing import AsyncGenerator, Literal

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import Message
from yarl import URL

from anonflow.config import Config

from anonflow.bot.events.models import Events, ExecutorDeletionEvent, ModerationDecisionEvent, ModerationStartedEvent
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
        self.planner.set_functions(self.delete_message, self.moderation_decision)

    async def delete_message(self, message_link: str):
        """
        Deletes a message by message_link.
        Call this function only when the user explicitly requests to delete their own message.
        Do not use it for moderation or automatic cleanup.
        """
        parsed_url = URL(message_link)
        parsed_path = parsed_url.path.strip("/").split("/")

        publication_channel_ids = self.config.forwarding.publication_channel_ids

        if not publication_channel_ids:
            return ExecutorDeletionEvent(success=False)

        if (
            len(parsed_path) == 3
            and parsed_path[0] == "c"
            and parsed_path[1] in publication_channel_ids
        ):
            channel_id = parsed_path[1]
            message_id = parsed_path[2]
            try:
                await self.bot.delete_message(channel_id, message_id=message_id)
                return ExecutorDeletionEvent(success=True, message_id=message_id)
            except TelegramBadRequest:
                return ExecutorDeletionEvent(success=False, message_id=message_id)

        return ExecutorDeletionEvent(success=False)

    async def moderation_decision(
        self, status: Literal["APPROVE", "REJECT"], explanation: str
    ):
        """
        Processes a message with a moderation decision by status and explanation.
        This function must be called whenever there is no exact user request or no other available function
        matching the user's intent. Status must be either "APPROVE" if the message is allowed, or "REJECT" if it should be blocked.
        """

        moderation_map = {"APPROVE": True, "REJECT": False}

        return ModerationDecisionEvent(
            approved=moderation_map.get(status, False), explanation=explanation
        )

    async def process_message(self, message: Message) -> AsyncGenerator[Events, None]:
        yield ModerationStartedEvent()

        functions = await self.planner.plan((message.text or message.caption))
        function_names = self.planner.get_function_names()

        for func in functions:
            func_name = func.get("name")
            if hasattr(self, func_name) and func_name in function_names:
                try:
                    self._logger.info(
                        f"Executing {func_name}({', '.join(map(str, func.get('args', [])))})"
                    )
                    yield await getattr(self, func_name)(*func.get("args", []))
                except Exception:
                    self._logger.exception(
                        f"Failed to execute {func_name}({', '.join(map(str, func.get('args', [])))})"
                    )
            else:
                self._logger.warning("Function %s not found, skipping.", func_name)
