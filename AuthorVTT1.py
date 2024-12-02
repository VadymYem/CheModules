# meta developer: @BlazeFtg, @Author_Che
# requires: pydub speechRecognition moviepy telethon
from io import BytesIO
import os
import tempfile
import logging

import speech_recognition as srec
from pydub import AudioSegment as auds
from moviepy.editor import VideoFileClip
from telethon.tl.types import DocumentAttributeVideo, Message

from .. import loader, utils

logger = logging.getLogger(__name__)

@loader.tds
class AuthorVtt1Mod(loader.Module):
    """Розпізнавання голосу через Google Recognition API з авто-режимом"""
    strings = {
        "name": "Author's Voice-to-text(vtt)",
        "pref": "<b>[Author's VTT]</b> ",
        "converted": "<b>AuthorChe-VTT:</b>\n<i>{}</i>",
        "autovoice_ru_on": "<b>🫠 Автоматичне розпізнавання російських голосових повідомлень увімкнено в цьому чаті</b>",
        "autovoice_ru_off": "<b>🫠 Автоматичне розпізнавання російських голосових повідомлень вимкнено в цьому чаті</b>",
        "autovoice_uk_on": "<b>🫠 Автоматичне розпізнавання українських голосових повідомлень увімкнено в цьому чаті</b>",
        "autovoice_uk_off": "<b>🫠 Автоматичне розпізнавання українських голосових повідомлень вимкнено в цьому чаті</b>",
        "autovoice_en_on": "<b>🫠 Автоматичне розпізнавання англійських голосових повідомлень увімкнено в цьому чаті</b>",
        "autovoice_en_off": "<b>🫠 Автоматичне розпізнавання англійських голосових повідомлень вимкнено в цьому чаті</b>",
        "voice_not_found": "🫠 Голосове повідомлення не знайдено",
        "error": "🚫 <b>Помилка розпізнавання! Можливі проблеми з розпізнаванням мови.</b>",
        "too_big": "🫥 <b>Голосове повідомлення занадто велике для розпізнавання</b>",
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue("ignore_users", [], validator=loader.validators.Series(validator=loader.validators.TelegramID())),
            loader.ConfigValue("silent", False, validator=loader.validators.Boolean()),
        )
        self.chats_ru = set()
        self.chats_uk = set()
        self.chats_en = set()

    async def client_ready(self, client, db):
        self.db = db

    async def _process_audio(self, m, lang, file_type='audio'):
        """Загальний метод для обробки аудіо або відео"""
        reply = await m.get_reply_message()
        if not reply or not reply.media:
            await m.edit(self.strings["pref"] + "reply to media...")
            return

        # Визначення типу медіа
        is_voice = hasattr(reply.media.document, 'attributes') and any(
            getattr(attr, 'voice', False) for attr in reply.media.document.attributes
        )
        is_audio = reply.audio is not None
        is_video = reply.video is not None

        # Перевірка типу файлу
        if file_type == 'audio' and not (is_audio or is_voice):
            await m.edit(self.strings["pref"] + "reply to audio...")
            return
        
        if file_type == 'video' and not is_video:
            await m.edit(self.strings["pref"] + "reply to video...")
            return
        
        if file_type == 'voice' and not is_voice:
            await m.edit(self.strings["pref"] + "reply to voice message...")
            return
        
        await m.edit(self.strings["pref"] + "Processing...")
        
        try:
            # Завантаження файлу у BytesIO
            source = BytesIO(await reply.download_media(bytes))
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=".tmp") as temp_file:
                temp_file.write(source.read())
                temp_file_name = temp_file.name

            try:
                # Конвертація в аудіо WAV
                with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as audio_temp_file:
                    if is_video:
                        video = VideoFileClip(temp_file_name)
                        video.audio.write_audiofile(audio_temp_file.name, codec="pcm_s16le")
                    else:
                        auds.from_file(temp_file_name).export(audio_temp_file.name, format="wav")
                    audio_source = audio_temp_file.name

                # Розпізнавання мови
                recog = srec.Recognizer()
                with srec.AudioFile(audio_source) as audio_file:
                    audio_content = recog.record(audio_file)
                
                recognized_text = recog.recognize_google(audio_content, language=lang)
                await m.edit(self.strings["pref"] + recognized_text)

            except Exception as e:
                logger.exception("Audio processing error")
                await m.edit(self.strings["pref"] + f"Помилка: {str(e)}")
            finally:
                # Видалення тимчасових файлів
                if os.path.exists(temp_file_name):
                    os.unlink(temp_file_name)
                if os.path.exists(audio_source):
                    os.unlink(audio_source)

        except Exception as e:
            await m.edit(self.strings["pref"] + f"Помилка завантаження: {str(e)}")

    @loader.owner
    async def avcmd(self, m):
        """.av <reply to audio> - розпізнати авдіо українською"""
        await self._process_audio(m, "uk-UA", 'audio')

    @loader.owner
    async def arcmd(self, m):
        """.ar <reply to audio> - розпізнати кацапське аудіо"""
        await self._process_audio(m, "ru-RU", 'audio')

    @loader.owner
    async def aecmd(self, m):
        """.ae <reply to audio> - розпізнати аудіо англійською"""
        await self._process_audio(m, "en-US", 'audio')

    @loader.owner
    async def avccmd(self, m):
        """.avc <reply to video> - розпізнати українське відео"""
        await self._process_audio(m, "uk-UA", 'video')

    @loader.owner
    async def arccmd(self, m):
        """.arc <reply to video> - розпізнати російське відео"""
        await self._process_audio(m, "ru-RU", 'video')

    @loader.owner
    async def aeccmd(self, m):
        """.aec <reply to video> - розпізнати англійське відео"""
        await self._process_audio(m, "en-US", 'video')

    @loader.unrestricted
    async def aevcmd(self, m):
        """.aev <reply to voice> - розпізнати англійську голосову"""
        await self._process_audio(m, "en-US", 'voice')

    @loader.unrestricted
    async def avccmd(self, message):
        """Toggle auto-recognition for Ukrainian voice messages in the current chat"""
        chat_id = utils.get_chat_id(message)

        if chat_id in self.chats_uk:
            self.chats_uk.remove(chat_id)
            await message.respond(self.strings["autovoice_uk_off"])
        else:
            self.chats_uk.add(chat_id)
            await message.respond(self.strings["autovoice_uk_on"])

    @loader.unrestricted
    async def arccmd(self, message):
        """Toggle auto-recognition for Russian voice messages in the current chat"""
        chat_id = utils.get_chat_id(message)

        if chat_id in self.chats_ru:
            self.chats_ru.remove(chat_id)
            await message.respond(self.strings["autovoice_ru_off"])
        else:
            self.chats_ru.add(chat_id)
            await message.respond(self.strings["autovoice_ru_on"])

    async def watcher(self, message):
        try:
            # Перевірка наявності медіафайлу
            if not message.media:
                return

            # Визначення типу медіа
            is_voice = (
                hasattr(message.media, 'document') and 
                message.media.document.attributes and
                any(getattr(attr, 'voice', False) for attr in message.media.document.attributes)
            )
            is_audio = message.audio is not None
            is_video = message.video is not None

            # Перевірка типів медіа
            if not (is_voice or is_audio or is_video):
                return

            chat_id = utils.get_chat_id(message)
            
            # Перевірка ігнорованих користувачів
            if message.sender_id in self.config["ignore_users"]:
                return

            # Визначення тривалості
            duration = 0
            try:
                if is_video:
                    duration = next(
                        attr.duration
                        for attr in message.video.attributes
                        if isinstance(attr, DocumentAttributeVideo)
                    )
                elif is_voice or is_audio:
                    duration = next(
                        (attr.duration for attr in message.media.document.attributes 
                         if hasattr(attr, 'duration')), 0
                    )
            except Exception:
                return

            # Перевірка розміру та тривалості
            if duration > 65 or message.document.size / 1024 / 1024 > 5:
                if not self.config["silent"]:
                    await message.respond(self.strings["too_big"])
                return

            # Перевірка автоматичного розпізнавання для чату
            current_chats = {
                'uk': self.chats_uk,
                'ru': self.chats_ru,
                'en': self.chats_en
            }

            for lang, chats in current_chats.items():
                if chat_id in chats:
                    await self._auto_recognize(message, lang)
                    break

        except Exception as e:
            logger.exception(f"Error in watcher: {e}")

    async def _auto_recognize(self, message, lang):
        """Automatic voice recognition"""
        try:
            source = BytesIO(await message.download_media(bytes))
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=".tmp") as temp_file:
                temp_file.write(source.read())
                temp_file_name = temp_file.name

            try:
                # Конвертація в аудіо WAV
                with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as audio_temp_file:
                    if message.video:
                        video = VideoFileClip(temp_file_name)
                        video.audio.write_audiofile(audio_temp_file.name, codec="pcm_s16le")
                    else:
                        auds.from_file(temp_file_name).export(audio_temp_file.name, format="wav")
                    audio_source = audio_temp_file.name

                recog = srec.Recognizer()
                with srec.AudioFile(audio_source) as audio_file:
                    audio_content = recog.record(audio_file)
                
                # Розпізнавання мови
                lang_map = {
                    'uk': "uk-UA",
                    'ru': "ru-RU",
                    'en': "en-US"
                }
                recognized_text = recog.recognize_google(audio_content, language=lang_map[lang])
                await message.respond(self.strings["converted"].format(recognized_text))

            except Exception:
                logger.exception("Auto recognition error")
                if not self.config["silent"]:
                    await message.respond(self.strings["error"])
            finally:
                # Видалення тимчасових файлів
                if os.path.exists(temp_file_name):
                    os.unlink(temp_file_name)
                if os.path.exists(audio_source):
                    os.unlink(audio_source)

        except Exception:
            logger.exception("Voice recognition failed")
            if not self.config["silent"]:
                await message.respond(self.strings["error"])
