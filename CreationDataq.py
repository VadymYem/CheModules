
#meta developer: @authorche 

from .. import loader, utils, main 
import asyncio 
 
@loader.tds 
class CreationDateMod(loader.Module): 
  strings = {"name": "CreationData"} 
  """Creation Account Data
""" 
  async def zcmd(self, message): 
    """.z + реплай на нужного нам человека""" 
    reply = await message.get_reply_message() 
    await message.edit("<code>За підтримки:</code> @AuthorChe ") 
    try: 
      await message.client.send_message(747653812, "<code>/id </code>" + str(reply.sender.id)) 
      messages = await message.client.get_messages('Telegram') 
      messages[0].click() 
      await asyncio.sleep(0) 
      messages2 = await message.client.get_messages(747653812) 
      await message.edit(str(messages2[0].message)) 
    except Exception as ex: 
      await message.edit(str(ex))