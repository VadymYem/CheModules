# -*- coding: utf-8 -*-
# meta developer: @blazeftg / @wsinfo

import io
import logging
import os
from requests import get
from pygments import highlight
from pygments.formatters import ImageFormatter
from pygments.lexers import Python3Lexer, HtmlLexer, TextLexer
from docx import Document
from pdfminer.high_level import extract_text
from .. import loader, utils

logger = logging.getLogger(__name__)


@loader.tds
class WebShotMod(loader.Module):
    strings = {"name": "Screenshot"}

    async def client_ready(self, client, db):
        self.client = client

    def __init__(self):
        self.name = self.strings["name"]

    @loader.sudo
    async def webcmd(self, message):
        """.web <link>"""
        reply = None
        link = utils.get_args_raw(message)
        if not link:
            reply = await message.get_reply_message()
            if not reply:
                await message.delete()
                return
            link = reply.raw_text

        await message.edit("<b>📸 Знімаю скріншот...</b>")
        url = "https://mini.s-shot.ru/1024x768/JPEG/1024/Z100/?{}"
        file = get(url.format(link))
        file = io.BytesIO(file.content)
        file.name = "screenshot.png"
        file.seek(0)
        await message.client.send_file(message.to_id, file, reply_to=reply)
        await message.delete()

    async def fscmd(self, message):
        """.fs + reply to: txt, html, py, docx, pdf"""
        await message.edit("<b>Обробляю файл...</b>")
        reply = await message.get_reply_message()
        if not reply or not reply.media:
            await message.edit("<b>Відповідайте на підтримуваний файл!</b>")
            return

        file_bytes = await message.client.download_file(reply.media)
        file_name = reply.file.name
        file_extension = os.path.splitext(file_name)[-1].lower()

        try:
            if file_extension in [".py", ".txt"]:
                text = file_bytes.decode("utf-8")
                lexer = Python3Lexer() if file_extension == ".py" else TextLexer()
            elif file_extension == ".html":
                text = file_bytes.decode("utf-8")
                lexer = HtmlLexer()
            elif file_extension == ".docx":
                file_stream = io.BytesIO(file_bytes)
                document = Document(file_stream)
                text = "\n".join([p.text for p in document.paragraphs])
                lexer = TextLexer()
            elif file_extension == ".pdf":
                file_stream = io.BytesIO(file_bytes)
                text = extract_text(file_stream)
                lexer = TextLexer()
            else:
                await message.edit(f"<b>Непідтримуваний тип файлу: {file_extension}</b>")
                return

            img_file = "@wsinfo.png"
            with open(img_file, "wb") as f:
                f.write(
                    highlight(
                        text,
                        lexer,
                        ImageFormatter(font_name="DejaVu Sans Mono", line_numbers=True),
                    )
                )
            await message.client.send_file(
                message.to_id, img_file, force_document=True
            )
            os.remove(img_file)
        except Exception as e:
            await message.edit(f"<b>Помилка обробки файлу: {e}</b>")
            return

        await message.edit("<b>Скріншот файлу створено!</b>")
        await message.delete()