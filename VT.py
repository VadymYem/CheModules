
#meta developer: @AuthorChe

import os, json, requests
from .. import loader, utils

def register(cb):
 cb(VirusMod())

class VirusMod(loader.Module):
 strings = {'name': 'VirusTotal'}
 def init(self):
  self.name = self.strings['name']
  self._me = None
  self._ratelimit = []

 async def vtcmd(self, message):
  """Checks files for viruses using VirusTotal"""
  fil = ""
  reply = await message.get_reply_message()
  if not reply:
   await message.edit("<b>You did not select the file.</b>")
   return
  else:
   for i in os.listdir():
    if "file" in i:
     os.system(f"rm -rf {i}")
   await message.edit("<b>Download...</b>")
   await reply.download_media('file')
   for i in os.listdir():
    if "file" in i:
     fil = i
   if not fil:
    await message.edit("<b>You did not select the file.</b>")
    return
   await message.edit("<b>Scan...</b>") 
   if fil not in ["file.jpg", "file.png", "file.ico", "file.mp3", "file.mp4", "file.gif", "file.txt"]: 
    token = "36a0e8d295738c70d877b5aca0be95d5fac70525edf2b48e2ea802bcd7226ec3"
    params = dict(apikey = token)
    with open(fil, 'rb') as file:
     files = dict(file=(fil, file))
     response = requests.post('https://www.virustotal.com/vtapi/v2/file/scan', files=files, params=params)
    os.system(f"rm -rf {fil}")
    try:
     if response.status_code == 200:
      false = []
      result=response.json()
      res = (json.dumps(result, sort_keys=False, indent=4)).split()[10].split('"')[1]
      params = dict(apikey = token, resource=res)
      response = requests.get('https://www.virustotal.com/vtapi/v2/file/report', params=params)
      if response.status_code == 200:
       result = response.json()
       for key in result['scans']:
        if result['scans'][key]['detected']:
         false.append(f"⛔️ <b>{key}</b>\n ╰ <code>{result['scans'][key]['result']}</code>")
      out = '\n'.join(false) if len(false) > 0 else '<b>✅ File is clean.</b>'
      await message.edit(f"🧬 Detections: {len(false)} / {len(result['scans'])}\n\n{out}\n\n" + f'''⚜️<a href="https://www.virustotal.com/gui/file/{result['resource']}/detection">Link to VirusTotal</a>''')
    except:
     await message.edit("<b>Scan Error.</b>")
   else:
    await message.edit("<b>This format is not supported.</b>")
    os.system(f"rm -rf {fil}")