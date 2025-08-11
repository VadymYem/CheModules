# meta developer: @blazeftg / @wsinfo
# meta version: 1.2.4
# meta hikka: *

import asyncio
import time
from telethon import events
from telethon.tl.types import Message
from .. import loader, utils

@loader.tds
class AskPlexMod(loader.Module):
    """
    Безкоштовний модуль для взаємодії з @askplexbot,
    який коректно очікує на редагування повідомлення.
    Включає режим тригера з розширеними налаштуваннями.
    """

    strings = {
        "name": "AskPlexAI",
        "loading": "🔄 <b>Запитую AuthorAi...</b>",
        "no_args": "🚫 <b>Ви не ввели запит.</b>\nНапишіть <code>.а &lt;текст&gt;</code>",
        "start_text": "<b>🤖 AuthorAi:</b>\n",
        "context_text": "✅ <b>Діалог з AuthorAi скинуто.</b>",
        "timeout_error": "⏳ <b>AuthorAi не відповів протягом 120 секунд.</b> Спробуйте ще раз.",
        "trigger_prefix": "ас ",
        "mode_on": "✅ <b>Режим тригера увімкнено.</b>\nТепер повідомлення, що починаються з <code>ас </code>, будуть оброблятися в дозволених чатах.",
        "mode_off": "ℹ️ <b>Режим тригера вимкнено.</b>",
        "chat_added": "✅ <b>Чат додано до списку дозволених для тригера.</b>",
        "chat_already_added": "ℹ️ <b>Цей чат вже є у списку дозволених.</b>",
        "powered_by": "\n\n<a href='https://t.me/wsinfo/'>Про Автора</a>"
                      " | <a href='https://authorche.top/donate'>Підтримати❤️‍🔥</a>"
                      "\n————————————\n"
                      "Powered by <a href='https://authorche.top'>AuthorChe</a>",
        "wait_limit": "⏳ <b>Занадто багато запитів.</b> Будь ласка, зачекайте <b>{} секунд</b> перед наступним використанням.",
    }

    def __init__(self):
        """Ініціалізація конфігурації модуля"""
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
            ), # <-- ВАЛІДАТОР ПРИБРАНО ДЛЯ СУМІСНОСТІ
        )

    async def client_ready(self, client, db):
        """Ініціалізація клієнта та інших змінних"""
        self.client = client
        self.db = db
        self.me = await client.get_me()
        self.gpt_free = "@askplexbot"
        self.last_request_time = {}
        self.request_cooldown = 5  # 5 секунд

    async def _check_rate_limit(self, user_id: int) -> float or None:
        """Перевіряє ліміт запитів для користувача."""
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
        """Відправляє повідомлення та очікує на повну відповідь, відстежуючи редагування."""
        async with self.client.conversation(user_id, timeout=125) as conv:
            msg_to_bot = await conv.send_message(text)
            response = await conv.get_response()

            if "Міркую... ⏳" in response.text or "Thinking... ⏳" in response.text:
                try:
                    edited_event = await conv.wait_event(
                        events.MessageEdited(
                            chats=user_id,
                            func=lambda event: event.id == response.id
                        ),
                        timeout=120
                    )
                    response = edited_event
                except asyncio.TimeoutError:
                    return Message(message=self.strings["timeout_error"])

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
        """{text} - обробити текст через AuthorAi"""
        args = utils.get_args_raw(message)
        if not args:
            await utils.answer(message, self.strings["no_args"])
            return

        remaining_time = await self._check_rate_limit(message.sender_id)
        if remaining_time:
            await utils.answer(message, self.strings["wait_limit"].format(remaining_time))
            return
            
        processing_msg = await utils.answer(message, self.strings["loading"])

        response = await self.message_q(
            args, self.gpt_free, mark_read=True, delete=False, ignore_answer=False
        )

        if not response or not response.text:
            text = self.strings["timeout_error"]
        else:
            text = self.strings["start_text"] + response.text.replace("Perplexity", "AuthorAi")
            text += self.strings["powered_by"]

        await utils.answer(processing_msg, text)
        if message.is_reply:
             await message.delete()

        self.last_request_time[message.sender_id] = time.time()

    async def ааcmd(self, message: Message):
        """- скинути діалог і почати новий"""
        await self.message_q(
            "/newchat", self.gpt_free, mark_read=True, delete=True, ignore_answer=True
        )
        await utils.answer(message, self.strings["context_text"])

    async def askmecmd(self, message: Message):
        """- увімкнути/вимкнути режим тригера 'ас '"""
        current_mode = self.config["trigger_mode"]
        self.config["trigger_mode"] = not current_mode
        
        if not current_mode:
            await utils.answer(message, self.strings["mode_on"])
        else:
            await utils.answer(message, self.strings["mode_off"])

    async def addcmd(self, message: Message):
        """- додати поточний чат до списку дозволених для тригера"""
        chat_id = message.chat_id
        # Потрібно отримати список з конфігу, змінити його і зберегти назад
        allowed_chats = self.config["allowed_chats"]
        if chat_id not in allowed_chats:
            allowed_chats.append(chat_id)
            self.config["allowed_chats"] = allowed_chats
            await utils.answer(message, self.strings["chat_added"])
        else:
            await utils.answer(message, self.strings["chat_already_added"])

    @loader.watcher(no_commands=True)
    async def watcher(self, message: Message):
        """Слухач для тригера - автоматично обробляє повідомлення з префіксом 'ас '"""
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
            response = await self.message_q(
                query_text, self.gpt_free, mark_read=True, delete=False, ignore_answer=False
            )
            
            if response and response.text:
                text = self.strings["start_text"] + response.text.replace("Perplexity", "AuthorAi")
                text += self.strings["powered_by"]
                await utils.answer(message, text)
                self.last_request_time[message.sender_id] = time.time()
                
        except Exception as e:
            await utils.answer(message, f"❌ <b>Помилка:</b> {str(e)}")
