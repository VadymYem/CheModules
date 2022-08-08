
#                     Copyright 2022 t.me/AuthorChe 
#           Licensed under the Creative Commons CC BY-NC-ND 4.0
#
#                    Full license text can be found at:
#       https://creativecommons.org/licenses/by-nc-nd/4.0/legalcode
#
#                           Human-friendly one:
#            https://creativecommons.org/licenses/by-nc-nd/4.0

# meta developer: @Vadym_Yem


from telethon import events
from telethon.errors.rpcerrorlist import YouBlockedUserError

from .. import loader, utils


@loader.tds
class AsciiCheMod(loader.Module):
    """Ascii Art"""

    strings = {"name": "AsciiArt"}

    @loader.owner
    async def asciicmd(self, message):
        """Ascii Art"""
        args = utils.get_args_raw(message)
        reply = await message.get_reply_message()
        if not reply:
            return await message.edit("<b>Reply to media</b>")
        try:
            media = reply.media
        except Exception:
            return await message.edit("<b>Only media</b>")
        chat = "@asciiart_bot"
        await message.edit("<b>За підтримки @AuthorChe</b>")
        async with message.client.conversation(chat) as conv:
            try:
                response = conv.wait_event(
                    events.NewMessage(incoming=True, from_users=164766745)
                )
                mm = await message.client.send_file(chat, media, caption=args)
                response = await response
                await mm.delete()
            except YouBlockedUserError:
                return await message.reply(
                    "<b>Разблокируй @asciiart_bot</b>"
                )
            await message.delete()
            await response.delete()
            await message.client.send_file(
                message.to_id,
                response.media,
                reply_to=await message.get_reply_message(),
            )
