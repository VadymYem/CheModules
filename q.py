__version__ = (1, 2, 1)

# Цей файл є частиною Hikka Userbot!
# Модифіковано та українізовано для користувача.
# Базується на модулі "SQuotes" @yg_modules
# meta developer: @blazeftg & @wsinfo
# scope: hikka_only
# scope: hikka_min 1.6.3

import base64
import io
import requests
import telethon
from time import gmtime
from typing import List, Optional, Tuple, Union
from PIL import Image, ImageDraw
from telethon.tl import types
from telethon.extensions import html
from telethon.tl.patched import Message

from .. import loader, utils

class QuoteUtils:
    @staticmethod
    def ents(es: types.TypeMessageEntity) -> List[dict]:
        out: List[dict] = []
        if not es: return out
        for e in es:
            try:
                d = e.to_dict()
                t = d.pop("_", "").replace("MessageEntity", "").lower()
                if not t: continue
                
                mt = {
                    "bold": "bold", "italic": "italic", "underline": "underline", 
                    "strikethrough": "strikethrough", "code": "code", "pre": "pre", 
                    "texturl": "text_link", "url": "url", "email": "email", 
                    "phone": "phone_number", "mention": "mention", 
                    "mentionname": "text_mention", "hashtag": "hashtag", 
                    "cashtag": "cashtag", "botcommand": "bot_command", 
                    "spoiler": "spoiler", "customemoji": "custom_emoji",
                    "blockquote": "blockquote"
                }.get(t, t)
                
                it = {"type": mt, "offset": d.get("offset", 0), "length": d.get("length", 0)}
                
                if t == "texturl": it["url"] = d.get("url", "")
                elif t == "mentionname": it["user"] = {"id": d.get("user_id", 0)}
                elif t == "customemoji": it["custom_emoji_id"] = str(d.get("document_id", ""))
                elif t == "pre": it["language"] = d.get("language", "")
                
                out.append(it)
            except Exception: continue
        return out

    @staticmethod
    def dur(s: Union[int, float]) -> str:
        t = gmtime(s)
        return (f"{t.tm_hour:02d}:" if t.tm_hour > 0 else "") + f"{t.tm_min:02d}:{t.tm_sec:02d}"

    @staticmethod
    def desc(m: Message, rep: bool = False) -> str:
        if not rep:
            return ""
            
        if m.photo: return "📷 Фото"
        if m.sticker: return (m.file.emoji or "🗿") + " Стікер"
        if m.video_note: return "📹 Відеоповідомлення"
        if m.video: return "📹 Відео"
        if m.gif: return "🖼 GIF"
        if m.poll: return "📊 Опитування"
        if m.geo: return "📍 Місцезнаходження"
        if m.contact: return "👤 Контакт"
        
        if m.voice:
            return f"🎵 Голосове: {QuoteUtils.dur(m.voice.attributes[0].duration)}"
            
        if m.audio:
            attr = m.audio.attributes[0]
            performer = attr.performer if hasattr(attr, 'performer') and attr.performer else "Невідомий"
            title = attr.title if hasattr(attr, 'title') and attr.title else "Трек"
            return f"🎧 Музика: {QuoteUtils.dur(attr.duration)} | {performer} - {title}"
            
        if isinstance(m.media, types.MessageMediaDocument) and not QuoteUtils.pick(m):
            return f"💾 Файл: {m.file.name or 'Без назви'}"
            
        if isinstance(m.media, types.MessageMediaDice):
            return f"{m.media.emoticon} Кубик: {m.media.value}"
            
        if isinstance(m, types.MessageService):
            return f"Сервісне повідомлення: {m.action.to_dict().get('_')}"
            
        return ""

    @staticmethod
    def split(name: Optional[str]) -> Tuple[str, str]:
        if not name: return "", ""
        p = name.split()
        return (p[0], " ".join(p[1:]) if len(p) > 1 else "")

    @staticmethod
    def pick(m: Message):
        if m and m.media:
            return m.photo or m.sticker or m.video or m.video_note or m.gif or m.web_preview
        return None

    @staticmethod
    def wf(b: Optional[bytes]) -> List[int]:
        if not b: return []
        n = (len(b) * 8) // 5
        if not n: return []
        out: List[int] = []
        last = n - 1
        for i in range(last):
            j = i * 5
            bi, sh = j // 8, j % 8
            v = int.from_bytes(b[bi:bi + 2], "little") if bi + 1 < len(b) else b[bi]
            out.append((v >> sh) & 0b11111)
        j = last * 5
        bi, sh = j // 8, j % 8
        v = int.from_bytes(b[bi:bi + 2], "little") if bi + 1 < len(b) else b[bi]
        out.append((v >> sh) & 0b11111)
        return out

    @staticmethod
    async def img(b: bytes, circle: bool = False) -> Optional[str]:
        try:
            im = Image.open(io.BytesIO(b))
            if im.mode != "RGBA": im = im.convert("RGBA")
            if circle:
                size = min(im.size)
                mask = Image.new("L", (size, size), 0)
                ImageDraw.Draw(mask).ellipse((0, 0, size, size), fill=255)
                sq = Image.new("RGBA", (size, size), (0, 0, 0, 0))
                off = ((size - im.width) // 2, (size - im.height) // 2)
                sq.paste(im, off)
                im = Image.composite(sq, Image.new("RGBA", (size, size), (0, 0, 0, 0)), mask)
            o = io.BytesIO()
            im.save(o, format="PNG")
            return f"data:image/png;base64,{base64.b64encode(o.getvalue()).decode()}"
        except Exception:
            return None

    @staticmethod
    async def stc(b: bytes) -> Optional[str]:
        try:
            im = Image.open(io.BytesIO(b))
            if im.mode not in ("RGBA", "LA"): im = im.convert("RGBA")
            elif im.mode == "LA": im = im.convert("RGBA")
            o = io.BytesIO()
            im.save(o, format="PNG")
            return f"data:image/png;base64,{base64.b64encode(o.getvalue()).decode()}"
        except Exception:
            return None

    @staticmethod
    async def proc(cli, obj, m: Message) -> Optional[dict]:
        try:
            if m.voice:
                for a in m.voice.attributes or []:
                    if getattr(a, "voice", False) and hasattr(a, "waveform"):
                        return {"voice": {"waveform": QuoteUtils.wf(a.waveform)}}
            b: bytes = await cli.download_media(obj, bytes, thumb=-1)
            if not b: return None
            if m.sticker:
                u = await QuoteUtils.stc(b)
                return {"url": u} if u else None
            u = await QuoteUtils.img(b, circle=bool(m.video_note))
            return {"url": u} if u else None
        except Exception:
            return None

    @staticmethod
    async def ava(cli, uid: int) -> Optional[str]:
        try:
            b = await cli.download_profile_photo(uid, bytes)
            if b: return f"data:image/jpeg;base64,{base64.b64encode(b).decode()}"
        except Exception: pass
        return None

    @staticmethod
    async def post(url: str, data: dict):
        try:
            return await utils.run_sync(requests.post, url, json=data, timeout=30)
        except Exception:
            return None

@loader.tds
class Quotes(loader.Module):
    """Модуль для створення гарних цитат з повідомлень"""

    strings = {
        "name": "yg_quotes",
        "no_reply": "<emoji document_id=5465665476714773728>⚠️</emoji> <b>Немає відповіді на повідомлення</b>",
        "processing": "<emoji document_id=5350311258220405879>🔄</emoji> <b>Обробка...</b>",
        "api_processing": "<emoji document_id=5350311258220405879>🔄</emoji> <b>Очікування відповіді від API...</b>",
        "api_error": "<emoji document_id=5465665476714773728>⚠️</emoji> <b>Помилка API:</b> {}",
        "loading_media": "<emoji document_id=5350311258220405879>🔄</emoji> <b>Відправка...</b>",
        "no_args_or_reply": "<emoji document_id=5465665476714773728>⚠️</emoji> <b>Немає аргументів або відповіді</b>",
        "args_error": "<emoji document_id=5465665476714773728>⚠️</emoji> <b>Помилка розбору аргументів. Запит:</b> <code>{}</code>",
        "too_many_messages": "<emoji document_id=5465665476714773728>⚠️</emoji> <b>Забагато повідомлень. Максимум:</b> <code>{}</code>"
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue("type", "quote",
                               lambda: "Тип цитати (quote - звичайна, stories - для сторіз)",
                               validator=loader.validators.Choice(["quote", "stories"])),
            loader.ConfigValue("bg_color", "#162330",
                               lambda: "Колір фону цитати (наприклад, #1a1a1a або red)"),
            loader.ConfigValue("width", 512,
                               lambda: "Ширина цитати (px)",
                               validator=loader.validators.Integer(minimum=200, maximum=2000)),
            loader.ConfigValue("height", 768,
                               lambda: "Висота цитати (px)",
                               validator=loader.validators.Integer(minimum=200, maximum=2000)),
            loader.ConfigValue("scale", 2,
                               lambda: "Масштаб рендеру (якість)",
                               validator=loader.validators.Choice([1, 2, 3])),
            loader.ConfigValue("emoji_brand", "apple",
                               lambda: "Стиль емодзі (apple, google, twitter і т.д.)"),
            loader.ConfigValue("max_messages", 20,
                               lambda: "Максимальна кількість повідомлень у цитаті",
                               validator=loader.validators.Integer(minimum=1, maximum=50)),
            loader.ConfigValue("endpoint", "https://kok.gay/gayotes/generate",
                               lambda: "URL API-ендпоінту",
                               validator=loader.validators.Link())
        )

    async def client_ready(self, client, db):
        self.client = client
        self.db = db

    async def qcmd(self, m: Message):
        """
        Звичайні цитати:
        • .q — процитувати одне повідомлення з реплаю
        • .q 2 — процитувати 2 повідомлення
        • .q 3 #2d2d2d — 3 повідомлення на темному фоні
        • .q pink — фон за назвою кольору
        • .q !file — надіслати як файл (PNG)
        """
        try:
            args = utils.get_args(m)
            rep = await m.get_reply_message()
            if not rep:
                return await utils.answer(m, self.strings["no_reply"])
            
            # Відправляємо статус, але зберігаємо його об'єкт, щоб потім видалити
            st = await utils.answer(m, self.strings["processing"])
            doc = "!file" in args
            
            n = next((int(a) for a in args if a.isdigit() and int(a) > 0), 1)
            bg = next((a for a in args if a != "!file" and not a.isdigit()), self.config["bg_color"])
            
            if n > self.config["max_messages"]:
                return await utils.answer(st, self.strings["too_many_messages"].format(self.config["max_messages"]))

            js = await self.parse(m, n)
            if not js:
                return await utils.answer(st, self.strings["api_error"].format("Не вдалося зібрати повідомлення"))

            pay = {
                "backgroundColor": bg,
                "width": self.config["width"],
                "height": self.config["height"],
                "scale": self.config["scale"],
                "emojiBrand": self.config["emoji_brand"],
                "messages": js,
                "format": "webp" if not doc else "png",
                "type": self.config["type"]
            }

            await utils.answer(st, self.strings["api_processing"])
            r = await QuoteUtils.post(f"{self.config['endpoint']}.webp", pay)
            
            if not r or r.status_code != 200:
                try:
                    err = r.json().get("error", f"HTTP {r.status_code}") if r else "Network Error"
                except Exception:
                    err = f"HTTP {r.status_code}" if r else "Network Error"
                return await utils.answer(st, self.strings["api_error"].format(err))

            buf = io.BytesIO(r.content)
            buf.name = "Quote" + (".png" if doc else ".webp")
            buf.seek(0) # Важливо для запобігання помилок читання
            
            # ВИПРАВЛЕННЯ: Видаляємо статус і надсилаємо нове повідомлення
            await st.delete()
            await utils.answer(m, buf, force_document=doc, reply_to=rep.id)
            
        except Exception as e:
            # Якщо st існує, спробуємо відредагувати його, щоб показати помилку
            try: await utils.answer(st, f"<emoji document_id=5465665476714773728>⚠️</emoji> <b>Помилка:</b> {e}")
            except: await utils.answer(m, f"<emoji document_id=5465665476714773728>⚠️</emoji> <b>Помилка:</b> {e}")

    async def fqcmd(self, m: Message):
        """
        Фейкові цитати:
        • .fq <@ або ID> <текст> — цитата від користувача
        • .fq <reply> <текст> — цитата від автора реплаю
        • .fq <@/ID> <текст> -r <@/ID> <текст> — з відповіддю
        • .fq user1 текст; user2 текст — кілька повідомлень
        """
        try:
            raw = utils.get_args_html(m)
            rep = await m.get_reply_message()
            if not (raw or rep):
                return await utils.answer(m, self.strings["no_args_or_reply"])
            
            st = await utils.answer(m, self.strings["processing"])
            try:
                js = await self.fake(raw, rep)
            except (IndexError, ValueError):
                return await utils.answer(st, self.strings["args_error"].format(m.text))
                
            if len(js) > self.config["max_messages"]:
                return await utils.answer(st, self.strings["too_many_messages"].format(self.config["max_messages"]))

            payload = {
                "backgroundColor": self.config["bg_color"],
                "width": self.config["width"],
                "height": self.config["height"],
                "scale": self.config["scale"],
                "emojiBrand": self.config["emoji_brand"],
                "messages": js,
                "format": "webp",
                "type": self.config["type"]
            }

            await utils.answer(st, self.strings["api_processing"])
            r = await QuoteUtils.post(f"{self.config['endpoint']}.webp", payload)
            
            if not r or r.status_code != 200:
                try:
                    err = r.json().get("error", f"HTTP {r.status_code}") if r else "Network Error"
                except Exception:
                    err = f"HTTP {r.status_code}" if r else "Network Error"
                return await utils.answer(st, self.strings["api_error"].format(err))

            buf = io.BytesIO(r.content)
            buf.name = "Quote.webp"
            buf.seek(0)
            
            # ВИПРАВЛЕННЯ: Видаляємо статус і надсилаємо нове повідомлення
            await st.delete()
            await utils.answer(m, buf, reply_to=rep.id if rep else None)
            
        except Exception as e:
            try: await utils.answer(st, f"<emoji document_id=5465665476714773728>⚠️</emoji> <b>Помилка:</b> {e}")
            except: await utils.answer(m, f"<emoji document_id=5465665476714773728>⚠️</emoji> <b>Помилка:</b> {e}")

    async def parse(self, trg: Message, n: int) -> Optional[List[dict]]:
        try:
            rep = await trg.get_reply_message()
            lst: List[Message] = [mm async for mm in self.client.iter_messages(
                trg.chat_id, limit=n, reverse=True, add_offset=1, offset_id=rep.id if rep else None
            )]
        except Exception:
            return None

        out: List[dict] = []
        for mm in lst:
            try:
                u = await self.who(mm)
                if not u: continue
                
                name = telethon.utils.get_display_name(u)
                f, l = QuoteUtils.split(name)
                ava = await QuoteUtils.ava(self.client, getattr(u, "id", 0)) if getattr(u, "id", None) else None

                rb = None
                try:
                    r = await mm.get_reply_message()
                    if r:
                        rname = telethon.utils.get_display_name(r.sender)
                        rtxt = QuoteUtils.desc(r, True)
                        if r.raw_text:
                            rtxt = (rtxt + ". " + r.raw_text) if rtxt else r.raw_text
                        
                        rb = {
                            "name": rname,
                            "text": rtxt or "",
                            "entities": QuoteUtils.ents(r.entities),
                            "chatId": r.sender.id if r.sender else mm.chat_id,
                            "from": {"name": rname}
                        }
                except Exception:
                    rb = None

                med = None
                obj = QuoteUtils.pick(mm)
                if obj:
                    med = await QuoteUtils.proc(self.client, obj, mm)

                txt = mm.raw_text or ""
                ad = QuoteUtils.desc(mm)
                if ad:
                    txt = f"{txt}\n\n{ad}" if txt else ad

                item = {
                    "from": {
                        "id": getattr(u, "id", 0),
                        "first_name": getattr(u, "first_name", "") or f,
                        "last_name": getattr(u, "last_name", "") or l,
                        "username": getattr(u, "username", None),
                        "name": name,
                        "photo": {"url": ava} if ava else {}
                    },
                    "text": txt,
                    "entities": QuoteUtils.ents(mm.entities),
                    "avatar": True
                }

                try:
                    if mm.voice:
                        a = next((a for a in mm.voice.attributes or [] 
                                if getattr(a, "voice", False) and hasattr(a, "waveform")), None)
                        if a: item["voice"] = {"waveform": QuoteUtils.wf(a.waveform)}
                except Exception: pass

                if med:
                    item["voice" if "voice" in med else "media"] = med.get("voice", med)

                es = getattr(u, "emoji_status", None)
                if getattr(es, "document_id", None):
                    item["from"]["emoji_status"] = str(es.document_id)
                
                if rb:
                    item["replyMessage"] = rb
                    
                out.append(item)
            except Exception: continue
        return out

    async def who(self, m: Message):
        try:
            if m.fwd_from:
                if m.fwd_from.from_id:
                    pid = m.fwd_from.from_id
                    uid = pid.channel_id if isinstance(pid, types.PeerChannel) else pid.user_id
                    try:
                        return await self.client.get_entity(uid)
                    except Exception:
                        return m.sender
                if m.fwd_from.from_name:
                    return types.User(
                        id=hash(m.fwd_from.from_name) % 2147483647,
                        first_name=m.fwd_from.from_name,
                        username=None, phone=None, bot=False, verified=False, restricted=False,
                        scam=False, fake=False, premium=False
                    )
            return m.sender
        except Exception:
            return m.sender

    async def fake(self, args: str, rep: Optional[Message]) -> List[dict]:
        async def tok(ch: str):
            p = ch.split()
            if not p: return None, ""
            who = p[0]
            tx = ch.split(maxsplit=1)[1] if len(p) > 1 else ""
            try:
                u = await self.client.get_entity(int(who) if who.isdigit() else who)
                return u, tx
            except Exception:
                return None, tx

        if rep and not args:
            u = rep.sender
            name = telethon.utils.get_display_name(u)
            f, l = QuoteUtils.split(name)
            ava = await QuoteUtils.ava(self.client, u.id) if getattr(u, "id", None) else None
            msg = {
                "from": {
                    "id": u.id,
                    "first_name": getattr(u, "first_name", "") or f,
                    "last_name": getattr(u, "last_name", "") or l,
                    "username": getattr(u, "username", None),
                    "name": name,
                    "photo": {"url": ava} if ava else {}
                },
                "text": "", "entities": [], "avatar": True
            }
            es = getattr(u, "emoji_status", None)
            if getattr(es, "document_id", None):
                msg["from"]["emoji_status"] = str(es.document_id)
            return [msg]

        if rep and args:
            u = rep.sender
            return await self.fake(f"{getattr(u, 'id', '')} {args}", None)

        out: List[dict] = []
        for part in args.split("; "):
            try:
                rb = None
                if " -r " in part:
                    a, b = part.split(" -r ", 1)
                    u1, t1 = await tok(a)
                    u2, t2 = await tok(b)
                else:
                    u1, t1 = await tok(part)
                    u2, t2 = None, None
                
                if not u1: continue

                txt1, ents1 = html.parse(t1) if t1 else ("", [])

                name = telethon.utils.get_display_name(u1)
                f, l = QuoteUtils.split(name)
                ava = await QuoteUtils.ava(self.client, u1.id)

                if u2:
                    txt2, ents2 = html.parse(t2) if t2 else ("", [])
                    name2 = telethon.utils.get_display_name(u2)
                    ava2 = await QuoteUtils.ava(self.client, u2.id)
                    rb = {
                        "name": name2,
                        "text": txt2,
                        "entities": QuoteUtils.ents(ents2),
                        "chatId": u2.id,
                        "from": {"name": name2, "photo": {"url": ava2} if ava2 else {}}
                    }

                msg = {
                    "from": {
                        "id": u1.id,
                        "first_name": getattr(u1, "first_name", "") or f,
                        "last_name": getattr(u1, "last_name", "") or l,
                        "username": getattr(u1, "username", None),
                        "name": name,
                        "photo": {"url": ava} if ava else {}
                    },
                    "text": txt1, "entities": QuoteUtils.ents(ents1), "avatar": True
                }

                es = getattr(u1, "emoji_status", None)
                if getattr(es, "document_id", None):
                    msg["from"]["emoji_status"] = str(es.document_id)
                
                if rb:
                    msg["replyMessage"] = rb
                
                out.append(msg)
            except Exception: continue
        return out
