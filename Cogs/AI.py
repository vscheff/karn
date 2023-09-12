from discord import TextChannel, VoiceChannel
from discord.ext.commands import Cog, command, MissingRequiredArgument
from mysql.connector.errors import OperationalError
import openai
from os import getenv, stat
from os.path import exists
from random import choice, randint
from re import search, sub
from tiktoken import encoding_for_model

from utils import package_message


MAX_TOKENS = 4096
MAX_MSG_LEN = 3 * MAX_TOKENS // 4
TOKENS_PER_MESSAGE = 3
TOKENS_PER_REPLY = 3
MODEL = "gpt-3.5-turbo"
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
AI_DESCRIPTOR_FILEPATH = "./files/descriptor.txt"
DEFAULT_RUDE_MESSAGE = "shut up"
DEFAULT_RUDE_RESPONSE = "I will leave, my apologies."
DEFAULT_DESCRIPTOR = "your humble assistant"


class AI(Cog):

    def __init__(self, conn):
        openai.api_key = getenv("CHATGPT_TOKEN")
        openai.organization = getenv("CHATGPT_ORG")

        self.conn = conn

        self.reply_chance = 1

        try:
            self.get_rude_messages()
        except FileNotFoundError:
            self.rude_messages = [DEFAULT_RUDE_MESSAGE]
            with open(RUDE_MESSAGES_FILEPATH, 'w') as out_file:
                out_file.writelines(i + '\n' for i in self.rude_messages)

        self.rude_mtime = stat(RUDE_MESSAGES_FILEPATH).st_mtime_ns

        try:
            self.get_descriptors()
        except FileNotFoundError:
            self.descriptors = [DEFAULT_DESCRIPTOR]
            with open(AI_DESCRIPTOR_FILEPATH, 'w') as out_file:
                out_file.writelines(i + '\n' for i in self.descriptors)

        self.desc_mtime = stat(RUDE_MESSAGES_FILEPATH).st_mtime_ns

        if not exists(RUDE_RESPONSE_FILEPATH):
            with open(RUDE_RESPONSE_FILEPATH, 'w') as out_file:
                out_file.writelines(i + '\n' for i in [DEFAULT_RUDE_RESPONSE])

    def get_cursor(self):
        try:
            return self.conn.cursor()
        except OperationalError:
            self.conn.reconnect()
            return self.conn.cursor()

    def get_rude_messages(self):
        with open(RUDE_MESSAGES_FILEPATH, 'r') as in_file:
            self.rude_messages = [i.strip().lower() for i in in_file.readlines()]

    def get_descriptors(self):
        with open(AI_DESCRIPTOR_FILEPATH, 'r') as in_file:
            self.descriptors = [i.strip() for i in in_file.readlines()]

    @command(help="Generates natural language or code from a given prompt",
             brief="Generates natural language",
             aliases=["chat", "promt"])
    async def prompt(self, ctx, *, args, author=None):
        cursor = self.get_cursor()

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

        if stat(AI_DESCRIPTOR_FILEPATH).st_mtime_ns != self.desc_mtime:
            self.get_descriptors()
            self.desc_mtime = stat(RUDE_MESSAGES_FILEPATH).st_mtime_ns

        desc = choice(self.descriptors)
        reply = chat.choices[0].message.content
        # https://regex101.com/r/OF8qy1/4
        pattern = r"([aA]s)* an* (?:digital)*(?:virtual)*(?:time-traveling)* *" \
                  r"(?:golem)* *(?:(?:AI)|(?:digital))\s*(?:language model)*(?:assistant)*"
        reply = sub(pattern, r"\1 " + desc, reply)

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
        cursor = self.get_cursor()

        cursor.execute(f"DELETE FROM Karn WHERE channel_id = '{ctx.channel.id}'")

        await ctx.send(f"Deleted {cursor.rowcount} context messages from the database.")

        self.conn.commit()
        cursor.close()

    async def send_reply(self, msg):
        if len(msg.content) < MIN_MESSAGE_LEN:
            return

        # https://regex101.com/r/qA25Ux/1
        if search(r"[Kk]arn(?:\Z|[^+\-])", msg.content):
            if stat(RUDE_MESSAGES_FILEPATH).st_mtime_ns != self.rude_mtime:
                self.get_rude_messages()
                self.rude_mtime = stat(RUDE_MESSAGES_FILEPATH).st_mtime_ns

            lowered_content = msg.content.lower()

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
