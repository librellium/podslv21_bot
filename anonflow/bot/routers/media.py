import asyncio
from asyncio import CancelledError
from typing import Dict, List, Optional

from aiogram import Bot, F, Router
from aiogram.enums import ChatType
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.types import InputMediaPhoto, InputMediaVideo, Message

from anonflow.bot.utils.event_handler import EventHandler
from anonflow.bot.utils.message_manager import MessageManager
from anonflow.bot.utils.template_renderer import TemplateRenderer
from anonflow.config import Config
from anonflow.moderation import ModerationDecisionEvent, ModerationExecutor


class MediaRouter(Router):
    def __init__(
        self,
        config: Config,
        message_manager: MessageManager,
        template_renderer: TemplateRenderer,
        moderation_executor: Optional[ModerationExecutor] = None,
        event_handler: Optional[EventHandler] = None,
    ):
        super().__init__()

        self.config = config
        self.message_manager = message_manager
        self.renderer = template_renderer
        self.executor = moderation_executor
        self.event_handler = event_handler

        self.media_groups: Dict[str, List[Message]] = {}
        self.media_groups_tasks: Dict[str, asyncio.Task] = {}
        self.media_groups_lock = asyncio.Lock()

        self._register_handlers()

    def _register_handlers(self):
        @self.message(F.photo | F.video)
        async def on_photo(message: Message, bot: Bot):
            if message.chat.type != ChatType.PRIVATE:
                return

            def can_send_media(msgs: List[Message]):
                photos = len([msg for msg in msgs if msg.photo])
                videos = len([msg for msg in msgs if msg.video])

                return (
                    photos and "photo" in self.config.forwarding.types
                ) or (
                    videos and "video" in self.config.forwarding.types
                )

            async def get_media(msg: Message):
                caption = await self.renderer.render(
                    "messages/channel/media.j2", message=msg
                )

                if msg.photo and "photo" in self.config.forwarding.types:
                    return InputMediaPhoto(media=msg.photo[-1].file_id, caption=caption)
                elif msg.video and "video" in self.config.forwarding.types:
                    return InputMediaVideo(media=msg.video.file_id, caption=caption)

            async def process_messages(messages: list[Message]):
                if not messages:
                    return

                moderation_chat_ids = self.config.forwarding.moderation_chat_ids
                publication_channel_ids = self.config.forwarding.publication_channel_ids

                reply_to_message_id = messages[0].message_id

                try:
                    if can_send_media(messages):
                        moderation = self.config.moderation.enabled
                        moderation_passed = not moderation

                        group_message_id = None

                        targets = {}
                        if moderation_chat_ids:
                            for chat_id in moderation_chat_ids:
                                targets[chat_id] = True

                        if len(messages) > 1:
                            media = []
                            for msg in messages:
                                if moderation and msg.caption:
                                    async for event in self.executor.process_message(msg):
                                        if isinstance(event, ModerationDecisionEvent):
                                            moderation_passed = event.approved
                                        await self.event_handler.handle(event, message)

                                media.append(await get_media(msg))

                            if publication_channel_ids and moderation_passed:
                                for channel_id in publication_channel_ids:
                                    targets[channel_id] = False

                            for target, save_message_id in targets.items():
                                messages = await bot.send_media_group(target, media)

                                if save_message_id:
                                    group_message_id = messages[0].message_id
                        elif len(messages) == 1:
                            msg = messages[0]
                            caption = msg.caption

                            if moderation and caption:
                                async for event in self.executor.process_message(msg):
                                    if isinstance(event, ModerationDecisionEvent):
                                        moderation_passed = event.approved
                                    await self.event_handler.handle(event, message)

                            if publication_channel_ids and moderation_passed:
                                for channel_id in publication_channel_ids:
                                    targets[channel_id] = False

                            func = bot.send_photo if msg.photo else bot.send_video
                            file_id = (
                                msg.photo[-1].file_id
                                if msg.photo
                                else msg.video.file_id
                            )

                            for target, save_message_id in targets.items():
                                msg_id = (
                                    await func(
                                        target,
                                        file_id,
                                        caption=await self.renderer.render(
                                            "messages/channel/media.j2", message=msg
                                        ),
                                    )
                                ).message_id

                                if save_message_id:
                                    group_message_id = msg_id

                        self.message_manager.add(
                            reply_to_message_id, group_message_id, message.chat.id
                        )
                except (TelegramBadRequest, TelegramForbiddenError) as e:
                    await message.answer(
                        await self.renderer.render(
                            "messages/users/send/failure.j2",
                            message=message,
                            exception=e,
                        )
                    )

            media_group_id = message.media_group_id

            async def await_media_group():
                try:
                    await asyncio.sleep(2)
                    async with self.media_groups_lock:
                        messages = self.media_groups.pop(media_group_id, [])
                        self.media_groups_tasks.pop(media_group_id, None)
                    await process_messages(messages)
                except CancelledError:
                    pass

            if media_group_id:
                self.media_groups.setdefault(media_group_id, []).append(message)

                task = self.media_groups_tasks.get(media_group_id)
                if task:
                    task.cancel()

                self.media_groups_tasks[media_group_id] = asyncio.create_task(
                    await_media_group()
                )
                return

            await process_messages([message])
