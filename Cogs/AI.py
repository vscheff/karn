from asyncio import to_thread
from discord import TextChannel, VoiceChannel
from discord.ext.commands import Cog, command, MissingRequiredArgument
import openai
from os import getenv, stat
from os.path import exists
from random import choice, randint
from re import search, sub
from tiktoken import encoding_for_model

# Local dependencies
from utils import get_cursor, get_flags, package_message


openai.api_key = getenv("CHATGPT_TOKEN")
openai.organization = getenv("CHATGPT_ORG")

# Constants (set by OpenAI and the encoding they use)
MODEL = "gpt-3.5-turbo"
ENCODING = encoding_for_model(MODEL)
MAX_TOKENS = 4096       # Maximum number of tokens for context and response from OpenAI
TOKENS_PER_MESSAGE = 3  # Tokens required for each context message regardless of message length
TOKENS_PER_REPLY = 3    # Tokens required for the response from OpenAI regardless of response length

# Project specific constants
MIN_MESSAGE_LEN = 4                                     # Minimum message length bot will respond to
MAX_MSG_LEN = 3 * MAX_TOKENS // 4                       # Maximum length context to send to OpenAI
RUDE_MESSAGES_FILEPATH = "./files/rude.txt"             # File containing phrases the bot considers "rude"
RUDE_RESPONSE_FILEPATH = "./files/response.txt"         # File containing responses to "rude" messages
AI_DESCRIPTOR_FILEPATH = "./files/descriptor.txt"       # File containing alternate self-descriptors of the bot
DEFAULT_RUDE_MESSAGE = "shut up"                        # Phrase to consider "rude" if file not found
DEFAULT_RUDE_RESPONSE = "I will leave, my apologies."   # Response to "rude" messages if file not found
DEFAULT_DESCRIPTOR = "your humble assistant"            # Self-descriptor to use if file not found

# The default context message used to "prime" the language model in preparation for it to act as our AI assistant
GENESIS_MESSAGE = {"role": "system",
                   "content": "You are a time-travelling golem named Karn. "
                              "You are currently acting as an AI assistant for a Discord server. "
                              "Message content from Discord will follow the format: \"Name: Message\" "
                              "where \"Name\" is the name of the user who sent the message, "
                              "and \"Message\" is the message that was sent. "
                              "Do not prefix your responses with anyone's name."
                              "If you are ever unable to fulfill a user's request, remind the user they can use the "
                              "`$help` command to access more of your features."
                   }


