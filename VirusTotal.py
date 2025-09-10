#meta developer: @blazeftg, @wsinfo
import os, json, aiohttp, tempfile, asyncio
from .. import loader, utils
from hikkatl.tl.types import Message

__version__ = (1, 1, 0)


@loader.tds
class VirusTotalMod(loader.Module):
    """Перевіряє файли на віруси за допомогою VirusTotal"""

    strings = {
        "name": "VirusTotal",
        "no_file": "<emoji document_id=5210952531676504517>🚫</emoji> <b>Ви не вибрали файл.</b>",
        "no_reply": "<emoji document_id=5210952531676504517>🚫</emoji> <b>Відповідь на повідомлення з файлом необхідна.</b>",
        "reply_not_document": "<emoji document_id=5210952531676504517>🚫</emoji> <b>Відповідь має містити файл.</b>",
        "download": "<emoji document_id=5334677912270415274>📥</emoji> <b>Завантажую файл...</b>",
        "scan": "<emoji document_id=5325792861885570739>🔍</emoji> <b>Скануйю файл...</b>",
        "processing": "<emoji document_id=5325792861885570739>⏳</emoji> <b>Очікую результат сканування...</b>",
        "link": "🦠 Посилання на VirusTotal",
        "no_virus": "✅ Файл чистий. Переглянути детальний звіт можна за посиланням нижче.",
        "error": "<emoji document_id=5210952531676504517>❌</emoji> <b>Помилка сканування:</b>",
        "no_format": "<emoji document_id=5210952531676504517>🚫</emoji> <b>Цей формат файлу не підтримується для сканування.</b>",
        "no_apikey": "<emoji document_id=5260342697075416641>🚫</emoji> <b>Ви не вказали API ключ. Отримайте його на www.virustotal.com/gui/my-apikey</b>",
        "file_too_large": "<emoji document_id=5210952531676504517>📏</emoji> <b>Файл занадто великий. Максимальний розмір - 650MB.</b>",
        "analysis_timeout": "<emoji document_id=5210952531676504517>⏰</emoji> <b>Час очікування результату сканування вичерпано.</b>",
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "token-vt",
                None,
                lambda: "API ключ з www.virustotal.com/gui/my-apikey",
                validator=loader.validators.Hidden(),
            ),
            loader.ConfigValue(
                "max_wait_time",
                300,
                lambda: "Максимальний час очікування результату сканування (секунди)",
                validator=loader.validators.Integer(minimum=30, maximum=600),
            ),
        )

    @loader.command()
    async def vt(self, message: Message):
        """<відповідь на файл> - Перевіряє файли на наявність вірусів за допомогою VirusTotal"""
        if not message.is_reply:
            await utils.answer(message, self.strings("no_reply"))
            return

        reply = await message.get_reply_message()
        if not reply.document:
            await utils.answer(message, self.strings("reply_not_document"))
            return

        if not self.config.get("token-vt"):
            await utils.answer(message, self.strings("no_apikey"))
            return

        # Перевірка розміру файлу (VirusTotal обмеження - 650MB)
        if reply.document.size > 650 * 1024 * 1024:
            await utils.answer(message, self.strings("file_too_large"))
            return

        async with aiohttp.ClientSession() as session:
            with tempfile.TemporaryDirectory() as temp_dir:
                try:
                    await utils.answer(message, self.strings("download"))
                    
                    # Створюємо безпечне ім'я файлу
                    safe_filename = reply.document.attributes[0].file_name if reply.document.attributes else "unknown_file"
                    if not safe_filename:
                        safe_filename = f"file_{reply.document.id}"
                    
                    file_path = os.path.join(temp_dir, safe_filename)
                    await reply.download_media(file_path)

                    file_extension = os.path.splitext(safe_filename)[1].lower()
                    
                    # Розширений список підтримуваних форматів
                    allowed_extensions = (
                        ".exe", ".dll", ".sys", ".bat", ".cmd", ".com", ".pif", ".scr",
                        ".msi", ".jar", ".apk", ".dex", ".zip", ".rar", ".7z", ".tar",
                        ".gz", ".bz2", ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt",
                        ".pptx", ".rtf", ".js", ".vbs", ".ps1", ".py", ".php", ".html",
                        ".htm", ".swf", ".dmg", ".pkg", ".deb", ".rpm", ".iso"
                    )

                    if file_extension not in allowed_extensions:
                        await utils.answer(message, self.strings("no_format"))
                        return

                    token = self.config["token-vt"]
                    headers = {"x-apikey": token}

                    await utils.answer(message, self.strings("scan"))

                    # Відправляємо файл на сканування
                    with open(file_path, "rb") as file:
                        data = aiohttp.FormData()
                        data.add_field('file', file, filename=safe_filename)
                        
                        async with session.post(
                            "https://www.virustotal.com/api/v3/files",
                            headers=headers,
                            data=data,
                        ) as response:
                            if response.status != 200:
                                error_text = await response.text()
                                await utils.answer(message, f"{self.strings('error')} HTTP {response.status}\n<code>{error_text}</code>")
                                return

                            result = await response.json()
                            analysis_id = result["data"]["id"]

                    await utils.answer(message, self.strings("processing"))

                    # Очікуємо завершення аналізу
                    max_wait = self.config["max_wait_time"]
                    wait_time = 0
                    check_interval = 10  # Перевіряємо кожні 10 секунд

                    while wait_time < max_wait:
                        async with session.get(
                            f"https://www.virustotal.com/api/v3/analyses/{analysis_id}",
                            headers=headers,
                        ) as response:
                            if response.status != 200:
                                error_text = await response.text()
                                await utils.answer(message, f"{self.strings('error')} HTTP {response.status}\n<code>{error_text}</code>")
                                return

                            analysis_result = await response.json()
                            
                            # Перевіряємо статус аналізу
                            if analysis_result["data"]["attributes"]["status"] == "completed":
                                break
                            
                            await asyncio.sleep(check_interval)
                            wait_time += check_interval
                    else:
                        await utils.answer(message, self.strings("analysis_timeout"))
                        return

                    # Отримуємо детальний звіт
                    file_hash = analysis_result["meta"]["file_info"]["sha256"]
                    
                    async with session.get(
                        f"https://www.virustotal.com/api/v3/files/{file_hash}",
                        headers=headers,
                    ) as response:
                        if response.status != 200:
                            error_text = await response.text()
                            await utils.answer(message, f"{self.strings('error')} HTTP {response.status}\n<code>{error_text}</code>")
                            return

                        file_report = await response.json()
                        scan_results = file_report["data"]["attributes"]["last_analysis_results"]
                        
                        # Аналізуємо результати
                        detections = []
                        suspicious = []
                        total_engines = len(scan_results)
                        malicious_count = 0
                        suspicious_count = 0
                        
                        for engine, details in scan_results.items():
                            if details["category"] == "malicious":
                                malicious_count += 1
                                detections.append(f"🔴 <b>{engine}</b>: <code>{details.get('result', 'Malicious')}</code>")
                            elif details["category"] == "suspicious":
                                suspicious_count += 1
                                suspicious.append(f"🟡 <b>{engine}</b>: <code>{details.get('result', 'Suspicious')}</code>")

                        # Формуємо повідомлення
                        if malicious_count == 0 and suspicious_count == 0:
                            result_text = self.strings("no_virus")
                            status_emoji = "✅"
                        elif malicious_count > 0:
                            result_text = "\n".join(detections[:10])  # Показуємо перші 10 виявлень
                            if len(detections) > 10:
                                result_text += f"\n<i>... та ще {len(detections) - 10} виявлень</i>"
                            status_emoji = "🚨"
                        else:
                            result_text = "\n".join(suspicious[:5])  # Показуємо перші 5 підозрілих
                            if len(suspicious) > 5:
                                result_text += f"\n<i>... та ще {len(suspicious) - 5} підозрілих</i>"
                            status_emoji = "⚠️"

                        # Додаткова інформація про файл
                        file_info = file_report["data"]["attributes"]
                        file_size = file_info.get("size", 0)
                        file_type = file_info.get("type_description", "Unknown")
                        scan_date = file_info.get("last_analysis_date", 0)

                        info_text = f"📁 <b>Файл:</b> <code>{safe_filename}</code>\n"
                        info_text += f"📏 <b>Розмір:</b> <code>{self._format_size(file_size)}</code>\n"
                        info_text += f"🏷️ <b>Тип:</b> <code>{file_type}</code>\n"
                        info_text += f"🔍 <b>SHA256:</b> <code>{file_hash[:16]}...</code>\n\n"

                        final_text = f"{status_emoji} <b>Результат сканування:</b> {malicious_count + suspicious_count}/{total_engines}\n\n"
                        final_text += info_text
                        
                        if malicious_count > 0:
                            final_text += f"🚨 <b>Виявлено загроз:</b> {malicious_count}\n"
                        if suspicious_count > 0:
                            final_text += f"⚠️ <b>Підозрілих:</b> {suspicious_count}\n"
                            
                        final_text += f"\n{result_text}"

                        url = f"https://www.virustotal.com/gui/file/{file_hash}/detection"
                        
                        await self.inline.form(
                            text=final_text,
                            message=message,
                            reply_markup={
                                "text": self.strings("link"),
                                "url": url,
                            },
                        )

                except Exception as e:
                    await utils.answer(
                        message,
                        f"{self.strings('error')}\n\n<code>{type(e).__name__}: {str(e)}</code>",
                    )

    def _format_size(self, size_bytes):
        """Форматує розмір файлу у зручному вигляді"""
        if size_bytes == 0:
            return "0 B"
        
        size_names = ["B", "KB", "MB", "GB"]
        i = 0
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024
            i += 1
        
        return f"{size_bytes:.1f} {size_names[i]}"

    @loader.command()
    async def vtconfig(self, message: Message):
        """Показує поточну конфігурацію модуля VirusTotal"""
        config_text = "⚙️ <b>Конфігурація VirusTotal:</b>\n\n"
        
        if self.config.get("token-vt"):
            token = self.config["token-vt"]
            masked_token = f"{token[:8]}...{token[-4:]}" if len(token) > 12 else "***"
            config_text += f"🔑 <b>API ключ:</b> <code>{masked_token}</code> ✅\n"
        else:
            config_text += f"🔑 <b>API ключ:</b> <i>не встановлено</i> ❌\n"
            
        config_text += f"⏱️ <b>Час очікування:</b> <code>{self.config['max_wait_time']} сек</code>\n\n"
        config_text += "<i>Для налаштування використовуйте команди модуля конфігурації</i>"
        
        await utils.answer(message, config_text)