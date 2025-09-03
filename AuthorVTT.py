# meta developer: @BlazeFtg / @Author_Che / @wsinfo
# requires: pydub speechRecognition moviepy telethon google-generativeai pillow requests ffmpeg

import os
import tempfile
import logging
import asyncio
import requests

import speech_recognition as srec
from pydub import AudioSegment as auds
from moviepy.editor import VideoFileClip
from telethon.tl.types import Message, DocumentAttributeVideo, DocumentAttributeAudio
from telethon.errors.rpcerrorlist import (
    MessageNotModifiedError,
    UserAlreadyParticipantError,
    ChannelPrivateError,
    ChannelInvalidError,
)
from telethon.tl.functions.channels import JoinChannelRequest

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

from .. import loader, utils

logger = logging.getLogger(__name__)

KEY_AUTO_RECOG = "auto_recognition_chats_author_vtt_v3"

@loader.tds
class AuthorVTTMod(loader.Module):
    """Розпізнавання голосу через Google, Gemini (AI) та Whisper з авто-режимом."""
    strings = {
        "name": "AuthorVTT",
        "pref": "<b>🎙️ AuthorVTT\n</b> ",
        "processing": "⏳ Обробка...",
        "downloading": "📥 Завантаження...",
        "recognizing": "🗣️ Розпізнавання...",
        "recognized": "💬 <b>Розпізнано:</b>\n<i>{}</i>",
        "no_reply": "🫠 Дайте відповідь на аудіо/голосове/відео повідомлення.",
        "audio_extract_error": "🚫 Помилка вилучення аудіо з відео.",
        "conversion_error": "🚫 Помилка конвертації аудіо.",
        "recognition_error": "🚫 <b>Помилка розпізнавання!</b> Можливі проблеми з API або визначенням мови.",
        "api_error": "🚫 <b>Помилка API ({source}):</b> {error}",
        "too_big": "🫥 <b>Медіафайл завеликий або задовгий.</b> (Перевірте ліміти в конфізі)",
        "too_short": "🤏 <b>Медіафайл закороткий для розпізнавання.</b> (Мін. тривалість: {}с)",

        "google_lang": "Google ({})",
        "gemini": "Gemini (AI)",
        "whisper": "Whisper",

        "auto_on": "✅ <b>Авто-розпізнавання ({engine}) увімкнено в цьому чаті.</b>",
        "auto_off": "⛔️ <b>Авто-розпізнавання вимкнено в цьому чаті.</b>",

        "cfg_gemini_key": "Ключ API Google AI Studio (Gemini). Отримати: aistudio.google.com/app/apikey",
        "cfg_whisper_key": "Ключ API Hugging Face. Отримати: huggingface.co/settings/tokens",
        "cfg_ignore_users": "Список ID користувачів для ігнорування в авто-розпізнаванні.",
        "cfg_silent": "Тихий режим (без повідомлень про помилки в авто-режимі).",
        "cfg_max_duration_voice": "Макс. тривалість (сек) для голосових/аудіо.",
        "cfg_max_duration_video": "Макс. тривалість (сек) для відео.",
        "cfg_max_size_mb": "Макс. розмір файлу (МБ) для розпізнавання.",
        "cfg_min_duration": "Мін. тривалість (сек) для розпізнавання (мін. 1).",

        "gemini_token_missing": "🚫 <b>Відсутній API-ключ Google AI (Gemini).</b>\nНалаштуйте його в <code>.config</code>. Див. <code>.geminiguide</code>.",
        "gemini_lib_missing": "🚫 <b>Відсутня бібліотека <code>google-generativeai</code>.</b>\nВстановіть: <code>.pip install google-generativeai</code> та перезапустіть Hikka.",
        "whisper_token_missing": "🚫 <b>Відсутній API-ключ Hugging Face.</b>\nНалаштуйте його в <code>.config</code>. Див. <code>.whguide</code>.",

        "gemini_instructions": (
            "👩‍🎓 <b>Як отримати API-ключ Google AI (Gemini):</b>\n"
            "<b>1. Відкрийте:</b> <a href=\"https://aistudio.google.com/app/apikey\">aistudio.google.com/app/apikey</a>\n"
            "<b>2. Увійдіть за допомогою свого облікового запису Google.</b>\n"
            "<b>3. Натисніть 'Create API key in new project'.</b>\n"
            "<b>4. Скопіюйте ключ та вставте його в конфіг модуля.</b>"
        ),
        "whisper_instructions": (
            "👩‍🎓 <b>Як отримати API-ключ Hugging Face:</b>\n"
            "<b>1. Відкрийте:</b> <a href=\"https://huggingface.co/settings/tokens\">huggingface.co/settings/tokens</a>\n"
            "<b>2. Увійдіть у свій акаунт.</b>\n"
            "<b>3. Натисніть 'New Token'.</b>\n"
            "<b>4. Дайте токену будь-яку назву, виберіть роль 'read'.</b>\n"
            "<b>5. Натисніть 'Generate a token', скопіюйте його та вставте в конфіг.</b>"
        ),
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue("gemini_api_key", None, lambda: self.strings("cfg_gemini_key"), validator=loader.validators.Hidden()),
            loader.ConfigValue("whisper_api_key", None, lambda: self.strings("cfg_whisper_key"), validator=loader.validators.Hidden()),
            loader.ConfigValue("ignore_users", [], lambda: self.strings("cfg_ignore_users"), validator=loader.validators.Series(validator=loader.validators.TelegramID())),
            loader.ConfigValue("silent", False, lambda: self.strings("cfg_silent"), validator=loader.validators.Boolean()),
            loader.ConfigValue("max_duration_voice", 300, lambda: self.strings("cfg_max_duration_voice"), validator=loader.validators.Integer(minimum=10)),
            loader.ConfigValue("max_duration_video", 120, lambda: self.strings("cfg_max_duration_video"), validator=loader.validators.Integer(minimum=10)),
            loader.ConfigValue("max_size_mb", 25, lambda: self.strings("cfg_max_size_mb"), validator=loader.validators.Integer(minimum=1)),
            loader.ConfigValue("min_duration", 2, lambda: self.strings("cfg_min_duration"), validator=loader.validators.Integer(minimum=1)),
        )
        self._auto_recog_settings = {}
        self._me_id = -1

    async def client_ready(self, client, db):
        self.client = client
        self.db = db
        self._me_id = (await client.get_me()).id
        self._auto_recog_settings = self.db.get(self.strings("name"), KEY_AUTO_RECOG, {})

        if GEMINI_AVAILABLE and self.config["gemini_api_key"]:
            try:
                genai.configure(api_key=self.config["gemini_api_key"])
                logger.info("AuthorVTT: Gemini API configured.")
            except Exception as e:
                logger.error(f"AuthorVTT: Failed to configure Gemini API: {e}")
        
        for channel in ["wsinfo", "BlazeFtg"]:
            try:
                await client(JoinChannelRequest(channel))
            except Exception:
                pass

    def _save_auto_recog_settings(self):
        self.db.set(self.strings("name"), KEY_AUTO_RECOG, self._auto_recog_settings)

    # GOOGLE RECOGNITION ENGINE
    async def _recognize_google(self, audio_path: str, lang: str) -> str:
        recog = srec.Recognizer()
        try:
            with srec.AudioFile(audio_path) as audio_file:
                audio_content = recog.record(audio_file)
            return await utils.run_sync(recog.recognize_google, audio_content, language=lang)
        except srec.UnknownValueError:
            raise ValueError("Google не зміг розпізнати мовлення")
        except srec.RequestError as e:
            raise ConnectionError(f"Помилка сервісу Google: {e}")
        except Exception as e:
            raise RuntimeError(f"Внутрішня помилка Google Recognition: {e}")

    # GEMINI RECOGNITION ENGINE
    async def _recognize_gemini(self, audio_path: str, lang: str = None) -> str:
        if not GEMINI_AVAILABLE: raise RuntimeError("gemini_lib_missing")
        if not self.config["gemini_api_key"]: raise ValueError("gemini_token_missing")
        
        audio_file_resource = None
        try:
            genai.configure(api_key=self.config["gemini_api_key"])
            audio_file_resource = await utils.run_sync(genai.upload_file, path=audio_path)
            
            timeout = 300
            start_time = asyncio.get_event_loop().time()
            while audio_file_resource.state.name == "PROCESSING":
                if asyncio.get_event_loop().time() - start_time > timeout:
                    raise TimeoutError(f"Обробка файлу в Gemini зайняла більше {timeout}с")
                await asyncio.sleep(2)
                audio_file_resource = await utils.run_sync(genai.get_file, name=audio_file_resource.name)
            
            if audio_file_resource.state.name != "ACTIVE":
                raise RuntimeError(f"Файл в Gemini не оброблено (статус: {audio_file_resource.state.name})")

            model = genai.GenerativeModel(model_name="models/gemini-1.5-flash-latest")
            prompt = "Provide a precise transcription of the audio. Output only the text itself, with no extra commentary."
            response = await utils.run_sync(model.generate_content, [prompt, audio_file_resource], request_options={"timeout": 300})
            
            return response.text.strip()
        except Exception as e:
            logger.exception("Gemini recognition error")
            raise RuntimeError(f"Помилка обробки в Gemini: {e}")
        finally:
            if audio_file_resource:
                try:
                    await utils.run_sync(genai.delete_file, name=audio_file_resource.name)
                except Exception as del_err:
                    logger.warning(f"Gemini: Could not delete file {audio_file_resource.name}: {del_err}")

    # WHISPER RECOGNITION ENGINE
    async def _recognize_whisper(self, audio_path: str, lang: str = None) -> str:
        if not self.config["whisper_api_key"]: raise ValueError("whisper_token_missing")
        
        API_URL = "https://api-inference.huggingface.co/models/openai/whisper-large-v3"
        headers = {
            "Authorization": f"Bearer {self.config['whisper_api_key']}",
            "Content-Type": "audio/mpeg",
        }
        with open(audio_path, "rb") as f:
            data = f.read()

        response = await utils.run_sync(requests.post, API_URL, headers=headers, data=data)

        if response.status_code != 200:
            error_details = response.json().get("error", response.text)
            raise ConnectionError(f"({response.status_code}): {error_details}")
        
        return response.json().get("text", "").strip()

    # CORE MEDIA PROCESSING LOGIC
    async def _process_media(self, message: Message, engine: str, lang: str, status_msg: Message = None):
        target_message = await message.get_reply_message() or message
        
        if not target_message.media or (target_message.file.mime_type.split("/")[0] not in ["audio", "video"]):
            raise ValueError("no_reply")

        is_video = target_message.video is not None
        duration = getattr(target_message.media, 'duration', 0) or 0
        size_mb = (target_message.file.size or 0) / 1024 / 1024
        
        max_dur = self.config["max_duration_video"] if is_video else self.config["max_duration_voice"]
        min_dur = self.config["min_duration"]
        
        if duration and duration < min_dur: raise ValueError(self.strings("too_short").format(min_dur))
        if duration and duration > max_dur: raise ValueError("too_big")
        if size_mb > self.config["max_size_mb"]: raise ValueError("too_big")
        
        temp_dir = tempfile.mkdtemp()
        try:
            if status_msg: await status_msg.edit(self.strings("pref") + self.strings("downloading"))
            media_path = await target_message.download_media(file=os.path.join(temp_dir, "media"))
            
            if status_msg: await status_msg.edit(self.strings("pref") + self.strings("processing"))
            
            # Prepare a universal audio format (mp3 for Whisper, wav for Google)
            audio_for_api = os.path.join(temp_dir, "audio.wav" if engine == "google" else "audio.mp3")
            
            if is_video:
                with VideoFileClip(media_path) as clip:
                    if clip.audio is None: raise ValueError("audio_extract_error")
                    await utils.run_sync(clip.audio.write_audiofile, audio_for_api, logger=None)
            else:
                segment = await utils.run_sync(auds.from_file, media_path)
                await utils.run_sync(segment.export, audio_for_api, format="wav" if engine == "google" else "mp3")

            if status_msg: await status_msg.edit(self.strings("pref") + self.strings("recognizing"))

            if engine == "google": return await self._recognize_google(audio_for_api, lang)
            if engine == "gemini": return await self._recognize_gemini(audio_for_api)
            if engine == "whisper": return await self._recognize_whisper(audio_for_api)

        finally:
            for f in os.listdir(temp_dir): os.remove(os.path.join(temp_dir, f))
            os.rmdir(temp_dir)

    # COMMAND HANDLER
    async def _handle_recognition_command(self, message: Message, engine: str, lang: str = None):
        status_msg = await utils.answer(message, self.strings("pref") + self.strings("processing"))
        try:
            recognized_text = await self._process_media(message, engine, lang, status_msg)
            if not recognized_text: raise RuntimeError("Результат розпізнавання порожній.")
            
            await utils.answer(status_msg, self.strings("pref") + self.strings("recognized").format(recognized_text))
        except Exception as e:
            error_key = str(e)
            source = engine.capitalize()
            if engine == 'whisper': source = "Whisper"

            text = self.strings("recognition_error")
            if error_key in ["no_reply", "too_big", "audio_extract_error", "gemini_token_missing", "gemini_lib_missing", "whisper_token_missing"] or "too_short" in error_key:
                text = self.strings(error_key.split('(')[0].strip()) if '(' in error_key else self.strings(error_key)
            elif isinstance(e, (ConnectionError, TimeoutError)):
                text = self.strings("api_error").format(source=source, error=error_key)
            elif isinstance(e, RuntimeError):
                text = self.strings("api_error").format(source=source, error=error_key)

            await utils.answer(status_msg, self.strings("pref") + text)

    # MANUAL RECOGNITION COMMANDS
    @loader.owner
    async def vua(self, m: Message):
        """<відповідь> - Розпізнати українською (Google)"""
        await self._handle_recognition_command(m, "google", "uk-UA")

    @loader.owner
    async def vru(self, m: Message):
        """<відповідь> - Розпізнати російською (Google)"""
        await self._handle_recognition_command(m, "google", "ru-RU")

    @loader.owner
    async def ven(self, m: Message):
        """<відповідь> - Розпізнати англійською (Google)"""
        await self._handle_recognition_command(m, "google", "en-US")

    @loader.owner
    async def vai(self, m: Message):
        """<відповідь> - Розпізнати мовлення (Gemini AI)"""
        await self._handle_recognition_command(m, "gemini")

    @loader.owner
    async def wh(self, m: Message):
        """<відповідь> - Розпізнати мовлення (Whisper)"""
        await self._handle_recognition_command(m, "whisper")

    # AUTO RECOGNITION COMMANDS
    async def _toggle_auto_recog(self, message: Message, engine: str, lang: str = None):
        chat_id = str(utils.get_chat_id(message))
        current = self._auto_recog_settings.get(chat_id)
        new = {"engine": engine, "lang": lang}
        
        if current == new:
            self._auto_recog_settings.pop(chat_id)
            text = self.strings("auto_off")
        else:
            if engine == "gemini":
                if not GEMINI_AVAILABLE: return await utils.answer(message, self.strings("pref") + self.strings("gemini_lib_missing"))
                if not self.config["gemini_api_key"]: return await utils.answer(message, self.strings("pref") + self.strings("gemini_token_missing"))
            if engine == "whisper":
                if not self.config["whisper_api_key"]: return await utils.answer(message, self.strings("pref") + self.strings("whisper_token_missing"))
            
            self._auto_recog_settings[chat_id] = new
            engine_map = {"google": self.strings("google_lang").format(lang), "gemini": self.strings("gemini"), "whisper": self.strings("whisper")}
            text = self.strings("auto_on").format(engine=engine_map[engine])

        self._save_auto_recog_settings()
        await utils.answer(message, self.strings("pref") + text)

    @loader.owner
    async def autoua(self, m: Message):
        """Перемкнути авто-розпізнавання українською (Google)"""
        await self._toggle_auto_recog(m, "google", "uk-UA")

    @loader.owner
    async def autoru(self, m: Message):
        """Перемкнути авто-розпізнавання російською (Google)"""
        await self._toggle_auto_recog(m, "google", "ru-RU")

    @loader.owner
    async def autoen(self, m: Message):
        """Перемкнути авто-розпізнавання англійською (Google)"""
        await self._toggle_auto_recog(m, "google", "en-US")

    @loader.owner
    async def autoai(self, m: Message):
        """Перемкнути авто-розпізнавання (Gemini AI)"""
        await self._toggle_auto_recog(m, "gemini")

    @loader.owner
    async def autowh(self, m: Message):
        """Перемкнути авто-розпізнавання (Whisper)"""
        await self._toggle_auto_recog(m, "whisper")
    
    # WATCHER FOR AUTO-RECOGNITION
    @loader.watcher(only_media=True, no_cmd=True)
    async def watcher(self, message: Message):
        chat_id = str(utils.get_chat_id(message))
        settings = self._auto_recog_settings.get(chat_id)
        if not settings or not isinstance(message, Message): return

        if message.sender_id == self._me_id or (message.sender_id in self.config["ignore_users"]): return
        if not message.media or (message.file.mime_type.split('/')[0] not in ['audio', 'video']): return
        if getattr(message, 'gif', False): return

        status_msg = None
        try:
            # For watcher, we send a reply, which will be edited with the result or an error (if not silent)
            status_msg = await message.reply(self.strings("pref") + self.strings("processing"))
            recognized_text = await self._process_media(message, settings["engine"], settings["lang"], status_msg)
            
            if recognized_text:
                await status_msg.edit(self.strings("pref") + self.strings("recognized").format(recognized_text))
            else:
                await status_msg.delete() # If recognition is empty, delete the status message

        except Exception as e:
            logger.warning(f"AuthorVTT Watcher Error: {e}")
            if status_msg and not self.config["silent"]:
                # The _handle_recognition_command has similar logic we can reuse for error formatting
                error_key = str(e)
                source = settings['engine'].capitalize()
                if settings['engine'] == 'whisper': source = "Whisper"
                
                text = self.strings("recognition_error")
                if error_key in ["no_reply", "too_big", "audio_extract_error"] or "too_short" in error_key:
                     text = self.strings(error_key.split('(')[0].strip()) if '(' in error_key else self.strings(error_key)
                elif isinstance(e, (ConnectionError, TimeoutError, RuntimeError)):
                    text = self.strings("api_error").format(source=source, error=error_key)
                
                await status_msg.edit(self.strings("pref") + text)
            elif status_msg:
                await status_msg.delete() # If silent mode, just delete the "processing" message
    
    # GUIDE COMMANDS
    @loader.command()
    async def geminiguide(self, message: Message):
        """Інструкція для отримання API ключа Gemini"""
        await utils.answer(message, self.strings('gemini_instructions'))

    @loader.command()
    async def whguide(self, message: Message):
        """Інструкція для отримання API ключа Hugging Face"""
        await utils.answer(message, self.strings('whisper_instructions'))
