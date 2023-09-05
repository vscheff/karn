from discord import TextChannel
from discord.ext.commands import Cog, command, MissingRequiredArgument
from mysql.connector import connection, errors
import openai
from os import getenv
from random import randint
from tiktoken import get_encoding

from utils import package_message


MAX_TOKENS = 4096
MAX_MSG_LEN = 2 * MAX_TOKENS // 3
STATIC_TOKENS = 5
SQL_CONN_PARAMS = {"user": getenv("SQL_USER"),
                   "password": getenv("SQL_PASSWORD"),
                   "host": "localhost",
                   "database": "discord"}
MIN_MESSAGE_LEN = 4
GENESIS_MESSAGE = {"role": "system",
                   "content": "You are a time-travelling golem named Karn. "
                              "You are currently acting as an AI assistant for a Discord server. "
                              "Message content from Discord will follow the format: \"Name: Message\" "
                              "where \"Name\" is the name of the user who sent the message, "
                              "and \"Message\" is the message that was sent. "
                              "Do not prefix your responses with anyone's name."}


class AI(Cog):

    def __init__(self):
        openai.api_key = getenv("CHATGPT_TOKEN")
        openai.organization = getenv("CHATGPT_ORG")

        self.conn = None
        self.connect_to_sql_database()

        self.encoding = get_encoding("cl100k_base")

        self.reply_chance = 1

    def connect_to_sql_database(self):
        try:
            self.conn = connection.MySQLConnection(**SQL_CONN_PARAMS)
        except errors.ProgrammingError as e:
            print(f"ERROR: Database connection failed with error:\n{e}.")

    @command(help="Generates natural language or code from a given prompt",
             brief="Generates natural language",
             aliases=["chat", "promt"])
    async def prompt(self, ctx, *, args, author=None):
        try:
            cursor = self.conn.cursor()
        except errors.OperationalError:
            self.connect_to_sql_database()
            cursor = self.conn.cursor()

        channel_id = ctx.id if isinstance(ctx, TextChannel) else ctx.channel.id
        author = author if author else ctx.author.display_name
        cursor.execute(f"SELECT usr_role, content, id FROM Karn WHERE channel_id = {channel_id}")
        messages = [{"role": role, "content": content, "id": uuid} for role, content, uuid in cursor.fetchall()]

        if not messages:
            values = [channel_id, GENESIS_MESSAGE["role"], GENESIS_MESSAGE["content"]]
            cursor.execute("INSERT INTO Karn (channel_id, usr_role, content, id) VALUES (%s, %s, %s, UUID())", values)
            messages = [{key: val for key, val in GENESIS_MESSAGE.items()}]

        messages.append({"role": "user", "content": f"{author}: {args}"})
        values = [channel_id, "user", f"{author}: {args}"]
        cursor.execute("INSERT INTO Karn (channel_id, usr_role, content, id) VALUES (%s, %s, %s, UUID())", values)

        context_str = '\n'.join([f"{i['role']}: {i['content']}" for i in messages])

        while len(self.encoding.encode(context_str)) > MAX_MSG_LEN:
            for _ in range(2):
                del_msg = messages.pop(1)
                cursor.execute(f"DELETE FROM Karn WHERE id = '{del_msg['id']}'")
            context_str = '\n'.join([f"{i['role']}: {i['content']}" for i in messages])

        context = [{"role": i["role"], "content": i["content"]} for i in messages]
        chat = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=context)

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

        lowered_content = msg.content.lower()

        if "karn" in lowered_content:
            if "fuck off" in lowered_content:
                return await msg.channel.send("I will fuck right off.")

            return await self.prompt(msg.channel, args=msg.content, author=msg.author.display_name)

        if randint(1, 100) <= self.reply_chance:
            await self.prompt(msg.channel, args=msg.content, author=msg.author.display_name)
            self.reply_chance = 1
            return

        self.reply_chance += 1
