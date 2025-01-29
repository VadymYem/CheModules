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
        "no_args": "❌ <b>Введіть запит:</b> <code>{}{} {}</code>",
        "no_token": "❌ <b>Токен не знайдено! Додайте:</b> <code>.cfg huggingchat</code>",
        "asking": "🔄 <b>Генерація відповіді...</b>",
        "answer": "🤖 <b>Відповідь {}:</b>\n{}\n\n💬 <b>Запит:</b> {}",
        "api_error": "🚨 <b>Помилка API:</b> {}",
        "model_error": "⚠️ <b>Проблема з моделлю:</b>\n{}",
        "suggest_models": "🏷 <b>Рекомендовані моделі:</b>\n{}",
        "hf_models": (
            "<b>🦾 Рекомендовані моделі для використання:</b>\n\n"
            "┌ <code>meta-llama/Meta-Llama-3-8B-Instruct</code>\n"
            "├ <code>mistralai/Mistral-7B-Instruct-v0.2</code>\n"
            "├ <code>HuggingFaceH4/zephyr-7b-beta</code>\n"
            "├ <code>tiiuae/falcon-7b-instruct</code>\n"
            "└ <code>EleutherAI/gpt-neo-2.7B</code>\n\n"
            "📌 <i>Для зміни моделі використовуй</i> <code>.cfg huggingchat </code> в `default_model` назва моделі яка нам треба"
        ),
    }
    
    strings_ru = {
    "name": "HuggingChat",
    "no_args": "❌ <b>Введите запрос:</b> <code>{}{} {}</code>",
    "no_token": "❌ <b>Токен не найден! Добавьте:</b> <code>.cfg huggingchat</code>",
    "asking": "🔄 <b>Генерация ответа...</b>",
    "answer": "🤖 <b>Ответ {}:</b>\n{}\n\n💬 <b>Запрос:</b> {}",
    "api_error": "🚨 <b>Ошибка API:</b> {}",
    "model_error": "⚠️ <b>Проблема с моделью:</b>\n{}",
    "suggest_models": "🏷 <b>Рекомендуемые модели:</b>\n{}",
    "hf_models": (
        "<b>🦾 Рекомендуемые модели для использования:</b>\n\n"
        "┌ <code>meta-llama/Meta-Llama-3-8B-Instruct</code>\n"
        "├ <code>mistralai/Mistral-7B-Instruct-v0.2</code>\n"
        "├ <code>HuggingFaceH4/zephyr-7b-beta</code>\n"
        "├ <code>tiiuae/falcon-7b-instruct</code>\n"
        "└ <code>EleutherAI/gpt-neo-2.7B</code>\n\n"
        "📌 <i>Для смены модели используй</i> <code>.cfg huggingchat </code> в `default_model` название модели, которая нам нужна"
    ),
}

    strings_en = {
    "name": "HuggingChat",
    "no_args": "❌ <b>Enter a query:</b> <code>{}{} {}</code>",
    "no_token": "❌ <b>Token not found! Add:</b> <code>.cfg huggingchat</code>",
    "asking": "🔄 <b>Generating response...</b>",
    "answer": "🤖 <b>Response {}:</b>\n{}\n\n💬 <b>Query:</b> {}",
    "api_error": "🚨 <b>API Error:</b> {}",
    "model_error": "⚠️ <b>Model issue:</b>\n{}",
    "suggest_models": "🏷 <b>Recommended models:</b>\n{}",
    "hf_models": (
        "<b>🦾 Recommended models for use:</b>\n\n"
        "┌ <code>meta-llama/Meta-Llama-3-8B-Instruct</code>\n"
        "├ <code>mistralai/Mistral-7B-Instruct-v0.2</code>\n"
        "├ <code>HuggingFaceH4/zephyr-7b-beta</code>\n"
        "├ <code>tiiuae/falcon-7b-instruct</code>\n"
        "└ <code>EleutherAI/gpt-neo-2.7B</code>\n\n"
        "📌 <i>To change the model, use</i> <code>.cfg huggingchat </code> in `default_model` with the desired model name"
    ),
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
                "HuggingFaceH4/zephyr-7b-beta",
                "🦾 Default model (HuggingFace ID)",
            ),
            loader.ConfigValue(
                "max_new_tokens",
                512,
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
        
        self.recommended_models = [
            "meta-llama/Meta-Llama-3-8B-Instruct",
            "mistralai/Mistral-7B-Instruct-v0.2",
            "HuggingFaceH4/zephyr-7b-beta",
            "tiiuae/falcon-7b-instruct",
            "EleutherAI/gpt-neo-2.7B"
        ]

    async def client_ready(self, client, db):
        self.client = client
        self.db = db

    def _format_prompt(self, model: str, question: str) -> str:
        if "llama" in model.lower():
            return f"[INST] {question} [/INST]"
        elif "zephyr" in model.lower():
            return f"<|user|>\n{question}</s>\n<|assistant|>"
        elif "mistral" in model.lower():
            return f"[INST] {question} [/INST]"
        elif "gpt-neo" in model.lower():
            return f"{question}\n"  # ВИПРАВЛЕНО ВІДСТУПИ
        else:
            return question

    @loader.command()
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
            
            if response.status_code == 503:
                suggestions = "\n".join([f"• <code>{m}</code>" for m in self.recommended_models])
                error_msg += f"\n\n{self.strings['suggest_models'].format(suggestions)}"
            
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