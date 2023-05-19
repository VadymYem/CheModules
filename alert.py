__version__ = (1, 1, 0)
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineQueryResultArticle,
    InlineKeyboardButton,
    InputTextMessageContent,
)
from asyncio import sleep
from telethon.tl.types import Message
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.utils import get_display_name
from .. import loader  # noqa
import logging
from ..inline.types import InlineQuery
from ..utils import rand
from .. import utils  # noqa

logger = logging.getLogger(__name__)

ua = [
    "all",
    "Кіровоградська_область",
    "Попаснянська_територіальна_громада",
    "Бердянський_район",
    "Полтавська_область",
    "м_Краматорськ_та_Краматорська_територіальна_громада",
    "м_Старокостянтинів_та_Старокостянтинівська_територіальна_громада",
    "Ізюмський_район",
    "Покровська_територіальна_громада",
    "Волноваський_район",
    "Краматорський_район",
    "Київська_область",
    "м_Київ",
    "Херсонська_область",
    "Ніжинський_район",
    "Бахмутська_територіальна_громада",
    "м_Кремінна_та_Кремінська_територіальна_громада",
    "Рівненська_область",
    "Запорізька_область",
    "м_Маріуполь_та_Маріупольська_територіальна_громада",
    "м_Рівне_та_Рівненська_територіальна_громада",
    "м_Черкаси_та_Черкаська_територіальна_громада",
    "Марїнська_територіальна_громада",
    "Сквирська_територіальна_громада",
    "Охтирський_район",
    "м_Конотоп_та_Конотопська_територіальна_громада",
    "Вознесенський_район",
    "Сарненський_район",
    "Миколаївський_район",
    "Смілянська_територіальна_громада",
    "Сєвєродонецький_район",
    "Гірська_територіальна_громада",
    "Костянтинівська_територіальна_громада",
    "Прилуцький_район",
    "м_Пирятин_та_Пирятинська_територіальна_громада",
    "Вишгородська_територіальна_громада",
    "Воскресенська_територіальна_громада",
    "м_Переяслав_та_Переяславська_територіальна_громада",
    "м_Полтава_та_Полтавська_територіальна_громада",
    "м_Вознесенськ_та_Вознесенська_територіальна_громада",
    "Дружківська_територіальна_громада",
    "Золотоніський_район",
    "Макарівська_територіальна_громада",
    "Дубровицька_територіальна_громада",
    "Хмельницька_область",
    "Великоновосілківська_територіальна_громада",
    "м_Шостка_та_Шосткинська_територіальна_громада",
    "Львівська_область",
    "Волинська_область",
    "Первомайський_район",
    "м_Запоріжжя_та_Запорізька_територіальна_громада",
    "м_Бровари_та_Броварська_територіальна_громада",
    "Лиманська_територіальна_громада",
    "м_Лисичанськ_та_Лисичанська_територіальна_громада",
    "м_Бориспіль_та_Бориспільська_територіальна_громада",
    "м_Обухів_та_Обухівська_територіальна_громада",
    "Звенигородський_район",
    "Роздільнянський_район",
    "м_Нікополь_та_Нікопольська_територіальна_громада",
    "м_Першотравенськ_та_Першотравенська_територіальна_громада",
    "м_Васильків_та_Васильківська_територіальна_громада",
    "Кропивницький_район",
    "Шепетівський_район",
    "Житомирська_область",
    "Вараський_район",
    "Болградський_район",
    "Закарпатська_область",
    "Шосткинський_район",
    "Гребінківська_територіальна_громада",
    "Чернівецька_область",
    "Синельниківський_район",
    "Уманська_територіальна_громада",
    "Олешківська_територіальна_громада",
    "м_Кременчук_та_Кременчуцька_територіальна_громада",
    "Коростенський_район",
    "Купянський_район",
    "Подільський_район",
    "м_Мелітополь_та_Мелітопольська_територіальна_громада",
    "Ізмаїльський_район",
    "Вінницька_область",
    "м_Славутич_та_Славутицька_територіальна_громада",
    "Бородянська_територіальна_громада",
    "Святогірська_територіальна_громада",
    "Добропільська_територіальна_громада",
    "Черкаський_район",
    "Пологівський_район",
    "м_Сарни_та_Сарненська_територіальна_громада",
    "Маріупольський_район",
    "Лозівський_район",
    "Березівський_район",
    "Українська_територіальна_громада",
    "м_Охтирка_та_Охтирська_територіальна_громада",
    "Жашківська_територіальна_громада",
    "Житомирський_район",
    "Донецький_район",
    "м_Кривий_Ріг_та_Криворізька_територіальна_громада",
    "Радомишльська_територіальна_громада",
    "м_Дніпро_та_Дніпровська_територіальна_громада",
    "м_Миколаїв_та_Миколаївська_територіальна_громада",
    "Гостомелська_територіальна_громада",
    "м_Миргород_та_Миргородська_територіальна_громада",
    "Сумська_область",
    "Торецька_територіальна_громада",
    "м_Ватутіне_та_Ватутінська_територіальна_громада",
    "м_Коростень_та_Коростенська_територіальна_громада",
    "Харківський_район",
    "Уманський_район",
    "Сумський_район",
    "Одеський_район",
    "БілгородДністровський_район",
    "Тернопільська_область",
    "Первомайська_територіальна_громада",
    "м_Первомайськ_та_Первомайська_територіальна_громада",
    "Чугуївський_район",
    "м_Фастів_та_Фастівська_територіальна_громада",
    "Миронівська_територіальна_громада",
    "м_Лубни_та_Лубенська_територіальна_громада",
    "Черкаська_область",
    "Луганська_область",
    "м_Житомир_та_Житомирська_територіальна_громада",
    "Новоукраїнський_район",
    "м_Словянськ_та_Словянська_територіальна_громада",
    "Чернігівський_район",
    "м_Очаків_та_Очаківська_територіальна_громада",
    "Вугледарська_територіальна_громада",
    "м_Сєвєродонецьк_та_Сєвєродонецька_територіальна_громада",
    "Дніпропетровська_область",
    "Запорізький_район",
    "Широківська_територіальна_громада",
    "Узинська_територіальна_громада",
    "Миколаївська_область",
    "Харківська_область",
    "НовоградВолинський_район",
    "Курахівська_територіальна_громада",
    "м_Рубіжне_та_Рубіжанська_територіальна_громада",
    "Донецька_область",
    "м_Суми_та_Сумська_територіальна_громада",
    "м_Біла_Церква_та_Білоцерківська_територіальна_громада",
    "Голованівський_район",
    "Одеська_область",
    "Павлоградський_район",
    "Чернігівська_область",
    "Сватівський_район",
    "ІваноФранківська_область",
    "Покровський_район",
    "Бахмутський_район",
]


