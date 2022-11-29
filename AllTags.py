# scope: acbot_min 1.2.10
__version__ = (1, 0, 0)

#              © Copyright 2022
#           https://t.me/AuthorChe
#             Den4ikOstryyPer4ik
#
# 🔒      Licensed under the GNU AGPLv3
# 🌐 https://www.gnu.org/licenses/agpl-3.0.html

# meta developer: @AuthorChe
# scope: acbot_only

import asyncio
import time

from telethon.tl.types import Message, Channel
from telethon.tl.functions.channels import InviteToChannelRequest
from telethon.tl.functions.contacts import GetBlockedRequest

from .. import loader, utils


@loader.tds
class SilentTagsMod(loader.Module):
    """All tags and logs them"""

    strings = {
        "name": "AllTags",
        "tagged": """<b>Тебе згадали!\nЧат -- <a href="{}">{}</a>\nЮзер --> <a href="tg://openmessage?user_id={}">{}</a>\nТекст повідомлення:</b> \n<code>{}</code>\n<b>Посилання: <a href="https://t.me/c/{}/{}">КЛІК</a></b>""",
        "tag_mentioned": "<b>Окей</b>",
        "stags_status": "<b>🤫 ALL Tags logger {}</b>",
        "_cmd_doc_stags": "<on\\off> - Вкл\\викл запам'ятовування згадок",
        "_cls_doc": "Откл згадки",
        "_cfg_doc_ignore_users": (
            "Откл SilentTags для таких ID"
        ),
        "_cfg_doc_ignore_chats": "Откл SilentTags в чатах з ID",
        "_cfg_doc_ignore_bots": "Откл SilentTags для ботів",
        "_cfg_doc_ignore_blocked": (
            "Откл SilentTags для заблокованих"
        ),
        "_cfg_doc_silent_users": (
            "Не отправлять сообщения о тегах от пользователей с перечисленными ID"
        ),
        "_cfg_doc_silent_chats": (
            "Не отправлять сообщения о тегах в чатах с перечисленными ID"
        ),
        "_cfg_doc_silent_bots": "Не отправлять сообщения о тегах от ботов",
        "_cfg_doc_silent_blocked": (
            "Не отправлять сообщения о тегах от заблокированных пользователей"
        ),
        "_cfg_doc_silent": "Не отправлять сообщение о том, что активны Silent Tags",
        "_cfg_doc_use_whitelist": (
            "Преобразовать все списковые настройки в белый список"
        ),
    }

        
    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "silent",
                False,
                lambda: self.strings("_cfg_doc_silent"),
                validator=loader.validators.Boolean(),
            ),
            loader.ConfigValue(
                "ignore_bots",
                False,
                lambda: self.strings("_cfg_doc_ignore_bots"),
                validator=loader.validators.Boolean(),
            ),
            loader.ConfigValue(
                "ignore_blocked",
                False,
                lambda: self.strings("_cfg_doc_ignore_blocked"),
                validator=loader.validators.Boolean(),
            ),
            loader.ConfigValue(
                "ignore_users",
                doc=lambda: self.strings("_cfg_doc_ignore_users"),
                validator=loader.validators.Series(
                    validator=loader.validators.TelegramID()
                ),
            ),
            loader.ConfigValue(
                "ignore_chats",
                doc=lambda: self.strings("_cfg_doc_ignore_chats"),
                validator=loader.validators.Series(
                    validator=loader.validators.TelegramID()
                ),
            ),
            loader.ConfigValue(
                "silent_bots",
                False,
                lambda: self.strings("_cfg_doc_silent_bots"),
                validator=loader.validators.Boolean(),
            ),
            loader.ConfigValue(
                "silent_blocked",
                False,
                lambda: self.strings("_cfg_doc_silent_blocked"),
                validator=loader.validators.Boolean(),
            ),
            loader.ConfigValue(
                "silent_users",
                doc=lambda: self.strings("_cfg_doc_silent_users"),
                validator=loader.validators.Series(
                    validator=loader.validators.TelegramID()
                ),
            ),
            loader.ConfigValue(
                "silent_chats",
                doc=lambda: self.strings("_cfg_doc_silent_chats"),
                validator=loader.validators.Series(
                    validator=loader.validators.TelegramID()
                ),
            ),
            loader.ConfigValue(
                "use_whitelist",
                False,
                lambda: self.strings("_cfg_doc_use_whitelist"),
                validator=loader.validators.Boolean(),
            ),
        )

    @loader.loop(interval=300)
    async def get_blocked(self):
        self._blocked = [
            user.id
            for user in (
                await self._client(GetBlockedRequest(offset=0, limit=1000))
            ).users
        ]

    async def client_ready(self, client, db):
        self._ratelimit = []
        self._fw_protect = {}
        self._blocked = []
        self._fw_protect_limit = 5

        self.c, _ = await utils.asset_channel(
            self._client,
            "All-tags",
            "🔇 Chat for All tags",
            silent=True,
            _folder="hikka",
        )

        if self.config["ignore_blocked"] or self.config["silent_blocked"]:
            self.get_blocked.start()

        self.chat_aio = f"-100{self.c.id}"

    async def stagscmd(self, message: Message):
        """<on\\off> - Toggle notifications about tags"""
        args = utils.get_args_raw(message)

        if args not in ["on", "off"]:
            await utils.answer(
                message,
                self.strings("stags_status").format(
                    "active" if self.get("stags", False) else "inactive"
                ),
            )
            return

        args = args == "on"
        self.set("stags", args)
        self._ratelimit = []
        await utils.answer(
            message,
            self.strings("stags_status").format("now on" if args else "now off"),
        )

    async def watcher(self, message: Message):
        if (
            not getattr(message, "mentioned", False)
            or not self.get("stags", False)
            or utils.get_chat_id(message) == self.c.id
            or (
                self.config["whitelist"]
                and message.sender_id not in (self.config["ignore_users"] or [])
                or not self.config["whitelist"]
                and message.sender_id in (self.config["ignore_users"] or [])
            )
            or self.config["ignore_blocked"]
            and message.sender.id in self._blocked
            or (
                self.config["whitelist"]
                and utils.get_chat_id(message)
                not in (self.config["ignore_chats"] or [])
                or not self.config["whitelist"]
                and utils.get_chat_id(message) in (self.config["ignore_chats"] or [])
            )
            or self.config["ignore_bots"]
            and message.sender.bot
        ):
            return

        await self._client.send_read_acknowledge(
            message.chat_id,
            clear_mentions=False,
        )

        cid = utils.get_chat_id(message)

        if (
            cid in self._fw_protect
            and len(list(filter(lambda x: x > time.time(), self._fw_protect[cid])))
            > self._fw_protect_limit
        ):
            return

        if message.is_private:
            ctitle = "pm"
        else:
            chat = await self._client.get_entity(message.peer_id)
            grouplink = (
                f"https://t.me/{chat.username}"
                if getattr(chat, "username", None) is not None
                else ""
            )
            ctitle = chat.title

        if cid not in self._fw_protect:
            self._fw_protect[cid] = []

        uid = message.sender_id

        try:
            user = await self._client.get_entity(message.sender_id)
            uname = user.first_name
        except Exception:
            uname = "Unknown user"
            user = None

        async def send():
            await self.inline.bot.send_message(
                self.chat_aio,
                self.strings("tagged").format(
                    grouplink,
                    utils.escape_html(ctitle),
                    uid,
                    utils.escape_html(uname),
                    utils.escape_html(message.raw_text),
                    cid,
                    message.id,
                ),
                disable_web_page_preview=True,
                parse_mode="HTML",
            )

        if (
            (
                self.config["whitelist"]
                and message.sender_id not in (self.config["silent_users"] or [])
                or not self.config["whitelist"]
                and message.sender_id in (self.config["silent_users"] or [])
            )
            or self.config["silent_blocked"]
            and message.sender.id in self._blocked
            or (
                self.config["whitelist"]
                and utils.get_chat_id(message)
                not in (self.config["silent_chats"] or [])
                or not self.config["whitelist"]
                and utils.get_chat_id(message) in (self.config["silent_chats"] or [])
            )
            or not (isinstance(user, Channel))
            and self.config["silent_bots"]
            and message.sender.bot
        ):
            return

        try:
            await send()
        except Exception:
            await self._client(
                InviteToChannelRequest(
                    self.c,
                    [self.inline.bot_username],
                )
            )
            await send()

        self._fw_protect[cid] += [time.time() + 5 * 60]

        if cid not in self._ratelimit and not self.config["silent"]:
            self._ratelimit += [cid]
            ms = await utils.answer(message, self.strings("tag_mentioned"))
            await asyncio.sleep(3)
            await ms.delete()
