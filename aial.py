# meta developer: @blazeftg / @wsinfo
# meta version: 1.2.7
# meta hikka: *

import asyncio
import time
from telethon import events
from telethon.tl.types import Message
from .. import loader, utils

@loader.tds
class AskPlexMod(loader.Module):
    """
    Модуль для взаємодії з AI ботом (ID: 6218783903).
    Автоматичний рестарт при некоректній відповіді.
    """

    strings = {
        "name": "AskAI",
        "loading": "🔄 <b>Запитую AuthorAi...</b>",
        "restarting": "⚠️ <b>Відповідь некоректна або тайм-аут. Перезапускаю бота...</b>",
        "no_args": "🚫 <b>Ви не ввели запит.</b>\nНапишіть <code>.а &lt;текст&gt;</code>",
        "start_text": "<b>🤖 AuthorAi:</b>\n",
        "context_text": "✅ <b>Діалог з AuthorAi скинуто.</b>",
        "timeout_error": "⏳ <b>AuthorAi не відповів належним чином після перезапуску.</b>",
        "trigger_prefix": "ас ",
        "mode_on": "✅ <b>Режим тригера увімкнено.</b>",
        "mode_off": "ℹ️ <b>Режим тригера вимкнено.</b>",
        "chat_added": "✅ <b>Чат додано до списку дозволених.</b>",
        "chat_already_added": "ℹ️ <b>Цей чат вже є у списку дозволених.</b>",
        "powered_by": "\n\n<a href='https://t.me/wsinfo/'>Про Автора</a>"
                      " | <a href='https://authorche.top/donate'>Підтримати❤️‍🔥</a>"
                      "\n————————————\n"
                      "Powered by <a href='https://authorche.top'>AuthorChe</a>",
        "wait_limit": "⏳ <b>Ліміт запитів. Зачекайте {} с.</b>",
        "error_send": "❌ <b>Помилка:</b> <code>{}</code>",
    }

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
        )

    async def client_ready(self, client, db):
        self.client = client
        self.db = db
        self.me = await client.get_me()
        # ID бота, якого вказав юзер
        self.bot_id = 6218783903
        self.last_request_time = {}
        self.request_cooldown = 3

    async def _check_rate_limit(self, user_id: int) -> float or None:
        current_time = time.time()
        if user_id in self.last_request_time:
            time_passed = current_time - self.last_request_time[user_id]
            if time_passed < self.request_cooldown:
                return round(self.request_cooldown - time_passed, 1)
        return None

    def _validate_response(self, text: str) -> bool:
        """Перевіряє, чи містить відповідь ключові маркери формату"""
        required_keywords = ["Причина:", "Тривалість:", "Рівень загрози:"]
        # Перевіряємо, чи є хоча б 2 з 3 ключових фраз, щоб уникнути помилок через дрібні зміни
        matches = sum(1 for keyword in required_keywords if keyword in text)
        return matches >= 2

    async def message_q(self, text: str, user_id: int, message_to_edit=None):
        """Логіка: Запит -> Чекаємо 15с -> Перевірка -> (Якщо погано: /restart -> Запит)"""
        async with self.client.conversation(user_id, timeout=125) as conv:
            # === СПРОБА 1 ===
            try:
                await conv.send_message(text)
                
                # Чекаємо відповідь максимум 15 секунд для перевірки "швидкої та правильної" реакції
                try:
                    response = await conv.get_response(timeout=15)
                    
                    # Якщо бот каже "Thinking...", чекаємо редагування, але в межах тих самих 15с (сумарно)
                    if "Thinking" in response.text or "Запрос принят" in response.text:
                         response = await conv.wait_event(
                            events.MessageEdited(chats=user_id, func=lambda e: e.id == response.id),
                            timeout=15
                        )
                        # Отримуємо об'єкт повідомлення з події
                         if isinstance(response, events.MessageEdited.Event):
                             response = response.message

                    # ВАЛІДАЦІЯ
                    if not self._validate_response(response.text):
                        raise ValueError("Invalid format")
                    
                    # Якщо все ок - повертаємо відповідь
                    await conv.mark_read()
                    return response

                except (asyncio.TimeoutError, ValueError):
                    # Якщо тайм-аут 15с або формат невірний - йдемо в блок except
                    pass

            except Exception as e:
                # Ловимо помилки відправки першого повідомлення
                pass

            # === ЛОГІКА RESTART (Якщо перша спроба не вдалася) ===
            if message_to_edit:
                await utils.answer(message_to_edit, self.strings["restarting"])
            
            # 1. Шлемо /restart
            await conv.send_message("/restart")
            # 2. Чекаємо трохи, поки бот "очухається"
            await asyncio.sleep(2) 
            
            # 3. Шлемо запит знову
            await conv.send_message(text)

            # 4. Чекаємо відповідь (тепер даємо більше часу, бо це вже "надійна" спроба)
            try:
                response = await conv.get_response(timeout=60)
                
                if "Thinking" in response.text or "Запрос принят" in response.text:
                    response = await conv.wait_event(
                        events.MessageEdited(chats=user_id, func=lambda e: e.id == response.id),
                        timeout=60
                    )
                    if isinstance(response, events.MessageEdited.Event):
                        response = response.message
                
                await conv.mark_read()
                return response
            except asyncio.TimeoutError:
                return "TIMEOUT"

    async def аcmd(self, message: Message):
        """{text} - обробити текст через AuthorAi"""
        args = utils.get_args_raw(message)
        if not args:
            return await utils.answer(message, self.strings["no_args"])

        remaining_time = await self._check_rate_limit(message.sender_id)
        if remaining_time:
            return await utils.answer(message, self.strings["wait_limit"].format(remaining_time))
            
        processing_msg = await utils.answer(message, self.strings["loading"])

        # Викликаємо з новим ID
        response = await self.message_q(args, self.bot_id, message_to_edit=processing_msg)

        if response == "TIMEOUT" or response is None:
            text = self.strings["timeout_error"]
        elif hasattr(response, 'text'):
            text = self.strings["start_text"] + response.text.replace("Perplexity", "AuthorAi")
            text += self.strings["powered_by"]
        else:
            text = self.strings["timeout_error"]

        await utils.answer(processing_msg, text)
        if message.is_reply:
             await message.delete()

        self.last_request_time[message.sender_id] = time.time()

    async def ааcmd(self, message: Message):
        """- скинути діалог"""
        async with self.client.conversation(self.bot_id) as conv:
            await conv.send_message("/restart") # Для цього бота краще restart, ніж newchat
            await conv.mark_read()
        await utils.answer(message, self.strings["context_text"])

    async def askmecmd(self, message: Message):
        """- увімкнути/вимкнути режим тригера 'ас '"""
        self.config["trigger_mode"] = not self.config["trigger_mode"]
        await utils.answer(message, self.strings["mode_on"] if self.config["trigger_mode"] else self.strings["mode_off"])

    async def addcmd(self, message: Message):
        """- додати чат до дозволених"""
        allowed = list(self.config["allowed_chats"])
        if message.chat_id not in allowed:
            allowed.append(message.chat_id)
            self.config["allowed_chats"] = allowed
            await utils.answer(message, self.strings["chat_added"])
        else:
            await utils.answer(message, self.strings["chat_already_added"])

    @loader.watcher(no_commands=True)
    async def watcher(self, message: Message):
        if (
            not self.config["trigger_mode"]
            or not isinstance(message, Message)
            or message.sender_id == self.me.id
            or not message.text
            or message.chat_id not in self.config["allowed_chats"]
            or not message.text.lower().startswith(self.strings["trigger_prefix"])
        ):
            return
            
        query_text = message.text[len(self.strings["trigger_prefix"]):].strip()
        if not query_text: return
            
        response = await self.message_q(query_text, self.bot_id)
        
        if hasattr(response, 'text') and response.text:
            text = self.strings["start_text"] + response.text.replace("Perplexity", "AuthorAi")
            text += self.strings["powered_by"]
            await utils.answer(message, text)