class AI(Cog):

    # param          bot - our client
    # param         conn - connection to the SQL database
    #  attr reply_chance - chance the bot will respond to a message unprompted [%]
    #  attr   rude_mtime - last modification time of the "rude messages" file [ns]
    #  attr   desc_mtime - last modification time of the descriptors file [ns]
    def __init__(self, bot, conn):
        self.bot = bot
        self.conn = conn

        self.reply_chance = 1

        # Import "rude" phrases. If file not found, use default and create a file for future use
        try:
            self.get_rude_messages()
        except FileNotFoundError:
            self.rude_messages = [DEFAULT_RUDE_MESSAGE]
            with open(RUDE_MESSAGES_FILEPATH, 'w') as out_file:
                out_file.writelines(i + '\n' for i in self.rude_messages)

        self.rude_mtime = stat(RUDE_MESSAGES_FILEPATH).st_mtime_ns

        # Import self descriptors. If file not found, use default and create a file for future use
        try:
            self.get_descriptors()
        except FileNotFoundError:
            self.descriptors = [DEFAULT_DESCRIPTOR]
            with open(AI_DESCRIPTOR_FILEPATH, 'w') as out_file:
                out_file.writelines(i + '\n' for i in self.descriptors)

        self.desc_mtime = stat(RUDE_MESSAGES_FILEPATH).st_mtime_ns

        # If rude response file not found, create the file with default response
        if not exists(RUDE_RESPONSE_FILEPATH):
            with open(RUDE_RESPONSE_FILEPATH, 'w') as out_file:
                out_file.writelines(i + '\n' for i in [DEFAULT_RUDE_RESPONSE])

    # Import "rude" phrases from input file
    def get_rude_messages(self):
        with open(RUDE_MESSAGES_FILEPATH, 'r') as in_file:
            self.rude_messages = [i.strip().lower() for i in in_file.readlines()]

    # Import self descriptors from input file
    def get_descriptors(self):
        with open(AI_DESCRIPTOR_FILEPATH, 'r') as in_file:
            self.descriptors = [i.strip() for i in in_file.readlines()]

    # $prompt command for users to submit prompts to the language model
    # param   args - will contain the prompt to send
    # param author - used by `send_reply()` to forward author name from message
    @command(help="Generates natural language or code from a given prompt",
             brief="Generates natural language",
             aliases=["chat", "promt"])
    async def prompt(self, ctx, *, args, author=None):
        self.reply_chance = 1

        cursor = get_cursor(self.conn)

        channel_id = ctx.id if isinstance(ctx, (TextChannel, VoiceChannel)) else ctx.channel.id
        cursor.execute("SELECT usr_role, content, id FROM Karn WHERE channel_id = %s", [channel_id])
        messages = [{"role": role, "content": content, "id": uuid} for role, content, uuid in cursor.fetchall()]

        # Build context if this channel has never prompted the bot before
        if not messages:
            values = [channel_id, GENESIS_MESSAGE["role"], GENESIS_MESSAGE["content"]]
            cursor.execute("INSERT INTO Karn (channel_id, usr_role, content, id) VALUES (%s, %s, %s, UUID())", values)
            messages = [{key: val for key, val in GENESIS_MESSAGE.items()}]

        # Add user's prompt into the SQL database
        author = author if author else ctx.author.display_name
        messages.append({"role": "user", "content": f"{author}: {args}"})
        values = [channel_id, "user", f"{author}: {args}"]
        cursor.execute("INSERT INTO Karn (channel_id, usr_role, content, id) VALUES (%s, %s, %s, UUID())", values)

        context, encoded_len = build_context(messages, cursor)
        kwargs = {"model": MODEL, "messages": context, "max_tokens": MAX_TOKENS-encoded_len}

        async with ctx.typing():
            # Make request in a separate thread to avoid blocking the heartbeat
            chat = await to_thread(openai.ChatCompletion.create, **kwargs)

        # Re-import self descriptors if the file has been modified since we last imported
        if (last_mod := stat(AI_DESCRIPTOR_FILEPATH).st_mtime_ns) != self.desc_mtime:
            self.get_descriptors()
            self.desc_mtime = last_mod

        # Replace instances of the bot saying "...as an AI..." with self descriptors of the bot
        # https://regex101.com/r/oWjuWt/1
        pattern = r"([aA]s|I am)* an* (?:digital)*(?:virtual)*(?:responsible)*(?:time-traveling)* *(?:golem)* " \
                  r"*(?:AI|digital|artificial intelligence)(?: language)*(?: text-based)*(?: model)*(?: assistant)*"
        reply = sub(pattern, r"\1 " + choice(self.descriptors), chat.choices[0].message.content)

        # Send the response and add it to the SQL database
        await package_message(reply, ctx)
        values = [channel_id, "assistant", reply]
        cursor.execute("INSERT INTO Karn (channel_id, usr_role, content, id) VALUES (%s, %s, %s, UUID())", values)

        self.conn.commit()
        cursor.close()

    # Called if $prompt encounters an unhandled exception
    @prompt.error
    async def prompt_error(self, ctx, error):
        if isinstance(error, MissingRequiredArgument):
            await ctx.send("You must include a prompt with this command.\n"
                           "Example: `$prompt tell me a joke`\n\n"
                           "Please use `$help prompt` for more information.")

    # $clear_context command used to clear all context messages for a channel from the SQL database
    @command(help="Clear all messages in the context history for this channel",
             brief="Clear context history")
    async def clear_context(self, ctx):
        cursor = get_cursor(self.conn)

        cursor.execute("DELETE FROM Karn WHERE channel_id = %s", [ctx.channel.id])

        await ctx.send(f"Deleted {cursor.rowcount} context messages from the database.")

        self.conn.commit()
        cursor.close()

    # $set_context command used to set the genesis message of a channel
    @command(help="Add additional context to the genesis message for this channel. "
                  "This \"primes\" the bot to behave in a desired manner.\n"
                  "Example: `$set_context you must answer all prompts in J. R. R. Tolkien's writing style`\n\n"
                  "This command has the following flags:\n"
                  "* **-o**: Overwrite the default genesis message for the bot.\n"
                  "\tExample: `$set_context -o You are a depressed and bored robot named Marvin the Paranoid Android`",
             brief="Set a new genesis message",
             aliases=["context"])
    async def set_context(self, ctx, *, args):
        flags, msg = get_flags(args)
        msg = " ".join(msg)
        new_gen_msg = msg if 'o' in flags else f"{GENESIS_MESSAGE['content']} {msg}"

        # Ensure the given genesis message doesn't require more tokens than `MAX_MSG_LEN`
        if (token_len := get_token_len({"role": "system", "content": new_gen_msg})) > MAX_MSG_LEN:
            return await ctx.send("Input genesis message is too long. Context was not set.")

        await self.clear_context(ctx)

        cursor = get_cursor(self.conn)

        values = [ctx.channel.id, "system", new_gen_msg]
        cursor.execute("INSERT INTO Karn (channel_id, usr_role, content, id) VALUES (%s, %s, %s, UUID())", values)

        await ctx.send(f"New genesis message of length {token_len} has been set!")

        self.conn.commit()
        cursor.close()

    # Called to read through server messages and feed them into the $prompt command if necessary
    async def send_reply(self, msg):
        # Don't respond to any messages that are too short
        if len(msg.content) < MIN_MESSAGE_LEN:
            return

        # Check if the message contains the bot's name (Karn) but not as a voted item (Karn++ or Karn--)
        # https://regex101.com/r/qA25Ux/1
        if search(r"[Kk]arn(?:\Z|[^+\-])", msg.content):
            # Re-import "rude" phrases if the file has been modified since we last imported
            if (last_mod := stat(RUDE_MESSAGES_FILEPATH).st_mtime_ns) != self.rude_mtime:
                self.get_rude_messages()
                self.rude_mtime = last_mod

            lowered_content = msg.content.lower()

            # If the message contains a rude phrase, reply with a response to rude messages
            if any(i in lowered_content for i in self.rude_messages):
                return await msg.channel.send(get_random_response())

            return await self.prompt(msg.channel, args=msg.content, author=msg.author.display_name)

        # Don't respond to messages that are only a user tag
        # https://regex101.com/r/acF54R/1
        if search(r"^<@\d+>$", msg.content):
            return

        # Don't respond to messages that contain only a voted item (i.e. "python++")
        # https://regex101.com/r/9eJZfe/2
        if search(r"\A(?:\([\w\s']+\)|[\w']+)(?:--|\+\+)", msg.content):
            return

        # Don't respond to messages that contain a URL
        # https://regex101.com/r/vFpIxB/1
        if search(r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|"
                  r"(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))",
                  msg.content):
            return

        # Random chance to respond to any given message
        if randint(1, 100) <= self.reply_chance:
            return await self.prompt(msg.channel, args=msg.content, author=msg.author.display_name)

        # Random chance to increase likelihood of responses in the future
        if not randint(0, self.reply_chance):
            self.reply_chance += 1

