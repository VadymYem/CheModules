# meta developer: @blazeftg, @wsinfo
# 🔒 Licensed under the GNU AGPLv3
# 🌐 https://www.gnu.org/licenses/agpl-3.0.html

import logging
import requests

from .. import loader, utils

logger = logging.getLogger(__name__)

@loader.tds
class HuggingChatMod(loader.Module):
    """Універсальний чат з підтримкою легких моделей HuggingFace"""

    strings = {
        "name": "HuggingChat",
        "no_args": "❌ <b>Введіть запит:</b> 📌 <code>{}{} {}</code>",
        "no_token": "❌ <b>Токен не знайдено! Додайте:</b> 📌 <code>{}cfg huggingchat</code>",
        "asking": "🔄 <b>Генерація відповіді...</b>",
        "answer": "🤖 <b>Відповідь {}:</b>\n{}\n\n💬 <b>Запит:</b> {}",
        "api_error": "🚨 <b>Помилка API:</b> {}",
        "model_error": "⚠️ <b>Проблема з моделлю:</b>\n{}",
        "suggest_models": "🏷 <b>Рекомендовані моделі:</b>\n{}",
        "hf_models": (  
    "📌 <code>HuggingFaceH4/zephyr-7b-beta </code>(7B параметрів, ~5GB)\n"  
    "📌 <code>mistralai/Mistral-7B-Instruct-v0.2 </code>(7B, ~5GB)\n"  
    "📌 <code>tiiuae/falcon-7b-instruct </code>(7B, ~5GB)\n"  
      ),
    }
    
    strings_ru = {
        "name": "HuggingChat",
        "no_args": "❌ <b>Введите свой запрос:</b> 📌 <code>{}{} {}</code>",
        "no_token": "❌ <b>Токен не найден! Додайте:</b> 📌 <code>{}cfg huggingchat</code>",
        "asking": "🔄 <b>Генерация ответов...</b>",
        "answer": "🤖 <b>Ответ {}:</b>\n{}\n\n💬 <b>Запит:</b> {}",
        "api_error": "🚨 <b>Ошибка API:</b> {}",
        "model_error": "⚠️ <b>Проблема модели:</b>\n{}",
        "suggest_models": "🏷 <b>Рекомендуемые модели:</b>\n{}",
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "hf_api_key",
                None,
                "🔑 Токен HuggingFace (WRITE access required)",
                validator=loader.validators.Hidden(loader.validators.String())
            ),
            loader.ConfigValue(
                "default_model",
                "HuggingFaceH4/zephyr-7b-beta",  # Легка модель <10GB
                "🦾 Default model (HuggingFace ID)",
            ),
            loader.ConfigValue(
                "max_new_tokens",
                512,  # Зменшено для безпеки
                "📏 Max. Tokens",
                validator=loader.validators.Integer(minimum=100, maximum=1024)
            ),
            loader.ConfigValue(
                "temperature",
                0.7,
                "🎨 Creativity (0.1-1.0)",
                validator=loader.validators.Float(minimum=0.1, maximum=1.0)
            ),
        )

    async def client_ready(self, client, db):
        self.client = client
        self.db = db

    def _format_prompt(self, model: str, question: str) -> str:
        """Форматування запиту відповідно до вимог моделі"""
        if "zephyr" in model.lower():
            return f"<|user|>\n{question}</s>\n<|assistant|>"
        elif "mistral" in model.lower():
            return f"[INST] {question} [/INST]"
        elif "flan" in model.lower():
            return f"Question: {question}\nAnswer:"
        elif "oasst" in model.lower():
            return f"<|prompter|>{question}<|endoftext|><|assistant|>"
        else:
            return question  # Універсальний формат

    @loader.command(ru_doc="Модели которые рекомендую", en_doc="Models I recommend")
    async def hfmodels(self, message):
        """Показати рекомендовані моделі"""
        await utils.answer(message, self.strings["hf_models"])

    @loader.command()
    async def hfchat(self, message):
        """Задати питання моделі"""
        question = utils.get_args_raw(message)
        if not question:
            return await utils.answer(message, self.strings["no_args"].format(
                self.get_prefix(), "hfchat", "[запит]"
            ))

        if not self.config["hf_api_key"]:
            return await utils.answer(message, self.strings["no_token"].format(self.get_prefix()))

        await utils.answer(message, self.strings["asking"])

        headers = {
            "Authorization": f"Bearer {self.config['hf_api_key']}",
            "Content-Type": "application/json",
        }

        current_model = self.config["default_model"]
        payload = {
            "inputs": self._format_prompt(current_model, question),
            "parameters": {
                "max_new_tokens": self.config["max_new_tokens"],
                "temperature": self.config["temperature"],
                "return_full_text": False
            }
        }

        try:
            response = await utils.run_sync(
                requests.post,
                url=f"https://api-inference.huggingface.co/models/{current_model}",
                headers=headers,
                json=payload
            )

            if response.status_code == 200:
                result = response.json()
                if isinstance(result, list) and "generated_text" in result[0]:
                    answer = result[0]["generated_text"].strip()
                    return await utils.answer(
                        message,
                        self.strings["answer"].format(
                            current_model.split('/')[-1],
                            answer,
                            question
                        )
                    )
                return await utils.answer(message, self.strings["api_error"].format("Невірний формат відповіді"))

            error_data = response.json()
            error_msg = f"{response.status_code} - {error_data.get('error', 'Невідома помилка')}"
            
            # Якщо модель не підтримується
            if "currently loading" in error_msg.lower():
                suggestions = "\n".join([f"• {m}" for m in self.recommended_models])
                error_msg += self.strings["suggest_models"].format(suggestions)
            
            return await utils.answer(
                message,
                self.strings["model_error"].format(error_msg)
            )

        except Exception as e:
            logger.exception("API error")
            return await utils.answer(
                message,
                self.strings["api_error"].format(str(e))
            )