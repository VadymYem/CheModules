# meta developer: @blazeftg / @wsinfo
# meta version: 1.3.2
# meta hikka: *

import asyncio
import time
from telethon import events
from telethon.tl.types import Message
from .. import loader, utils

@loader.tds
class AskPlexMod(loader.Module):
    """
    Покращений модуль для взаємодії з АІ.
    v1.3.2 - Gigachat + авто-очищення джерел.
    """

    strings = {
        "name": "AskAI_Analyst",
        "loading": "🔄 <b>Аналізую (GigaChat)...</b>",
        "no_args": "🚫 <b>Ви не ввели запит.</b>\nНапишіть <code>.а &lt;текст&gt;</code>",
        "start_text": "<b>🤖 Analyst AI:</b>\n",
        "context_text": "✅ <b>Контекст діалогу скинуто.</b>",
        "timeout_error": "⏳ <b>AI не відповів вчасно.</b> Спробуйте ще раз.",
        "trigger_prefix": "ас ",
        "mode_on": "✅ <b>Режим тригера увімкнено.</b>",
        "mode_off": "ℹ️ <b>Режим тригера вимкнено.</b>",
        "chat_added": "✅ <b>Чат додано до списку дозволених.</b>",
        "chat_already_added": "ℹ️ <b>Цей чат вже є у списку.</b>",
        "powered_by": "\n\n<a href='https://t.me/wsinfo/'>Про Автора</a>"
                      " | <a href='https://authorche.top/donate'>Підтримати❤️‍🔥</a>"
                      "\n————————————\n"
                      "Powered by <a href='https://authorche.top'>AuthorChe</a>",
        "wait_limit": "⏳ <b>Ліміт запитів.</b> Зачекайте <b>{} с.</b>",
    }

    # СИСТЕМНИЙ ПРОМТ
    # Залишаємо англійською для кращого дотримання ролі, але адаптуємо під GigaChat
    SYSTEM_PROMPT = (
        "ROLE: Expert Military Strategic Analyst. "
        "TASK: Analyze the input and fill the OUTPUT TEMPLATE. "
        "RULES: "
        "1. NO IMAGES. TEXT ONLY. "
        "2. Do not list sources or references. "
        "3. Keep it brief and dry. "
        "\n\nDATA:\n"
    )

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "trigger_mode",
                False,
                "Чи увімкнений режим тригера 'ас '",
                validator=loader.validators.Boolean(),
            ),
            loader.ConfigValue(
                "allowed_chats",
                [],
                "Список ID чатів, де тригер 'ас ' буде працювати",
            ), 
            loader.ConfigValue(
                "use_analyst_mode",
                True,
                "Додавати системний промт аналітика до запитів",
                validator=loader.validators.Boolean(),
            ),
            loader.ConfigValue(
                "bot_username",
                "@gigachat_bot", 
                "Юзернейм бота",
            ),
        )

    async def client_ready(self, client, db):
        self.client = client
        self.db = db
        self.me = await client.get_me()
        self.gpt_bot = self.config["bot_username"]
        self.last_request_time = {}
        self.request_cooldown = 5

    def _clean_response(self, text: str) -> str:
        """Вирізає сміття з відповіді GigaChat"""
        # Список фраз, після яких треба обрізати текст
        cut_triggers = [
            "Для ответа использовал",
            "Источники:",
            "Sources:",
            "Для відповіді використав"
        ]
        
        cleaned = text
        for trigger in cut_triggers:
            if trigger in cleaned:
                cleaned = cleaned.split(trigger)[0]
        
        # Прибираємо зайві пробели та рекламу
        cleaned = cleaned.strip()
        cleaned = cleaned.replace("Perplexity", "AuthorAi").replace("Start exploring", "")
        return cleaned

    def _construct_prompt(self, user_text: str) -> str:
        """Очищає запит користувача і додає системний промт"""
        
        # Фраза, яку треба автоматично видалити з входу
        garbage_phrase = "Ніяких картинок не шукай, просто дай текстом  максимально точний аналіз."
        # Також чистимо варіації (на випадок різних пробілів)
        clean_text = user_text.replace(garbage_phrase, "")
        clean_text = clean_text.replace("Ніяких картинок не шукай, просто дай текстом максимально точний аналіз.", "")
        
        if self.config["use_analyst_mode"]:
            return f"{self.SYSTEM_PROMPT}{clean_text}"
        return clean_text

    async def _check_rate_limit(self, user_id: int) -> float or None:
        current_time = time.time()
        if user_id in self.last_request_time:
            time_passed = current_time - self.last_request_time[user_id]
            if time_passed < self.request_cooldown:
                return round(self.request_cooldown - time_passed, 1)
        return None

    async def message_q(
        self,
        text: str,
        user_id: int,
        mark_read: bool = False,
        delete: bool = False,
        ignore_answer: bool = False,
    ) -> Message or None:
        async with self.client.conversation(user_id, timeout=125) as conv:
            msg_to_bot = await conv.send_message(text)
            
            response = await conv.get_response()

            # Фільтруємо "думки" бота
            while response.text and (
                "Запрос" in response.text 
                or "принят" in response.text 
                or "Generating" in response.text 
                or "Печатает" in response.text
            ):
                response = await conv.get_response()

            if mark_read:
                await conv.mark_read()
            
            if delete:
                await msg_to_bot.delete()
                if response:
                    await response.delete()
            
            if ignore_answer:
                return None

            return response

    async def аcmd(self, message: Message):
        """{text} - обробити текст через AI-аналітика"""
        args = utils.get_args_raw(message)
        if not args:
            await utils.answer(message, self.strings["no_args"])
            return

        self.gpt_bot = self.config["bot_username"]

        remaining_time = await self._check_rate_limit(message.sender_id)
        if remaining_time:
            await utils.answer(message, self.strings["wait_limit"].format(remaining_time))
            return
            
        processing_msg = await utils.answer(message, self.strings["loading"])

        final_query = self._construct_prompt(args)

        try:
            response = await self.message_q(
                final_query, self.gpt_bot, mark_read=True, delete=False, ignore_answer=False
            )

            if not response or not response.text:
                text = self.strings["timeout_error"]
            else:
                # Очищаємо відповідь від джерел
                clean_text = self._clean_response(response.text)
                
                text = self.strings["start_text"] + clean_text
                text += self.strings["powered_by"]

            await utils.answer(processing_msg, text)
            if message.is_reply:
                 await message.delete()

            self.last_request_time[message.sender_id] = time.time()
        except Exception as e:
            await utils.answer(processing_msg, f"❌ Error: {e}")

    async def ааcmd(self, message: Message):
        """- скинути контекст діалогу"""
        self.gpt_bot = self.config["bot_username"]
        # Для GigaChat команда скидання може бути іншою, але /newchat або /reset зазвичай працюють
        # Якщо ні - доведеться просто писати "Забудь все"
        await self.message_q(
            "/restart", self.gpt_bot, mark_read=True, delete=True, ignore_answer=True
        )
        await utils.answer(message, self.strings["context_text"])

    async def askmecmd(self, message: Message):
        """- перемикач режиму тригера"""
        current_mode = self.config["trigger_mode"]
        self.config["trigger_mode"] = not current_mode
        
        if not current_mode:
            await utils.answer(message, self.strings["mode_on"])
        else:
            await utils.answer(message, self.strings["mode_off"])

    async def addcmd(self, message: Message):
        """- додати чат у дозволені"""
        chat_id = message.chat_id
        allowed_chats = self.config["allowed_chats"]
        if chat_id not in allowed_chats:
            allowed_chats.append(chat_id)
            self.config["allowed_chats"] = allowed_chats
            await utils.answer(message, self.strings["chat_added"])
        else:
            await utils.answer(message, self.strings["chat_already_added"])

    @loader.watcher(no_commands=True)
    async def watcher(self, message: Message):
        """Автоматична обробка повідомлень з префіксом 'ас '"""
        if (
            not self.config["trigger_mode"]
            or not isinstance(message, Message)
            or message.sender_id == self.me.id
            or message.via_bot_id
            or not message.text
            or message.chat_id not in self.config["allowed_chats"]
            or not message.text.lower().startswith(self.strings["trigger_prefix"])
        ):
            return
            
        remaining_time = await self._check_rate_limit(message.sender_id)
        if remaining_time:
            return

        query_text = message.text[len(self.strings["trigger_prefix"]):].strip()
        if not query_text:
            return
            
        try:
            self.gpt_bot = self.config["bot_username"]
            final_query = self._construct_prompt(query_text)

            response = await self.message_q(
                final_query, self.gpt_bot, mark_read=True, delete=False, ignore_answer=False
            )
            
            if response and response.text:
                clean_text = self._clean_response(response.text)
                text = self.strings["start_text"] + clean_text
                text += self.strings["powered_by"]
                await utils.answer(message, text)
                self.last_request_time[message.sender_id] = time.time()
                
        except Exception as e:
            await utils.answer(message, f"❌ <b>Помилка:</b> {str(e)}")
