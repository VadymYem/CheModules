# ©️ Dan Gazizullin, 2021-2023
# This file is a part of Hikka Userbot
# 🌐 https://github.com/hikariatama/Hikka
# You can redistribute it and/or modify it under the terms of the GNU AGPLv3
# 🔑 https://www.gnu.org/licenses/agpl-3.0.html

import hikkapyro
import hikkatl
from hikkatl.extensions.html import CUSTOM_EMOJIS
from hikkatl.tl.types import Message

from .. import loader, main, utils, version
from ..compat.dragon import DRAGON_EMOJI
from ..inline.types import InlineCall


@loader.tds
class CoreMod(loader.Module):
    """Control core userbot settings"""

    strings = {"name": "Settings",
                      "acbot": (
            (
    '✌️ <b>Привіт!\n\n<b>Юзербот</b> — це бот, який працює від імені звичайного користувача Telegram, надаючи розширені можливості, недоступні для класичних ботів. Наприклад, юзербот може читати повідомлення після їх надсилання, шукати інфо в гугл та виконувати інші дії, як і звичайний бот, але від імені користувача.\n\n<b>AuthorBot</b> — це один із найсучасніших юзерботів, який відрізняється високою продуктивністю та унікальними функціями. Ось його основні переваги:\n\n- 🆕 <b>Останні оновлення Telegram</b>: підтримка реакцій, відео-наклейок, цитат та інших нових функцій.\n- 🔓 <b>Поліпшена безпека</b>: вбудоване кешування сутностей та цільові правила безпеки.\n- 🎨 <b>Покращений інтерфейс</b>: зручний дизайн та оптимізована взаємодія з користувачем.\n- 📼 <b>Нові модулі</b>: оновлені та додані нові основні модулі для розширення функціоналу.\n- ⏱ <b>Стабільність та швидкість</b>: швидка робота та мінімальні затримки.\n- ▶️ <b>Вбудовані форми, галереї та списки</b>: зручні інструменти для взаємодії з користувачем.\n- 👨‍👦 <b>Підтримка NoNick</b>: можливість використовувати інший акаунт для роботи юзербота.\n- 🔁 <b>Повна сумісність</b>: працює з популярними юзерботами на базі Telethon.\n- 🇺🇦 <b>Підтримка української мови</b>: унікальна функція, яка відрізняє AuthorBot від інших.\n- <b>Унікальні модулі</b>: розроблені спеціально автором для покращення функціоналу.\n\nAuthorBot — це ідеальний вибір для тих, хто шукає сучасний, безпечний та зручний інструмент для автоматизації в Telegram.\n\n<b>🌍 </b><a href="https://authorche.pp.ua/"><b>WebSite</b></a>\n<b>👥 </b><a href="http://www.instagram.com/Vadym_Yem"><b>Instagram😎</b></a>'
),  
        }

    async def blacklistcommon(self, message: Message):
        args = utils.get_args(message)

        if len(args) > 2:
            await utils.answer(message, self.strings("too_many_args"))
            return

        chatid = None
        module = None

        if args:
            try:
                chatid = int(args[0])
            except ValueError:
                module = args[0]

        if len(args) == 2:
            module = args[1]

        if chatid is None:
            chatid = utils.get_chat_id(message)

        module = self.allmodules.get_classname(module)
        return f"{str(chatid)}.{module}" if module else chatid

    @loader.command()
    async def authorcmd(self, message: Message):
        await utils.answer_file(
            message,
            "https://github.com/hikariatama/assets/raw/master/hikka_cat_banner.mp4",
            self.strings("hikka").format(
                (
                    utils.get_platform_emoji()
                    if self._client.hikka_me.premium and CUSTOM_EMOJIS
                    else "💻 <b>AuthorBot</b>"
                ),
                *version.__version__,
                utils.get_commit_url(),
                f"{hikkatl.__version__} #{hikkatl.tl.alltlobjects.LAYER}",
                (
                    "<emoji document_id=5377399247589088543>🔥</emoji>"
                    if self._client.pyro_proxy
                    else "<emoji document_id=5418308381586759720>📴</emoji>"
                ),
                f"{hikkapyro.__version__} #{hikkapyro.raw.all.layer}",
            )
            + (
                ""
                if version.branch == "master"
                else self.strings("unstable").format(version.branch)
            ),
        )

    @loader.command()
    async def blacklist(self, message: Message):
        chatid = await self.blacklistcommon(message)

        self._db.set(
            main.__name__,
            "blacklist_chats",
            self._db.get(main.__name__, "blacklist_chats", []) + [chatid],
        )

        await utils.answer(message, self.strings("blacklisted").format(chatid))

    @loader.command()
    async def unblacklist(self, message: Message):
        chatid = await self.blacklistcommon(message)

        self._db.set(
            main.__name__,
            "blacklist_chats",
            list(set(self._db.get(main.__name__, "blacklist_chats", [])) - {chatid}),
        )

        await utils.answer(message, self.strings("unblacklisted").format(chatid))

    async def getuser(self, message: Message):
        try:
            return int(utils.get_args(message)[0])
        except (ValueError, IndexError):
            if reply := await message.get_reply_message():
                return reply.sender_id

            return message.to_id.user_id if message.is_private else False

    @loader.command()
    async def blacklistuser(self, message: Message):
        if not (user := await self.getuser(message)):
            await utils.answer(message, self.strings("who_to_blacklist"))
            return

        self._db.set(
            main.__name__,
            "blacklist_users",
            self._db.get(main.__name__, "blacklist_users", []) + [user],
        )

        await utils.answer(message, self.strings("user_blacklisted").format(user))

    @loader.command()
    async def unblacklistuser(self, message: Message):
        if not (user := await self.getuser(message)):
            await utils.answer(message, self.strings("who_to_unblacklist"))
            return

        self._db.set(
            main.__name__,
            "blacklist_users",
            list(set(self._db.get(main.__name__, "blacklist_users", [])) - {user}),
        )

        await utils.answer(
            message,
            self.strings("user_unblacklisted").format(user),
        )

    @loader.command()
    async def setprefix(self, message: Message):
        if not (args := utils.get_args_raw(message)):
            await utils.answer(message, self.strings("what_prefix"))
            return

        if len(args.split()) == 2 and args.split()[0] == "dragon":
            args = args.split()[1]
            is_dragon = True
        else:
            is_dragon = False

        if len(args) != 1:
            await utils.answer(message, self.strings("prefix_incorrect"))
            return

        if args == "s":
            await utils.answer(message, self.strings("prefix_incorrect"))
            return

        if (
            not is_dragon
            and args[0] == self._db.get("dragon.prefix", "command_prefix", ",")
            or is_dragon
            and args[0] == self._db.get(main.__name__, "command_prefix", ".")
        ):
            await utils.answer(message, self.strings("prefix_collision"))
            return

        oldprefix = (
            f"dragon {utils.escape_html(self.get_prefix('dragon'))}"
            if is_dragon
            else utils.escape_html(self.get_prefix())
        )
        self._db.set(
            "dragon.prefix" if is_dragon else main.__name__,
            "command_prefix",
            args,
        )
        await utils.answer(
            message,
            self.strings("prefix_set").format(
                (
                    DRAGON_EMOJI
                    if is_dragon
                    else "<emoji document_id=5197474765387864959>👍</emoji>"
                ),
                newprefix=utils.escape_html(
                    self.get_prefix() if is_dragon else args[0]
                ),
                oldprefix=utils.escape_html(oldprefix),
            ),
        )

    @loader.command()
    async def aliases(self, message: Message):
        await utils.answer(
            message,
            self.strings("aliases")
            + "\n".join(
                [
                    f"▫️ <code>{i}</code> &lt;- {y}"
                    for i, y in self.allmodules.aliases.items()
                ]
            ),
        )

    @loader.command()
    async def addalias(self, message: Message):
        if len(args := utils.get_args(message)) != 2:
            await utils.answer(message, self.strings("alias_args"))
            return

        alias, cmd = args
        if self.allmodules.add_alias(alias, cmd):
            self.set(
                "aliases",
                {
                    **self.get("aliases", {}),
                    alias: cmd,
                },
            )
            await utils.answer(
                message,
                self.strings("alias_created").format(utils.escape_html(alias)),
            )
        else:
            await utils.answer(
                message,
                self.strings("no_command").format(utils.escape_html(cmd)),
            )

    @loader.command()
    async def delalias(self, message: Message):
        args = utils.get_args(message)

        if len(args) != 1:
            await utils.answer(message, self.strings("delalias_args"))
            return

        alias = args[0]

        if not self.allmodules.remove_alias(alias):
            await utils.answer(
                message,
                self.strings("no_alias").format(utils.escape_html(alias)),
            )
            return

        current = self.get("aliases", {})
        del current[alias]
        self.set("aliases", current)
        await utils.answer(
            message,
            self.strings("alias_removed").format(utils.escape_html(alias)),
        )

    @loader.command()
    async def cleardb(self, message: Message):
        await self.inline.form(
            self.strings("confirm_cleardb"),
            message,
            reply_markup=[
                {
                    "text": self.strings("cleardb_confirm"),
                    "callback": self._inline__cleardb,
                },
                {
                    "text": self.strings("cancel"),
                    "action": "close",
                },
            ],
        )

    async def _inline__cleardb(self, call: InlineCall):
        self._db.clear()
        self._db.save()
        await utils.answer(call, self.strings("db_cleared"))
