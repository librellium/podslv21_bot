import asyncio
from asyncio import CancelledError
from typing import Dict, List, Optional

from aiogram import Bot, F, Router
from aiogram.enums import ChatType
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.types import InputMediaPhoto, InputMediaVideo, Message

from podslv21_bot.bot.utils.message_manager import MessageManager
from podslv21_bot.bot.utils.template_renderer import TemplateRenderer
from podslv21_bot.config import Config
from podslv21_bot.moderation import ModerationExecutor


class MediaRouter(Router):
    def __init__(self,
                 config: Config,
                 message_manager: MessageManager,
                 template_renderer: TemplateRenderer,
                 moderation_executor: Optional[ModerationExecutor] = None):
        super().__init__()

        self.config = config
        self.message_manager = message_manager
        self.renderer = template_renderer
        self.executor = moderation_executor

        self.media_groups: Dict[int, List[str]] = {}
        self.media_groups_tasks: Dict[int, asyncio.Task] = {}
        self.media_groups_lock = asyncio.Lock()

        self._register_handlers()

    def _register_handlers(self):
        @self.message(F.photo | F.video)
        async def on_photo(message: Message, bot: Bot):
            if ("photo" not in self.config.forwarding.types\
                and "video" not in self.config.forwarding.types)\
                    or message.chat.type != ChatType.PRIVATE:
                return

            def can_send_media(msgs: List[Message]):
                photos = len([msg for msg in msgs if msg.photo])
                videos = len([msg for msg in msgs if msg.video])

                return (photos and "photo" in self.config.forwarding.types) or (videos and "video" in self.config.forwarding.types)

            def get_media(msg: Message):
                caption = self.config.forwarding.message_template.format(text=msg.caption) if msg.caption else None
                parse_mode = "HTML" if msg.caption else None

                if msg.photo and "photo" in self.config.forwarding.types:
                    return InputMediaPhoto(
                        media=msg.photo[-1].file_id,
                        caption=caption,
                        parse_mode=parse_mode
                    )
                elif msg.video and "video" in self.config.forwarding.types:
                    return InputMediaVideo(
                        media=msg.video.file_id,
                        caption=caption,
                        parse_mode=parse_mode
                    )

            async def process_messages(messages: list[Message]):
                if not messages: return

                reply_to_message_id = messages[0].message_id

                try:
                    if can_send_media(messages):
                        moderation = self.config.moderation.enabled
                        moderation_passed = not moderation

                        group_message_id = None
                        targets = {
                            self.config.forwarding.moderation_chat_id: True
                        }

                        sent_message = await message.answer(
                            await self.renderer.render("messages/moderation/pending.j2", message)
                        )
                        if len(messages) > 1:
                            media = []
                            for msg in messages:
                                if moderation and msg.caption:
                                    async for event in self.executor.process_message(msg.caption):
                                        if event.type == "moderation_decision":
                                            if event.result.status == "PASS":
                                                moderation_passed = True
                                            elif event.result.status == "REJECT":
                                                await message.answer(
                                                    await self.renderer.render("messages/moderation/rejected.j2", message)
                                                )

                                    await sent_message.delete()

                                media.append(get_media(msg))

                            if moderation_passed:
                                targets[self.config.forwarding.publication_chat_id] = False

                            for target, save_message_id in targets.items():
                                messages = await bot.send_media_group(
                                    target,
                                    media
                                )

                                if save_message_id:
                                    group_message_id = messages[0].message_id
                        elif len(messages) == 1:
                            msg = messages[0]
                            caption = msg.caption

                            if moderation and caption:
                                async for event in self.executor.process_message(caption):
                                    if event.type == "moderation_decision":
                                        if event.result.status == "PASS":
                                            moderation_passed = True
                                        elif event.result.status == "REJECT":
                                            await message.answer(
                                                await self.renderer.render("messages/moderation/rejected.j2", message)
                                            )

                                await sent_message.delete()

                            targets[self.config.forwarding.publication_chat_id] = False

                            func = bot.send_photo if msg.photo else bot.send_video
                            file_id = msg.photo[-1].file_id if msg.photo else msg.video.file_id

                            for target, save_message_id in targets.items():
                                msg = await func(
                                    target,
                                    file_id,
                                    caption=self.config.forwarding.message_template.format(text=msg.caption or ""),
                                    parse_mode="HTML"
                                )

                                if save_message_id:
                                    group_message_id = msg.message_id

                        self.message_manager.add(reply_to_message_id, group_message_id, message.chat.id)
                        if moderation_passed:
                            await message.answer(
                                await self.renderer.render("messages/send/success.j2", message)
                            )
                except (TelegramBadRequest, TelegramForbiddenError) as e:
                    await message.answer(
                        await self.renderer.render("messages/send/success.j2", message)
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
                if task: task.cancel()

                self.media_groups_tasks[media_group_id] = asyncio.create_task(await_media_group())
                return

            await process_messages([message])