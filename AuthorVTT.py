# meta developer: @BlazeFtg / @Author_Che
# requires: pydub speechRecognition moviepy telethon google-generativeai pillow

from io import BytesIO
import os
import tempfile
import logging
import base64
import asyncio

import speech_recognition as srec
from pydub import AudioSegment as auds
from moviepy.editor import VideoFileClip
from telethon.tl.types import (
    DocumentAttributeVideo,
    Message,
    DocumentAttributeAudio,
)
from telethon.errors.rpcerrorlist import MessageNotModifiedError # Додано для обробки виключення

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

from .. import loader, utils

logger = logging.getLogger(__name__)

KEY_AUTO_RECOG = "auto_recognition_chats_author_vtt"

@loader.tds
class AuthorVTTModEnhanced(loader.Module):
    """Розпізнавання голосу через Google Recognition та Gemini (AI Studio) з авто-режимом. AuthorVTT"""
    strings = {
        "name": "AuthorVTT: Голос в Текст",
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
        "too_big": "🫥 <b>Медіафайл завеликий або задовгий для розпізнавання.</b> (Діють ліміти на тривалість/розмір)",
        "google_lang": "Google ({})",
        "gemini": "Gemini (авто-мова)",
        "auto_on": "✅ <b>Автоматичне розпізнавання ({engine}) увімкнено в цьому чаті.</b>",
        "auto_off": "⛔️ <b>Автоматичне розпізнавання вимкнено в цьому чаті.</b>",

        "cfg_gemini_key": "Ключ API Google AI Studio (Gemini). Отримати з https://aistudio.google.com/app/apikey",
        "cfg_ignore_users": "Список ID користувачів (крім себе) для ігнорування в авто-розпізнаванні.",
        "cfg_silent": "Тихий режим для помилок авто-розпізнавання (без повідомлень про помилки).",
        "cfg_max_duration_voice": "Макс. тривалість (секунди) для авто-розпізнавання голосових/аудіо.",
        "cfg_max_duration_video": "Макс. тривалість (секунди) для авто-розпізнавання відео.",
        "cfg_max_size_mb": "Макс. розмір файлу (МБ) для авто-розпізнавання.",

        "gemini_token_missing": (
            "<b><emoji document_id=5980953710157632545>❌</emoji>Відсутній API-ключ Google AI (Gemini).</b>\n"
            "Налаштуйте його через <code>.config</code> команду модуля.\n"
            "<i>Див. <code>.geminiguide</code> для інструкцій.</i>"
        ),
         "gemini_lib_missing": (
            "<b><emoji document_id=5980953710157632545>❌</emoji>Відсутня бібліотека `google-generativeai`.</b>\n"
            "Встановіть її: <code>.pip install google-generativeai</code> та перезапустіть Hikka."
        ),
        "gemini_instructions": (
            "<emoji document_id=5238154170174820439>👩‍🎓</emoji> <b>Як отримати API-ключ Google AI (Gemini):</b>\n"
            "<b>1. Відкрийте Google AI Studio:</b> <a href=\"https://aistudio.google.com/app/apikey\">aistudio.google.com/app/apikey</a> <emoji document_id=4904848288345228262>👤</emoji>\n"
            "<b>2. Увійдіть за допомогою свого облікового запису Google.</b>\n"
            "<b>3. Натисніть 'Create API key in new project' (Створити API-ключ у новому проекті).</b> <emoji document_id=5431757929940273672>➕</emoji>\n"
            "<b>4. Скопіюйте згенерований API-ключ.</b> <emoji document_id=4916036072560919511>✅</emoji>\n"
            "<b>5. Використайте <code>.config</code> в Hikka, знайдіть цей модуль та вставте ключ у поле 'Gemini api key'.</b>"
        ),
    }

    strings_ru = {
        "_cls_doc": "Распознавание голоса через Google Recognition и Gemini (AI Studio) с авто-режимом. AuthorVTT",
        "name": "AuthorVTT: Голос в Текст",
        "pref": "<b>🎙️ AuthorVTT:</b> ",
        "processing": "⏳ Обработка...",
        "downloading": "📥 Загрузка...",
        "recognizing": "🗣️ Распознавание...",
        "recognized": "💬 <b>Распознано:</b>\n<i>{}</i>",
        "no_reply": "🫠 Ответьте на аудио/голосовое/видео сообщение.",
        "audio_extract_error": "🚫 Ошибка извлечения аудио из видео.",
        "conversion_error": "🚫 Ошибка конвертации аудио.",
        "recognition_error": "🚫 <b>Ошибка распознавания!</b> Возможны проблемы с API или определением языка.",
        "api_error": "🚫 <b>Ошибка API ({source}):</b> {error}",
        "too_big": "🫥 <b>Медиафайл слишком большой или длинный для распознавания.</b> (Применяются лимиты на длительность/размер)",
        "google_lang": "Google ({})",
        "gemini": "Gemini (авто-язык)",
        "auto_on": "✅ <b>Автоматическое распознавание ({engine}) включено в этом чате.</b>",
        "auto_off": "⛔️ <b>Автоматическое распознавание отключено в этом чате.</b>",
        "cfg_gemini_key": "Ключ API Google AI Studio (Gemini). Получить с https://aistudio.google.com/app/apikey",
        "cfg_ignore_users": "Список ID пользователей (кроме себя) для игнорирования в авто-распознавании.",
        "cfg_silent": "Тихий режим для ошибок авто-распознавания (без сообщений об ошибках).",
        "cfg_max_duration_voice": "Макс. длительность (секунды) для авто-распознавания голосовых/аудио.",
        "cfg_max_duration_video": "Макс. длительность (секунды) для авто-распознавания видео.",
        "cfg_max_size_mb": "Макс. размер файла (МБ) для авто-распознавания.",
        "gemini_token_missing": "<b><emoji document_id=5980953710157632545>❌</emoji>Отсутствует API-ключ Google AI (Gemini).</b>\nНастройте его через <code>.config</code>.\n<i>См. <code>.geminiguide</code> для инструкций.</i>",
        "gemini_lib_missing": "<b><emoji document_id=5980953710157632545>❌</emoji>Отсутствует библиотека `google-generativeai`.</b>\nУстановите ее: <code>.pip install google-generativeai</code> и перезапустите Hikka.",
        "gemini_instructions": "<emoji document_id=5238154170174820439>👩‍🎓</emoji> <b>Как получить API-ключ Google AI (Gemini):</b>\n<b>1. Откройте Google AI Studio:</b> <a href=\"https://aistudio.google.com/app/apikey\">aistudio.google.com/app/apikey</a> <emoji document_id=4904848288345228262>👤</emoji>\n<b>2. Войдите с помощью своего аккаунта Google.</b>\n<b>3. Нажмите 'Create API key in new project'.</b> <emoji document_id=5431757929940273672>➕</emoji>\n<b>4. Скопируйте сгенерированный API-ключ.</b> <emoji document_id=4916036072560919511>✅</emoji>\n<b>5. Используйте <code>.config</code> в Hikka, найдите этот модуль и вставьте ключ в 'Gemini api key'.</b>",
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "gemini_api_key",
                None,
                lambda: self.strings("cfg_gemini_key"),
                validator=loader.validators.Hidden(),
            ),
            loader.ConfigValue(
                "ignore_users",
                [],
                lambda: self.strings("cfg_ignore_users"),
                validator=loader.validators.Series(validator=loader.validators.TelegramID())
            ),
            loader.ConfigValue(
                "silent",
                False,
                lambda: self.strings("cfg_silent"),
                validator=loader.validators.Boolean()
            ),
             loader.ConfigValue(
                "max_duration_voice",
                300,
                lambda: self.strings("cfg_max_duration_voice"),
                validator=loader.validators.Integer(minimum=10)
            ),
            loader.ConfigValue(
                "max_duration_video",
                120,
                lambda: self.strings("cfg_max_duration_video"),
                validator=loader.validators.Integer(minimum=10)
            ),
            loader.ConfigValue(
                "max_size_mb",
                20,
                lambda: self.strings("cfg_max_size_mb"),
                validator=loader.validators.Integer(minimum=1)
            ),
        )
        self._auto_recog_settings = {}
        self._me_id = -1

    async def client_ready(self, client, db):
        self.client = client
        self.db = db
        self_user = await client.get_me()
        if self_user:
            self._me_id = self_user.id
        else:
            logger.error("AuthorVTT: Could not get self user ID during client_ready.")

        self._auto_recog_settings = self.db.get(self.strings("name"), KEY_AUTO_RECOG, {})

        if GEMINI_AVAILABLE and self.config["gemini_api_key"]:
             try:
                 current_gemini_key = getattr(getattr(genai, '_client', None), 'api_key', None)
                 if not current_gemini_key or current_gemini_key != self.config["gemini_api_key"]:
                    genai.configure(api_key=self.config["gemini_api_key"])
                    logger.info("Gemini API configured successfully for AuthorVTT.")
                 else:
                    logger.info("Gemini API already configured with the current key for AuthorVTT.")
             except Exception as e:
                 logger.error(f"Failed to configure Gemini API for AuthorVTT: {e}")

    def _save_auto_recog_settings(self):
        self.db.set(self.strings("name"), KEY_AUTO_RECOG, self._auto_recog_settings)

    async def _recognize_google(self, audio_path: str, lang: str) -> str:
        recog = srec.Recognizer()
        try:
            with srec.AudioFile(audio_path) as audio_file:
                audio_content = recog.record(audio_file)
            return await utils.run_sync(recog.recognize_google, audio_content, language=lang)
        except srec.UnknownValueError: 
            raise ValueError("Google Speech Recognition could not understand audio")
        except srec.RequestError as e: 
            raise ConnectionError(f"Could not request results from Google: {e}")
        except Exception as e: 
            logger.exception("Google recognition internal error")
            raise RuntimeError(f"Google recognition internal error: {e}")

    async def _recognize_gemini(self, audio_path: str, lang: str = None) -> str:
        if not GEMINI_AVAILABLE:
             raise RuntimeError("gemini_lib_missing") 
        if not self.config["gemini_api_key"]:
            raise ValueError("gemini_token_missing") 

        audio_file = None 
        try:
            current_gemini_key = getattr(getattr(genai, '_client', None), 'api_key', None)
            if not current_gemini_key or current_gemini_key != self.config["gemini_api_key"]:
                genai.configure(api_key=self.config["gemini_api_key"])
                logger.info("Gemini API re-configured in _recognize_gemini.")

            logger.debug(f"Gemini: Uploading file {audio_path}")
            audio_file = await utils.run_sync(genai.upload_file, path=audio_path)
            logger.debug(f"Gemini: File {audio_file.name} uploaded, state: {audio_file.state.name}")

            upload_timeout = 300  
            start_time = asyncio.get_event_loop().time()
            while audio_file.state.name == "PROCESSING":
                if asyncio.get_event_loop().time() - start_time > upload_timeout:
                    logger.warning(f"Gemini: File {audio_file.name} processing timed out. Attempting delete.")
                    try: await utils.run_sync(genai.delete_file, name=audio_file.name)
                    except Exception as del_e: logger.error(f"Gemini: Failed to delete timed-out file: {del_e}")
                    raise TimeoutError(f"Gemini file processing timeout ({upload_timeout}s)")
                await asyncio.sleep(2) 
                audio_file = await utils.run_sync(genai.get_file, name=audio_file.name)
                logger.debug(f"Gemini: File {audio_file.name} state: {audio_file.state.name}")

            if audio_file.state.name == "FAILED":
                raise RuntimeError(f"Gemini file processing failed (state: {audio_file.state.name})")
            if audio_file.state.name != "ACTIVE":
                 raise RuntimeError(f"Gemini file not active (state: {audio_file.state.name})")

            model = genai.GenerativeModel(model_name="models/gemini-1.5-flash-latest")
            prompt = "Transcribe the audio file accurately." 
            logger.debug(f"Gemini: Sending request to model for file {audio_file.name}")
            response = await utils.run_sync(
                 model.generate_content, [prompt, audio_file], request_options={"timeout": 300} 
            )

            if not response.candidates:
                 safety_feedback = getattr(response, 'prompt_feedback', None)
                 block_reason = "Unknown safety block"
                 if safety_feedback and hasattr(safety_feedback, 'block_reason') and safety_feedback.block_reason:
                    block_reason = safety_feedback.block_reason.name 
                 logger.warning(f"Gemini: Response blocked. Reason: {block_reason}, Feedback: {safety_feedback}")
                 raise RuntimeError(f"Gemini response blocked (Reason: {block_reason})")

            recognized_text = ""
            try:
                 recognized_text = response.text 
            except ValueError: 
                 if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
                     recognized_text = "".join(part.text for part in response.candidates[0].content.parts if hasattr(part, "text"))

            if not recognized_text.strip():
                logger.warning(f"Gemini: Returned empty text. Candidates: {response.candidates}")
                raise RuntimeError("Gemini returned empty text")

            return recognized_text.strip()

        except TimeoutError as e: 
             logger.error(f"Gemini: Timeout error: {e}")
             raise ConnectionError(str(e)) 
        except Exception as e:
            logger.exception(f"Gemini: General error in _recognize_gemini")
            if isinstance(e, (ValueError, RuntimeError, ConnectionError)) and (
                str(e) in ["gemini_token_missing", "gemini_lib_missing"] or
                "Gemini response blocked" in str(e) or
                "Gemini returned empty text" in str(e) or
                "Gemini file processing" in str(e)
            ):
                raise
            if audio_file and hasattr(audio_file, 'name') and audio_file.state.name == "ACTIVE":
                logger.info(f"Gemini: Attempting to delete file {audio_file.name} after error: {e}")
                try: await utils.run_sync(genai.delete_file, name=audio_file.name)
                except Exception as del_e: logger.warning(f"Gemini: Could not delete file {audio_file.name} after error: {del_e}")
            raise RuntimeError(f"Gemini processing error: {e}") 
        finally:
             if audio_file and hasattr(audio_file, 'name') and audio_file.state.name == "ACTIVE":
                 logger.debug(f"Gemini: Deleting file {audio_file.name} in finally block.")
                 try:
                     await utils.run_sync(genai.delete_file, name=audio_file.name)
                     logger.info(f"Gemini: Successfully deleted file {audio_file.name}")
                 except Exception as delete_err:
                     logger.warning(f"Gemini: Could not delete file {audio_file.name} in finally: {delete_err}")


    async def _process_media(
        self,
        message: Message,
        engine: str,
        lang: str = None,
        suppress_status_messages: bool = False
    ) -> str:
        reply = await message.get_reply_message()
        target_message = reply or message

        if not target_message or not target_message.media or \
           (target_message.file.mime_type.split("/")[0] not in ["audio", "video"]):
            raise ValueError("no_reply") 

        is_video = target_message.video is not None
        duration = 0
        size_mb = (target_message.file.size or 0) / 1024 / 1024
        max_duration_cfg = self.config["max_duration_voice"] 

        try:
            doc_attrs, attr_type_cls = (None, None)
            if is_video and target_message.video and hasattr(target_message.video, 'attributes'):
                doc_attrs = target_message.video.attributes
                max_duration_cfg = self.config["max_duration_video"]
                attr_type_cls = DocumentAttributeVideo
            elif (target_message.audio or target_message.voice) and \
                 target_message.document and hasattr(target_message.document, 'attributes'):
                doc_attrs = target_message.document.attributes
                max_duration_cfg = self.config["max_duration_voice"]
                attr_type_cls = DocumentAttributeAudio

            if doc_attrs and attr_type_cls:
                media_attrs = next((attr for attr in doc_attrs if isinstance(attr, attr_type_cls)), None)
                if media_attrs and hasattr(media_attrs, 'duration'):
                    duration = media_attrs.duration
        except Exception as e:
             logger.warning(f"Could not get media duration attributes: {e}")
        
        if (duration != 0 and duration > max_duration_cfg) or \
           (size_mb > self.config["max_size_mb"]):
             logger.warning(f"Media too large/long: duration={duration}s (max={max_duration_cfg}s), size={size_mb:.2f}MB (max={self.config['max_size_mb']}MB)")
             raise ValueError("too_big") 

        status_msg = None
        if not suppress_status_messages:
            status_msg = await utils.answer(message, self.strings("pref") + self.strings("downloading"))

        temp_dir = tempfile.mkdtemp()
        original_media_path = None
        media_name = target_message.file.name or f"media_{target_message.id}.{getattr(target_message.file, 'ext', 'file') or 'file'}"
        
        try:
            original_media_path = await target_message.download_media(file=os.path.join(temp_dir, media_name))
            if not suppress_status_messages and status_msg:
                await status_msg.edit(self.strings("pref") + self.strings("processing"))
            
            audio_source_path_for_api = original_media_path 
            if engine == "google": 
                wav_audio_path = os.path.join(temp_dir, "audio.wav")
                if is_video:
                    logger.debug(f"Extracting audio from video to WAV for Google: {original_media_path}")
                    with VideoFileClip(original_media_path) as video_clip:
                         if video_clip.audio is None:
                              raise ValueError(self.strings("audio_extract_error")) 
                         await utils.run_sync(video_clip.audio.write_audiofile, wav_audio_path, codec="pcm_s16le", logger=None)
                else: 
                    logger.debug(f"Converting audio to WAV for Google: {original_media_path}")
                    audio_segment = await utils.run_sync(auds.from_file, original_media_path)
                    await utils.run_sync(audio_segment.export, wav_audio_path, format="wav")
                audio_source_path_for_api = wav_audio_path
            
            if not os.path.exists(audio_source_path_for_api): 
                 logger.error(f"Audio source for API does not exist: {audio_source_path_for_api}")
                 raise IOError(f"Audio source for API not found: {audio_source_path_for_api}")

            if not suppress_status_messages and status_msg:
                await status_msg.edit(self.strings("pref") + self.strings("recognizing"))

            recognized_text = ""
            if engine == "google":
                if not lang: raise ValueError("Language code required for Google engine") 
                recognized_text = await self._recognize_google(audio_source_path_for_api, lang)
            elif engine == "gemini":
                 recognized_text = await self._recognize_gemini(audio_source_path_for_api, lang) 
            else: 
                raise ValueError(f"Unknown recognition engine: {engine}") 

            if not suppress_status_messages and status_msg:
                pass 
            return recognized_text

        except (ValueError, RuntimeError, IOError, ConnectionError) as e:
            logger.warning(f"Error during media processing in _process_media: {e} (Type: {type(e)})")
            
            if not suppress_status_messages:
                error_display_text = str(e) 
                if str(e) == "no_reply": error_display_text = self.strings("no_reply")
                elif str(e) == "too_big": error_display_text = self.strings("too_big")
                elif str(e) == self.strings("audio_extract_error"): error_display_text = self.strings("audio_extract_error")
                elif str(e) == "gemini_token_missing": error_display_text = self.strings("gemini_token_missing")
                elif str(e) == "gemini_lib_missing": error_display_text = self.strings("gemini_lib_missing")
                elif isinstance(e, ConnectionError):
                    source = "API"
                    if "Google" in str(e): source = "Google API"
                    elif "Gemini" in str(e): source = "Gemini API"
                    error_display_text = self.strings("api_error").format(source=source, error=e)
                elif isinstance(e, IOError): 
                    error_display_text = self.strings("conversion_error") + f" ({e})"
                else: 
                    error_display_text = self.strings("recognition_error") + f" ({e})"
                
                try:
                     if status_msg: 
                         await status_msg.edit(self.strings("pref") + error_display_text)
                     else: 
                         await utils.answer(message, self.strings("pref") + error_display_text)
                except Exception as display_err: 
                     logger.error(f"Failed to display error to user: {display_err}")
            raise 
        finally:
            try:
                for filename in os.listdir(temp_dir): 
                     file_path = os.path.join(temp_dir, filename)
                     if os.path.isfile(file_path) or os.path.islink(file_path):
                         os.unlink(file_path)
                os.rmdir(temp_dir) 
            except Exception as cleanup_err:
                logger.error(f"Failed to cleanup temp dir {temp_dir}: {cleanup_err}")


    async def _handle_recognition_command(self, message: Message, engine: str, lang: str = None):
        """Обробник для команд ручного розпізнавання - редагує повідомлення команди результатом."""

        # Helper function to safely edit the command message
        async def _edit_command_message(text_content: str):
            if message.out: # Can only edit our own outgoing messages
                try:
                    # Determine parse mode - Hikka often uses HTML.
                    # Use client's default or explicitly set to "html".
                    parse_html = None
                    # Check if client has parse_mode and it's not None/empty
                    if hasattr(self.client, 'parse_mode') and self.client.parse_mode: 
                        parse_html = self.client.parse_mode
                    
                    if not parse_html: # Default to HTML if not set or client.parse_mode is None/empty
                        parse_html = "html"
                        
                    await message.edit(text_content, parse_mode=parse_html)
                except MessageNotModifiedError:
                    pass # Message content is the same, no action needed
                except Exception as e_edit:
                    logger.error(f"Failed to edit message (ID: {message.id}) directly: {e_edit}")

        try:
            await _edit_command_message(self.strings("pref") + self.strings("processing"))

            recognized_text = await self._process_media(
                message,
                engine,
                lang,
                suppress_status_messages=True 
            )

            final_text_output = self.strings("recognized").format(recognized_text)
            await _edit_command_message(self.strings("pref") + final_text_output)

        except Exception as e:
            logger.warning(f"Error in _handle_recognition_command (engine: {engine}): {e} (Type: {type(e)})")
            
            error_message_text = ""
            error_key = str(e) 

            if error_key in self.strings: 
                try: error_message_text = self.strings(error_key).format(error=str(e)) 
                except KeyError: error_message_text = self.strings(error_key) 
            elif isinstance(e, ConnectionError): 
                source = "API" 
                if "Google" in str(e): source = "Google API"
                elif "Gemini" in str(e): source = "Gemini API"
                error_message_text = self.strings("api_error").format(source=source, error=str(e))
            elif isinstance(e, IOError): 
                 error_message_text = self.strings("conversion_error") + f" ({str(e)})"
            else: 
                error_message_text = self.strings("recognition_error") + f" ({str(e)})"
            
            try:
                await _edit_command_message(self.strings("pref") + error_message_text)
            except Exception as edit_final_error: 
                logger.error(f"Secondary log: Failed to edit command message with final error: {edit_final_error}")

    @loader.owner
    @loader.command(alias="vua", ru_doc=".vua <реплай> - Распознать украинский (Google)")
    async def vuacmd(self, message: Message):
        """Розпізнати українською (Google)"""
        await self._handle_recognition_command(message, "google", "uk-UA")

    @loader.owner
    @loader.command(alias="vru", ru_doc=".vru <реплай> - Распознать русский (Google)")
    async def vrucmd(self, message: Message):
        """Розпізнати російською (Google)"""
        await self._handle_recognition_command(message, "google", "ru-RU")

    @loader.owner
    @loader.command(alias="ven", ru_doc=".ven <реплай> - Распознать английский (Google)")
    async def vencmd(self, message: Message):
        """Розпізнати англійською (Google)"""
        await self._handle_recognition_command(message, "google", "en-US")

    @loader.owner
    @loader.command(alias="vai", ru_doc=".vai <реплай> - Распознать речь (Gemini, авто-язык)")
    async def vaicmd(self, message: Message):
        """Розпізнати мовлення (Gemini, авто-мова)"""
        await self._handle_recognition_command(message, "gemini")

    async def _toggle_auto_recog(self, message: Message, engine: str, lang: str = None):
        chat_id = utils.get_chat_id(message)
        chat_id_str = str(chat_id)
        current_setting = self._auto_recog_settings.get(chat_id_str)
        new_setting = {"engine": engine, "lang": lang}

        response_text_key = ""
        engine_name_display = engine.capitalize() 

        if current_setting == new_setting: 
            self._auto_recog_settings.pop(chat_id_str, None)
            response_text_key = "auto_off"
        else: 
            if engine == "gemini": 
                 if not GEMINI_AVAILABLE:
                      await utils.answer(message, self.strings("pref") + self.strings("gemini_lib_missing"))
                      return
                 if not self.config["gemini_api_key"]:
                      await utils.answer(message, self.strings("pref") + self.strings("gemini_token_missing"))
                      return

            self._auto_recog_settings[chat_id_str] = new_setting
            response_text_key = "auto_on"
            if engine == 'google' and lang: engine_name_display = self.strings('google_lang').format(lang)
            elif engine == 'gemini': engine_name_display = self.strings('gemini')
        
        self._save_auto_recog_settings()
        final_response_text = self.strings(response_text_key)
        if response_text_key == "auto_on":
            final_response_text = final_response_text.format(engine=engine_name_display)
        
        await utils.answer(message, self.strings("pref") + final_response_text)


    @loader.owner
    @loader.command(alias="autoua", ru_doc="Вкл/выкл авто-распознавание украинского (Google) в чате")
    async def autouacmd(self, message: Message):
        """Перемкнути авто-розпізнавання українською (Google) в чаті"""
        await self._toggle_auto_recog(message, "google", "uk-UA")

    @loader.owner
    @loader.command(alias="autoru", ru_doc="Вкл/выкл авто-распознавание русского (Google) в чате")
    async def autorucmd(self, message: Message):
        """Перемкнути авто-розпізнавання російською (Google) в чаті"""
        await self._toggle_auto_recog(message, "google", "ru-RU")

    @loader.owner
    @loader.command(alias="autoen", ru_doc="Вкл/выкл авто-распознавание английского (Google) в чате")
    async def autoencmd(self, message: Message):
        """Перемкнути авто-розпізнавання англійською (Google) в чаті"""
        await self._toggle_auto_recog(message, "google", "en-US")

    @loader.owner
    @loader.command(alias="autoai", ru_doc="Вкл/выкл авто-распознавание (Gemini, авто-язык) в чате")
    async def autoaicmd(self, message: Message):
        """Перемкнути авто-розпізнавання (Gemini, авто-мова) в чаті"""
        await self._toggle_auto_recog(message, "gemini")

    @loader.watcher(only_media=True, no_cmd=True)
    async def watcher(self, message: Message):
        if not isinstance(message, Message): return 
        chat_id = utils.get_chat_id(message)
        settings = self._auto_recog_settings.get(str(chat_id))
        if not settings: return 

        is_video = message.video is not None and not getattr(message, 'gif', False)
        is_audio = message.audio is not None
        is_voice = getattr(message, 'voice', None) is not None or \
                   (message.document and any(
                       isinstance(attr, DocumentAttributeAudio) and getattr(attr, 'voice', False)
                       for attr in getattr(message.document, 'attributes', [])
                   ))
        if not (is_video or is_audio or is_voice): return 

        sender = await message.get_sender()
        if not sender or sender.bot: return 
        if self._me_id != -1 and message.sender_id != self._me_id and message.sender_id in self.config["ignore_users"]:
            return

        engine, lang = settings["engine"], settings["lang"]
        logger.debug(f"AuthorVTT Watcher: Triggered for chat {chat_id} by {message.sender_id} (engine: {engine})")
        try:
            recognized_text = await self._process_media(message, engine, lang, suppress_status_messages=False)
            
            if recognized_text and recognized_text.strip(): 
                 await message.reply(self.strings("recognized").format(recognized_text))
            else:
                 logger.warning(f"AuthorVTT Watcher: Empty text received for chat {chat_id}. No reply sent.")

        except Exception as e:
            logger.warning(f"AuthorVTT Watcher: Error processing message in chat {chat_id} (engine {engine}): {e}. "
                           "Error display is handled by _process_media if not in silent mode.")

    @loader.command(ru_doc="Инструкция по получению API ключа Gemini")
    async def geminiguide(self, message: Message):
        """Інструкція для отримання API ключа Gemini"""
        await utils.answer(message, self.strings('gemini_instructions'))
