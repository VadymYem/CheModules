                               
# meta developer: @Vadym_Yem

__version__ = (4, 1, 5)

import logging, time
from telethon.utils import get_display_name
from aiogram.types import Message as AiogramMessage
from .. import loader, utils
from ..inline.types import InlineCall

logger = logging.getLogger(__name__)


@loader.unrestricted
@loader.ratelimit
@loader.tds
class FeedbackBotMod(loader.Module):

    strings = {
        "name": "📥 Feedback",
        "start": ("✌️ Привiт, вітаю в меню зворотнього зв'язку з {}"),
        "fb_message": "📝 Натисніть перед відправкою  повідомлення",
        "wait": "⏳ Ви можете відправити повідомлення через {} секунд(-и)",
        "feedback": "📝 Write 1 message",
        "sent": "✅ <b>Your message has been sent to owner</b>",
        "banned": "🚫 На жаль ти порушив одне з правил. Тому я вимушений обмежити доступ...",
        "user_banned": "🚫 {} забанен",
         "/nometa": "👨‍🎓 <b><u>Правила общения в Интернете:</u></b>\n\n <b>🚫 <u>Не пиши</u> просто 'Привет'</b>\n <b>🚫 <u>Не рекламируй </u> ничего</b>\n <b>🚫 <u>Не оскорбляй</u> никого</b>\n <b>🚫 <u>Не разбивай</u> сообщения на миллион кусочков</b>\n <b> Спасибо что прочитали :) </b>",
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            "ratelimit",
            "1",
            lambda: "Rate limit(in minutes)",
        )
        self.name = self.strings["name"]

    async def client_ready(self, client, db):
        self._client = client

        self._name = utils.escape_html(get_display_name(await client.get_me()))

        self._ratelimit = {}
        self._ban_list = []

        self.__doc__ = "Module from add feedback bot 👨‍💻\n\n" \
        "📝 Dev: @Vadym_Yem\n" \
        "📥 Source: @Vadym_Yem\n" \
        f"🏔 Feedback command: /feedback\n\n" \
        


    async def aiogram_watcher(self, message: AiogramMessage):
        if message.text == "/feedback":
            if str(message.from_user.id) in str(self._ban_list):
                return await message.answer(
                    self.strings("banned")
                )
            _markup = self.inline.generate_markup(
                {"text": self.strings("fb_message"), "data": "fb_message"}
            )
            await message.answer(
                self.strings("start").format(self._name),
                reply_markup=_markup,
            )
        if self.inline.gs(message.from_user.id) == "fb_send_message":
            await self.inline.bot.forward_message(
                self._tg_id,
                message.chat.id,
                message.message_id,
            )
            _markup = self.inline.generate_markup(
                {"text": "🚫 Ban", "data": f"fb_ban/{message.from_user.id}"}
            )
            await self.inline.bot.send_message(
                self._tg_id,
                f"{message.chat.id}",
                reply_markup=_markup,
            )
            await message.answer(self.strings("sent"))
            self._ratelimit[message.from_user.id] = time.time() + self.config["ratelimit"] * 60
            self.inline.ss(message.from_user.id, False)

    @loader.inline_everyone
    async def feedback_callback_handler(self, call: InlineCall):
        if call.data == "fb_cancel":
            self.inline.ss(call.from_user.id, False)
            await self.inline.bot.delete_message(
                call.message.chat.id,
                call.message.message_id,
            )
            return
        if call.data.split('/')[0] == "fb_ban":
            fb_ban_id = call.data.split('/')[1]
            if str(fb_ban_id) in str(self._ban_list):
                pass
            else:
                self._ban_list.append(fb_ban_id)
                await call.answer(self.strings("user_banned").format(fb_ban_id))

        if call.data != "fb_message":
            return

        if str(call.from_user.id) in str(self._ban_list):
            await call.answer(
                self.strings("banned"),
                show_alert=True,
            )

        if (
            call.from_user.id in self._ratelimit
            and self._ratelimit[call.from_user.id] > time.time()
        ):
            await call.answer(
                self.strings("wait").format(self._ratelimit[call.from_user.id] - time.time()),
                show_alert=True,
            )
            return

        self.inline.ss(call.from_user.id, "fb_send_message")
        
        await call.answer(
            self.strings("feedback").format(self._name, self.config["ratelimit"]),
        )