class AirAlertUaTESTMod(loader.Module):
    """🇺🇦 Попередження про повітряну тривогу.
    Потрібно бути підписаним на @air_alert_ua та включені повідомлення у вашому боті"""

    strings = {"name": "AirAlertTEST"}

    async def client_ready(self, client, db) -> None:
        self.db = db
        self.client = client
        self.regions = db.get(self.strings["name"], "regions", [])
        self.bot_id = (await self.inline.bot.get_me()).id
        self.nametag = db.get(self.strings["name"], "nametag", "")
        self.forwards = db.get(self.strings["name"], "forwards", [])
        self.me = (await client.get_me()).id
        try:
            await client(
                JoinChannelRequest(await self.client.get_entity("t.me/air_alert_ua"))
            )
        except Exception:
            logger.error("Can't join t.me/air_alert_ua")

    async def alertforwardcmd(self, message: Message) -> None:
        """Перенаправлення попереджень на інші чати.
        Щоб додати/видалити, введіть команду з посиланням на чат.
        Щоб переглянути чати, введіть команду без аргументів
        Для встановлення .alertforward set <text>"""
        text = utils.get_args_raw(message)
        if text[:3] == "set":
            self.nametag = text[4:]
            self.db.set(self.strings["name"], "nametag", self.nametag)
            return await utils.answer(
                message,
                f"🏷 <b>Табличка успішно встановлена: <code>{self.nametag}</code></b>",
            )
        if not text:
            chats = "<b>Поточні чати для перенаправлення: </b>\n"
            for chat in self.forwards:
                chats += f"{get_display_name(await self.client.get_entity(chat))}\n"
            await utils.answer(message, chats)
            return
        try:
            chat = (await self.client.get_entity(text.replace("https://", ""))).id
        except Exception:
            await utils.answer(message, "<b>Чат не знайдено</b>")
            return
        if chat in self.forwards:
            self.forwards.remove(chat)
            self.db.set(self.strings["name"], "forwards", self.forwards)
            await utils.answer(message, "<b>Чат успішно видалено для перенаправлення</b>")
        else:
            self.forwards.append(chat)
            self.db.set(self.strings["name"], "forwards", self.forwards)
            await utils.answer(
                message, "<b>Чат успішно встановлений для перенаправлення</b>"
            )

    async def alert_inline_handler(self, query: InlineQuery) -> None:
        """Вибір регіонів.
        Щоб отримати всі попередження, введіть alert all.
        Щоб переглянути ваші регіони alert my"""
        text = query.args
        if not text:
            result = ua
        elif text == "my":
            result = self.regions
        else:
            result = [region for region in ua if text.lower() in region.lower()]
        if not result:
            await query.e404()
            return
        res = [
            InlineQueryResultArticle(
                id=rand(20),
                title=f"{'✅' if reg in self.regions else '❌'}{reg if reg != 'all' else 'Всі повідомлення'}",
                description=f"Натисніть щоб {'видалити' if reg in self.regions else 'додати'}"
                if reg != "all"
                else f"🇺🇦 Натисніть щоб {'вимкнути' if 'all' in self.regions else 'ввімкнути'} всі повідомлення",
                input_message_content=InputTextMessageContent(
                    f"⌛ Редагування регіону <code>{reg}</code>",
                    parse_mode="HTML",
                ),
            )
            for reg in result[:50]
        ]
        await query.answer(res, cache_time=0)

    async def watcher(self, message: Message) -> None:
        if (
                getattr(message, "out", False)
                and getattr(message, "via_bot_id", False)
                and message.via_bot_id == self.bot_id
                and "⌛ Редагування регіону" in getattr(message, "raw_text", "")
        ):
            self.regions = self.db.get(self.strings["name"], "regions", [])
            region = message.raw_text[25:]
            state = "додано"
            if region not in self.regions:
                self.regions.append(region)
            else:
                self.regions.remove(region)
                state = "видалено"
            self.db.set(self.strings["name"], "regions", self.regions)
            try:
                e = await self.client.get_entity("t.me/air_alert_ua")
                sub = not e.left
            except Exception:
                sub = False
            n = "\n"
            res = f"<b>Регіон <code>{region}</code> успішно {state}</b>{n}"
            if not sub:
                res += (
                    "<b>НЕ ВИХОДИ З @air_alert_ua (інакше нічого працювати не буде)</b>"
                )
                await self.client(
                    JoinChannelRequest(
                        await self.client.get_entity("t.me/air_alert_ua")
                    )
                )
            await self.inline.form(res, message=message)
        if (
                getattr(message, "peer_id", False)
                and getattr(message.peer_id, "channel_id", 0) == 1766138888
                and (
                "all" in self.regions
                or any(reg in message.raw_text for reg in self.regions)
        )
        ):
            for _ in range(1):
                await self.inline.bot.send_message(
                    self.me, message.text, parse_mode="HTML"
                )
                await sleep(1)
            for chat in self.forwards:
                await self.client.send_message(
                    chat,
                    message.text + "\n\n" + self.nametag,
                )
        return
