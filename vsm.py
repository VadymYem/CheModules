#meta developer: @AuthorChe | @Vadym_Yem 
from .. import loader, utils 
 
@loader.tds 
class SearchvMusicMod(loader.Module): 
    """ 
    Модуль SearchMusic - поиск музыки 
    Работает через бота 
    """ 
    strings = {"name": "SearchMusic-v1"} 
 
    async def vsmcmd(self, message): 
        """Используй: .vsm «название» чтобы найти музыку по названию.""" 
        args = utils.get_args_raw(message) 
        reply = await message.get_reply_message() 
        if not args: 
            return await message.edit("<b>Немає аргументів.</b>")  
        try: 
            await message.edit("<b>Завантажую...</b>") 
            music = await message.client.inline_query('shazambot', args) 
            await message.delete() 
            await message.client.send_file(message.to_id, music[0].result.document, reply_to=reply.id if reply else None) 
        except: return await message.client.send_message(message.chat_id, f"<b>Музику з назвою '<code>{args}</code>' не знайдено.</b>")
