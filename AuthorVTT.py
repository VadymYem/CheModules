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
from telethon.errors.rpcerrorlist import UserAlreadyParticipantError
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
        "no_reply": "🫠 Дайте відповідь на аудіо/голосове/відео.",
        "audio_extract_error": "🚫 Помилка вилучення аудіо.",
        "conversion_error": "🚫 Помилка конвертації аудіо.",
        "recognition_error": "🚫 <b>Помилка розпізнавання!</b>",
        "api_error": "🚫 <b>Помилка API ({source}):</b> {error}",
        "too_big": "🫥 <b>Медіафайл завеликий або задовгий.</b>",
        "too_short": "🤏 <b>Медіафайл закороткий (мін. {}с).</b>",

        "google_lang": "Google ({})",
        "gemini": "Gemini (AI)",
        "whisper": "Whisper",

        "auto_on": "✅ <b>Авто-розпізнавання ({engine}) увімкнено.</b>",
        "auto_off": "⛔️ <b>Авто-розпізнавання вимкнено.</b>",

        "cfg_gemini_key": "Ключ API Google AI Studio (Gemini).",
        "cfg_whisper_key": "Ключ API Hugging Face (для Whisper).",
        "cfg_ignore_users": "Список ID користувачів для ігнорування.",
        "cfg_silent": "Тихий режим (без помилок в авто-режимі).",
        "cfg_max_duration_voice": "Макс. тривалість (сек) для голосових/аудіо.",
        "cfg_max_duration_video": "Макс. тривалість (сек) для відео.",
        "cfg_max_size_mb": "Макс. розмір файлу (МБ).",
        "cfg_min_duration": "Мін. тривалість (сек) для розпізнавання.",

        "gemini_token_missing": "🚫 <b>Відсутній API-ключ Gemini.</b>\nНалаштуйте в <code>.config</code>. Інфо: <code>.geminiguide</code>.",
        "gemini_lib_missing": "🚫 <b>Відсутня бібліотека <code>google-generativeai</code>.</b>",
        "whisper_token_missing": "🚫 <b>Відсутній API-ключ Hugging Face.</b>\nНалаштуйте в <code>.config</code>. Інфо: <code>.whguide</code>.",

        "gemini_instructions": "👩‍🎓 <b>Як отримати API-ключ Gemini:</b>\n<b>1. Відкрийте:</b> <a href=\"https://aistudio.google.com/app/apikey\">aistudio.google.com</a>\n<b>2. Увійдіть та натисніть 'Create API key'.</b>\n<b>3. Скопіюйте ключ та вставте в конфіг модуля.</b>",
        "whisper_instructions": "👩‍🎓 <b>Як отримати API-ключ для Whisper:</b>\n<b>1. Відкрийте:</b> <a href=\"https://huggingface.co/settings/tokens\">huggingface.co/settings/tokens</a>\n<b>2. Увійдіть та натисніть 'New Token'.</b>\n<b>3. Виберіть роль 'read' та скопіюйте токен.</b>",
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue("gemini_api_key", None, lambda: self.strings["cfg_gemini_key"], validator=loader.validators.Hidden()),
            loader.ConfigValue("whisper_api_key", None, lambda: self.strings["cfg_whisper_key"], validator=loader.validators.Hidden()),
            loader.ConfigValue("ignore_users", [], lambda: self.strings["cfg_ignore_users"], validator=loader.validators.Series(validator=loader.validators.TelegramID())),
            loader.ConfigValue("silent", False, lambda: self.strings["cfg_silent"], validator=loader.validators.Boolean()),
            loader.ConfigValue("max_duration_voice", 300, lambda: self.strings["cfg_max_duration_voice"], validator=loader.validators.Integer(minimum=10)),
            loader.ConfigValue("max_duration_video", 120, lambda: self.strings["cfg_max_duration_video"], validator=loader.validators.Integer(minimum=10)),
            loader.ConfigValue("max_size_mb", 25, lambda: self.strings["cfg_max_size_mb"], validator=loader.validators.Integer(minimum=1)),
            loader.ConfigValue("min_duration", 2, lambda: self.strings["cfg_min_duration"], validator=loader.validators.Integer(minimum=1)),
        )

    async def client_ready(self, client, db):
        self.client = client
        self.db = db
        self._me_id = (await client.get_me()).id
        self._auto_recog_settings = self.db.get(self.strings["name"], KEY_AUTO_RECOG, {})
        if GEMINI_AVAILABLE and self.config["gemini_api_key"]:
            try:
                genai.configure(api_key=self.config["gemini_api_key"])
            except Exception as e:
                logger.error(f"AuthorVTT: Gemini API configure error: {e}")
        for channel in ["wsinfo", "BlazeFtg"]:
            try:
                await client(JoinChannelRequest(channel))
            except UserAlreadyParticipantError:
                pass
            except Exception as e:
                logger.warning(f"AuthorVTT: Can't join {channel}: {e}")

    # RECOGNITION ENGINES
    async def _recognize_google(self, path: str, lang: str) -> str:
        r = srec.Recognizer()
        with srec.AudioFile(path) as source:
            audio = r.record(source)
        return await utils.run_sync(r.recognize_google, audio, language=lang)

    async def _recognize_gemini(self, path: str) -> str:
        if not GEMINI_AVAILABLE: raise RuntimeError("gemini_lib_missing")
        if not self.config["gemini_api_key"]: raise ValueError("gemini_token_missing")
        
        file = None
        try:
            genai.configure(api_key=self.config["gemini_api_key"])
            file = await utils.run_sync(genai.upload_file, path=path)
            model = genai.GenerativeModel(model_name="models/gemini-1.5-flash-latest")
            prompt = "Provide a precise transcription of the audio. Output only the text itself."
            response = await utils.run_sync(model.generate_content, [prompt, file], request_options={"timeout": 300})
            return response.text.strip()
        finally:
            if file: await utils.run_sync(genai.delete_file, name=file.name)

    async def _recognize_whisper(self, path: str) -> str:
        if not self.config["whisper_api_key"]: raise ValueError("whisper_token_missing")
        API_URL = "https://api-inference.huggingface.co/models/openai/whisper-large-v3"
        headers = {"Authorization": f"Bearer {self.config['whisper_api_key']}", "Content-Type": "audio/mpeg"}
        with open(path, "rb") as f: data = f.read()
        r = await utils.run_sync(requests.post, API_URL, headers=headers, data=data)
        if r.status_code != 200: raise ConnectionError(f"({r.status_code}): {r.json().get('error', r.text)}")
        return r.json().get("text", "").strip()

    # CORE LOGIC
    async def _process_media(self, msg: Message, engine: str, lang: str, status: Message):
        target = await msg.get_reply_message() or msg
        if not target.media or target.file.mime_type.split("/")[0] not in ["audio", "video"]:
            raise ValueError("no_reply")

        is_video = target.video is not None
        duration = getattr(target.media, 'duration', 0) or 0
        
        max_dur = self.config["max_duration_video"] if is_video else self.config["max_duration_voice"]
        min_dur = self.config["min_duration"]
        
        if duration and duration < min_dur: raise ValueError(self.strings["too_short"].format(min_dur))
        if duration and duration > max_dur: raise ValueError("too_big")
        if (target.file.size or 0) / 1024 / 1024 > self.config["max_size_mb"]: raise ValueError("too_big")
        
        tmp = tempfile.mkdtemp()
        try:
            await status.edit(self.strings["pref"] + self.strings["downloading"])
            media = await target.download_media(file=os.path.join(tmp, "media"))
            await status.edit(self.strings["pref"] + self.strings["processing"])
            
            api_format = "wav" if engine == "google" else "mp3"
            api_audio = os.path.join(tmp, f"audio.{api_format}")
            
            segment = await utils.run_sync(auds.from_file, media)
            await utils.run_sync(segment.export, api_audio, format=api_format)

            await status.edit(self.strings["pref"] + self.strings["recognizing"])

            if engine == "google": return await self._recognize_google(api_audio, lang)
            if engine == "gemini": return await self._recognize_gemini(api_audio)
            if engine == "whisper": return await self._recognize_whisper(api_audio)
        finally:
            for f in os.listdir(tmp): os.remove(os.path.join(tmp, f))
            os.rmdir(tmp)

    async def _format_error(self, e: Exception, engine: str) -> str:
        key = str(e)
        source_map = {"google": "Google", "gemini": "Gemini", "whisper": "Whisper"}
        
        if key in self.strings: return self.strings(key)
        if "too_short" in key: return key
        if isinstance(e, (ConnectionError, TimeoutError)):
            return self.strings("api_error").format(source=source_map.get(engine, "API"), error=key)
        
        logger.exception("Recognition error")
        return self.strings("recognition_error")

    # COMMANDS
    async def _run_command(self, m: Message, engine: str, lang: str = None):
        status = await utils.answer(m, self.strings("pref") + self.strings("processing"))
        try:
            text = await self._process_media(m, engine, lang, status)
            if not text: raise RuntimeError("Результат розпізнавання порожній.")
            await utils.answer(status, self.strings("pref") + self.strings("recognized").format(text))
        except Exception as e:
            await utils.answer(status, self.strings("pref") + await self._format_error(e, engine))
        if m.out: await m.delete()

    async def vua(self, m: Message):
        """<відп> - Розпізнати українською (Google)"""
        await self._run_command(m, "google", "uk-UA")

    async def vru(self, m: Message):
        """<відп> - Розпізнати російською (Google)"""
        await self._run_command(m, "google", "ru-RU")

    async def ven(self, m: Message):
        """<відп> - Розпізнати англійською (Google)"""
        await self._run_command(m, "google", "en-US")

    async def vai(self, m: Message):
        """<відп> - Розпізнати мовлення (Gemini AI)"""
        await self._run_command(m, "gemini")

    async def wh(self, m: Message):
        """<відп> - Розпізнати мовлення (Whisper)"""
        await self._run_command(m, "whisper")

    # AUTO-TOGGLE COMMANDS
    async def _toggle_auto(self, m: Message, engine: str, lang: str = None):
        chat_id = str(utils.get_chat_id(m))
        new = {"engine": engine, "lang": lang}

        if self._auto_recog_settings.get(chat_id) == new:
            self._auto_recog_settings.pop(chat_id)
            text = self.strings("auto_off")
        else:
            if engine == "gemini" and not self.config["gemini_api_key"]:
                return await utils.answer(m, self.strings("pref") + self.strings("gemini_token_missing"))
            if engine == "whisper" and not self.config["whisper_api_key"]:
                return await utils.answer(m, self.strings("pref") + self.strings("whisper_token_missing"))
            
            self._auto_recog_settings[chat_id] = new
            engine_map = {"google": self.strings("google_lang").format(lang), "gemini": self.strings("gemini"), "whisper": self.strings("whisper")}
            text = self.strings("auto_on").format(engine=engine_map[engine])

        self.db.set(self.strings["name"], KEY_AUTO_RECOG, self._auto_recog_settings)
        await utils.answer(m, self.strings("pref") + text)

    async def autoua(self, m: Message):
        """Увімкнути/вимкнути авто-розпізнавання українською (Google)"""
        await self._toggle_auto(m, "google", "uk-UA")

    async def autoru(self, m: Message):
        """Увімкнути/вимкнути авто-розпізнавання російською (Google)"""
        await self._toggle_auto(m, "google", "ru-RU")

    async def autoen(self, m: Message):
        """Увімкнути/вимкнути авто-розпізнавання англійською (Google)"""
        await self._toggle_auto(m, "google", "en-US")

    async def autoai(self, m: Message):
        """Увімкнути/вимкнути авто-розпізнавання (Gemini AI)"""
        await self._toggle_auto(m, "gemini")

    async def autowh(self, m: Message):
        """Увімкнути/вимкнути авто-розпізнавання (Whisper)"""
        await self._toggle_auto(m, "whisper")

    # WATCHER
    @loader.watcher(only_media=True, no_cmd=True)
    async def watcher(self, message: Message):
        chat_id = str(utils.get_chat_id(message))
        settings = self._auto_recog_settings.get(chat_id)
        if not settings or not isinstance(message, Message): return
        if message.sender_id == self._me_id or message.sender_id in self.config["ignore_users"]: return
        if not message.media or message.file.mime_type.split('/')[0] not in ['audio', 'video'] or getattr(message, 'gif', False): return

        status = None
        try:
            status = await message.reply(self.strings("pref") + self.strings("processing"))
            text = await self._process_media(message, settings["engine"], settings["lang"], status)
            if text: await status.edit(self.strings("pref") + self.strings("recognized").format(text))
            else: await status.delete()
        except Exception as e:
            if status and not self.config["silent"]:
                await status.edit(self.strings("pref") + await self._format_error(e, settings["engine"]))
            elif status: await status.delete()

    # GUIDES
    async def geminiguide(self, m: Message):
        """Інструкція для отримання API ключа Gemini"""
        await utils.answer(m, self.strings('gemini_instructions'))

    async def whguide(self, m: Message):
        """Інструкція для отримання API ключа для Whisper"""
        await utils.answer(m, self.strings('whisper_instructions'))
