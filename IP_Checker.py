#meta developer: @Vadym_Yem

from .. import loader, utils
import requests

@loader.tds
class IPCheckerMod(loader.Module):
    """Информация об IP адресе"""
    strings = {"name": "IP_Checker"}
    
    async def ipcmd(self, message):
        """ .ip <ip которое пробиваем>"""
        await message.edit(f"<b>Пробиваем....</b>")
        ip = utils.get_args_raw(message)
        is_proxy = False
        is_hosting = True
        if ip == '':
            await message.edit(f"<b>[Ошибка] Введи айпи для пробива.</b>")
            return
        else:
            response = requests.get('http://ip-api.com/json/{ip}?fields=26404155'.format(ip = ip))
            if response.json()['status'] == 'success':
                if response.json()['proxy'] == True:
                    is_proxy = "Да"
                else:
                    is_proxy = "Нет"
            else:
                pass
            if response.json()['status'] == 'success':
                if response.json()['hosting'] == True:
                    is_hosting = "Да"
                else:
                    is_hosting = "Нет"
            else:
                pass
            if response.json()['status'] == 'fail':
                await message.edit(f"<b>[Ошибка] Информация по этому IP не может быть найдена.\nДанные об ошибке: </b>" + f"<code>{response.json()['message']}</code>")
                return
            else:
                await message.edit("Информация по IP: " + f"<code>{str(response.json()['query'])}</code>" +"\nСтрана: " + f"<code>{str(response.json()['country'])}</code>" +"\nКод страны: " + f"<code>{str(response.json()['countryCode'])}</code>" +"\nОбласть: " + f"<code>{str(response.json()['regionName'])}</code>" +"\nГород: " + f"<code>{str(response.json()['city'])}</code>" +"\nПочтовый индекс: " + f"<code>{str(response.json()['zip'])}</code>" +"\nЧасовой пояс: " + f"<code>{str(response.json()['timezone'])}</code>" +"\nВалюта: " + f"<code>{str(response.json()['currency'])}</code>" +"\nПровайдер: " + f"<code>{str(response.json()['org'])}</code>" +"\nЯвляется прокси сервисом? " + f"<code>{str(is_proxy)}</code>" +"\nЯвляется хостингом? " + f"<code>{str(is_hosting)}</code>")