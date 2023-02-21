

import openai
from .. import loader, utils
from telethon.tl.types import Message  # type: ignore


@loader.tds
class ChatGPTMod(loader.Module):
    strings = {
        "name": "ChatGPT",
        "wait": "<emoji document_id=5471981853445463256>🤖</emoji><b> ChatGPT generating response, please wait</b>",
        "quest": "\n\n\n<emoji document_id=5819167501912640906>❔</emoji><b> Your question to ChatGPT was:</b> {args}",
        "args_err": "<emoji document_id=5215534321183499254>⛔️</emoji><b> You didn't ask a question ChatGPT</b>",
        "conf_err": "<emoji document_id=5215534321183499254>⛔️</emoji><b> You didn't provide an api key for ChatGPT</b>",
    }
    strings_ua = {
        "wait": "<emoji document_id=5471981853445463256>🤖</emoji><b> Штучний інтелект генерує відповідь, зачекайте</b>",
        "quest": "\n\n\n<emoji document_id=5819167501912640906>❔</emoji><b> Вашим питанням було:</b> {args}",
        "args_err": "<emoji document_id=5215534321183499254>⛔️</emoji><b> Ви не запитали нічого</b>",
        "conf_err": "<emoji document_id=5215534321183499254>⛔️</emoji><b> Ви не вказали api key для ChatGPT</b>",
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "api_key",
                None,
                lambda: "Api key for ChatGPT",
                validator=loader.validators.Hidden(),
            ),
        )

    async def gptcmd(self, message: Message):
        """<question> - question for ChatGPT"""
        args = utils.get_args_raw(message)
        if not args:
            await utils.answer(message, self.strings("args_err"))
            return
        if self.config["api_key"] is None:
            await utils.answer(message, self.strings("conf_err"))
            return
        await utils.answer(message, self.strings("wait").format(args=args))
        openai.api_key = self.config["api_key"]
        model_engine = "text-davinci-003"
        completion = openai.Completion.create(
            engine=model_engine,
            prompt=args,
            max_tokens=1024,
            n=1,
            stop=None,
            temperature=0.5,
        )
        response = completion.choices[0].text
        await utils.answer(message, response + self.strings("quest").format(args=args))