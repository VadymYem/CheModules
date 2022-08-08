
#meta developer: @authorche 

from .. import loader, utils, main 
import asyncio 
 
@loader.tds 
class EOGMod(loader.Module): 
  strings = {"name": "AuthorEOG"} 
  """AuthorEOG

P.s Для новых пользователей бота(@eyeofficialgod_bot) нужно подтверждение""" 
  async def xcmd(self, message): 
    """.x + реплай на нужного нам человека""" 
    reply = await message.get_reply_message() 
    await message.edit("<code>За підтримки:</code> @AuthorChe ") 
    try: 
      await message.client.send_message(5204744471, "<code>#id</code>" + str(reply.sender.id)) 
      await asyncio.sleep(2)  
      await asyncio.sleep(3) 
      await asyncio.sleep(4) 
      messages = await message.client.get_messages('Telegram') 
      messages[0].click() 
      await asyncio.sleep(5) 
      messages2 = await message.client.get_messages(5204744471) 
      await message.edit(str(messages2[0].message)) 
    except Exception as ex: 
      await message.edit(str(ex))