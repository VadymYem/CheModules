#meta developer: @Vadym_Yem

from .. import loader, utils
import requests

@loader.tds
class IPCheckerMod(loader.Module):
    """Iнформацiя про IP адрес"""
    strings = {"name": "IP_Checker"}
    
    async def ipcmd(self, message):
        """ .ip <ip яке перевіряємо>"""
        await message.edit(f"<b>Перевіряю....</b>")
        ip = utils.get_args_raw(message)
        is_proxy = False
        is_hosting = True
        if ip == '':
            await message.edit(f"<b>[Помилка] Введи айпі для пробиву.</b>")
            return
        else:
            response = requests.get('http://ip-api.com/json/{ip}?fields=26404155'.format(ip = ip))
            if response.json()['status'] == 'success':
                if response.json()['proxy'] == True:
                    is_proxy = "Так"
                else:
                    is_proxy = "Ні"
            else:
                pass
            if response.json()['status'] == 'success':
                if response.json()['hosting'] == True:
                    is_hosting = "Так"
                else:
                    is_hosting = "Ні"
            else:
                pass
            if response.json()['status'] == 'fail':
                await message.edit(f"<b>[Ошибка] Информация по этому IP не может быть найдена.\nДанные об ошибке: </b>" + f"<code>{response.json()['message']}</code>")
                return
            else:
                await message.edit("Інформація по IP: " + f"<code>{str(response.json()['query'])}</code>" +"\nСтрана: " + f"<code>{str(response.json()['country'])}</code>" +"\nКод країни: " + f"<code>{str(response.json()['countryCode'])}</code>" +"\nОбласть: " + f"<code>{str(response.json()['regionName'])}</code>" +"\nМісто: " + f"<code>{str(response.json()['city'])}</code>" +"\nПоштовий індекс: " + f"<code>{str(response.json()['zip'])}</code>" +"\nЧасовий пояс: " + f"<code>{str(response.json()['timezone'])}</code>" +"\nВалюта: " + f"<code>{str(response.json()['currency'])}</code>" +"\nПровайдер: " + f"<code>{str(response.json()['org'])}</code>" +"\nПроксі сервер? " + f"<code>{str(is_proxy)}</code>" +"\nХостинг? " + f"<code>{str(is_hosting)}</code>")
