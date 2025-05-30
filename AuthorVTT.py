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
from telethon.errors.rpcerrorlist import ( # Оновлено для обробки виключень
    MessageNotModifiedError,
    UserAlreadyParticipantError,
    ChannelPrivateError,
    ChannelInvalidError,
)
from telethon.tl.functions.channels import JoinChannelRequest # Додано для підписки на канали

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
        "too_short": "🤏 <b>Медіафайл закороткий для розпізнавання.</b> (Налаштуйте мінімальну тривалість)", # NEW
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
        "cfg_min_duration_voice": "Мін. тривалість (секунди) для авто-розпізнавання голосових/аудіо (мін. 1).", # NEW
        "cfg_min_duration_video": "Мін. тривалість (секунди) для авто-розпізнавання відео (мін. 1).", # NEW

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
        "pref": "<b>🎙️ AuthorVTT\n</b> ",
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
        "too_short": "🤏 <b>Медиафайл слишком короткий для распознавания.</b> (Настройте минимальную длительность)", # NEW
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
        "cfg_min_duration_voice": "Мин. длительность (секунды) для авто-распознавания голосовых/аудио (мин. 1).", # NEW
        "cfg_min_duration_video": "Мин. длительность (секунды) для авто-распознавания видео (мин. 1).", # NEW
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
                300, # 5 minutes
                lambda: self.strings("cfg_max_duration_voice"),
                validator=loader.validators.Integer(minimum=10)
            ),
            loader.ConfigValue(
                "max_duration_video",
                120, # 2 minutes
                lambda: self.strings("cfg_max_duration_video"),
                validator=loader.validators.Integer(minimum=10)
            ),
            loader.ConfigValue(
                "max_size_mb",
                20,
                lambda: self.strings("cfg_max_size_mb"),
                validator=loader.validators.Integer(minimum=1)
            ),
            loader.ConfigValue( # NEW
                "min_duration_voice",
                2, # seconds
                lambda: self.strings("cfg_min_duration_voice"),
                validator=loader.validators.Integer(minimum=1)
            ),
            loader.ConfigValue( # NEW
                "min_duration_video",
                2, # seconds
                lambda: self.strings("cfg_min_duration_video"),
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
                 # Ensure genai is configured only once or if key changes
                 current_gemini_key = getattr(getattr(genai, '_client', None), 'api_key', None)
                 if not current_gemini_key or current_gemini_key != self.config["gemini_api_key"]:
                    genai.configure(api_key=self.config["gemini_api_key"])
                    logger.info("AuthorVTT: Gemini API configured successfully.")
                 else:
                    logger.info("AuthorVTT: Gemini API already configured with the current key.")
             except Exception as e:
                 logger.error(f"AuthorVTT: Failed to configure Gemini API: {e}")

        channels_to_join = ["wsinfo", "BlazeFtg"]
        for channel_username in channels_to_join:
            try:
                entity = await client.get_entity(channel_username)
                # Check if we are already a member might require more specific checks
                # For now, JoinChannelRequest handles UserAlreadyParticipantError
                logger.info(f"AuthorVTT: Attempting to join channel: @{channel_username}")
                await client(JoinChannelRequest(entity))
                logger.info(f"AuthorVTT: Successfully joined or already a member of @{channel_username}")
            except UserAlreadyParticipantError:
                logger.info(f"AuthorVTT: Already a participant in @{channel_username}")
            except (ChannelPrivateError, ChannelInvalidError) as e: # More specific errors
                logger.error(f"AuthorVTT: Could not join @{channel_username}: {type(e).__name__} - {e}")
            except Exception as e:
                logger.error(f"AuthorVTT: An unexpected error occurred while trying to join @{channel_username}: {e}")


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

    async def _recognize_gemini(self, audio_path: str, lang: str = None) -> str: # lang is not used by gemini here but kept for signature consistency
        if not GEMINI_AVAILABLE:
             raise RuntimeError("gemini_lib_missing")
        if not self.config["gemini_api_key"]:
            raise ValueError("gemini_token_missing")

        audio_file_resource = None # Renamed to avoid clash with genai.AudioFile
        try:
            # Re-check and configure API key if necessary
            current_gemini_key = getattr(getattr(genai, '_client', None), 'api_key', None)
            if not current_gemini_key or current_gemini_key != self.config["gemini_api_key"]:
                genai.configure(api_key=self.config["gemini_api_key"])
                logger.info("AuthorVTT: Gemini API re-configured in _recognize_gemini.")

            logger.debug(f"Gemini: Uploading file {audio_path}")
            # Use a different variable name for the uploaded file object
            audio_file_resource = await utils.run_sync(genai.upload_file, path=audio_path)
            logger.debug(f"Gemini: File {audio_file_resource.name} uploaded, state: {audio_file_resource.state.name}")

            upload_timeout = 300
            start_time = asyncio.get_event_loop().time()
            while audio_file_resource.state.name == "PROCESSING":
                if asyncio.get_event_loop().time() - start_time > upload_timeout:
                    logger.warning(f"Gemini: File {audio_file_resource.name} processing timed out. Attempting delete.")
                    try: await utils.run_sync(genai.delete_file, name=audio_file_resource.name)
                    except Exception as del_e: logger.error(f"Gemini: Failed to delete timed-out file during processing: {del_e}")
                    raise TimeoutError(f"Gemini file processing timeout ({upload_timeout}s)")
                await asyncio.sleep(2)
                audio_file_resource = await utils.run_sync(genai.get_file, name=audio_file_resource.name)
                logger.debug(f"Gemini: File {audio_file_resource.name} state: {audio_file_resource.state.name}")

            if audio_file_resource.state.name == "FAILED":
                raise RuntimeError(f"Gemini file processing failed (state: {audio_file_resource.state.name})")
            if audio_file_resource.state.name != "ACTIVE":
                 raise RuntimeError(f"Gemini file not active (state: {audio_file_resource.state.name})")

            model = genai.GenerativeModel(model_name="models/gemini-1.5-flash-latest")
            prompt = "Transcribe the audio file accurately. Provide only the transcribed text, without any additional comments or elaborations."
            logger.debug(f"Gemini: Sending request to model for file {audio_file_resource.name}")
            response = await utils.run_sync(
                 model.generate_content, [prompt, audio_file_resource], request_options={"timeout": 300}
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
            except ValueError: # Fallback for cases where .text might fail but parts exist
                 if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
                     recognized_text = "".join(part.text for part in response.candidates[0].content.parts if hasattr(part, "text"))

            if not recognized_text.strip():
                logger.warning(f"Gemini: Returned empty text. Candidates: {response.candidates}")
                # Consider if this should be an error or just an empty transcription
                raise RuntimeError("Gemini returned empty text") # Treating as an error for now

            return recognized_text.strip()

        except TimeoutError as e:
             logger.error(f"Gemini: Timeout error: {e}")
             raise ConnectionError(str(e)) # Propagate as ConnectionError for consistent API error handling
        except Exception as e:
            logger.exception(f"Gemini: General error in _recognize_gemini")
            # Re-raise specific, known exceptions to be handled by caller
            if isinstance(e, (ValueError, RuntimeError, ConnectionError)) and (
                str(e) in ["gemini_token_missing", "gemini_lib_missing"] or
                "Gemini response blocked" in str(e) or
                "Gemini returned empty text" in str(e) or # Ensure this is re-raised
                "Gemini file processing" in str(e) # Ensure this is re-raised
            ):
                raise
            # Attempt to delete the file if it was uploaded and is active before raising a generic error
            if audio_file_resource and hasattr(audio_file_resource, 'name') and audio_file_resource.state.name == "ACTIVE":
                logger.info(f"Gemini: Attempting to delete file {audio_file_resource.name} after error: {e}")
                try: await utils.run_sync(genai.delete_file, name=audio_file_resource.name)
                except Exception as del_e: logger.warning(f"Gemini: Could not delete file {audio_file_resource.name} after error: {del_e}")
            raise RuntimeError(f"Gemini processing error: {e}") # General catch-all
        finally:
             # Ensure file is deleted if it exists and is active
             if audio_file_resource and hasattr(audio_file_resource, 'name') and audio_file_resource.state.name == "ACTIVE":
                 logger.debug(f"Gemini: Deleting file {audio_file_resource.name} in finally block.")
                 try:
                     await utils.run_sync(genai.delete_file, name=audio_file_resource.name)
                     logger.info(f"Gemini: Successfully deleted file {audio_file_resource.name}")
                 except Exception as delete_err:
                     logger.warning(f"Gemini: Could not delete file {audio_file_resource.name} in finally: {delete_err}")


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

        # Determine max and min duration based on media type
        max_duration_cfg = self.config["max_duration_voice"]
        min_duration_cfg = self.config["min_duration_voice"] # NEW
        if is_video:
            max_duration_cfg = self.config["max_duration_video"]
            min_duration_cfg = self.config["min_duration_video"] # NEW

        try:
            doc_attrs, attr_type_cls = (None, None)
            if is_video and target_message.video and hasattr(target_message.video, 'attributes'):
                doc_attrs = target_message.video.attributes
                attr_type_cls = DocumentAttributeVideo
            elif (target_message.audio or target_message.voice) and \
                 target_message.document and hasattr(target_message.document, 'attributes'):
                doc_attrs = target_message.document.attributes
                attr_type_cls = DocumentAttributeAudio

            if doc_attrs and attr_type_cls:
                media_attrs = next((attr for attr in doc_attrs if isinstance(attr, attr_type_cls)), None)
                if media_attrs and hasattr(media_attrs, 'duration'):
                    duration = media_attrs.duration # Duration in seconds
        except Exception as e:
             logger.warning(f"Could not get media duration attributes: {e}")
        
        # Check against configured limits (including new min_duration)
        if duration != 0: # Only check duration if we could retrieve it
            if duration < min_duration_cfg: # NEW CHECK
                logger.warning(f"Media too short: duration={duration}s (min={min_duration_cfg}s)")
                raise ValueError("too_short")
            if duration > max_duration_cfg:
                logger.warning(f"Media too long: duration={duration}s (max={max_duration_cfg}s)")
                raise ValueError("too_big")
        
        if size_mb > self.config["max_size_mb"]:
             logger.warning(f"Media too large: size={size_mb:.2f}MB (max={self.config['max_size_mb']}MB)")
             raise ValueError("too_big") # Could also be a separate "too_large_file" error if needed

        status_msg = None
        if not suppress_status_messages: # This is True for manual commands, False for watcher by default
            # For watcher, if self.config["silent"] is True, we don't want to send status messages for errors
            # So, we only send initial status if not silent mode OR if it's a manual command
            if not (self.config["silent"] and message.out is False) or message.out is True : # message.out distinguishes manual cmd from watcher
                 try:
                    status_msg = await utils.answer(message, self.strings("pref") + self.strings("downloading"))
                 except Exception as e:
                    logger.warning(f"Could not send initial status message: {e}")


        temp_dir = tempfile.mkdtemp()
        original_media_path = None
        # Try to get a more meaningful name if possible, fallback if not
        media_name = getattr(target_message.file, 'name', None) or \
                     f"media_{target_message.id}.{getattr(target_message.file, 'ext', 'file') or 'file'}"
        
        try:
            original_media_path = await target_message.download_media(file=os.path.join(temp_dir, media_name))
            if status_msg: # only edit if it was created
                await status_msg.edit(self.strings("pref") + self.strings("processing"))
            
            audio_source_path_for_api = original_media_path
            # Google engine requires WAV format
            if engine == "google":
                wav_audio_path = os.path.join(temp_dir, "audio.wav")
                if is_video:
                    logger.debug(f"Extracting audio from video to WAV for Google: {original_media_path}")
                    with VideoFileClip(original_media_path) as video_clip:
                         if video_clip.audio is None:
                              raise ValueError(self.strings("audio_extract_error")) # Use string key for consistency
                         await utils.run_sync(video_clip.audio.write_audiofile, wav_audio_path, codec="pcm_s16le", logger=None)
                else: # Audio file
                    logger.debug(f"Converting audio to WAV for Google: {original_media_path}")
                    audio_segment = await utils.run_sync(auds.from_file, original_media_path)
                    await utils.run_sync(audio_segment.export, wav_audio_path, format="wav")
                audio_source_path_for_api = wav_audio_path
            
            if not os.path.exists(audio_source_path_for_api):
                 logger.error(f"Audio source for API does not exist: {audio_source_path_for_api}")
                 raise IOError(f"Audio source for API not found: {audio_source_path_for_api}")

            if status_msg:
                await status_msg.edit(self.strings("pref") + self.strings("recognizing"))

            recognized_text = ""
            if engine == "google":
                if not lang: raise ValueError("Language code required for Google engine")
                recognized_text = await self._recognize_google(audio_source_path_for_api, lang)
            elif engine == "gemini":
                 recognized_text = await self._recognize_gemini(audio_source_path_for_api, lang) # lang is not used but passed
            else:
                raise ValueError(f"Unknown recognition engine: {engine}")

            # Do not delete status_msg here, _handle_recognition_command or watcher will handle final message
            return recognized_text

        except (ValueError, RuntimeError, IOError, ConnectionError, TimeoutError) as e:
            logger.warning(f"Error during media processing in _process_media: {e} (Type: {type(e)})")
            
            # Handle silent mode for watcher
            # suppress_status_messages is True for manual commands.
            # For watcher (message.out is False), only send error if not self.config["silent"]
            should_send_error_message = not suppress_status_messages and \
                                        (message.out or not self.config["silent"])

            if should_send_error_message:
                error_display_text = str(e) # Default to the exception message
                # Map known exception string values to user-friendly messages
                if str(e) == "no_reply": error_display_text = self.strings("no_reply")
                elif str(e) == "too_big": error_display_text = self.strings("too_big")
                elif str(e) == "too_short": error_display_text = self.strings("too_short") # NEW
                elif str(e) == self.strings("audio_extract_error"): error_display_text = self.strings("audio_extract_error")
                elif str(e) == "gemini_token_missing": error_display_text = self.strings("gemini_token_missing")
                elif str(e) == "gemini_lib_missing": error_display_text = self.strings("gemini_lib_missing")
                # More specific API error handling based on exception type or message content
                elif isinstance(e, ConnectionError) or "API" in str(e) or "Gemini" in str(e) or "Google" in str(e):
                    source = "API"
                    if "Google" in str(e): source = "Google"
                    elif "Gemini" in str(e) or "timeout" in str(e).lower() and engine=="gemini": source = "Gemini" # Include timeout for Gemini here
                    error_display_text = self.strings("api_error").format(source=source, error=str(e))
                elif isinstance(e, IOError):
                    error_display_text = self.strings("conversion_error") # + f" ({e})" # Avoid verbose internal errors
                else: # Fallback for other RuntimeErrors or ValueErrors
                    error_display_text = self.strings("recognition_error") # + f" ({e})"

                try:
                     if status_msg:
                         await status_msg.edit(self.strings("pref") + error_display_text)
                     else: # If status_msg wasn't created (e.g. initial send failed, or silent watcher)
                         await utils.answer(message, self.strings("pref") + error_display_text)
                except Exception as display_err:
                     logger.error(f"Failed to display error to user: {display_err}")
            raise # Re-raise the exception to be caught by the calling function (command handler or watcher)
        finally:
            try:
                if os.path.isdir(temp_dir): # Check if temp_dir was created and exists
                    for filename in os.listdir(temp_dir):
                         file_path = os.path.join(temp_dir, filename)
                         if os.path.isfile(file_path) or os.path.islink(file_path):
                             os.unlink(file_path)
                    os.rmdir(temp_dir)
            except Exception as cleanup_err:
                logger.error(f"Failed to cleanup temp dir {temp_dir}: {cleanup_err}")


    async def _handle_recognition_command(self, message: Message, engine: str, lang: str = None):
        """Обробник для команд ручного розпізнавання - редагує повідомлення команди результатом."""
        # For manual commands, we always want to show status, so suppress_status_messages=True
        # in _process_media, and we manage editing the command message here.

        original_message_to_edit = message # The command message itself

        try:
            # Edit the command message itself to show "processing"
            await original_message_to_edit.edit(self.strings("pref") + self.strings("processing"))

            recognized_text = await self._process_media(
                message, # Pass the original command message, _process_media will get reply from it
                engine,
                lang,
                suppress_status_messages=True # We are handling status updates by editing the command message
            )

            final_text_output = self.strings("recognized").format(recognized_text)
            await original_message_to_edit.edit(self.strings("pref") + final_text_output)

        except Exception as e:
            # Error occurred in _process_media, it was re-raised.
            # Now display the error by editing the original command message.
            logger.warning(f"Error in _handle_recognition_command (engine: {engine}): {e} (Type: {type(e)})")
            
            error_message_text = ""
            error_key = str(e)

            # Attempt to map known error keys/types to user-friendly strings
            if error_key == "no_reply": error_message_text = self.strings("no_reply")
            elif error_key == "too_big": error_message_text = self.strings("too_big")
            elif error_key == "too_short": error_message_text = self.strings("too_short") # NEW
            elif error_key == self.strings("audio_extract_error"): error_message_text = self.strings("audio_extract_error") # if valueerror has this string
            elif error_key == "gemini_token_missing": error_message_text = self.strings("gemini_token_missing")
            elif error_key == "gemini_lib_missing": error_message_text = self.strings("gemini_lib_missing")
            elif isinstance(e, ConnectionError) or "API" in str(e) or "Gemini" in str(e) or "Google" in str(e):
                source = "API"
                if "Google" in str(e): source = "Google"
                elif "Gemini" in str(e) or "timeout" in str(e).lower() and engine=="gemini": source = "Gemini"
                error_message_text = self.strings("api_error").format(source=source, error=str(e))
            elif isinstance(e, IOError):
                 error_message_text = self.strings("conversion_error")
            else: # Fallback for other errors
                error_message_text = self.strings("recognition_error") + f" ({str(e)})" # Add exception details for unmapped errors
            
            try:
                await original_message_to_edit.edit(self.strings("pref") + error_message_text)
            except MessageNotModifiedError:
                pass # It's fine if the message content is already the error message
            except Exception as edit_final_error:
                logger.error(f"Failed to edit command message with final error: {edit_final_error}. Sending as new message.")
                # Fallback: if editing fails, send as a new reply
                await utils.answer(message, self.strings("pref") + error_message_text)


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

        # Determine if it's a relevant media type
        is_video = message.video is not None and not getattr(message, 'gif', False) # Exclude GIFs
        is_audio_file = message.audio is not None
        is_voice_message = getattr(message, 'voice', None) is not None or \
                   (message.document and any(
                       isinstance(attr, DocumentAttributeAudio) and getattr(attr, 'voice', False)
                       for attr in getattr(message.document, 'attributes', [])
                   ))
        
        if not (is_video or is_audio_file or is_voice_message): return

        sender = await message.get_sender()
        if not sender or sender.bot: return
        # Don't process own outgoing messages in watcher unless it's a reply to something else
        # and auto-recognition is on. However, this is usually for others.
        # The main check is for ignored users (excluding self from being ignored by default).
        if self._me_id != -1 and message.sender_id != self._me_id and message.sender_id in self.config["ignore_users"]:
            logger.debug(f"AuthorVTT Watcher: Ignoring message from user {message.sender_id} in chat {chat_id} as per ignore_users list.")
            return
        # Avoid processing own messages if they are not replies, mainly to prevent loops if module replies to itself.
        # If it's an outgoing message from self, and it's not a reply, skip.
        if message.out and not message.is_reply:
            # This could be debated, but generally auto-transcribe is for incoming.
            # If you want to auto-transcribe your own voice notes, this might need adjustment
            # or rely on manual commands.
            return

        engine, lang = settings["engine"], settings["lang"]
        logger.debug(f"AuthorVTT Watcher: Triggered for chat {chat_id} by {message.sender_id} (engine: {engine})")
        
        try:
            # For watcher, suppress_status_messages is False, so _process_media will handle
            # sending status messages (downloading, processing, recognizing)
            # and also error messages if self.config["silent"] is False.
            recognized_text = await self._process_media(
                message, # Pass the new message itself
                engine,
                lang,
                suppress_status_messages=False # Let _process_media handle status/errors based on silent config
            )
            
            if recognized_text and recognized_text.strip():
                 # Reply to the original media message
                 await message.reply(self.strings("recognized").format(recognized_text))
            else:
                 # This case should ideally be caught by "Gemini returned empty text" or similar error
                 logger.warning(f"AuthorVTT Watcher: Empty text received for chat {chat_id} from _process_media. No reply sent.")

        except Exception as e:
            # If self.config["silent"] is True, _process_media would have raised the error
            # but not sent a message to the chat. If False, it would have sent it.
            # Log here for visibility regardless of silent mode.
            if self.config["silent"]:
                logger.warning(
                    f"AuthorVTT Watcher (Silent Mode): Error processing message in chat {chat_id} (engine {engine}): {e}. "
                    "Error not sent to chat due to silent mode."
                )
            else:
                logger.warning(
                    f"AuthorVTT Watcher: Error processing message in chat {chat_id} (engine {engine}): {e}. "
                    "Error display was handled by _process_media."
                )
            # No need to send another message here, _process_media handles it if not silent.

    @loader.command(ru_doc="Инструкция по получению API ключа Gemini")
    async def geminiguide(self, message: Message):
        """Інструкція для отримання API ключа Gemini"""
        await utils.answer(message, self.strings('gemini_instructions'))

