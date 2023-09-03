from discord import TextChannel
from discord.ext.commands import Cog, command, MissingRequiredArgument
from json import dump, load
import openai
from os import getenv
from random import randint

from utils import package_message


MIN_MESSAGE_LEN = 4
MESSAGE_HISTORY_FILEPATH = "./msg_history.json"
GENESIS_MESSAGE = {"role": "system",
                   "content": "You are a time-travelling golem named Karn. "
                              "You are currently acting as an AI assistant for a Discord server."}


class AI(Cog):

    def __init__(self):
        openai.api_key = getenv("CHATGPT_TOKEN")
        openai.organization = getenv("CHATGPT_ORG")

        try:
            with open(MESSAGE_HISTORY_FILEPATH, 'r') as inFile:
                self.messages = load(inFile)
        except FileNotFoundError:
            self.messages = {}

        self.reply_chance = 1

    @command(help="Generates natural language or code from a given prompt",
             brief="Generates natural language")
    async def prompt(self, ctx, *, args):
        channel_id = str(ctx.id if isinstance(ctx, TextChannel) else ctx.channel.id)

        if channel_id not in self.messages:
            self.messages[channel_id] = [{key: val for key, val in GENESIS_MESSAGE.items()}]

        self.messages[channel_id].append({"role": "user", "content": args})

        while True:
            try:
                chat = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=self.messages[channel_id])
            except openai.error.InvalidRequestError:
                self.messages[channel_id].pop(1)
            else:
                break

        reply = chat.choices[0].message.content
        await package_message(reply, ctx)
        self.messages[channel_id].append({"role": "assistant", "content": reply})

        with open(MESSAGE_HISTORY_FILEPATH, 'w') as outFile:
            dump(self.messages, outFile, indent=2)

    @prompt.error
    async def prompt_error(self, ctx, error):
        if isinstance(error, MissingRequiredArgument):
            await ctx.send("You must include a prompt with this command.\n"
                           "Example: $prompt tell me a joke\n\n"
                           "Please use `$help prompt` for more information.")

    async def send_reply(self, msg, bot_id):
        if msg.author.id == bot_id or len(msg.content) < MIN_MESSAGE_LEN or msg.content[0] == '$':
            return

        if "karn" in msg.content.lower():
            return await self.prompt(msg.channel, args=msg.content)

        if randint(1, 100) <= self.reply_chance:
            await self.prompt(msg.channel, args=msg.content)
            self.reply_chance = 1
            return

        self.reply_chance += 1
