import io
import json

import grapheme
from telethon.tl.types import Message
from telethon.utils import get_display_name

from .. import loader, utils


@loader.tds
class RPMod(loader.Module):
    """RPMod (Male/Universal Ukrainian Version)"""

    strings = {
        "name": "RPMod",
    }

    strings_uk = {
        "args": "🚫 <b>Невірні аргументи</b>",
        "success": "✅ <b>Успішно</b>",
        "rp_on": "✅ <b>RPM увімкнено в цьому чаті</b>",
        "rp_off": "✅ <b>RPM вимкнено в цьому чаті</b>",
        "rplist": "🦊 <b>Поточні RP команди:</b>\n\n{}",
        "backup_caption": (
            "🦊 <b>Мої RP команди. Ти можеш відновити їх використовуючи"
            " </b><code>.rprestore</code>"
        ),
        "no_file": "🚫 <b>Дай відповідь на файл .json</b>",
        "restored": (
            "✅ <b>RP команди відновлено. Переглянути: "
            " </b><code>.rplist</code>"
        ),
        "_cmd_doc_rp": (
            "<команда> <повідомлення> - Додати RP команду. Якщо повідомлення не вказано,"
            " команда буде видалена"
        ),
        "_cmd_doc_rptoggle": "Увімкнути\\вимкнути RP режим в поточному чаті",
        "_cmd_doc_rplist": "Показати список всіх RP команд",
        "_cmd_doc_rpbackup": "Зберегти RP команди у файл (бекап)",
        "_cmd_doc_rprestore": "Відновити RP команди з файлу",
        "_cmd_doc_rpchats": "Показати чати, де активний режим RP",
        "_cls_doc": "Українізований RPMod з підтримкою коментарів (New Format).",
    }

    async def client_ready(self, client, db):
        # База дій (Чоловіча версія)
        default_rp = {
            # === Романтика / До дівчини ===
            "поцілувати": "💋 пристрасно поцілував",
            "цьом": "😘 ніжно цьомнув",
            "обійняти": "🤗 міцно притиснув до себе",
            "пригорнути": "🫂 пригорнув і не відпускає",
            "шия": "🧛 залишив засос на шиї",
            "рука": "🤝 взяв за руку",
            "вушко": "👂 прошепотів на вушко",
            "на руки": "🏋️‍♂️ взяв на руки",
            "зігріти": "🧥 накинув куртку на плечі",
            "масаж": "💆‍♂️ розім'яв плечі",
            "погладити": "🫳 погладив по голові",
            "заспокоїти": "🤫 притиснув до грудей і заспокоїв",
            "дупа": "🍑 ляснув по дупі",
            "шльопати": "👋 відшльопав",
            "ліжко": "🛌 повалив на ліжко",
            "роздягнути": "👗 знімає одяг з",
            "кусати": "🦷 грайливо вкусив",
            "дивитися": "👀 не зводить погляду з",

            # === Спілкування / Онлайн ===
            "пінг": "📡 перевіряє зв'язок з",
            "спам": "📨 закидав повідомленнями",
            "войс": "🎤 записав голосове для",
            "дзвінок": "📞 набрав",
            "відео": "📹 ввімкнув камеру для",
            "скрін": "📸 зробив скріншот листування з",
            "мем": "🐸 показав мем",
            "репорт": "⚠️ кинув скаргу на",
            "бан": "🚫 заблокував",
            "чс": "🧱 кинув у чорний список",
            "лайк": "👍 оцінив фото",
            "посилання": "🔗 кинув лінк у",
            "онлайн": "🟢 чекає в мережі на",
            "офлайн": "🔴 пішов спати, залишивши",
            "інет": "📶 скаржиться на пінг",

            # === Емоції / Реакції ===
            "крінж": "😬 зловив крінж з",
            "база": "🫡 видав базу для",
            "жиза": "👌 погоджується, що це жиза з",
            "треш": "🗑️ в ахуї від",
            "фейспалм": "🤦‍♂️ пробив обличчя фейспалмом через",
            "душно": "🥵 відкрив вікно, бо душно від",
            "клоун": "🤡 вручив перуку клоуна",
            "ор": "🤣 волає з",
            "сміх": "😆 сміється з",
            "шок": "😱 в шоці від",
            "злість": "😡 злиться на",
            "ігнор": "😒 ігнорує",
            "сумнів": "🤨 підозріло дивиться на",
            "повага": "🤝 висловив повагу",

            # === Агресія / Бійка ===
            "вдарити": "👊 прописав у щелепу",
            "ляпас": "👋 дав ляпаса",
            "пнути": "🦶 дав підсрачника",
            "стук": "🔨 стукнув по голові",
            "вбити": "🔪 ліквідував",
            "стріляти": "🔫 зробив контрольний постріл у",
            "спалити": "🔥 спалив",
            "втопити": "🌊 пустив на дно",
            "послати": "🖕 послав за російським кораблем",
            "плюнути": "💦 плюнув під ноги",
            "накричати": "🤬 накричав на",
            "задушити": "🧣 схопив за горло",

            # === По-братськи / Їжа ===
            "пиво": "🍻 п'є пиво з",
            "віскі": "🥃 налив віскі для",
            "кава": "☕ п'є каву з",
            "дим": "💨 пустив дим в обличчя",
            "кальян": "😶‍🌫️ передав трубку кальяну",
            "їсти": "🍔 їсть бургер з",
            "шаурма": "🌯 їсть шаурму з",
            "п'ять": "✋ дав п'ять",
            "привітати": "👋 привітався з",
        }
        
        self.rp = self.get("rp", default_rp)
        self.chats = self.get("active", [])

    async def rpcmd(self, message: Message):
        """<команда> <дія> - Додати/Змінити. Без аргументів видаляє."""
        args = utils.get_args_raw(message)
        try:
            command = args.split(" ", 1)[0].lower()
            msg = args.split(" ", 1)[1]
        except Exception:
            if not args:
                await utils.answer(message, self.strings("args"))
                return
            command = args.split(" ", 1)[0].lower()
            if command in self.rp:
                del self.rp[command]
                self.set("rp", self.rp)
                await utils.answer(message, self.strings("success") + f": видалено '{command}'")
            else:
                await utils.answer(message, self.strings("args"))
            return

        self.rp[command] = msg
        self.set("rp", self.rp)
        await utils.answer(message, self.strings("success") + f": додано '{command}'")

    async def rptogglecmd(self, message: Message):
        """Вкл/Викл модуль у чаті"""
        cid = str(utils.get_chat_id(message))
        if cid in self.chats:
            self.chats.remove(cid)
            await utils.answer(message, self.strings("rp_off"))
        else:
            self.chats += [cid]
            await utils.answer(message, self.strings("rp_on"))
        self.set("active", self.chats)

    @loader.unrestricted
    async def rplistcmd(self, message: Message):
        """Список команд"""
        sorted_cmds = sorted(self.rp.items())
        chunk_size = 50
        lines = [f"▫️ <b>{cmd}</b> — {msg}" for cmd, msg in sorted_cmds]
        text = self.strings("rplist").format("")
        
        if len(lines) > chunk_size:
            await utils.answer(message, text + "\n".join(lines[:chunk_size]))
            for i in range(chunk_size, len(lines), chunk_size):
                await message.respond("\n".join(lines[i:i + chunk_size]))
        else:
            await utils.answer(message, text + "\n".join(lines))

    async def rpbackupcmd(self, message: Message):
        """Бекап налаштувань"""
        file = io.BytesIO(json.dumps(self.rp, ensure_ascii=False, indent=4).encode("utf-8"))
        file.name = "rp-backup-male.json"
        await self._client.send_file(
            utils.get_chat_id(message),
            file,
            caption=self.strings("backup_caption"),
        )
        await message.delete()

    async def rprestorecmd(self, message: Message):
        """Відновлення налаштувань"""
        reply = await message.get_reply_message()
        if not reply or not reply.media:
            await utils.answer(message, self.strings("no_file"))
            return

        try:
            file_data = await self._client.download_file(reply.media, bytes)
            file_decoded = file_data.decode("utf-8")
            self.rp = json.loads(file_decoded)
            self.set("rp", self.rp)
            await utils.answer(message, self.strings("restored"))
        except Exception as e:
            await utils.answer(message, f"🚫 <b>Error:</b> {str(e)}")

    async def rpchatscmd(self, message: Message):
        """Список активних чатів"""
        if not self.chats:
            await utils.answer(message, "🦊 <b>Пусто.</b>")
            return
        chat_list = []
        for chat in self.chats:
            try:
                entity = await self._client.get_entity(int(chat))
                name = utils.escape_html(get_display_name(entity))
                chat_list.append(f"    🇺🇦 {name}")
            except Exception:
                chat_list.append(f"    👻 <i>{chat}</i>")
        await utils.answer(
            message,
            f"🦊 <b>RPM активний у {len(self.chats)} чатах:</b>\n\n" + "\n".join(chat_list),
        )

    async def watcher(self, message: Message):
        try:
            cid = str(utils.get_chat_id(message))
            if cid not in self.chats: return
            if not isinstance(message, Message): return
            if not message.raw_text: return
            
            args = message.raw_text.split()
            if not args: return
            
            cmd = args[0].lower()
            if cmd not in self.rp: return
        except: return

        msg = self.rp[cmd]
        
        # --- Логіка пошуку цілі та коментарів ---
        
        reply_entity = None
        target_entity = None
        comment = ""

        # 1. Шукаємо реплай
        reply_msg = await message.get_reply_message()
        if reply_msg:
            try:
                reply_entity = await self._client.get_entity(reply_msg.sender_id)
            except: pass

        # 2. Шукаємо аргумент-юзера (меншн)
        # Логіка: [команда] [юзер?] [текст...]
        if len(args) > 1:
            try:
                # Спробуємо отримати юзера з першого аргументу
                potential_user = await self._client.get_entity(args[1])
                target_entity = potential_user
                
                # Якщо юзер знайдений в args[1], то коментар це все, що далі (args[2:])
                if len(args) > 2:
                    comment = " ".join(args[2:])
            except:
                # Якщо перший аргумент НЕ юзер
                if reply_msg:
                    # Якщо є реплай, то весь текст після команди - це коментар
                    comment = " ".join(args[1:])
                else:
                    # Немає реплаю і перший аргумент не юзер. 
                    # Це може бути просто текст без цілі, або помилка.
                    # В рамках поточного модуля РП без цілі не працює (або вимагає реплай).
                    pass

        final_target = target_entity if target_entity else reply_entity

        if not final_target:
            return

        sender = await self._client.get_entity(message.sender_id)

        # Обробка емодзі
        if utils.emoji_pattern.match(next(grapheme.graphemes(msg))):
            msg_parts = list(grapheme.graphemes(msg))
            emoji = msg_parts[0]
            action_text = "".join(msg_parts[1:])
        else:
            emoji = "🦊"
            action_text = " " + msg

        # Лінк на відправника та ціль
        s_link = f'<a href="tg://user?id={sender.id}">{utils.escape_html(sender.first_name)}</a>'
        t_link = f'<a href="tg://user?id={final_target.id}">{utils.escape_html(final_target.first_name)}</a>'

        # Формування фінального рядка
        output = f"{emoji} {s_link}<b>{action_text}</b> {t_link}"
        
        # Додавання коментаря З НОВОГО РЯДКА (формат 🗨️ Зі словами:)
        if comment:
            safe_comment = utils.escape_html(comment)
            output += f"\n🗨️ Зі словами: {safe_comment}"

        await utils.answer(message, output)