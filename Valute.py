from telethon import events
from telethon.errors.rpcerrorlist import YouBlockedUserError
from .. import loader, utils

class ValuteMod(loader.Module):
    """Valute Converter"""

    strings = {"name": "Valute"}

    async def valcmd(self, message):
        """<sum> <valute> - Get exchange"""
        state = utils.get_args_raw(message)

        if not state:
            await utils.answer(message, "<b>Будь ласка, введіть суму та валюту для конвертації.</b>")
            return

        chat = "@exchange_rates_vsk_bot"

        try:
            async with message.client.conversation(chat) as conv:
                # Очікуємо відповідь від бота
                response = conv.wait_event(
                    events.NewMessage(incoming=True, from_users=1210425892)
                )

                # Відправляємо повідомлення боту
                bot_send_message = await message.client.send_message(
                    chat, state.strip()
                )

                # Чекаємо на відповідь
                bot_response = await response

        except YouBlockedUserError:
            await utils.answer(message, f"<b>Убери из ЧС:</b> {chat}")
            return
        except Exception as e:
            await utils.answer(message, f"<b>Сталася помилка:</b> {str(e)}")
            return

        # Перевіряємо, чи є текст у відповіді
        if bot_response.message.message:
            # Відправляємо текст без імені відправника
            await message.client.send_message(message.chat_id, bot_response.message.message)
        else:
            # Якщо немає тексту — пересилаємо повідомлення з іменем відправника
            await message.client.forward_messages(message.chat_id, bot_response.message)

        # Видаляємо повідомлення, щоб не захаращувати чат
        await message.delete()  # Видаляємо введену команду
        await bot_send_message.delete()
        await bot_response.delete()

    async def convcmd(self, message):
        """<sum> <from_valute> <to_valute> - Convert currency"""
        args = utils.get_args(message)

        if len(args) != 3:
            await utils.answer(message, "<b>Будь ласка, введіть суму і дві валюти для конвертації.</b>")
            return

        sum_value, from_currency, to_currency = args

        chat = "@exchange_rates_vsk_bot"
        convert_command = f"/convert {sum_value} {from_currency.upper()} {to_currency.upper()}"

        try:
            async with message.client.conversation(chat) as conv:
                # Очікуємо відповідь від бота
                response = conv.wait_event(
                    events.NewMessage(incoming=True, from_users=1210425892)
                )

                # Відправляємо команду /convert боту
                bot_send_message = await message.client.send_message(
                    chat, convert_command
                )

                # Чекаємо на відповідь
                bot_response = await response

        except YouBlockedUserError:
            await utils.answer(message, f"<b>Убери из ЧС:</b> {chat}")
            return
        except Exception as e:
            await utils.answer(message, f"<b>Сталася помилка:</b> {str(e)}")
            return

        # Перевіряємо, чи є текст у відповіді
        if bot_response.message.message:
            # Відправляємо текст без імені відправника
            await message.client.send_message(message.chat_id, bot_response.message.message)
        else:
            # Якщо немає тексту — пересилаємо повідомлення з іменем відправника
            await message.client.forward_messages(message.chat_id, bot_response.message)

        # Видаляємо повідомлення, щоб не захаращувати чат
        await message.delete()  # Видаляємо введену команду
        await bot_send_message.delete()
        await bot_response.delete()