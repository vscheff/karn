from discord import TextChannel
from discord.ext.commands import Cog, command, MissingRequiredArgument
from json import dump, load
from mysql.connector import connection, errors
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

        conn_params = {"user": getenv("SQL_USER"),
                       "password": getenv("SQL_PASSWORD"),
                       "host": "localhost",
                       "database": "discord"}

        try:
            self.conn = connection.MySQLConnection(**conn_params)
        except errors.ProgrammingError as e:
            print(f"ERROR: Database connection failed with error:\n{e}.")
            return

        # try:
        #     with open(MESSAGE_HISTORY_FILEPATH, 'r') as inFile:
        #         self.messages = load(inFile)
        # except FileNotFoundError:
        #     self.messages = {}

        self.reply_chance = 1

    @command(help="Generates natural language or code from a given prompt",
             brief="Generates natural language",
             aliases=["chat", "promt"])
    async def prompt(self, ctx, *, args):
        cursor = self.conn.cursor()
        channel_id = ctx.id if isinstance(ctx, TextChannel) else ctx.channel.id
        cursor.execute(f"SELECT usr_role, content, id FROM Karn WHERE channel_id = {channel_id}")
        messages = [{"role": role, "content": content, "id": uuid} for role, content, uuid in cursor.fetchall()]

        if not messages:
            values = [channel_id, GENESIS_MESSAGE["role"], GENESIS_MESSAGE["content"]]
            cursor.execute("INSERT INTO Karn (channel_id, usr_role, content, id) VALUES (%s, %s, %s, UUID())", values)
            messages = [{key: val for key, val in GENESIS_MESSAGE.items()}]

        messages.append({"role": "user", "content": args})
        values = [channel_id, "user", args]
        cursor.execute("INSERT INTO Karn (channel_id, usr_role, content, id) VALUES (%s, %s, %s, UUID())", values)

        while True:
            try:
                context = [{key: val for key, val in i.items() if key != "id"} for i in messages]
                chat = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=context)
            except openai.error.InvalidRequestError:
                del_msg = messages.pop(1)
                cursor.execute(f"DELETE FROM Karn WHERE id = {del_msg['id']}")
            else:
                break

        reply = chat.choices[0].message.content
        await package_message(reply, ctx)
        values = [channel_id, "assistant", reply]
        cursor.execute("INSERT INTO Karn (channel_id, usr_role, content, id) VALUES (%s, %s, %s, UUID())", values)
        self.conn.commit()
        cursor.close()

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
