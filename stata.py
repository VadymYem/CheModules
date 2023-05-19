from .. import loader
from telethon.tl.types import *
@loader.tds
class StataMod(loader.Module):
  "Статистика чатy"
  strings = {"name": "ChatStata"}
  @loader.owner
  async def statacmd(self, m):
	  await m.edit("<b>📊Рахую...</b>")
	  al = str((await m.client.get_messages(m.to_id, limit=0)).total)
	  ph = str((await m.client.get_messages(m.to_id, limit=0, filter=InputMessagesFilterPhotos())).total)
	  vi = str((await m.client.get_messages(m.to_id, limit=0, filter=InputMessagesFilterVideo())).total)
	  mu = str((await m.client.get_messages(m.to_id, limit=0, filter=InputMessagesFilterMusic())).total)
	  vo = str((await m.client.get_messages(m.to_id, limit=0, filter=InputMessagesFilterVideo())).total)
	  vv = str((await m.client.get_messages(m.to_id, limit=0, filter=InputMessagesFilterRoundVideo())).total)
	  do = str((await m.client.get_messages(m.to_id, limit=0, filter=InputMessagesFilterDocument())).total)
	  urls = str((await m.client.get_messages(m.to_id, limit=0, filter=InputMessagesFilterUrl())).total)
	  gifs = str((await m.client.get_messages(m.to_id, limit=0, filter=InputMessagesFilterGif())).total)
	  geos = str((await m.client.get_messages(m.to_id, limit=0, filter=InputMessagesFilterGeo())).total)
	  cont = str((await m.client.get_messages(m.to_id, limit=0, filter=InputMessagesFilterContacts())).total)
	  await m.edit(
	    ("<b>✉️Всього повідомлень:</b> {}\n"+
	    "<b>🖼️Всього фотографій:</b> {}\n"+
	    "<b>📹Всього відео:</b> {}\n"+
	    "<b>🎵Всього музики: :</b> {}\n"+
	    "<b>🎶Всього голосових повідомлень:</b> {}\n"+
	    "<b>🎥Всього відеоповідомлень:</b> {}\n"+
	    "<b>📂Всього файлів:</b> {}\n"+
	    "<b>🔗Всього посилань:</b> {}\n"+
	    "<b>🎞️Всього GIF:</b> {}\n"+
	    "<b>🗺️Всього координат:</b> {}\n"+
	    "<b>👭Контактів:</b> {}").format(al, ph, vi, mu, vo, vv, do, urls, gifs, geos, cont))