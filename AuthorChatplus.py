from .. import loader, utils
def register(cb):
	cb(AuthorChatPlusMod())
class AuthorChatPlusMod(loader.Module):
	"""use achelp"""
	strings = {'name': 'AuthorChat'}
	def __init__(self):
		self.name = self.strings['name']
		self._me = None
		self._ratelimit = []
	async def client_ready(self, client, db):
		self._db = db
		self._client = client
		self.me = await client.get_me()
	async def achelpcmd(self, message):
		"""Show Info"""
		await message.edit("""<code>This module is now available only to users of AuthorChe's userbot</code>
""")


		