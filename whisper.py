# requires: pydub speechRecognition moviepy telethon requests google-generativeai pillow

from io import BytesIO
import os
import tempfile
import logging
import base64
import asyncio # Додано для asyncio.sleep

import speech_recognition as srec
from pydub import AudioSegment as auds
from moviepy.editor import VideoFileClip # AudioFileClip не використовується напряму, pydub краще
from telethon.tl.types import (
    DocumentAttributeVideo,
    Message,
    DocumentAttributeAudio, # <-- Імпорт додано
)
import requests
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

from .. import loader, utils

logger = logging.getLogger(__name__)

# Формат зберігання налаштувань авто-розпізнавання:
# { chat_id: {"engine": "google" | "whisper" | "gemini", "lang": "uk-UA" | "ru-RU" | "en-US" | None}, ... }
KEY_AUTO_RECOG = "auto_recognition_chats"

@loader.tds
class AuthorVttModEnhanced(loader.Module):
    """Розпізнавання голосу через Google Recognition, Whisper (HF) та Gemini (AI Studio) з авто-режимом"""
    strings = {
        "name": "Enhanced Voice-to-text",
        "pref": "<b>[Enhanced VTT]</b> ",
        "processing": "⏳ Processing...",
        "downloading": "📥 Downloading...",
        "recognizing": "🗣️ Recognizing...",
        "recognized": "💬 <b>Recognized:</b>\n<i>{}</i>",
        "no_reply": "🫠 Reply to audio/voice/video message.",
        "audio_extract_error": "🚫 Error extracting audio from video.",
        "conversion_error": "🚫 Error converting audio.",
        "recognition_error": "🚫 <b>Recognition Error!</b> Possible issues with API or language detection.",
        "api_error": "🚫 <b>API Error ({source}):</b> {error}",
        "too_big": "🫥 <b>Media file is too large or too long for recognition.</b> (Max duration/size limits apply)",
        "google_lang": "Google ({})",
        "whisper": "Whisper (auto-lang)",
        "gemini": "Gemini (auto-lang)",

        "auto_on": "✅ <b>Automatic recognition ({engine}) enabled in this chat.</b>",
        "auto_off": "⛔️ <b>Automatic recognition disabled in this chat.</b>",

        # Config Help
        "cfg_hf_key": "Hugging Face API Token. Get from https://huggingface.co/settings/tokens",
        "cfg_gemini_key": "Google AI Studio (Gemini) API Key. Get from https://aistudio.google.com/app/apikey",
        "cfg_ignore_users": "List of user IDs to ignore for auto-recognition.",
        "cfg_silent": "Silent mode for auto-recognition errors (no error messages).",
        "cfg_max_duration_voice": "Max duration (seconds) for voice/audio auto-recognition.",
        "cfg_max_duration_video": "Max duration (seconds) for video auto-recognition.",
        "cfg_max_size_mb": "Max file size (MB) for auto-recognition.",

        # API Key missing errors
        "hf_token_missing": (
            "<b><emoji document_id=5980953710157632545>❌</emoji>Missing Hugging Face API token.</b>\n"
            "Configure it using <code>.config</code> command.\n"
            "<i>See <code>.hfguide</code> for instructions.</i>"
        ),
        "gemini_token_missing": (
            "<b><emoji document_id=5980953710157632545>❌</emoji>Missing Google AI (Gemini) API token.</b>\n"
            "Configure it using <code>.config</code> command.\n"
            "<i>See <code>.geminiguide</code> for instructions.</i>"
        ),
         "gemini_lib_missing": (
            "<b><emoji document_id=5980953710157632545>❌</emoji>Missing `google-generativeai` library.</b>\n"
            "Install it using <code>.pip install google-generativeai</code> and restart Hikka."
        ),

        # Guides
        "hf_instructions": (
            "<emoji document_id=5238154170174820439>👩‍🎓</emoji> <b>How to get Hugging Face API token:</b>\n"
            "<b>1. Open Hugging Face and sign in:</b> <a href=\"https://huggingface.co/\">huggingface.co</a> <emoji document_id=4904848288345228262>👤</emoji>\n"
            "<b>2. Go to Settings → Access Tokens:</b> <a href=\"https://huggingface.co/settings/tokens\">huggingface.co/settings/tokens</a> <emoji document_id=5222142557865128918>⚙️</emoji>\n"
            "<b>3. Click 'New Token'.</b> <emoji document_id=5431757929940273672>➕</emoji>\n"
            "<b>4. Give it a name (e.g., 'hikka-vtt') and select Role 'read'.</b> <emoji document_id=5253952855185829086>⚙️</emoji>\n"
            "<b>5. Click 'Generate Token'.</b> <emoji document_id=5253652327734192243>➕</emoji>\n"
            "<b>6. Copy the token.</b> <emoji document_id=4916036072560919511>✅</emoji>\n"
            "<b>7. Use <code>.config</code> in Hikka, find this module, and paste the token into 'Hf api key'.</b>"
        ),
        "gemini_instructions": (
            "<emoji document_id=5238154170174820439>👩‍🎓</emoji> <b>How to get Google AI (Gemini) API key:</b>\n"
            "<b>1. Open Google AI Studio:</b> <a href=\"https://aistudio.google.com/app/apikey\">aistudio.google.com/app/apikey</a> <emoji document_id=4904848288345228262>👤</emoji>\n"
            "<b>2. Sign in with your Google Account.</b>\n"
            "<b>3. Click 'Create API key in new project'.</b> <emoji document_id=5431757929940273672>➕</emoji>\n"
            "<b>4. Copy the generated API key.</b> <emoji document_id=4916036072560919511>✅</emoji>\n"
            "<b>5. Use <code>.config</code> in Hikka, find this module, and paste the key into 'Gemini api key'.</b>"
        ),
    }
    # Додаємо російські рядки для сумісності (можна розширити)
    strings_ru = {
        "_cls_doc": "Распознавание голоса через Google Recognition, Whisper (HF) и Gemini (AI Studio) с авто-режимом",
        "pref": "<b>[Enhanced VTT]</b> ",
        "processing": "⏳ Обработка...",
        "downloading": "📥 Загрузка...",
        "recognizing": "🗣️ Распознавание...",
        "recognized": "💬 <b>Распознано:</b>\n<i>{}</i>",
        "no_reply": "🫠 Ответьте на аудио/голосовое/видео сообщение.",
        "recognition_error": "🚫 <b>Ошибка распознавания!</b> Возможны проблемы с API или определением языка.",
        "api_error": "🚫 <b>Ошибка API ({source}):</b> {error}",
        "too_big": "🫥 <b>Медиафайл слишком большой или длинный для распознавания.</b> (Применяются лимиты на длительность/размер)",
        "google_lang": "Google ({})",
        "whisper": "Whisper (авто-язык)",
        "gemini": "Gemini (авто-язык)",
        "auto_on": "✅ <b>Автоматическое распознавание ({engine}) включено в этом чате.</b>",
        "auto_off": "⛔️ <b>Автоматическое распознавание отключено в этом чате.</b>",
        "hf_token_missing": "<b><emoji document_id=5980953710157632545>❌</emoji>Отсутствует API-токен Hugging Face.</b>\nНастройте его через <code>.config</code>.\n<i>См. <code>.hfguide</code> для инструкций.</i>",
        "gemini_token_missing": "<b><emoji document_id=5980953710157632545>❌</emoji>Отсутствует API-ключ Google AI (Gemini).</b>\nНастройте его через <code>.config</code>.\n<i>См. <code>.geminiguide</code> для инструкций.</i>",
        "gemini_lib_missing": "<b><emoji document_id=5980953710157632545>❌</emoji>Отсутствует библиотека `google-generativeai`.</b>\nУстановите ее: <code>.pip install google-generativeai</code> и перезапустите Hikka.",
    }


    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "hf_api_key",
                None,
                lambda: self.strings("cfg_hf_key"),
                validator=loader.validators.Hidden(),
            ),
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
                300, # 5 хвилин за замовчуванням
                lambda: self.strings("cfg_max_duration_voice"),
                validator=loader.validators.Integer(minimum=10)
            ),
            loader.ConfigValue(
                "max_duration_video",
                120, # 2 хвилини за замовчуванням
                lambda: self.strings("cfg_max_duration_video"),
                validator=loader.validators.Integer(minimum=10)
            ),
            loader.ConfigValue(
                "max_size_mb",
                20, # 20 MB за замовчуванням
                lambda: self.strings("cfg_max_size_mb"),
                validator=loader.validators.Integer(minimum=1)
            ),
        )
        self._auto_recog_settings = {} # Ініціалізуємо тут, завантажимо в client_ready


    async def client_ready(self, client, db):
        self.client = client
        self.db = db
        # Завантажуємо налаштування авторозпізнавання при старті
        self._auto_recog_settings = self.db.get(self.strings("name"), KEY_AUTO_RECOG, {})

        # Перевірка Gemini API ключа при старті (якщо бібліотека є)
        if GEMINI_AVAILABLE and self.config["gemini_api_key"]:
             try:
                 genai.configure(api_key=self.config["gemini_api_key"])
                 logger.info("Gemini API configured successfully.")
             except Exception as e:
                 logger.error(f"Failed to configure Gemini API: {e}")


    def _save_auto_recog_settings(self):
        """Зберігає поточні налаштування авторозпізнавання в БД"""
        self.db.set(self.strings("name"), KEY_AUTO_RECOG, self._auto_recog_settings)

    # --- Розпізнавачі ---

    async def _recognize_google(self, audio_path: str, lang: str) -> str:
        """Розпізнавання через Google Speech Recognition (speech_recognition library)"""
        recog = srec.Recognizer()
        try:
            with srec.AudioFile(audio_path) as audio_file:
                audio_content = recog.record(audio_file)
            return await utils.run_sync(recog.recognize_google, audio_content, language=lang)
        except srec.UnknownValueError:
            raise ValueError("Google Speech Recognition could not understand audio")
        except srec.RequestError as e:
            raise ConnectionError(f"Could not request results from Google Speech Recognition service; {e}")
        except Exception as e:
            logger.exception("Google recognition error")
            raise e


    async def _recognize_whisper(self, audio_path: str) -> str:
        """Розпізнавання через Whisper (Hugging Face API)"""
        if not self.config["hf_api_key"]:
            raise ValueError("hf_token_missing") # Повертаємо ключ строки для обробки

        api_url = "https://api-inference.huggingface.co/models/openai/whisper-large-v3" # Можна обрати іншу модель
        headers = {"Authorization": f"Bearer {self.config['hf_api_key']}"}

        try:
            with open(audio_path, "rb") as f:
                 audio_bytes = f.read()

            response = await utils.run_sync(
                requests.post,
                url=api_url,
                headers=headers,
                data=audio_bytes, # Передаємо байти напряму
                timeout=300 # Додаємо таймаут для довгих файлів
            )

            response.raise_for_status() # Перевірка на HTTP помилки (4xx, 5xx)
            result = response.json()

            if "text" in result:
                # Іноді API повертає leading/trailing пробіли
                return result["text"].strip() if result["text"] else ""
            elif "error" in result:
                # Перевірка на специфічну помилку завантаження моделі
                if "is currently loading" in result["error"]:
                     estimated_time = result.get("estimated_time", 20.0)
                     logger.warning(f"Whisper model is loading, estimated time: {estimated_time}s. Retrying might help.")
                     raise ConnectionError(f"Whisper model loading (est: {estimated_time:.1f}s). Please wait and try again.")
                raise RuntimeError(f"Whisper API error: {result['error']}")
            else:
                raise RuntimeError("Whisper API returned an unexpected response.")

        except requests.exceptions.Timeout:
             logger.error("Whisper API request timed out.")
             raise ConnectionError("Whisper API request timed out.")
        except requests.exceptions.RequestException as e:
            logger.exception("Whisper API request error")
            raise ConnectionError(f"Whisper API connection error: {e}")
        except Exception as e:
            logger.exception("Whisper recognition error")
            if isinstance(e, ValueError) and str(e) == "hf_token_missing":
                 raise e
            if isinstance(e, ConnectionError): # Перехоплюємо ConnectionError від завантаження моделі
                 raise e
            raise RuntimeError(f"Whisper processing error: {e}")


    async def _recognize_gemini(self, audio_path: str, lang: str = None) -> str:
        """Розпізнавання через Gemini API (AI Studio)"""
        if not GEMINI_AVAILABLE:
             raise RuntimeError("gemini_lib_missing")
        if not self.config["gemini_api_key"]:
            raise ValueError("gemini_token_missing")

        audio_file = None # Ініціалізуємо змінну
        try:
            # 1. Configure API (вже зроблено в client_ready, але перевірка не завадить)
            if not getattr(genai, '_client', None): # Проста перевірка чи є клієнт
                genai.configure(api_key=self.config["gemini_api_key"])

            # 2. Upload file
            logger.info(f"Uploading {audio_path} to Gemini...")
            audio_file = await utils.run_sync(genai.upload_file, path=audio_path)
            logger.info(f"File uploaded: {audio_file.name}, starting state: {audio_file.state}")

            # Чекаємо, доки файл обробиться (з таймаутом)
            upload_timeout = 300 # 5 хвилин на завантаження/обробку файлу
            start_time = asyncio.get_event_loop().time()
            while audio_file.state.name == "PROCESSING":
                if asyncio.get_event_loop().time() - start_time > upload_timeout:
                     raise TimeoutError(f"Gemini file upload/processing timed out after {upload_timeout}s")
                await asyncio.sleep(2) # Чекаємо трохи довше між перевірками
                # Оновлюємо статус файлу
                audio_file = await utils.run_sync(genai.get_file, name=audio_file.name)
                logger.debug(f"Gemini file state: {audio_file.state.name}")


            if audio_file.state.name == "FAILED":
                logger.error(f"Gemini file processing failed: {audio_file.state}")
                raise RuntimeError(f"Gemini file processing failed")
            if audio_file.state.name != "ACTIVE":
                 logger.error(f"Gemini file is not active, state: {audio_file.state.name}")
                 raise RuntimeError(f"Gemini file is not active, state: {audio_file.state.name}")

            # 3. Make the request
            model = genai.GenerativeModel(model_name="models/gemini-1.5-flash-latest")

            prompt = "Transcribe the audio file accurately."
            # Мова зараз не додається, бо Gemini 1.5 добре визначає її автоматично

            logger.info("Sending request to Gemini model...")
            response = await utils.run_sync(
                 model.generate_content,
                 [prompt, audio_file],
                 request_options={"timeout": 300} # Таймаут для самого запиту до моделі
            )
            logger.info("Received response from Gemini model.")

            # Перевірка наявності тексту у відповіді
            # Gemini API може блокувати відповідь з міркувань безпеки
            if not response.candidates:
                 safety_feedback = getattr(response, 'prompt_feedback', 'Unknown safety block')
                 logger.warning(f"Gemini response blocked or empty. Feedback: {safety_feedback}")
                 raise RuntimeError(f"Gemini response blocked. Reason: {safety_feedback}")

            # Витягуємо текст
            try:
                 recognized_text = response.text
            except ValueError as ve: # Може виникнути, якщо відповідь не містить тексту
                 logger.warning(f"Gemini response has no text part: {ve}. Candidates: {response.candidates}")
                 raise RuntimeError(f"Gemini response has no text part: {ve}")

            return recognized_text.strip() if recognized_text else ""

        except TimeoutError as e: # Перехоплюємо таймаут завантаження
             logger.error(str(e))
             raise ConnectionError(str(e))
        except Exception as e:
            logger.exception("Gemini recognition error")
            if isinstance(e, (ValueError, RuntimeError)) and str(e) in ["gemini_token_missing", "gemini_lib_missing"]:
                raise e
            if isinstance(e, ConnectionError): # Перехоплюємо інші ConnectionError
                 raise e
            # Спробуємо очистити файл, якщо він був завантажений і виникла інша помилка
            if audio_file and hasattr(audio_file, 'name'):
                logger.info(f"Attempting to delete Gemini file {audio_file.name} after error...")
                try:
                    await utils.run_sync(genai.delete_file, name=audio_file.name)
                    logger.info(f"Deleted Gemini file {audio_file.name} after error.")
                except Exception as delete_err:
                    logger.warning(f"Could not delete Gemini file {audio_file.name} after error: {delete_err}")

            raise RuntimeError(f"Gemini processing error: {e}")
        finally:
             # Гарантоване видалення файлу після успішного розпізнавання
             if audio_file and hasattr(audio_file, 'name') and audio_file.state.name == "ACTIVE":
                 logger.info(f"Attempting to delete Gemini file {audio_file.name} after successful recognition...")
                 try:
                     await utils.run_sync(genai.delete_file, name=audio_file.name)
                     logger.info(f"Deleted Gemini file: {audio_file.name}")
                 except Exception as delete_err:
                     logger.warning(f"Could not delete Gemini file {audio_file.name}: {delete_err}")


    # --- Основна логіка обробки ---

    async def _process_media(self, message: Message, engine: str, lang: str = None) -> str:
        """
        Загальний метод для завантаження, конвертації та розпізнавання медіа.
        Повертає розпізнаний текст або викликає виняток.
        """
        reply = await message.get_reply_message()
        target_message = reply or message

        if not target_message or not target_message.media or \
           (target_message.file.mime_type.split("/")[0] not in ["audio", "video"]):
            raise ValueError("no_reply")

        is_video = target_message.video is not None
        duration = 0
        size_mb = (target_message.file.size or 0) / 1024 / 1024

        # Отримання тривалості (безпечно)
        try:
            if is_video:
                 video_attrs = next((attr for attr in target_message.video.attributes if isinstance(attr, DocumentAttributeVideo)), None)
                 if video_attrs: duration = video_attrs.duration
                 max_duration = self.config["max_duration_video"]
            else: # audio or voice
                 if target_message.document and target_message.document.attributes:
                     audio_attrs = next((attr for attr in target_message.document.attributes if isinstance(attr, DocumentAttributeAudio)), None) # Перевіряємо саме DocumentAttributeAudio
                     if audio_attrs: duration = audio_attrs.duration
                 max_duration = self.config["max_duration_voice"]
        except Exception as e:
             logger.warning(f"Could not get media duration/attributes: {e}")
             max_duration = self.config["max_duration_voice"] # fallback

        # Перевірка лімітів
        if (duration and duration > max_duration) or \
           (size_mb and size_mb > self.config["max_size_mb"]):
             logger.warning(f"Media too large/long: duration={duration}s (max={max_duration}s), size={size_mb:.2f}MB (max={self.config['max_size_mb']}MB)")
             raise ValueError("too_big")


        status_msg = await utils.answer(message, self.strings("downloading"))

        temp_dir = tempfile.mkdtemp()
        original_media_path = None
        wav_audio_path = None
        media_name = target_message.file.name or f"media_{target_message.id}.{target_message.file.ext or 'file'}"


        try:
            original_media_path = await target_message.download_media(file=os.path.join(temp_dir, media_name))
            await utils.answer(status_msg, self.strings("processing"))

            # --- Конвертація в WAV (для Google і як fallback) ---
            wav_audio_path = os.path.join(temp_dir, "audio.wav")
            audio_source_path_for_api = None # Шлях до файлу для передачі в API

            try:
                if is_video:
                    logger.debug(f"Extracting audio from video: {original_media_path}")
                    with VideoFileClip(original_media_path) as video:
                         if video.audio is None:
                              raise ValueError("Video has no audio track.")
                         await utils.run_sync(video.audio.write_audiofile, wav_audio_path, codec="pcm_s16le", logger=None) # logger=None щоб уникнути спаму від moviepy
                    audio_source_path_for_api = wav_audio_path
                else:
                    # Для Whisper/Gemini спробуємо передати оригінал, якщо це можливо
                    # Google потребує WAV
                    if engine == "google":
                        logger.debug(f"Converting audio to WAV for Google: {original_media_path}")
                        audio_segment = await utils.run_sync(auds.from_file, original_media_path)
                        await utils.run_sync(audio_segment.export, wav_audio_path, format="wav")
                        audio_source_path_for_api = wav_audio_path
                    else:
                         # Для Whisper/Gemini використовуємо оригінальний файл
                         logger.debug(f"Using original audio file for {engine}: {original_media_path}")
                         audio_source_path_for_api = original_media_path

                if not audio_source_path_for_api:
                     raise RuntimeError("Could not determine audio source path for API.")

                logger.info(f"Prepared audio for {engine}: {audio_source_path_for_api}")

            except Exception as conv_err:
                logger.exception("Audio conversion/extraction failed")
                # Спробуємо сконвертувати в WAV як fallback, якщо ще не зроблено
                if engine != "google" and not os.path.exists(wav_audio_path):
                     try:
                         logger.warning("Falling back to WAV conversion for non-Google engine.")
                         audio_segment = await utils.run_sync(auds.from_file, original_media_path)
                         await utils.run_sync(audio_segment.export, wav_audio_path, format="wav")
                         audio_source_path_for_api = wav_audio_path
                         logger.info(f"Fallback WAV conversion successful: {wav_audio_path}")
                     except Exception as fallback_err:
                          logger.error(f"Fallback WAV conversion also failed: {fallback_err}")
                          raise IOError(f"{self.strings('conversion_error')}: {conv_err}") from conv_err
                else:
                     raise IOError(f"{self.strings('conversion_error')}: {conv_err}") from conv_err


            await utils.answer(status_msg, self.strings("recognizing"))

            # --- Виклик відповідного розпізнавача ---
            recognized_text = ""
            if engine == "google":
                if not lang: raise ValueError("Language code required for Google engine")
                recognized_text = await self._recognize_google(audio_source_path_for_api, lang)
            elif engine == "whisper":
                recognized_text = await self._recognize_whisper(audio_source_path_for_api)
            elif engine == "gemini":
                 if not GEMINI_AVAILABLE: raise RuntimeError("gemini_lib_missing")
                 recognized_text = await self._recognize_gemini(audio_source_path_for_api, lang)
            else:
                raise ValueError(f"Unknown recognition engine: {engine}")

            # Успіх - видаляємо повідомлення про статус і повертаємо текст
            await status_msg.delete()
            return recognized_text

        except (ValueError, RuntimeError, IOError, ConnectionError) as e:
            # Обробка очікуваних помилок (включаючи помилки API та конвертації)
            error_key = str(e)
            specific_error_msg = str(e)

            # Перевіряємо, чи це ключ нашої строки помилки
            is_known_error_key = error_key in self.strings

            if is_known_error_key:
                error_message = self.strings(error_key).format(error=specific_error_msg) # Форматуємо, якщо є плейсхолдер {error}
            elif isinstance(e, ConnectionError): # Загальна помилка з'єднання/API
                source = "API"
                if "Whisper" in specific_error_msg: source = "Whisper API"
                elif "Google" in specific_error_msg: source = "Google API"
                elif "Gemini" in specific_error_msg: source = "Gemini API"
                error_message = self.strings("api_error").format(source=source, error=specific_error_msg)
            elif isinstance(e, IOError): # Помилка конвертації/IO
                 error_message = specific_error_msg # Вже містить текст помилки
            else: # Інші RuntimeError/ValueError
                error_message = self.strings("recognition_error") + f" ({specific_error_msg})"

            logger.warning(f"Processing failed: {error_message}") # Логуємо фінальне повідомлення

            try:
                 # Використовуємо message.edit замість utils.answer для статусних повідомлень
                 await status_msg.edit(self.strings("pref") + error_message)
            except Exception: # Якщо не вдалося відредагувати
                 await utils.answer(message, self.strings("pref") + error_message)

            raise # Прокидаємо виняток далі

        finally:
            # --- Очищення тимчасових файлів ---
            try:
                # Видаляємо всі файли у тимчасовій папці
                for filename in os.listdir(temp_dir):
                     file_path = os.path.join(temp_dir, filename)
                     try:
                         if os.path.isfile(file_path) or os.path.islink(file_path):
                             os.unlink(file_path)
                     except Exception as delete_err:
                         logger.error(f"Failed to delete temp file {file_path}: {delete_err}")
                os.rmdir(temp_dir)
                logger.debug(f"Cleaned up temporary directory: {temp_dir}")
            except Exception as cleanup_err:
                logger.error(f"Failed to cleanup temp dir {temp_dir}: {cleanup_err}")


    # --- Команди ---

    async def _handle_recognition_command(self, message: Message, engine: str, lang: str = None):
        """Обробник для команд ручного розпізнавання"""
        try:
            recognized_text = await self._process_media(message, engine, lang)
            engine_name = engine.capitalize()
            if engine == 'google' and lang:
                engine_name = self.strings('google_lang').format(lang)
            elif engine == 'whisper':
                engine_name = self.strings('whisper')
            elif engine == 'gemini':
                 engine_name = self.strings('gemini')

            # Відповідаємо на оригінальне повідомлення, якщо був реплай
            target_message = await message.get_reply_message() or message
            await target_message.reply(self.strings("recognized").format(recognized_text))

            # Якщо обробляли реплай, вихідне повідомлення команди можна видалити
            if await message.get_reply_message():
                 await message.delete()

        except Exception as e:
            # Помилки вже оброблені та показані користувачеві в _process_media
            logger.debug(f"Recognition command failed: {e}")


    @loader.owner
    @loader.command(ru_doc=".av <реплай> - Распознать украинский (Google)")
    async def avcmd(self, message: Message):
        """Recognize Ukrainian (Google)"""
        await self._handle_recognition_command(message, "google", "uk-UA")

    @loader.owner
    @loader.command(ru_doc=".ar <реплай> - Распознать русский (Google)")
    async def arcmd(self, message: Message):
        """Recognize Russian (Google)"""
        await self._handle_recognition_command(message, "google", "ru-RU")

    @loader.owner
    @loader.command(ru_doc=".ae <реплай> - Распознать английский (Google)")
    async def aecmd(self, message: Message):
        """Recognize English (Google)"""
        await self._handle_recognition_command(message, "google", "en-US")

    @loader.owner
    @loader.command(alias="aw", ru_doc=".aw <реплай> - Распознать речь (Whisper, авто-язык)")
    async def awhispercmd(self, message: Message):
        """Recognize speech (Whisper, auto-language)"""
        await self._handle_recognition_command(message, "whisper")

    @loader.owner
    @loader.command(alias="ag", ru_doc=".ag <реплай> - Распознать речь (Gemini, авто-язык)")
    async def ageminicmd(self, message: Message):
        """Recognize speech (Gemini, auto-language)"""
        await self._handle_recognition_command(message, "gemini")

    # --- Команда ОДНОРАЗОВОГО розпізнавання через Whisper ---
    # Ця команда раніше вмикала/вимикала авто-режим, тепер робить одноразове розпізнавання
    @loader.owner
    @loader.command(ru_doc=".autow <реплай> - Распознать речь ОДИН РАЗ (Whisper, авто-язык)")
    async def autowcmd(self, message: Message):
        """Recognize speech ONE TIME (Whisper, auto-language)"""
        await self._handle_recognition_command(message, "whisper")


    # --- Команди ТУМБЛЕРІВ авто-розпізнавання ---

    async def _toggle_auto_recog(self, message: Message, engine: str, lang: str = None):
        """Вмикає/вимикає авто-розпізнавання для чату"""
        chat_id = utils.get_chat_id(message)
        chat_id_str = str(chat_id)
        current_setting = self._auto_recog_settings.get(chat_id_str)

        new_setting = {"engine": engine, "lang": lang}

        if current_setting == new_setting:
            # Вимикаємо, якщо поточне налаштування таке саме
            self._auto_recog_settings.pop(chat_id_str, None)
            self._save_auto_recog_settings()
            await utils.answer(message, self.strings("auto_off"))
        else:
             # Вмикаємо або змінюємо налаштування
             # Перевірка наявності ключів API перед увімкненням
            if engine == "whisper" and not self.config["hf_api_key"]:
                 await utils.answer(message, self.strings("hf_token_missing"))
                 return
            if engine == "gemini":
                 if not GEMINI_AVAILABLE:
                      await utils.answer(message, self.strings("gemini_lib_missing"))
                      return
                 if not self.config["gemini_api_key"]:
                      await utils.answer(message, self.strings("gemini_token_missing"))
                      return

            self._auto_recog_settings[chat_id_str] = new_setting
            self._save_auto_recog_settings()

            engine_name = engine.capitalize()
            if engine == 'google' and lang:
                engine_name = self.strings('google_lang').format(lang)
            elif engine == 'whisper':
                engine_name = self.strings('whisper')
            elif engine == 'gemini':
                 engine_name = self.strings('gemini')

            await utils.answer(message, self.strings("auto_on").format(engine=engine_name))


    @loader.owner # Або @loader.unrestricted, якщо дозволити всім
    @loader.command(alias="autov", ru_doc="Вкл/выкл авто-распознавание украинского (Google) в чате")
    async def autoukcmd(self, message: Message):
        """Toggle auto-recognition for Ukrainian (Google)"""
        await self._toggle_auto_recog(message, "google", "uk-UA")

    @loader.owner
    @loader.command(alias="autor", ru_doc="Вкл/выкл авто-распознавание русского (Google) в чате")
    async def autorucmd(self, message: Message):
        """Toggle auto-recognition for Russian (Google)"""
        await self._toggle_auto_recog(message, "google", "ru-RU")

    @loader.owner
    @loader.command(alias="autoe", ru_doc="Вкл/выкл авто-распознавание английского (Google) в чате")
    async def autoencmd(self, message: Message):
        """Toggle auto-recognition for English (Google)"""
        await self._toggle_auto_recog(message, "google", "en-US")

    # Команда для ВВІМКНЕННЯ/ВИМКНЕННЯ авто-режиму Whisper
    @loader.owner
    @loader.command(alias="toggleautow", ru_doc="Вкл/выкл АВТО-распознавание (Whisper) в чате")
    async def toggleautowhispcmd(self, message: Message):
        """Toggle AUTO-recognition (Whisper, auto-lang)"""
        await self._toggle_auto_recog(message, "whisper")

    @loader.owner
    @loader.command(alias="autog", ru_doc="Вкл/выкл авто-распознавание (Gemini) в чате")
    async def autogemicmd(self, message: Message):
        """Toggle auto-recognition (Gemini, auto-lang)"""
        await self._toggle_auto_recog(message, "gemini")


    # --- Watcher ---

    @loader.watcher(only_media=True, no_cmd=True)
    async def watcher(self, message: Message):
        chat_id = utils.get_chat_id(message)
        settings = self._auto_recog_settings.get(str(chat_id))

        if not settings: # Авто-розпізнавання вимкнено для цього чату
            return

        # Перевірка типу медіа (голос, аудіо, відео без анімації)
        is_video = message.video is not None and not message.gif
        is_audio = message.audio is not None
        # Виправлена перевірка голосових повідомлень:
        is_voice = message.voice is not None or \
                   (message.document and any(
                       isinstance(attr, DocumentAttributeAudio) and attr.voice
                       for attr in getattr(message.document, 'attributes', [])
                   ))

        if not (is_video or is_audio or is_voice):
            return # Не є цільовим типом медіа

        # Ігнорування користувачів
        sender = await message.get_sender()
        if not sender or sender.bot or sender.is_self: # Ігноруємо ботів та себе
             return
        if message.sender_id in self.config["ignore_users"]:
            logger.debug(f"Ignoring message from user {message.sender_id} in chat {chat_id}")
            return

        # Отримання налаштувань для цього чату
        engine = settings["engine"]
        lang = settings["lang"] # Може бути None для Whisper/Gemini

        logger.debug(f"Auto-recognition triggered for chat {chat_id} with engine {engine} (lang: {lang})")

        try:
            # _process_media тепер обробляє саме повідомлення
            # Вона також містить перевірку розміру/тривалості
            recognized_text = await self._process_media(message, engine, lang)

            # Відповідаємо на оригінальне повідомлення
            # Перевіряємо, чи текст не порожній
            if recognized_text and recognized_text.strip():
                 await message.reply(self.strings("recognized").format(recognized_text))
            else:
                 logger.warning(f"Auto-recognition for chat {chat_id} resulted in empty text.")


        except ValueError as e:
            err_key = str(e)
            if err_key == "too_big" and not self.config["silent"]:
                 try: await message.reply(self.strings("pref") + self.strings("too_big"))
                 except Exception: pass
            elif err_key in self.strings and not self.config["silent"]:
                 try: await message.reply(self.strings("pref") + self.strings(err_key).format(error=str(e)))
                 except Exception: pass
            else:
                 logger.warning(f"Watcher value error in chat {chat_id}: {e}")

        except Exception as e:
            logger.exception(f"Auto-recognition watcher failed for chat {chat_id}")
            if not self.config["silent"]:
                 # Формуємо повідомлення про помилку
                error_key = "recognition_error"
                error_message_fmt = self.strings(error_key)
                specific_error_msg = str(e)

                if isinstance(e, ConnectionError):
                     source = "API"
                     if "Whisper" in specific_error_msg: source = "Whisper API"
                     elif "Google" in specific_error_msg: source = "Google API"
                     elif "Gemini" in specific_error_msg: source = "Gemini API"
                     error_key = "api_error"
                     error_message_fmt = self.strings(error_key).format(source=source, error="{error}") # Залишаємо плейсхолдер
                elif str(e) in self.strings:
                     error_key = str(e)
                     error_message_fmt = self.strings(error_key) # Тут може не бути {error}

                # Форматуємо, якщо можливо, інакше додаємо текст помилки в дужках
                try:
                     final_error_message = error_message_fmt.format(error=specific_error_msg)
                except KeyError: # Якщо в форматі немає {error}
                     final_error_message = error_message_fmt + f" ({specific_error_msg})"

                try:
                     await message.reply(self.strings("pref") + final_error_message)
                except Exception:
                     pass

    # --- Допоміжні команди ---
    @loader.command(ru_doc="Инструкция по получению токена Hugging Face")
    async def hfguide(self, message: Message):
        """Show Hugging Face token guide"""
        await utils.answer(message, self.strings('hf_instructions'))

    @loader.command(ru_doc="Инструкция по получению API ключа Gemini")
    async def geminiguide(self, message: Message):
        """Show Google AI (Gemini) API key guide"""
        await utils.answer(message, self.strings('gemini_instructions'))