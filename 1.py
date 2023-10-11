

from random import choice, randint

from .. import loader, utils
from ..inline.types import InlineQuery


@loader.tds
class InlineRandomMod(loader.Module):
    """Random tools for your userbot"""

    strings = {"name": "InlineRandom"}

    @loader.inline_everyone
    async def coin_inline_handler(self, query: InlineQuery) -> dict:
        """Орел чи Решка?"""

        r = "🦅 Орел" if randint(0, 1) else "🪙 Решка"

        return {
            "title": "Кинути монетку =)",
            "description": "Орел чи решка. Перевір свою вдачу!",
            "message": f"<i>В тебе випало...</i> <b>{r}</b>",
            "thumb": "https://img.icons8.com/external-justicon-flat-justicon/64/000000/external-coin-pirates-justicon-flat-justicon-1.png",
        }

    @loader.inline_everyone
    async def random_inline_handler(self, query: InlineQuery) -> dict:
        """[number] - вибрати рандом число менше вказаного"""

        if not query.args:
            return

        a = query.args

        if not str(a).isdigit():
            return

        return {
            "title": "Вибрати число менше ніж {a}",
            "description": "Бог удачі вибере вам рандомно число, нижче вказаного!",
            "message": f"<i>Бог удачі вибирає число...</i> <b>{randint(1, int(a))}</b>",
            "thumb": "https://img.icons8.com/external-flaticons-flat-flat-icons/64/000000/external-numbers-auction-house-flaticons-flat-flat-icons.png",
        }

    @loader.inline_everyone
    async def choice_inline_handler(self, query: InlineQuery) -> dict:
        """[аргументи, розділені комою] - Зробити вибір"""

        if not query.args or not query.args.count(","):
            return

        a = query.args

        return {
            "title": "Виберу одне зі списку",
            "description": "Допоможу в надскладному виборі!",
            "message": (
                "<i>Бог удачі вибрав...</i>"
                f" <b>{choice(a.split(',')).strip()}</b>"
            ),
            "thumb": "https://img.icons8.com/external-filled-outline-geotatah/64/000000/external-choice-customer-satisfaction-filled-outline-filled-outline-geotatah.png",
        }