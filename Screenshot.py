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
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
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
        """.web <link> [full]"""
        args = utils.get_args_raw(message).split()
        full = "full" in args  # Перевірка наявності аргументу "full"
        link = next((arg for arg in args if arg != "full"), None)

        if not link:
            reply = await message.get_reply_message()
            if not reply:
                await message.delete()
                return
            link = reply.raw_text

        await message.edit("<b>📸 Знімаю скріншот...</b>")

        try:
            # Використання Selenium для зняття повного скріншоту
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--window-size=1920,1080")

            with webdriver.Chrome(options=chrome_options) as driver:
                driver.get(link)
                if full:
                    height = driver.execute_script("return document.body.scrollHeight")
                    driver.set_window_size(1920, height)  # Підлаштовуємо висоту для full-page
                screenshot = driver.get_screenshot_as_png()

            file = io.BytesIO(screenshot)
            file.name = "screenshot_full.png" if full else "screenshot.png"
            file.seek(0)
            await message.client.send_file(message.to_id, file)
        except Exception as e:
            await message.edit(f"<b>Помилка зняття скріншота: {e}</b>")
            return

        await message.delete()

    async def fscmd(self, message):
        """.fs <full> + reply to: txt, html, py, docx, pdf"""
        args = utils.get_args_raw(message)
        full = "full" in args  # Перевірка наявності аргументу full
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

            img_file = "@wsinfo_full.png" if full else "@wsinfo.png"
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
