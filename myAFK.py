import time
import logging
import datetime
import asyncio
from telethon import types
from .. import loader, utils
from ..inline.types import InlineCall
from telethon.tl.functions.users import GetFullUserRequest
from telethon.tl.functions.account import UpdateProfileRequest

logger = logging.getLogger(__name__)


class MyAfkMod(loader.Module):
	"""Professional AFK module by AuthorChe"""

	async def client_ready(self, client, db):
		self._db = db
		self._me = await client.get_me()
		self._db.set(__name__, 'change_name', True)
		# Запускаємо автоматичний режим сну
		asyncio.create_task(self._auto_sleep_manager())

	strings = {
		"name": "myAFK",
		"lname": "| ~⁧  ~dev/",

		"bt_off_afk": "🌟 <b>Режим offline</b> <b>вимкнено</b>! Знову на зв'язку ✨",
		"bt_off_work": "💼 <b>Робочий статус</b> <b>вимкнено</b>! Вільний час ✨",

		"_cfg_cst_btn": "Посилання на чат, яке перебуватиме під текстом АФК. Щоб зовсім прибрати, напишіть None",
		"button__text": "Додати інлайн кнопку відключення АФК режиму?",
		"custom_text__afk_text": "Кастомний текст афк. Використовуй {time} для виведення останнього часу перебування у мережі, {reason} для причини",
		"work_text__text": "Кастомний текст робочого статусу. Використовуй {time} для початку робочого дня",
	}

	def render_settings(self):
		active = self._db.get(__name__, 'afk')
		work_active = self._db.get(__name__, 'work')
		auto_sleep = self._db.get(__name__, 'auto_sleep', True)
		
		if active == True:
			a_active = "Увімкнено ✅"
		else:
			a_active = 'Вимкнено 🚫'
			
		if work_active == True:
			w_active = "Увімкнено ✅"
		else:
			w_active = 'Вимкнено 🚫'
			
		if auto_sleep == True:
			s_active = "Увімкнено ✅"
		else:
			s_active = 'Вимкнено 🚫'
			
		change_name = self._db.get(__name__, 'change_name')
		if change_name == True:
			a_change_name = 'Так'
		else:
			a_change_name = 'Ні'
		
		# Отримуємо поточний час сервера
		current_time = datetime.datetime.now().strftime("%H:%M:%S")
		current_date = datetime.datetime.now().strftime("%d.%m.%Y")
		
		# Отримуємо налаштування часу
		sleep_start = self.config.get("sleep_start_time", 22)
		sleep_end = self.config.get("sleep_end_time", 8)
		work_start = self.config.get("work_start_time", 9)
		work_end = self.config.get("work_end_time", 18)
			
		text = (
			f'🎆 <b>myAfk Professional</b>\n'
			f'🕒 <b>Час сервера:</b> <code>{current_time}</code> ({current_date})\n\n'
			f'├<b>Offline режим:</b> {a_active}\n'
			f'├<b>Робочий статус:</b> {w_active}\n'
			f'├<b>Авто-сон:</b> {s_active} ({sleep_start:02d}:00-{sleep_end:02d}:00)\n'
			f'├<b>Авто-робота:</b> Увімкнено ✅ ({work_start:02d}:00-{work_end:02d}:00)\n'
			f'└<b>Зміна префікса:</b> <code>{a_change_name}</code> 📝'
		)
		return text

	def __init__(self):
		self.config = loader.ModuleConfig(
			loader.ConfigValue(
				"prefix",
				'| ~⁧  ~dev/',
				doc=lambda: 'Префікс, який додаватиметься до вашого імені під час входу до АФК'
			),
			loader.ConfigValue(
				"afk_text",
				"🔅 <b>Наразі я не в мережі</b>\n📡 Зв'язок зі мною тимчасово недоступний, але кожне ваше повідомлення буде уважно прочитане та отримає відповідь згодом.\n\n✨ Запрошую скористатися моментом і відкрити для себе мою творчість: поезію, музику та авторські проєкти.\n(Кнопки нижче допоможуть швидко перейти до розділів)\n\n{reason_text}",
				doc=lambda: self.strings("custom_text__afk_text"),
			),
			loader.ConfigValue(
				"work_text",
				"💼 <b>Працюю над важливими завданнями</b>\n⚙️ Робочий процес триває вже <code>{time}</code>, і я зосереджений на створенні нового та важливого.\n\n📌 Пропоную у цей час відкрити для себе мої творчі ресурси — вірші, музичні твори та історію мого шляху.\nПовідомлення я отримаю й відповім, щойно завершиться робота.",
				doc=lambda: self.strings("work_text__text"),
			),
			loader.ConfigValue(
				"sleep_text",
				"😴 <b>Відпочиваю</b>\n💤 Ваше повідомлення буде отримане та уважно прочитане, а відповідь надійде після пробудження.\n\n✨ Рекомендую провести цей час із користю — ознайомтеся з моєю поезією, музикою та творчими проєктами.\nКнопки нижче відкриють для вас усі розділи.",
				doc=lambda: "Текст для автоматичного режиму сну",
			),
			loader.ConfigValue(
				"ignore_chats",
				[],
				lambda: "Чати, у яких myAfk не спрацьовуватиме",
				validator=loader.validators.Series(
                    validator=loader.validators.Union(
                        loader.validators.TelegramID(),
                        loader.validators.RegExp("[0-9]"),
                    ),
                ),
			),
			loader.ConfigValue(
				"button",
				True,
				doc=lambda: self.strings("button__text"),
				validator=loader.validators.Boolean(),
			),
			loader.ConfigValue(
				"auto_sleep",
				True,
				doc=lambda: "Автоматичне ввімкнення режиму сну",
				validator=loader.validators.Boolean(),
			),
			loader.ConfigValue(
				"sleep_start_time",
				22,
				doc=lambda: "Година початку автоматичного режиму сну (0-23)",
				validator=loader.validators.Integer(minimum=0, maximum=23),
			),
			loader.ConfigValue(
				"sleep_end_time",
				8,
				doc=lambda: "Година закінчення автоматичного режиму сну (0-23)",
				validator=loader.validators.Integer(minimum=0, maximum=23),
			),
			loader.ConfigValue(
				"auto_work",
				False,
				doc=lambda: "Автоматичне ввімкнення робочого статусу",
				validator=loader.validators.Boolean(),
			),
			loader.ConfigValue(
				"work_start_time",
				9,
				doc=lambda: "Година початку автоматичного робочого дня (0-23)",
				validator=loader.validators.Integer(minimum=0, maximum=23),
			),
			loader.ConfigValue(
				"work_end_time",
				18,
				doc=lambda: "Година закінчення автоматичного робочого дня (0-23)",
				validator=loader.validators.Integer(minimum=0, maximum=23),
			),
		)

	def _get_main_buttons(self):
		"""Повертає основні кнопки для всіх повідомлень"""
		return [
			[
				{
					"text": "✍️ Про Автора", 
					"url": "https://authorche.top"
				},
				{
					"text": "💝 Підтримати",
					"url": "https://authorche.top/donate"
				}
			]
		]

	def _afk_custom_text(self, reason=None) -> str:
		if reason:
			reason_text = f"📝 <b>Причина:</b> <i>{reason}</i>"
		else:
			reason_text = ""

		return self.config["afk_text"].format(
			reason_text=reason_text
		)

	def _work_custom_text(self) -> str:
		now = datetime.datetime.now().replace(microsecond=0)
		work_start = datetime.datetime.fromtimestamp(
			self._db.get(__name__, "work_start")
		).replace(microsecond=0)

		time_diff = now - work_start

		return self.config["work_text"].format(
			time=time_diff
		)

	def _sleep_text(self) -> str:
		return self.config["sleep_text"]

	def _is_time_in_range(self, start_hour, end_hour, current_hour):
		"""Перевіряє чи поточна година знаходиться в діапазоні"""
		if start_hour <= end_hour:
			return start_hour <= current_hour < end_hour
		else:  # Діапазон через північ (наприклад, 22:00 - 8:00)
			return current_hour >= start_hour or current_hour < end_hour

	async def _auto_sleep_manager(self):
		"""Автоматичне управління режимом сну та роботи"""
		while True:
			now = datetime.datetime.now()
			hour = now.hour
			
			# Перевіряємо автоматичний сон
			if self.config.get("auto_sleep", True):
				sleep_start = self.config.get("sleep_start_time", 22)
				sleep_end = self.config.get("sleep_end_time", 8)
				
				is_sleep_time = self._is_time_in_range(sleep_start, sleep_end, hour)
				is_afk = self._db.get(__name__, "afk", False)
				is_work = self._db.get(__name__, "work", False)
				is_sleep_mode = self._db.get(__name__, "sleep_mode", False)
				
				if is_sleep_time and not is_afk and not is_work:
					# Час спати - вмикаємо режим сну
					self._db.set(__name__, "afk", True)
					self._db.set(__name__, "sleep_mode", True)
					self._db.set(__name__, "gone", time.time())
					self._db.set(__name__, "ratelimit", [])
					
					if self._db.get(__name__, "change_name", True):
						prefix = self.config['prefix']
						current_name = (await self._client.get_me()).last_name or ""
						if not current_name.endswith(prefix):
							new_name = current_name + prefix
							await self._client(UpdateProfileRequest(last_name=new_name))
					
				elif not is_sleep_time and is_sleep_mode:
					# Час прокидатися - вимикаємо режим сну
					self._db.set(__name__, "afk", False)
					self._db.set(__name__, "sleep_mode", False)
					self._db.set(__name__, "gone", None)
					self._db.set(__name__, "ratelimit", [])
					
					if self._db.get(__name__, "change_name", True):
						prefix = self.config['prefix']
						current_name = (await self._client.get_me()).last_name or ""
						if current_name.endswith(prefix):
							new_name = current_name[:-len(prefix)]
							await self._client(UpdateProfileRequest(last_name=new_name))
			
			# Перевіряємо автоматичну роботу
			if self.config.get("auto_work", False):
				work_start = self.config.get("work_start_time", 9)
				work_end = self.config.get("work_end_time", 18)
				
				is_work_time = self._is_time_in_range(work_start, work_end, hour)
				is_work = self._db.get(__name__, "work", False)
				is_afk = self._db.get(__name__, "afk", False)
				is_sleep_mode = self._db.get(__name__, "sleep_mode", False)
				
				if is_work_time and not is_work and not is_afk and not is_sleep_mode:
					# Час працювати - вмикаємо робочий режим
					self._db.set(__name__, "work", True)
					self._db.set(__name__, "work_start", time.time())
					self._db.set(__name__, "ratelimit", [])
					
					if self._db.get(__name__, "change_name", True):
						prefix = self.config['prefix']
						current_name = (await self._client.get_me()).last_name or ""
						if not current_name.endswith(prefix):
							new_name = current_name + prefix
							await self._client(UpdateProfileRequest(last_name=new_name))
					
				elif not is_work_time and is_work and self._db.get(__name__, "auto_work_active", False):
					# Робочий день закінчився - вимикаємо робочий режим
					self._db.set(__name__, "work", False)
					self._db.set(__name__, "work_start", None)
					self._db.set(__name__, "ratelimit", [])
					self._db.set(__name__, "auto_work_active", False)
					
					if self._db.get(__name__, "change_name", True):
						prefix = self.config['prefix']
						current_name = (await self._client.get_me()).last_name or ""
						if current_name.endswith(prefix):
							new_name = current_name[:-len(prefix)]
							await self._client(UpdateProfileRequest(last_name=new_name))
			
			await asyncio.sleep(1800)  # Перевіряємо кожні 30 хвилин

	@loader.command()
	async def now(self, message):
		"""- показати поточний час та статус режимів"""
		current_time = datetime.datetime.now()
		time_str = current_time.strftime("%H:%M")
		date_str = current_time.strftime("%d.%m.%Y")
		
		# Перевіряємо активні режими
		is_afk = self._db.get(__name__, "afk", False)
		is_work = self._db.get(__name__, "work", False)
		is_sleep_mode = self._db.get(__name__, "sleep_mode", False)
		
		status_text = f"🕐 <b>Зараз {time_str}</b> ({date_str})\n\n"
		
		if not is_afk and not is_work:
			status_text += "✅ <b>Статус:</b> Онлайн\n"
		else:
			# Визначаємо активний режим та його тривалість
			if is_work:
				work_start = self._db.get(__name__, "work_start")
				if work_start:
					work_start_time = datetime.datetime.fromtimestamp(work_start)
					work_duration = current_time - work_start_time
					duration_str = str(work_duration).split('.')[0]  # Прибираємо мікросекунди
					
					status_text += f"💼 <b>Статус:</b> Робочий режим\n"
					status_text += f"⏱️ <b>Триває:</b> {duration_str}\n"
					
					# Перевіряємо чи це автоматичний режим
					auto_work = self.config.get('auto_work', False)
					if auto_work and self._db.get(__name__, "auto_work_active", False):
						work_end = self.config.get("work_end_time", 18)
						end_hour = datetime.datetime.now().replace(hour=work_end, minute=0, second=0, microsecond=0)
						if current_time < end_hour:
							time_left = end_hour - current_time
							hours_left = int(time_left.total_seconds() // 3600)
							minutes_left = int((time_left.total_seconds() % 3600) // 60)
							status_text += f"🔚 <b>До завершення:</b> {hours_left}г {minutes_left}хв\n"
						
			elif is_sleep_mode:
				gone_time = self._db.get(__name__, "gone")
				if gone_time:
					sleep_start_time = datetime.datetime.fromtimestamp(gone_time)
					sleep_duration = current_time - sleep_start_time
					duration_str = str(sleep_duration).split('.')[0]
					
					status_text += f"😴 <b>Статус:</b> Режим сну (авто)\n"
					status_text += f"⏱️ <b>Триває:</b> {duration_str}\n"
					
					# Час до пробудження
					sleep_end = self.config.get("sleep_end_time", 8)
					tomorrow = current_time + datetime.timedelta(days=1)
					if current_time.hour < sleep_end:
						# Пробудження сьогодні
						wake_time = current_time.replace(hour=sleep_end, minute=0, second=0, microsecond=0)
					else:
						# Пробудження завтра
						wake_time = tomorrow.replace(hour=sleep_end, minute=0, second=0, microsecond=0)
					
					if current_time < wake_time:
						time_left = wake_time - current_time
						hours_left = int(time_left.total_seconds() // 3600)
						minutes_left = int((time_left.total_seconds() % 3600) // 60)
						status_text += f"🌅 <b>До пробудження:</b> {hours_left}г {minutes_left}хв\n"
						
			elif is_afk:
				gone_time = self._db.get(__name__, "gone")
				if gone_time:
					afk_start_time = datetime.datetime.fromtimestamp(gone_time)
					afk_duration = current_time - afk_start_time
					duration_str = str(afk_duration).split('.')[0]
					
					status_text += f"🌙 <b>Статус:</b> Offline режим\n"
					status_text += f"⏱️ <b>Триває:</b> {duration_str}\n"
					
					# Показуємо причину якщо є
					reason = self._db.get(__name__, "afk_reason")
					if reason:
						status_text += f"📝 <b>Причина:</b> <i>{reason}</i>\n"
		
		# Додаємо інформацію про автоматичні режими
		auto_sleep = self._db.get(__name__, 'auto_sleep', True)
		auto_work = self.config.get('auto_work', False)
		
		if auto_sleep or auto_work:
			status_text += "\n🤖 <b>Автоматичні режими:</b>\n"
			
			if auto_sleep:
				sleep_start = self.config.get("sleep_start_time", 22)
				sleep_end = self.config.get("sleep_end_time", 8)
				status_text += f"• 🌙 Сон: {sleep_start:02d}:00-{sleep_end:02d}:00\n"
				
			if auto_work:
				work_start = self.config.get("work_start_time", 9)
				work_end = self.config.get("work_end_time", 18)
				status_text += f"• 💼 Робота: {work_start:02d}:00-{work_end:02d}:00\n"
		
		await utils.answer(message, status_text)

	@loader.command()
	async def afkconfig(self, message):
		"""- відкрити налаштування модуля"""
		
		await self.inline.form(
			message=message, 
			text='<b>⚙️ Відкрити налаштування</b>', 
			reply_markup=[{'text': '🔴 Відкрити', 'callback': self.settings}]
		)

	@loader.command()
	async def afk(self, message):
		"""[причина] - увійти до offline режиму"""
		args = utils.get_args_raw(message)
		reason = args if args else None
		
		self._db.set(__name__, "afk", True)
		self._db.set(__name__, "gone", time.time())
		self._db.set(__name__, "ratelimit", [])
		self._db.set(__name__, "afk_reason", reason)
		self._db.set(__name__, "sleep_mode", False)  # Це не автоматичний сон
		
		change_name = self._db.get(__name__, "change_name", True)

		if change_name:
			prefix = self.config['prefix']
			current_name = (await self._client.get_me()).last_name or ""
			if not current_name.endswith(prefix):
				new_name = current_name + prefix
				await message.client(UpdateProfileRequest(last_name=new_name))

		reason_display = f" з причиною: <i>{reason}</i>" if reason else ""
		await utils.answer(
			message, 
			f'🌙 <b>Offline</b> режим успішно <b>увімкнено</b>{reason_display}!\n\n'
			f'✨ <i>Тепер люди зможуть дізнатися про ваші вірші та музику!</i>'
		)

	@loader.command()
	async def work(self, message):
		"""- увімкнути/вимкнути робочий статус"""
		is_working = self._db.get(__name__, "work", False)
		
		if is_working:
			# Вимикаємо робочий статус
			self._db.set(__name__, "work", False)
			self._db.set(__name__, "work_start", None)
			self._db.set(__name__, "ratelimit", [])
			self._db.set(__name__, "auto_work_active", False)
			
			change_name = self._db.get(__name__, "change_name", True)
			if change_name:
				prefix = self.config['prefix']
				current_name = (await self._client.get_me()).last_name or ""
				if current_name.endswith(prefix):
					new_name = current_name[:-len(prefix)]
					await message.client(UpdateProfileRequest(last_name=new_name))
			
			await utils.answer(message, '💼 <b>Робочий статус</b> успішно <b>вимкнено</b>! Вільний час ✨')
		else:
			# Вмикаємо робочий статус
			self._db.set(__name__, "work", True)
			self._db.set(__name__, "work_start", time.time())
			self._db.set(__name__, "ratelimit", [])
			self._db.set(__name__, "auto_work_active", True)
			
			change_name = self._db.get(__name__, "change_name", True)
			if change_name:
				prefix = self.config['prefix']
				current_name = (await self._client.get_me()).last_name or ""
				if not current_name.endswith(prefix):
					new_name = current_name + prefix
					await message.client(UpdateProfileRequest(last_name=new_name))
			
			await utils.answer(message, '💼 <b>Робочий статус</b> успішно <b>увімкнено</b>!')

	@loader.command()
	async def unafk(self, message):
		"""- вийти з offline режиму"""

		self._db.set(__name__, "afk", False)
		self._db.set(__name__, "work", False)
		self._db.set(__name__, "gone", None)
		self._db.set(__name__, "work_start", None)
		self._db.set(__name__, "ratelimit", [])
		self._db.set(__name__, "sleep_mode", False)
		self._db.set(__name__, "auto_work_active", False)
		
		change_name = self._db.get(__name__, "change_name", True)

		if change_name:
			prefix = self.config['prefix']
			current_name = (await self._client.get_me()).last_name or ""
			if current_name.endswith(prefix):
				new_name = current_name[:-len(prefix)]
				await message.client(UpdateProfileRequest(last_name=new_name))
		
		await utils.answer(message, '🌟 <b>Offline режим</b> успішно <b>вимкнено</b>! Знову на зв\'язку ✨')
		await self.allmodules.log("MyAfk now stopped.")

	def _get_reply_markup(self, is_work=False, is_sleep=False):
		"""Генерує reply markup в залежності від режиму"""
		main_buttons = self._get_main_buttons()
		
		if self.config["button"]:
			if is_work:
				control_button = {
					"text": "💼 Завершити робочий день", 
					"callback": self.button_cancel_work,
				}
			else:
				control_button = {
					"text": "🌟 Повернутися онлайн", 
					"callback": self.button_cancel,
				}
			
			return [
				[control_button]
			] + main_buttons
		else:
			return main_buttons

	@loader.watcher()
	async def watcher(self, message):
		if not isinstance(message, types.Message):
			return
		if utils.get_chat_id(message) in self.config['ignore_chats']: 
			return
		if message.mentioned or getattr(message.to_id, "user_id", None) == self._me.id:
			afk_state = self._db.get(__name__, "afk", False)
			work_state = self._db.get(__name__, "work", False)
			
			if not afk_state and not work_state:
				return
				
			logger.debug("tagged!")
			ratelimit = self._db.get(__name__, "ratelimit", [])
			if utils.get_chat_id(message) in ratelimit:
				return
			else:
				self._db.setdefault(__name__, {}).setdefault("ratelimit", []).append(
					utils.get_chat_id(message)
				)
				self._db.save()
			
			user = await utils.get_user(message)
			if user.is_self or user.bot or user.verified:
				logger.debug("User is self, bot or verified.")
				return
			
			# Визначаємо тип повідомлення та текст
			is_sleep = self._db.get(__name__, "sleep_mode", False)
			
			if work_state:
				text = self._work_custom_text()
				reply_markup = self._get_reply_markup(is_work=True)
			elif is_sleep:
				text = self._sleep_text()
				reply_markup = self._get_reply_markup(is_sleep=True)
			else:
				reason = self._db.get(__name__, "afk_reason")
				text = self._afk_custom_text(reason)
				reply_markup = self._get_reply_markup()
			
			await self.inline.form(
				message=message, 
				text=text,
				reply_markup=reply_markup,
				silent=True
			)

	async def button_cancel(self, call: InlineCall):
		self._db.set(__name__, "afk", False)
		self._db.set(__name__, "gone", None)
		self._db.set(__name__, "ratelimit", [])
		self._db.set(__name__, "sleep_mode", False)
		
		change_name = self._db.get(__name__, "change_name", True)
		await self.allmodules.log("myAFК now not working.")

		if change_name:
			prefix = self.config['prefix']
			current_name = (await self._client.get_me()).last_name or ""
			if current_name.endswith(prefix):
				new_name = current_name[:-len(prefix)]
				await self._client(UpdateProfileRequest(last_name=new_name))

		await call.edit(self.strings["bt_off_afk"])

	async def button_cancel_work(self, call: InlineCall):
		self._db.set(__name__, "work", False)
		self._db.set(__name__, "work_start", None)
		self._db.set(__name__, "ratelimit", [])
		self._db.set(__name__, "auto_work_active", False)
		
		change_name = self._db.get(__name__, "change_name", True)
		await self.allmodules.log("myAFК work mode stopped.")

		if change_name:
			prefix = self.config['prefix']
			current_name = (await self._client.get_me()).last_name or ""
			if current_name.endswith(prefix):
				new_name = current_name[:-len(prefix)]
				await self._client(UpdateProfileRequest(last_name=new_name))

		await call.edit(self.strings["bt_off_work"])

	async def settings(self, call: InlineCall):
		info = self.render_settings()
		await call.edit(
			text=info,
			reply_markup=[
				[
					{
						'text': '📝 Префікс',
						'callback': self.settings_name
					},
					{
						'text': '🌙 Авто-сон',
						'callback': self.settings_auto_sleep
					}
				],
				[
					{
						'text': '💼 Авто-робота',
						'callback': self.settings_auto_work
					},
					{
						'text': '⏰ Час режимів',
						'callback': self.settings_time
					}
				],
				[
					{
						"text": "🚫 Закрити",
						"action": 'close'
					}
				]
			]
		)

	async def settings_time(self, call: InlineCall):
		sleep_start = self.config.get("sleep_start_time", 22)
		sleep_end = self.config.get("sleep_end_time", 8)
		work_start = self.config.get("work_start_time", 9)
		work_end = self.config.get("work_end_time", 18)
		current_time = datetime.datetime.now().strftime("%H:%M")
		
		await call.edit(
			text=(
				f'⏰ <b>Налаштування часу режимів</b>\n\n'
				f'🕒 <b>Поточний час сервера:</b> <code>{current_time}</code>\n\n'
				f'🌙 <b>Режим сну:</b> {sleep_start:02d}:00 - {sleep_end:02d}:00\n'
				f'💼 <b>Робочий час:</b> {work_start:02d}:00 - {work_end:02d}:00\n\n'
				f'ℹ️ Для зміни часу використовуйте конфіг модуля:\n'
				f'• <code>sleep_start_time</code> - початок сну\n'
				f'• <code>sleep_end_time</code> - кінець сну\n'
				f'• <code>work_start_time</code> - початок робочого дня\n'
				f'• <code>work_end_time</code> - кінець робочого дня\n\n'
				f'📝 Значення вказуються в годинах (0-23)'
			),
			reply_markup=[
				[{'text': '↩️ Назад', 'callback': self.settings}]
			]
		)

	async def settings_auto_work(self, call: InlineCall):
		auto_work = self.config.get('auto_work', False)
		work_start = self.config.get("work_start_time", 9)
		work_end = self.config.get("work_end_time", 18)
		status = "увімкнено ✅" if auto_work else "вимкнено 🚫"
		
		await call.edit(
			text=(
				f'💼 <b>Автоматичний робочий статус</b>\n\n'
				f'📊 <b>Поточний статус:</b> {status}\n\n'
				f'⏰ <b>Робочий час:</b> {work_start:02d}:00 - {work_end:02d}:00\n'
				f'💼 При увімкненні модуль автоматично переходить в робочий режим в робочий час\n\n'
				f'❔ <b>Бажаєте змінити налаштування?</b>'
			),
			reply_markup=[
				[
					{
						'text': '✅ Увімкнути',
						"callback": self.auto_work_on
					},
					{
						"text": '🚫 Вимкнути',
						"callback": self.auto_work_off
					}
				],
				[{'text': '↩️ Назад', 'callback': self.settings}]
			]
		)

	async def auto_work_on(self, call: InlineCall):
		self.config['auto_work'] = True
		info = self.render_settings()
		await call.edit(
			text=info,
			reply_markup=[
				[
					{
						'text': '📝 Префікс',
						'callback': self.settings_name
					},
					{
						'text': '🌙 Авто-сон',
						'callback': self.settings_auto_sleep
					}
				],
				[
					{
						'text': '💼 Авто-робота',
						'callback': self.settings_auto_work
					},
					{
						'text': '⏰ Час режимів',
						'callback': self.settings_time
					}
				],
				[
					{
						"text": "🚫 Закрити",
						"action": 'close'
					}
				]
			]
		)

	async def auto_work_off(self, call: InlineCall):
		self.config['auto_work'] = False
		info = self.render_settings()
		await call.edit(
			text=info,
			reply_markup=[
				[
					{
						'text': '📝 Префікс',
						'callback': self.settings_name
					},
					{
						'text': '🌙 Авто-сон',
						'callback': self.settings_auto_sleep
					}
				],
				[
					{
						'text': '💼 Авто-робота',
						'callback': self.settings_auto_work
					},
					{
						'text': '⏰ Час режимів',
						'callback': self.settings_time
					}
				],
				[
					{
						"text": "🚫 Закрити",
						"action": 'close'
					}
				]
			]
		)

	async def settings_auto_sleep(self, call: InlineCall):
		auto_sleep = self._db.get(__name__, 'auto_sleep', True)
		sleep_start = self.config.get("sleep_start_time", 22)
		sleep_end = self.config.get("sleep_end_time", 8)
		status = "увімкнено ✅" if auto_sleep else "вимкнено 🚫"
		
		await call.edit(
			text=(
				f'🌙 <b>Автоматичний режим сну</b>\n\n'
				f'📊 <b>Поточний статус:</b> {status}\n\n'
				f'⏰ <b>Час роботи:</b> {sleep_start:02d}:00 - {sleep_end:02d}:00\n'
				f'💤 При увімкненні модуль автоматично переходить в режим сну вночі\n\n'
				f'❔ <b>Бажаєте змінити налаштування?</b>'
			),
			reply_markup=[
				[
					{
						'text': '✅ Увімкнути',
						"callback": self.auto_sleep_on
					},
					{
						"text": '🚫 Вимкнути',
						"callback": self.auto_sleep_off
					}
				],
				[{'text': '↩️ Назад', 'callback': self.settings}]
			]
		)

	async def auto_sleep_on(self, call: InlineCall):
		self._db.set(__name__, 'auto_sleep', True)
		info = self.render_settings()
		await call.edit(
			text=info,
			reply_markup=[
				[
					{
						'text': '📝 Префікс',
						'callback': self.settings_name
					},
					{
						'text': '🌙 Авто-сон',
						'callback': self.settings_auto_sleep
					}
				],
				[
					{
						'text': '💼 Авто-робота',
						'callback': self.settings_auto_work
					},
					{
						'text': '⏰ Час режимів',
						'callback': self.settings_time
					}
				],
				[
					{
						"text": "🚫 Закрити",
						"action": 'close'
					}
				]
			]
		)

	async def auto_sleep_off(self, call: InlineCall):
		self._db.set(__name__, 'auto_sleep', False)
		info = self.render_settings()
		await call.edit(
			text=info,
			reply_markup=[
				[
					{
						'text': '📝 Префікс',
						'callback': self.settings_name
					},
					{
						'text': '🌙 Авто-сон',
						'callback': self.settings_auto_sleep
					}
				],
				[
					{
						'text': '💼 Авто-робота',
						'callback': self.settings_auto_work
					},
					{
						'text': '⏰ Час режимів',
						'callback': self.settings_time
					}
				],
				[
					{
						"text": "🚫 Закрити",
						"action": 'close'
					}
				]
			]
		)

	async def settings_name(self, call: InlineCall):
		change_name = self._db.get(__name__, 'change_name', True)
		status = "увімкнено ✅" if change_name else "вимкнено 🚫"
		
		await call.edit(
			text=(
				f'📝 <b>Налаштування префікса</b>\n\n'
				f'📊 <b>Поточний статус:</b> {status}\n'
				f'🏷️ <b>Префікс:</b> <code>{self.config["prefix"]}</code>\n\n'
				f'ℹ️ При увімкненні префікс <b>додається</b> до кінця вашого ніку\n'
				f'⚠️ При вимкненні - нік залишається без змін\n\n'
				f'❔ <b>Бажаєте змінити налаштування?</b>'
			),
			reply_markup=[
				[
					{
						'text': '✅ Увімкнути',
						"callback": self.name_yes
					},
					{
						"text": '🚫 Вимкнути',
						"callback": self.name_no
					}
				],
				[{'text': '↩️ Назад', 'callback': self.settings}]
			]
		)

	async def name_yes(self, call: InlineCall):
		self._db.set(__name__, 'change_name', True)
		info = self.render_settings()
		await call.edit(
			text=info,
			reply_markup=[
				[
					{
						'text': '📝 Префікс',
						'callback': self.settings_name
					},
					{
						'text': '🌙 Авто-сон',
						'callback': self.settings_auto_sleep
					}
				],
				[
					{
						'text': '💼 Авто-робота',
						'callback': self.settings_auto_work
					},
					{
						'text': '⏰ Час режимів',
						'callback': self.settings_time
					}
				],
				[
					{
						"text": "🚫 Закрити",
						"action": 'close'
					}
				]
			]
		)

	async def name_no(self, call: InlineCall):
		self._db.set(__name__, 'change_name', False)
		info = self.render_settings()
		await call.edit(
			text=info,
			reply_markup=[
				[
					{
						'text': '📝 Префікс',
						'callback': self.settings_name
					},
					{
						'text': '🌙 Авто-сон',
						'callback': self.settings_auto_sleep
					}
				],
				[
					{
						'text': '💼 Авто-робота',
						'callback': self.settings_auto_work
					},
					{
						'text': '⏰ Час режимів',
						'callback': self.settings_time
					}
				],
				[
					{
						"text": "🚫 Закрити",
						"action": 'close'
					}
				]
			]
		)

	def get_afk(self):
		return self._db.get(__name__, "afk", False) or self._db.get(__name__, "work", False)