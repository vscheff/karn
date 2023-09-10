from discord import TextChannel, VoiceChannel
from discord.ext.commands import Cog, command, MissingRequiredArgument
from mysql.connector import connection, errors
import openai
from os import getenv, stat
from os.path import exists
from random import choice, randint
from tiktoken import encoding_for_model

from utils import package_message


MAX_TOKENS = 4096
MAX_MSG_LEN = 3 * MAX_TOKENS // 4
TOKENS_PER_MESSAGE = 3
TOKENS_PER_REPLY = 3
MODEL = "gpt-3.5-turbo"
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
RUDE_MESSAGES_FILEPATH = "./files/rude.txt"
RUDE_RESPONSE_FILEPATH = "./files/response.txt"
DEFAULT_RUDE_MESSAGE = "shut up"
DEFAULT_RUDE_RESPONSE = "I will leave, my apologies."


class AI(Cog):

    def __init__(self):
        openai.api_key = getenv("CHATGPT_TOKEN")
        openai.organization = getenv("CHATGPT_ORG")

        self.conn = None
        self.connect_to_sql_database()

        self.reply_chance = 1

        try:
            self.get_rude_messages()
        except FileNotFoundError:
            self.rude_messages = [DEFAULT_RUDE_MESSAGE]
            with open(RUDE_MESSAGES_FILEPATH, 'w') as out_file:
                out_file.writelines(self.rude_messages)

        self.rude_mtime = stat(RUDE_MESSAGES_FILEPATH).st_mtime_ns

        if not exists(RUDE_RESPONSE_FILEPATH):
            with open(RUDE_RESPONSE_FILEPATH, 'w') as out_file:
                out_file.writelines(DEFAULT_RUDE_RESPONSE)

    def connect_to_sql_database(self):
        try:
            self.conn = connection.MySQLConnection(**SQL_CONN_PARAMS)
        except errors.ProgrammingError as e:
            print(f"ERROR: Database connection failed with error:\n{e}.")

    def get_rude_messages(self):
        with open(RUDE_MESSAGES_FILEPATH, 'r') as in_file:
            self.rude_messages = [i.strip().lower() for i in in_file.readlines()]

    @command(help="Generates natural language or code from a given prompt",
             brief="Generates natural language",
             aliases=["chat", "promt"])
    async def prompt(self, ctx, *, args, author=None):
        try:
            cursor = self.conn.cursor()
        except errors.OperationalError:
            self.connect_to_sql_database()
            cursor = self.conn.cursor()

        channel_id = ctx.id if isinstance(ctx, (TextChannel, VoiceChannel)) else ctx.channel.id
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

        while (encoded_len := get_token_len(messages)) > MAX_MSG_LEN:
            cursor.execute(f"DELETE FROM Karn WHERE id = '{messages.pop(1)['id']}'")

        context = [{"role": i["role"], "content": i["content"]} for i in messages]
        chat = openai.ChatCompletion.create(model=MODEL, messages=context, max_tokens=MAX_TOKENS-encoded_len)

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
                           "Example: `$prompt tell me a joke`\n\n"
                           "Please use `$help prompt` for more information.")

    @command(help="Clear all messages in the context history for this channel",
             brief="Clear context history")
    async def clear_context(self, ctx):
        cursor = self.conn.cursor()
        cursor.execute(f"DELETE FROM Karn WHERE channel_id = '{ctx.channel.id}'")

        await ctx.send(f"Deleted {cursor.rowcount} context messages from the database.")

        self.conn.commit()
        cursor.close()

    async def send_reply(self, msg):
        if msg.author.bot or len(msg.content) < MIN_MESSAGE_LEN or msg.content[0] == '$':
            return

        lowered_content = msg.content.lower()

        if "karn" in lowered_content:
            if stat(RUDE_MESSAGES_FILEPATH).st_mtime_ns != self.rude_mtime:
                self.get_rude_messages()

            if any(i in lowered_content for i in self.rude_messages):
                return await msg.channel.send(get_random_response())

            return await self.prompt(msg.channel, args=msg.content, author=msg.author.display_name)

        if randint(1, 100) <= self.reply_chance:
            await self.prompt(msg.channel, args=msg.content, author=msg.author.display_name)
            self.reply_chance = 1
            return

        self.reply_chance += 1


ENCODING = encoding_for_model(MODEL)

def get_token_len(messages):
    num_tokens = 0
    for msg in messages:
        num_tokens += TOKENS_PER_MESSAGE
        for val in msg.values():
            num_tokens += len(ENCODING.encode(val))

    return num_tokens + TOKENS_PER_REPLY

def get_random_response():
    with open(RUDE_RESPONSE_FILEPATH, 'r') as in_file:
        return choice(in_file.readlines())
