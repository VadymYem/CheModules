__version__ = (1, 2, 0)
#meta developer: @author_che
import contextlib
import io
import logging
import time
import typing

from telethon.tl.types import (
    DocumentAttributeFilename,
    Message,
    PeerChat,
    UpdateDeleteChannelMessages,
    UpdateDeleteMessages,
    UpdateEditChannelMessage,
    UpdateEditMessage,
)
from telethon.utils import get_display_name

from .. import loader, utils

logger = logging.getLogger(__name__)


@loader.tds
class NekoSpy(loader.Module):
    """
    Зберігає видалені та відредаговані повідомлення, а також самознищувані медіа.
    Виправлено помилку валидації SendPhoto та роботу save_sd.
    """

    # Емодзі для логів
    icon_spy = "🕵️‍♂️"
    icon_groups = "👥"
    icon_pm = "👤"
    icon_trash = "🗑"
    icon_edit = "✏️"
    icon_fire = "🔥"

    strings = {
        "name": "Spy",
        "state": f"{icon_spy} <b>Режим шпигуна тепер {{}}</b>",
        "spybl": f"{icon_spy} <b>Чат додано до чорного списку (ігнорування)</b>",
        "spybl_removed": f"{icon_spy} <b>Чат видалено з чорного списку</b>",
        "spybl_clear": f"{icon_spy} <b>Чорний список очищено</b>",
        "spywl": f"{icon_spy} <b>Чат додано до білого списку (відстежування)</b>",
        "spywl_removed": f"{icon_spy} <b>Чат видалено з білого списку</b>",
        "spywl_clear": f"{icon_spy} <b>Білий список очищено</b>",
        "whitelist": f"\n{icon_spy} <b>Стежу ТІЛЬКИ за повідомленнями від:</b>\n{{}}",
        "always_track": f"\n{icon_spy} <b>ЗАВЖДИ стежу за повідомленнями від:</b>\n{{}}",
        "blacklist": f"\n{icon_spy} <b>ІГНОРУЮ повідомлення від:</b>\n{{}}",
        "chat": f"{icon_groups} <b>Стеження у групах активне</b>\n",
        "pm": f"{icon_pm} <b>Стеження в особистих повідомленнях активне</b>\n",
        "mode_off": f"{icon_pm} <b>Стеження вимкнено. Увімкнути: </b><code>{{}}spymode</code>\n",
        
        "deleted_pm": (
            f'{icon_trash} <b><a href="{{}}">{{}}</a> видалив(ла) <a href="{{message_url}}">повідомлення</a> в ПП.'
            ' Зміст:</b>\n{{}}'
        ),
        "deleted_chat": (
            f'{icon_trash} <b><a href="{{message_url}}">Повідомлення</a> в чаті <a href="{{}}">{{}}</a> від <a'
            ' href="{{}}">{{}}</a> було видалено. Зміст:</b>\n{{}}'
        ),
        "edited_pm": (
            f'{icon_edit} <b><a href="{{}}">{{}}</a> змінив(ла) <a href="{{message_url}}">повідомлення</a>'
            ' в ПП. Старий зміст:</b>\n{{}}'
        ),
        "edited_chat": (
            f'{icon_edit} <b><a href="{{message_url}}">Повідомлення</a> в чаті <a href="{{}}">{{}}</a>'
            ' від <a href="{{}}">{{}}</a> було змінено. Старий зміст:</b>\n{{}}'
        ),
        
        "on": "Увімкнено",
        "off": "Вимкнено",
        "cfg_enable_pm": "Увімкнути режим шпигуна в особистих повідомленнях",
        "cfg_enable_groups": "Увімкнути режим шпигуна в групах",
        "cfg_whitelist": "Білий список (зберігати повідомлення тільки звідси)",
        "cfg_blacklist": "Чорний список (ігнорувати повідомлення звідси)",
        "cfg_always_track": (
            "Список пріоритетного стеження (зберігати завжди, ігноруючи налаштування)"
        ),
        "cfg_log_edits": "Зберігати історію редагування повідомлень",
        "cfg_ignore_inline": "Ігнорувати повідомлення від інлайн-ботів (@bot ...)",
        "cfg_fw_protect": "Затримка між відправкою повідомлень (захист від флуду)",
        
        "sd_media": (
            f"{icon_fire} <b><a href='tg://user?id={{}}'>{{}}</a> надіслав(ла) самознищуване"
            " медіа</b>"
        ),
        "save_sd": (
            f"{icon_fire} <b>Збереження самознищуваних медіа активне</b>\n"
        ),
        "cfg_save_sd": "Зберігати самознищувані фото/відео",
    }

    strings_uk = strings

    def __init__(self):
        self._tl_channel = None
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "enable_pm",
                True,
                lambda: self.strings("cfg_enable_pm"),
                validator=loader.validators.Boolean(),
            ),
            loader.ConfigValue(
                "enable_groups",
                False,
                lambda: self.strings("cfg_enable_groups"),
                validator=loader.validators.Boolean(),
            ),
            loader.ConfigValue(
                "whitelist",
                [],
                lambda: self.strings("cfg_whitelist"),
                validator=loader.validators.Series(),
            ),
            loader.ConfigValue(
                "blacklist",
                [],
                lambda: self.strings("cfg_blacklist"),
                validator=loader.validators.Series(),
            ),
            loader.ConfigValue(
                "always_track",
                [],
                lambda: self.strings("cfg_always_track"),
                validator=loader.validators.Series(),
            ),
            loader.ConfigValue(
                "log_edits",
                True,
                lambda: self.strings("cfg_log_edits"),
                validator=loader.validators.Boolean(),
            ),
            loader.ConfigValue(
                "ignore_inline",
                True,
                lambda: self.strings("cfg_ignore_inline"),
                validator=loader.validators.Boolean(),
            ),
            loader.ConfigValue(
                "fw_protect",
                3.0,
                lambda: self.strings("cfg_fw_protect"),
                validator=loader.validators.Float(minimum=0.0),
            ),
            loader.ConfigValue(
                "save_sd",
                True,
                lambda: self.strings("cfg_save_sd"),
                validator=loader.validators.Boolean(),
            ),
        )

        self._queue = []
        self._cache = {}
        self._next = 0
        self._cache_limit = 5000

    @loader.loop(interval=0.1, autostart=True)
    async def sender(self):
        if not self._queue or self._next > time.time():
            return

        item = self._queue.pop(0)
        try:
            # Виконуємо функцію відправки
            await item()
        except Exception as e:
            logger.error(f"Error sending log message: {e}")
        
        self._next = int(time.time()) + self.config["fw_protect"]

    @staticmethod
    def _int(value: typing.Union[str, int], /) -> typing.Union[str, int]:
        return int(value) if str(value).isdigit() else value

    @property
    def blacklist(self):
        return list(
            map(
                self._int,
                self.config["blacklist"]
                + [777000, self._client.tg_id, self._tl_channel, self.inline.bot_id],
            )
        )

    @blacklist.setter
    def blacklist(self, value: list):
        self.config["blacklist"] = list(
            set(value)
            - {777000, self._client.tg_id, self._tl_channel, self.inline.bot_id}
        )

    @property
    def whitelist(self):
        return list(map(self._int, self.config["whitelist"]))

    @whitelist.setter
    def whitelist(self, value: list):
        self.config["whitelist"] = value

    @property
    def always_track(self):
        return list(map(self._int, self.config["always_track"]))

    async def client_ready(self):
        # Створюємо або знаходимо канал для логів
        channel, _ = await utils.asset_channel(
            self._client,
            "Spy",
            "Архів видалених та змінених повідомлень (Spy Module)",
            silent=True,
            invite_bot=True,
            avatar="https://authorche.top/poems/logo.jpg",
            _folder="hikka",
        )

        self._channel = channel.id
        self._tl_channel = channel.id

    @loader.command(
        ru_doc="Включить/выключить режим слежения",
        uk_doc="Увімкнути/вимкнути режим стеження"
    )
    async def spymode(self, message: Message):
        """Увімкнути або вимкнути режим шпигуна"""
        new_state = not self.get("state", False)
        self.set("state", new_state)
        await utils.answer(
            message,
            self.strings("state").format(
                self.strings("on" if new_state else "off")
            ),
        )

    @loader.command(
        ru_doc="Добавить / удалить чат из черного списка",
        uk_doc="Додати / видалити чат із чорного списку"
    )
    async def spybl(self, message: Message):
        """Додати або видалити поточний чат з чорного списку"""
        chat = utils.get_chat_id(message)
        if chat in self.blacklist:
            self.blacklist = list(set(self.blacklist) - {chat})
            await utils.answer(message, self.strings("spybl_removed"))
        else:
            self.blacklist = list(set(self.blacklist) | {chat})
            await utils.answer(message, self.strings("spybl"))

    @loader.command(
        ru_doc="Очистить черный список",
        uk_doc="Очистити чорний список"
    )
    async def spyblclear(self, message: Message):
        """Повністю очистити чорний список"""
        self.blacklist = []
        await utils.answer(message, self.strings("spybl_clear"))

    @loader.command(
        ru_doc="Добавить / удалить чат из белого списка",
        uk_doc="Додати / видалити чат з білого списку"
    )
    async def spywl(self, message: Message):
        """Додати або видалити поточний чат з білого списку"""
        chat = utils.get_chat_id(message)
        if chat in self.whitelist:
            self.whitelist = list(set(self.whitelist) - {chat})
            await utils.answer(message, self.strings("spywl_removed"))
        else:
            self.whitelist = list(set(self.whitelist) | {chat})
            await utils.answer(message, self.strings("spywl"))

    @loader.command(
        ru_doc="Очистить белый список",
        uk_doc="Очистити білий список"
    )
    async def spywlclear(self, message: Message):
        """Повністю очистити білий список"""
        self.whitelist = []
        await utils.answer(message, self.strings("spywl_clear"))

    async def _get_entities_list(self, entities: list) -> str:
        return "\n".join(
            [
                f" ▫️ <b><a href=\"{utils.get_entity_url(await self._client.get_entity(x, exp=0))}\">"
                f"{utils.escape_html(get_display_name(await self._client.get_entity(x, exp=0)))}</a></b>"
                for x in entities
            ]
        )

    @loader.command(
        ru_doc="Показать текущую конфигурацию",
        uk_doc="Показати поточні налаштування"
    )
    async def spyinfo(self, message: Message):
        """Показати інформацію про налаштування модуля"""
        if not self.get("state"):
            await utils.answer(
                message, self.strings("mode_off").format(self.get_prefix())
            )
            return

        info = ""

        if self.config["save_sd"]:
            info += self.strings("save_sd")

        if self.config["enable_groups"]:
            info += self.strings("chat")

        if self.config["enable_pm"]:
            info += self.strings("pm")

        if self.whitelist:
            info += self.strings("whitelist").format(
                await self._get_entities_list(self.whitelist)
            )

        if self.config["blacklist"]:
            info += self.strings("blacklist").format(
                await self._get_entities_list(self.config["blacklist"])
            )

        if self.always_track:
            info += self.strings("always_track").format(
                await self._get_entities_list(self.always_track)
            )

        await utils.answer(message, info)

    # --- Логіка відправки (Fix) ---

    async def _send_safe(self, caption, file=None):
        """
        Універсальна функція відправки.
        Використовує self._client замість self.inline.bot для файлів,
        щоб уникнути помилок валідації Pydantic/Aiogram.
        """
        try:
            if file:
                # Telethon (self._client) коректно обробляє BytesIO
                await self._client.send_file(
                    self._channel,
                    file,
                    caption=caption,
                    force_document=False # Дозволяє відправляти фото як фото
                )
            else:
                # Текст можна слати через бота, щоб було гарніше, 
                # але надійніше теж через клієнт, щоб уникнути лімітів
                await self._client.send_message(
                    self._channel,
                    caption,
                    link_preview=False
                )
        except Exception as e:
            logger.error(f"Failed to send log: {e}")

    async def _message_deleted(self, msg_obj: Message, caption: str):
        caption = self.inline.sanitise_text(caption)

        if not msg_obj.photo and not msg_obj.video and not msg_obj.document and not msg_obj.voice:
            # Тільки текст
            self._queue.append(lambda: self._send_safe(caption))
            return

        # Обробка стікерів
        if msg_obj.sticker:
            self._queue.append(lambda: self._send_safe(caption + "\n\n[Стікер]"))
            return

        # Завантаження медіа
        async def _async_media_sender():
            try:
                # Завантажуємо медіа в пам'ять
                data = await self._client.download_media(msg_obj, bytes)
                file = io.BytesIO(data)
                file.seek(0)
                
                # Даємо правильне ім'я (важливо для Telethon)
                if msg_obj.photo:
                    file.name = "deleted.jpg"
                elif msg_obj.video:
                    file.name = "deleted.mp4"
                elif msg_obj.voice:
                    file.name = "deleted.ogg"
                elif msg_obj.document:
                    fname = "file"
                    for attr in msg_obj.document.attributes:
                        if isinstance(attr, DocumentAttributeFilename):
                            fname = attr.file_name
                            break
                    file.name = fname
                else:
                    file.name = "unknown.bin"

                await self._send_safe(caption, file)
            except Exception as e:
                # Якщо не вдалося завантажити, шлемо просто текст помилки
                await self._send_safe(caption + f"\n\n🚫 <b>Медіа втрачено:</b> {e}")

        self._queue.append(_async_media_sender)

    async def _message_edited(self, caption: str, msg_obj: Message):
        async def _async_edit_sender():
            try:
                file = None
                if msg_obj.media and not msg_obj.sticker:
                    data = await self._client.download_media(msg_obj, bytes)
                    file = io.BytesIO(data)
                    file.seek(0)
                    
                    if msg_obj.photo: file.name = "edited.jpg"
                    elif msg_obj.video: file.name = "edited.mp4"
                    elif msg_obj.voice: file.name = "edited.ogg"
                    else: file.name = "edited_file"
                
                await self._send_safe(caption, file)
            except Exception as e:
                await self._send_safe(caption + f"\n\n🚫 <b>Медіа втрачено:</b> {e}")

        self._queue.append(_async_edit_sender)

    # --- Обробники подій ---

    @loader.raw_handler(UpdateEditChannelMessage)
    async def channel_edit_handler(self, update: UpdateEditChannelMessage):
        if (
            not self.get("state", False)
            or update.message.out
            or (self.config["ignore_inline"] and update.message.via_bot_id)
        ):
            return

        try:
            chat_id = utils.get_chat_id(update.message)
            key = f"{chat_id}/{update.message.id}"
            
            if key in self._cache and (
                chat_id in self.always_track
                or self._cache[key].sender_id in self.always_track
                or (
                    self.config["log_edits"]
                    and self.config["enable_groups"]
                    and chat_id not in self.blacklist
                    and (not self.whitelist or chat_id in self.whitelist)
                )
            ):
                msg_obj = self._cache[key]
                # Перевірка чи текст змінився
                if not msg_obj.sender.bot and update.message.raw_text != msg_obj.raw_text:
                    await self._message_edited(
                        self.strings("edited_chat").format(
                            utils.get_entity_url(msg_obj.chat),
                            utils.escape_html(get_display_name(msg_obj.chat)),
                            utils.get_entity_url(msg_obj.sender),
                            utils.escape_html(get_display_name(msg_obj.sender)),
                            msg_obj.text,
                            message_url=await utils.get_message_link(msg_obj),
                        ),
                        msg_obj,
                    )

            self._cache[key] = update.message
        except Exception:
            pass

    def _should_capture(self, user_id: int, chat_id: int) -> bool:
        return (
            chat_id not in self.blacklist
            and user_id not in self.blacklist
            and (
                not self.whitelist
                or chat_id in self.whitelist
                or user_id in self.whitelist
            )
        )

    @loader.raw_handler(UpdateEditMessage)
    async def pm_edit_handler(self, update: UpdateEditMessage):
        if (
            not self.get("state", False)
            or update.message.out
            or (self.config["ignore_inline"] and update.message.via_bot_id)
        ):
            return

        key = update.message.id
        msg_obj = self._cache.get(key)
        
        try:
            if key in self._cache and update.message.raw_text != msg_obj.raw_text:
                # Перевірки дозволів
                should_log = False
                if self._cache[key].sender_id in self.always_track:
                    should_log = True
                elif utils.get_chat_id(self._cache[key]) in self.always_track:
                    should_log = True
                elif self.config["log_edits"] and self._should_capture(self._cache[key].sender_id, utils.get_chat_id(self._cache[key])):
                    is_group = isinstance(msg_obj.peer_id, PeerChat)
                    if (self.config["enable_pm"] and not is_group) or (self.config["enable_groups"] and is_group):
                        should_log = True

                if should_log:
                    sender = await self._client.get_entity(msg_obj.sender_id, exp=0)
                    if not sender.bot:
                        is_group = isinstance(msg_obj.peer_id, PeerChat)
                        
                        if is_group:
                            chat = await self._client.get_entity(msg_obj.peer_id.chat_id, exp=0)
                            formatted = self.strings("edited_chat").format(
                                utils.get_entity_url(chat),
                                utils.escape_html(get_display_name(chat)),
                                utils.get_entity_url(sender),
                                utils.escape_html(get_display_name(sender)),
                                msg_obj.text,
                                message_url=await utils.get_message_link(msg_obj),
                            )
                        else:
                            formatted = self.strings("edited_pm").format(
                                utils.get_entity_url(sender),
                                utils.escape_html(get_display_name(sender)),
                                msg_obj.text,
                                message_url=await utils.get_message_link(msg_obj),
                            )
                            
                        await self._message_edited(formatted, msg_obj)

            self._cache[update.message.id] = update.message
        except Exception:
            pass

    @loader.raw_handler(UpdateDeleteMessages)
    async def pm_delete_handler(self, update: UpdateDeleteMessages):
        if not self.get("state", False):
            return

        for message in update.messages:
            if message not in self._cache:
                continue

            msg_obj = self._cache.pop(message)

            try:
                chat_id = utils.get_chat_id(msg_obj)
                if (
                    msg_obj.sender_id not in self.always_track
                    and chat_id not in self.always_track
                    and (
                        not self._should_capture(msg_obj.sender_id, chat_id)
                        or (self.config["ignore_inline"] and msg_obj.via_bot_id)
                        or (not self.config["enable_groups"] and isinstance(msg_obj.peer_id, PeerChat))
                        or (not self.config["enable_pm"] and not isinstance(msg_obj.peer_id, PeerChat))
                    )
                ):
                    continue

                sender = await self._client.get_entity(msg_obj.sender_id, exp=0)
                if sender.bot:
                    continue

                is_group = isinstance(msg_obj.peer_id, PeerChat)
                if is_group:
                    chat = await self._client.get_entity(msg_obj.peer_id.chat_id, exp=0)
                    text = self.strings("deleted_chat").format(
                        utils.get_entity_url(chat),
                        utils.escape_html(get_display_name(chat)),
                        utils.get_entity_url(sender),
                        utils.escape_html(get_display_name(sender)),
                        msg_obj.text,
                        message_url=await utils.get_message_link(msg_obj),
                    )
                else:
                    text = self.strings("deleted_pm").format(
                        utils.get_entity_url(sender),
                        utils.escape_html(get_display_name(sender)),
                        msg_obj.text,
                        message_url=await utils.get_message_link(msg_obj),
                    )

                await self._message_deleted(msg_obj, text)
            except Exception as e:
                logger.error(f"Error in delete handler: {e}")

    @loader.raw_handler(UpdateDeleteChannelMessages)
    async def channel_delete_handler(self, update: UpdateDeleteChannelMessages):
        if not self.get("state", False):
            return

        for message in update.messages:
            key = f"{update.channel_id}/{message}"
            if key not in self._cache:
                continue

            msg_obj = self._cache.pop(key)

            try:
                chat_id = utils.get_chat_id(msg_obj)
                if (
                    msg_obj.sender_id in self.always_track
                    or chat_id in self.always_track
                    or self.config["enable_groups"]
                    and (
                        self._should_capture(msg_obj.sender_id, chat_id)
                        and (not self.config["ignore_inline"] or not msg_obj.via_bot_id)
                        and not msg_obj.sender.bot
                    )
                ):
                    await self._message_deleted(
                        msg_obj,
                        self.strings("deleted_chat").format(
                            utils.get_entity_url(msg_obj.chat),
                            utils.escape_html(get_display_name(msg_obj.chat)),
                            utils.get_entity_url(msg_obj.sender),
                            utils.escape_html(get_display_name(msg_obj.sender)),
                            msg_obj.text,
                            message_url=await utils.get_message_link(msg_obj),
                        ),
                    )
            except Exception:
                pass

    @loader.watcher("in")
    async def watcher(self, message: Message):
        """Watcher for SD media and caching messages"""
        
        # --- Виправлена та стабільна логіка Save SD ---
        if self.config["save_sd"] and message.media:
            is_sd = False
            
            # 1. TTL в атрибутах медіа
            if hasattr(message.media, "ttl_seconds") and message.media.ttl_seconds:
                is_sd = True
            
            # 2. TTL у фото (Telegram API layer quirks)
            elif hasattr(message.media, "photo") and hasattr(message.media.photo, "ttl_seconds") and message.media.photo.ttl_seconds:
                is_sd = True
                
            # 3. TTL повідомлення (нове API)
            elif hasattr(message, "ttl_period") and message.ttl_period:
                is_sd = True
            
            if is_sd:
                async def _save_sd_task():
                    try:
                        # Качаємо байтами
                        media_bytes = await self._client.download_media(message, bytes)
                        media_io = io.BytesIO(media_bytes)
                        media_io.seek(0)
                        
                        # Встановлюємо ім'я файлу (критично для Telethon)
                        if getattr(message, "photo", None):
                            media_io.name = "sd_capture.jpg"
                        else:
                            media_io.name = "sd_capture.mp4"
                        
                        sender = await self._client.get_entity(message.sender_id)
                        caption = self.strings("sd_media").format(
                            utils.get_entity_url(sender),
                            utils.escape_html(get_display_name(sender)),
                        )
                        
                        # Відправляємо через CLIENT, а не бота
                        await self._client.send_file(
                            self._channel,
                            media_io,
                            caption=caption
                        )
                    except Exception as e:
                        logger.error(f"Failed to capture SD media: {e}")

                self._queue.append(_save_sd_task)

        # --- Кешування повідомлень ---
        try:
            if len(self._cache) > self._cache_limit:
                # Очищаємо старі повідомлення
                keys_to_remove = list(self._cache.keys())[:100]
                for k in keys_to_remove:
                    del self._cache[k]

            key = (
                message.id
                if message.is_private or isinstance(message.peer_id, PeerChat)
                else f"{utils.get_chat_id(message)}/{message.id}"
            )
            self._cache[key] = message
        except Exception:
            pass
