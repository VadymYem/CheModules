__version__ = (1, 5, 0)
#meta developer: @author_che
import contextlib
import io
import logging
import time
import typing

# Спроба імпорту типів для aiogram 3.x (використовується в Hikka)
try:
    from aiogram.types import BufferedInputFile
except ImportError:
    BufferedInputFile = None

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
    Зберігає видалені та відредаговані повідомлення.
    Відправка ТІЛЬКИ через інлайн-бота для захисту акаунту від спамбану.
    Виправлено помилку 'Event object has no attribute media'.
    Покращено роботу зі стікерами.
    """

    strings = {
        "name": "Spy",
        "state": "🕵️‍♂️ <b>Режим шпигуна тепер {}</b>",
        "spybl": "🕵️‍♂️ <b>Чат додано до чорного списку (ігнорування)</b>",
        "spybl_removed": "🕵️‍♂️ <b>Чат видалено з чорного списку</b>",
        "spybl_clear": "🕵️‍♂️ <b>Чорний список очищено</b>",
        "spywl": "🕵️‍♂️ <b>Чат додано до білого списку (відстежування)</b>",
        "spywl_removed": "🕵️‍♂️ <b>Чат видалено з білого списку</b>",
        "spywl_clear": "🕵️‍♂️ <b>Білий список очищено</b>",
        "whitelist": "\n🕵️‍♂️ <b>Стежу ТІЛЬКИ за повідомленнями від:</b>\n{}",
        "always_track": "\n🕵️‍♂️ <b>ЗАВЖДИ стежу за повідомленнями від:</b>\n{}",
        "blacklist": "\n🕵️‍♂️ <b>ІГНОРУЮ повідомлення від:</b>\n{}",
        "chat": "👥 <b>Стеження у групах активне</b>\n",
        "pm": "👤 <b>Стеження в особистих повідомленнях активне</b>\n",
        "mode_off": "👤 <b>Стеження вимкнено. Увімкнути: </b><code>{}spymode</code>\n",
        
        "deleted_pm": (
            '🗑 <b><a href="{}">{}</a> видалив(ла) <a href="{}">повідомлення</a> в ПП.'
            ' Зміст:</b>\n{}'
        ),
        "deleted_chat": (
            '🗑 <b><a href="{}">Повідомлення</a> в чаті <a href="{}">{}</a> від <a'
            ' href="{}">{}</a> було видалено. Зміст:</b>\n{}'
        ),
        "edited_pm": (
            '✏️ <b><a href="{}">{}</a> змінив(ла) <a href="{}">повідомлення</a>'
            ' в ПП. Старий зміст:</b>\n{}'
        ),
        "edited_chat": (
            '✏️ <b><a href="{}">Повідомлення</a> в чаті <a href="{}">{}</a>'
            ' від <a href="{}">{}</a> було змінено. Старий зміст:</b>\n{}'
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
            "🔥 <b><a href='tg://user?id={}'>{}</a> надіслав(ла) самознищуване"
            " медіа</b>"
        ),
        "save_sd": (
            "🔥 <b>Збереження самознищуваних медіа активне</b>\n"
        ),
        "cfg_save_sd": "Зберігати самознищувані фото/відео",
        "bot_error": "\n\n⚠️ <i>Не вдалося відправити медіа через бота. Можливо, файл завеликий або пошкоджений.</i>",
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
            await item()
        except Exception as e:
            logger.error(f"Error sending log message: {e}")
        
        # Затримка між відправками (налаштовується в конфігу)
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
        channel, _ = await utils.asset_channel(
            self._client,
            "Spy",
            "Архів видалених та змінених повідомлень (Spy)",
            silent=True,
            invite_bot=True,
            avatar="https://img.icons8.com/color/480/spy.png",
            _folder="hikka",
        )

        self._channel = int(f"-100{channel.id}")
        self._tl_channel = channel.id

    # --- Команди ---

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

    # --- Логіка відправки через БОТА ---

    async def _send_bot_text(self, caption):
        """Відправка ТЕКСТУ через БОТА"""
        try:
            await self.inline.bot.send_message(
                self._channel,
                caption,
                disable_web_page_preview=True
            )
        except Exception as e:
            logger.error(f"Bot text send error: {e}")

    async def _send_bot_media(self, caption, file_io: io.BytesIO, type_hint: str):
        """
        Відправка МЕДІА через БОТА з використанням BufferedInputFile.
        Це вирішує проблему validation errors.
        """
        try:
            file_io.seek(0)
            file_bytes = file_io.read()
            
            # Підготовка файлу для aiogram
            if BufferedInputFile:
                media_file = BufferedInputFile(file_bytes, filename=file_io.name)
            else:
                media_file = file_io
                media_file.seek(0)

            if type_hint == "photo":
                await self.inline.bot.send_photo(self._channel, photo=media_file, caption=caption)
            elif type_hint == "video":
                await self.inline.bot.send_video(self._channel, video=media_file, caption=caption)
            elif type_hint == "voice":
                await self.inline.bot.send_voice(self._channel, voice=media_file, caption=caption)
            elif type_hint == "sticker":
                # Стікери шлемо без підпису, бо send_sticker не приймає caption
                await self.inline.bot.send_sticker(self._channel, sticker=media_file)
            else:
                await self.inline.bot.send_document(self._channel, document=media_file, caption=caption)
        
        except Exception as e:
            logger.error(f"Bot media send error: {e}")
            await self._send_bot_text(caption + self.strings("bot_error"))


    async def _message_deleted(self, msg_obj: Message, caption: str):
        caption = self.inline.sanitise_text(caption)

        # 1. Стікери - особлива логіка
        if msg_obj.sticker:
            # Спочатку текст з емодзі стікера
            sticker_emoji = msg_obj.file.emoji if msg_obj.file.emoji else "🗿"
            text_update = f"{caption}\n\n[Стікер {sticker_emoji}]"
            self._queue.append(lambda: self._send_bot_text(text_update))

            # Потім сам стікер окремим повідомленням
            async def _async_sticker_sender():
                try:
                    data = await self._client.download_media(msg_obj, bytes)
                    file = io.BytesIO(data)
                    file.name = "sticker.webp" # Стандарт для статичних
                    # Для анімованих/відео можна додати перевірку атрибутів, але бот зазвичай розуміє сам
                    
                    await self._send_bot_media("", file, "sticker")
                except Exception as e:
                    pass # Якщо стікер не вантажиться, просто ігноруємо, текст вже пішов

            self._queue.append(_async_sticker_sender)
            return

        # 2. Тільки текст (якщо немає медіа або є веб-сторінка)
        if not msg_obj.media or (hasattr(msg_obj.media, "webpage") and msg_obj.media.webpage):
            self._queue.append(lambda: self._send_bot_text(caption))
            return

        # 3. Інші медіа файли
        async def _async_media_sender():
            try:
                data = await self._client.download_media(msg_obj, bytes)
                file = io.BytesIO(data)
                
                type_hint = "doc"
                if msg_obj.photo: 
                    file.name = "deleted.jpg"
                    type_hint = "photo"
                elif msg_obj.video: 
                    file.name = "deleted.mp4"
                    type_hint = "video"
                elif msg_obj.voice: 
                    file.name = "deleted.ogg"
                    type_hint = "voice"
                elif msg_obj.document:
                    fname = "file"
                    for attr in msg_obj.document.attributes:
                        if isinstance(attr, DocumentAttributeFilename):
                            fname = attr.file_name
                            break
                    file.name = fname
                else:
                    file.name = "unknown.bin"

                await self._send_bot_media(caption, file, type_hint)
            except Exception as e:
                await self._send_bot_text(caption + f"\n\n🚫 <b>Не вдалося завантажити медіа:</b> {e}")

        self._queue.append(_async_media_sender)

    async def _message_edited(self, caption: str, msg_obj: Message):
        # Текст
        if not msg_obj.media or (hasattr(msg_obj.media, "webpage") and msg_obj.media.webpage):
             self._queue.append(lambda: self._send_bot_text(caption))
             return

        # Медіа
        async def _async_edit_sender():
            try:
                data = await self._client.download_media(msg_obj, bytes)
                file = io.BytesIO(data)
                
                type_hint = "doc"
                if msg_obj.photo: 
                    file.name = "edited.jpg"
                    type_hint = "photo"
                elif msg_obj.video: 
                    file.name = "edited.mp4"
                    type_hint = "video"
                elif msg_obj.voice: 
                    file.name = "edited.ogg"
                    type_hint = "voice"
                else: 
                    file.name = "edited_file"
                
                await self._send_bot_media(caption, file, type_hint)
            except Exception as e:
                await self._send_bot_text(caption + f"\n\n🚫 <b>Не вдалося завантажити медіа:</b> {e}")

        self._queue.append(_async_edit_sender)

    # --- Обробники ---

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
                if not msg_obj.sender.bot and update.message.raw_text != msg_obj.raw_text:
                    link = await utils.get_message_link(msg_obj)
                    chat_title = utils.escape_html(get_display_name(msg_obj.chat))
                    sender_title = utils.escape_html(get_display_name(msg_obj.sender))
                    
                    formatted = self.strings("edited_chat").format(
                        link,          
                        link,          
                        chat_title,    
                        utils.get_entity_url(msg_obj.sender), 
                        sender_title,  
                        msg_obj.text   
                    )
                    await self._message_edited(formatted, msg_obj)

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
                        link = await utils.get_message_link(msg_obj)
                        sender_url = utils.get_entity_url(sender)
                        sender_name = utils.escape_html(get_display_name(sender))

                        if is_group:
                            chat = await self._client.get_entity(msg_obj.peer_id.chat_id, exp=0)
                            chat_name = utils.escape_html(get_display_name(chat))
                            
                            formatted = self.strings("edited_chat").format(
                                link,       
                                link,       
                                chat_name,  
                                sender_url, 
                                sender_name,
                                msg_obj.text
                            )
                        else:
                            formatted = self.strings("edited_pm").format(
                                sender_url, 
                                sender_name,
                                link,       
                                msg_obj.text
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
                link = await utils.get_message_link(msg_obj)
                sender_url = utils.get_entity_url(sender)
                sender_name = utils.escape_html(get_display_name(sender))

                if is_group:
                    chat = await self._client.get_entity(msg_obj.peer_id.chat_id, exp=0)
                    chat_name = utils.escape_html(get_display_name(chat))
                    
                    text = self.strings("deleted_chat").format(
                        link,        
                        link,        
                        chat_name,   
                        sender_url,  
                        sender_name, 
                        msg_obj.text 
                    )
                else:
                    text = self.strings("deleted_pm").format(
                        sender_url,  
                        sender_name, 
                        link,        
                        msg_obj.text 
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
                    link = await utils.get_message_link(msg_obj)
                    sender_url = utils.get_entity_url(msg_obj.sender)
                    sender_name = utils.escape_html(get_display_name(msg_obj.sender))
                    chat_name = utils.escape_html(get_display_name(msg_obj.chat))
                    chat_url = utils.get_entity_url(msg_obj.chat)

                    await self._message_deleted(
                        msg_obj,
                        self.strings("deleted_chat").format(
                            link,        
                            chat_url,    
                            chat_name,   
                            sender_url,  
                            sender_name, 
                            msg_obj.text 
                        ),
                    )
            except Exception:
                pass

    @loader.watcher("in")
    async def watcher(self, message: Message):
        """Watcher for SD media and caching messages"""
        
        # FIX: Перевірка типу повідомлення для уникнення AttributeError
        if not isinstance(message, Message):
            return

        # --- Save SD ---
        if self.config["save_sd"] and message.media:
            is_sd = False
            if hasattr(message.media, "ttl_seconds") and message.media.ttl_seconds:
                is_sd = True
            elif hasattr(message.media, "photo") and hasattr(message.media.photo, "ttl_seconds") and message.media.photo.ttl_seconds:
                is_sd = True
            elif hasattr(message, "ttl_period") and message.ttl_period:
                is_sd = True
            
            if is_sd:
                async def _save_sd_task():
                    try:
                        media_bytes = await self._client.download_media(message, bytes)
                        file = io.BytesIO(media_bytes)
                        
                        type_hint = "doc"
                        if getattr(message, "photo", None):
                            file.name = "sd_capture.jpg"
                            type_hint = "photo"
                        else:
                            file.name = "sd_capture.mp4"
                            type_hint = "video"
                        
                        sender = await self._client.get_entity(message.sender_id)
                        caption = self.strings("sd_media").format(
                            utils.get_entity_url(sender),
                            utils.escape_html(get_display_name(sender)),
                        )
                        
                        await self._send_bot_media(caption, file, type_hint)
                    except Exception as e:
                        logger.error(f"Failed to capture SD media: {e}")

                self._queue.append(_save_sd_task)

        # --- Caching ---
        try:
            if len(self._cache) > self._cache_limit:
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