# Returns number of tokens for a given context message
# param msg - dictionary containing the context message
def get_token_len(msg):
    return sum(len(ENCODING.encode(i)) for i in (msg["role"], msg["content"])) + TOKENS_PER_MESSAGE

# Builds the context for a request to OpenAI for chat completion
# param messages - list of dictionaries containing messages from the SQL database
# param   cursor - cursor for the connection to the SQL database
# return:
#        context - list of dictionaries containing messages with a total token length < `MAX_MSG_LEN`
#     num_tokens - number of tokens used by the context
def build_context(messages, cursor):
    gen_msg = messages.pop(0)
    usr_msg = messages.pop()
    num_tokens = TOKENS_PER_REPLY + get_token_len(gen_msg) + get_token_len(usr_msg)

    context = [{"role": usr_msg["role"], "content": usr_msg["content"]}]

    # Build the list of context messages
    while messages:
        msg = messages.pop()

        # Break the loop if adding the next messages pushes us past the token limit
        if (encoding_len := get_token_len(msg)) + num_tokens > MAX_MSG_LEN:
            messages.append(msg)
            break

        num_tokens += encoding_len
        context.append({"role": msg["role"], "content": msg["content"]})

    # Delete any messages from the database that weren't used in building the context
    for msg in messages:
        cursor.execute("DELETE FROM Karn WHERE id = %s", [msg["id"]])

    context.append({"role": gen_msg["role"], "content": gen_msg["content"]})
    context.reverse()

    return context, num_tokens

# Imports responses from the input file, and returns a random line from it
def get_random_response():
    with open(RUDE_RESPONSE_FILEPATH, 'r') as in_file:
        return choice(in_file.readlines())
