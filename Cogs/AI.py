from discord.ext.commands import Cog, command, MissingRequiredArgument
import openai
from os import getenv
from random import randint

from utils import package_message


OPENAI_API_KEY = getenv("CHATGPT_TOKEN")
OPENAI_ORG = getenv("CHATGPT_ORG")


class AI(Cog):

    def __init__(self):
        openai.api_key = getenv("CHATGPT_TOKEN")
        openai.organization = getenv("CHATGPT_ORG")

        self.messages = [{"role": "system", "content": "You are a Time-Travelling Golem named Karn."}]

        self.reply_chance = 1

    @command(help="Generates natural language or code from a given prompt",
             brief="Generates natural language")
    async def chat(self, ctx, *, args):
        self.messages.append({"role": "user", "content": args})
        chat = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=self.messages)
        reply = chat.choices[0].message.content
        await package_message(reply, ctx)
        self.messages.append({"role": "assistant", "content": reply})

    @chat.error
    async def chat_error(self, ctx, error):
        if isinstance(error, MissingRequiredArgument):
            await ctx.send("You must include a prompt with this command.\n"
                           "Example: $chat tell me a joke\n\n"
                           "Please use `$help chat` for more information.")

    async def send_reply(self, msg, bot_id):
        if msg.author.id == bot_id:
            return

        if "karn" in msg.content or "Karn" in msg.content:
            return await self.chat(msg.channel, args=msg.content)

        if randint(1, 100) <= self.reply_chance:
            await self.chat(msg.channel, args=msg.content)
            self.reply_chance = 1
            return

        self.reply_chance += 1
