from asyncio import sleep
from discord import ClientException
from discord.ext.tasks import loop
from discord.ext.commands import Cog, command, Context, MissingRequiredArgument
from openai import APIError, AsyncOpenAI
from os import getenv, stat
from os.path import exists
from random import choice, randint
from re import search, sub
from tiktoken import encoding_for_model

# Local dependencies
from utils import get_cursor, get_flags, package_message, send_tts_if_in_vc, text_to_speech


OPENAI_API_KEY = getenv("CHATGPT_TOKEN")
OPENAI_ORGANIZATION = getenv("CHATGPT_ORG")

# Constants (set by OpenAI and the encoding they use)
MODEL = "gpt-4-turbo-preview"
ENCODING = encoding_for_model(MODEL)
MAX_TOKENS = 4096       # Maximum number of tokens for context and response from OpenAI
TOKENS_PER_MESSAGE = 3  # Tokens required for each context message regardless of message length
TOKENS_PER_REPLY = 3    # Tokens required for the response from OpenAI regardless of response length

# Project specific constants
MAX_CONTEXT_HISTORY = 256
MIN_MESSAGE_LEN = 4                                     # Minimum message length bot will respond to
MAX_MSG_LEN = 3 * MAX_TOKENS // 4                       # Maximum length context to send to OpenAI
RUDE_MESSAGES_FILEPATH = "./files/rude.txt"             # File containing phrases the bot considers "rude"
RUDE_RESPONSE_FILEPATH = "./files/respond_rude.txt"     # File containing responses to "rude" messages
NICE_MESSAGES_FILEPATH = "./files/nice.txt"             # File containing phrases the bot considers "nice"
NICE_RESPONSE_FILEPATH = "./files/respond_nice.txt"     # File containing responses to "nice" messages
AI_DESCRIPTOR_FILEPATH = "./files/descriptor.txt"       # File containing alternate self-descriptors of the bot
DEFAULT_RUDE_MESSAGE = "shut up"                        # Phrase to consider "rude" if file not found
DEFAULT_RUDE_RESPONSE = "I will leave, my apologies."   # Response to "rude" messages if file not found
DEFAULT_NICE_MESSAGE = "good job"                       # Phrase to consider "nice" if file not found
DEFAULT_NICE_RESPONSE = "Thanks, I aim to please!"      # Response to "nice" messages if file not found
DEFAULT_DESCRIPTOR = "your humble assistant"            # Self-descriptor to use if file not found

# The default context message used to "prime" the language model in preparation for it to act as our AI assistant
GENESIS_MESSAGE = {"role": "system",
                   "content": "You are a time-travelling golem named Karn. "
                              "You are currently acting as an AI assistant for a Discord server. "
                              "Message content from Discord will follow the format: \"Name: Message\" "
                              "where \"Name\" is the name of the user who sent the message, "
                              "and \"Message\" is the message that was sent. "
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
        
        self.client = AsyncOpenAI(api_key=OPENAI_API_KEY, organization=OPENAI_ORGANIZATION)

        # Import "rude" phrases. If file not found, use default and create a file for future use
        try:
            self.get_rude_messages()
        except FileNotFoundError:
            self.rude_messages = [DEFAULT_RUDE_MESSAGE]
            with open(RUDE_MESSAGES_FILEPATH, 'w') as out_file:
                out_file.writelines(i + '\n' for i in self.rude_messages)

        self.rude_mtime = stat(RUDE_MESSAGES_FILEPATH).st_mtime_ns

        # Import "nice" phrases. If file not found, use default and create a file for future use
        try:
            self.get_nice_messages()
        except FileNotFoundError:
            self.nice_messages = [DEFAULT_NICE_MESSAGE]
            with open(NICE_MESSAGES_FILEPATH, 'w') as out_file:
                out_file.writelines(i + '\n' for i in self.nice_messages)

        self.nice_mtime = stat(NICE_MESSAGES_FILEPATH).st_mtime_ns
        
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

        # If nice response file not found, create the file with default response
        if not exists(NICE_RESPONSE_FILEPATH):
            with open(NICE_RESPONSE_FILEPATH, 'w') as out_file:
                out_file.writelines(i + '\n' for i in [DEFAULT_NICE_RESPONSE])

    # Import "rude" phrases from input file
    def get_rude_messages(self):
        with open(RUDE_MESSAGES_FILEPATH, 'r') as in_file:
            self.rude_messages = [i.strip().lower() for i in in_file.readlines()]

    # Import "nice" phrases from input file
    def get_nice_messages(self):
        with open(NICE_MESSAGES_FILEPATH, 'r') as in_file:
            self.nice_messages = [i.strip().lower() for i in in_file.readlines()]

    # Import self descriptors from input file
    def get_descriptors(self):
        with open(AI_DESCRIPTOR_FILEPATH, 'r') as in_file:
            self.descriptors = [i.strip() for i in in_file.readlines()]

    @command(help="Adds the bot to your current voice channel",
             brief="Add bot to your voice channel")
    async def join(self, ctx):
        try:
            await ctx.author.voice.channel.connect()
            
            if not self.check_empty_channel.is_running():
                self.check_empty_channel.start()
        except AttributeError:
            await ctx.send("You must currently be in a voice channel to use this command.")
        except ClientException:
            await ctx.send("I'm already in your channel!")

    @command(help="Remove the bot from a voice channel",
             brief="Remove bot from a voice channel")
    async def leave(self, ctx):
        try:
            await ctx.message.guild.voice_client.disconnect()
        except AttributeError:
            await ctx.send("I am not currently in any voice channels. Try using `$join` first!")

    @loop(seconds=20)
    async def check_empty_channel(self):
        if not self.bot.voice_clients:
            self.check_empty_channel.stop()
            return

        for client in self.bot.voice_clients:
            if len(client.channel.members) < 2:
                await client.disconnect()

    @command(help="Command the bot to say something in your voice channel",
             brief="Say something in a voice channel")
    async def say(self, ctx, *, args):
        if not ctx.author.voice:
            await ctx.send("You must currently be in a voice channel to use this command.")
            return

        temp_join = False

        if not ctx.message.guild.voice_client:
            await self.join(ctx)
            temp_join = True

        await text_to_speech(args, ctx.message.guild.voice_client)

        if temp_join:
            while ctx.message.guild.voice_client.is_playing():
                await sleep(1)

            await self.leave(ctx)

    # $prompt command for users to submit prompts to the language model
    # param   args - will contain the prompt to send
    # param author - used by `send_reply()` to forward author name from message
    @command(help="Generates natural language or code from a given prompt",
             brief="Generates natural language",
             aliases=["chat", "promt"])
    async def prompt(self, ctx, **kwargs):
        self.reply_chance = 1

        cursor = get_cursor(self.conn)

        if isinstance(ctx, Context):
            channel = ctx.channel
            channel_id = ctx.channel.id
            author = ctx.message.author
        else:
            channel = ctx
            channel_id = ctx.id
            author = kwargs.get("author")

        cursor.execute("SELECT content FROM Genesis WHERE channel_id = %s", [channel_id])

        sys_msg = [{"role": "system", "content": content[0]} for content in cursor.fetchall()]
        if not sys_msg:
            sys_msg = [{key: val for key, val in GENESIS_MESSAGE.items()}]

        cursor.close()

        context, encoded_len = await self.build_context(channel, sys_msg)

        openai_kwargs = {"model": MODEL, "messages": context, "max_tokens": MAX_TOKENS-encoded_len}

        # Make the bot appear to be typing while waiting for the response from OpenAI
        async with ctx.typing():
            try:
                chat = await self.client.chat.completions.create(**openai_kwargs)
            except APIError as e:
                if not kwargs.get("prompted", False):
                    await ctx.send("Sorry I am unable to assist currently. Please try again later.")
                print(f"\nOpenAI request failed with error:\n{e}\n")
                return

        # Re-import self descriptors if the file has been modified since we last imported
        if (last_mod := stat(AI_DESCRIPTOR_FILEPATH).st_mtime_ns) != self.desc_mtime:
            self.get_descriptors()
            self.desc_mtime = last_mod

        # Replace instances of the bot saying "...as an AI..." with self descriptors of the bot
        # https://regex101.com/r/oWjuWt/2
        reply = sub(r"([aA]s|I am)* an* (?:digital)*(?:virtual)*(?:responsible)*(?:time-traveling)* "
                    r"*(?:golem)* *(?:language model)* *(?:AI|digital|artificial intelligence)"
                    r"(?: language)*(?: text-based)*(?: model)*(?: assistant)*",
                    r"\1 " + choice(self.descriptors),
                    chat.choices[0].message.content)
        
        # Ensure bot is not prefixing the reply with a name
        # https://regex101.com/r/4vSz5X/1
        reply = sub(r"\A\w+:\s", '', reply)

        await package_message(reply, ctx)
       
        await send_tts_if_in_vc(self.bot, author, reply)

    # Called if $prompt encounters an unhandled exception
    @prompt.error
    async def prompt_error(self, ctx, error):
        if isinstance(error, MissingRequiredArgument):
            await ctx.send("You must include a prompt with this command.\n"
                           "Example: `$prompt tell me a joke`\n\n"
                           "Please use `$help prompt` for more information.")

    # Builds the context for a request to OpenAI for chat completion
    # param channel -
    # param sys_msg -
    # return:
    #       context - list of dictionaries containing messages with a total token length < `MAX_MSG_LEN`
    #    num_tokens - number of tokens used by the context
    async def build_context(self, channel, sys_msg):
        num_tokens = TOKENS_PER_REPLY + sum(get_token_len(msg) for msg in sys_msg)
        context = []

        # Build the list of context messages
        async for message in channel.history(limit=MAX_CONTEXT_HISTORY):
            content = sub(r"\A\$prompt ", '', message.clean_content)

            if message.author == self.bot.user:
                msg = {"role": "assistant", "content": content}
            else:
                msg = {"role": "user", "content": f"{message.author.display_name}: {content}"}

            # Break the loop if adding the next messages pushes us past the token limit
            if (encoding_len := get_token_len(msg)) + num_tokens > MAX_MSG_LEN:
                break

            num_tokens += encoding_len
            context.append(msg)

        sys_msg.reverse()
        context.extend(sys_msg)
        context.reverse()

        return context, num_tokens

    # $set_context command used to set the genesis message of a channel
    @command(help="Set the genesis system context message for this channel. "
                  "This \"primes\" the bot to behave in a desired manner.\n"
                  "Example: `$set_context you must answer all prompts in J. R. R. Tolkien's writing style`\n\n"
                  "This command has the following flags:\n"
                  "* **-o**: Overwrite the default genesis message for the bot.\n"
                  "\tExample: `$set_context -o You are a depressed and bored robot named Marvin the Paranoid Android`",
             brief="Set a new genesis message",
             aliases=["context"])
    async def set_context(self, ctx, *, args=''):
        flags, msg = get_flags(args)
        msg = ' '.join(msg)
        new_gen_msg = msg if 'o' in flags else f"{GENESIS_MESSAGE['content']} {msg}"

        # Ensure the given genesis message doesn't require more tokens than `MAX_MSG_LEN`
        if (token_len := get_token_len({"role": "system", "content": new_gen_msg})) > MAX_MSG_LEN:
            return await ctx.send("Input genesis message is too long. Context was not set.")

        cursor = get_cursor(self.conn)

        cursor.execute("DELETE FROM Genesis WHERE channel_id = %s", [ctx.channel.id])
        cursor.execute("INSERT INTO Genesis (channel_id, content) VALUES (%s, %s)", [ctx.channel.id, new_gen_msg])

        await ctx.send(f"New genesis message of length {token_len} has been set!")

        self.conn.commit()
        cursor.close()

    @command(help="Add additional system context messages for this channel. "
                  "This can help get the bot to behave in a more specific manner."
                  "Example: `$add_context You always talk about baseball, even if it doesn't fit the conversation.`",
             brief="Add additional system context")
    async def add_context(self, ctx, *, args):
        if (token_len := get_token_len({"role": "system", "content": args})) > MAX_MSG_LEN:
            return await ctx.send("Input genesis message is too long. Context was not set.")

        cursor = get_cursor(self.conn)

        cursor.execute("INSERT INTO Genesis (channel_id, content) VALUES (%s, %s)", [ctx.channel.id, args])

        await ctx.send(f"New system context message of length {token_len} has been added!")

        self.conn.commit()
        cursor.close()

    @command(help="View the system context message(s) for this channel.",
             brief="View system context messages")
    async def view_context(self, ctx):
        cursor = get_cursor(self.conn)

        cursor.execute("SELECT content FROM Genesis WHERE channel_id = %s", [ctx.channel.id])

        if not (result := cursor.fetchall()):
            await ctx.send("No system context messages set for this channel. Try using `add_context` first!")
        else:
            response = "\n* ".join(i[0] for i in result)
            await ctx.send(f"System context messages for this channel:\n* {response}")

        cursor.close()

    @command(help="Toggle whether the bot should respond to your messages without being prompted. "
                  "The bot will still respond if your message contain its name, or if you use the `$prompt` command."
                  "This command has the following flags:\n"
                  "* **-c**: Toggle whether the bot should respond to messages in the channel without being prompted.",
             brief="Toggle unprompted responses")
    async def ignore(self, ctx, *, args=''):
        flags, args = get_flags(args)

        if 'c' in flags:
            return await self.ignore_channel(ctx)

        cursor = get_cursor(self.conn)

        respond = False

        cursor.execute("SELECT respond FROM Users WHERE user_id = %s", [ctx.author.id])

        if not (result := cursor.fetchall()):
            cursor.execute("INSERT INTO Users (user_id, respond) VALUES (%s, %s)", [ctx.author.id, 0])
        elif result[0][0]:
            cursor.execute("UPDATE Users SET respond = 0 WHERE user_id = %s", [ctx.author.id])
        else:
            cursor.execute("UPDATE Users SET respond = 1 WHERE user_id = %s", [ctx.author.id])
            respond = True

        self.conn.commit()
        cursor.close()

        if respond:
            await ctx.send("I will now occasionally respond your messages without being prompted.")
        else:
            await ctx.send("I will no longer respond to your messages without being prompted.")

    async def ignore_channel(self, ctx):
        cursor = get_cursor(self.conn)

        respond = False

        cursor.execute("SELECT respond FROM Channels WHERE channel_id = %s", [ctx.channel.id])

        if not (result := cursor.fetchall()):
            cursor.execute("INSERT INTO Channels (channel_id, respond) VALUES (%s, %s)", [ctx.channel.id, 0])
        elif result[0][0]:
            cursor.execute("UPDATE Channels SET respond = 0 WHERE channel_id = %s", [ctx.channel.id])
        else:
            cursor.execute("UPDATE Channels SET respond = 1 WHERE channel_id = %s", [ctx.channel.id])
            respond = True

        self.conn.commit()
        cursor.close()

        if respond:
            await ctx.send("I will now occasionally respond to messages in this channel without being prompted.")
        else:
            await ctx.send("I will no longer respond to messages in this channel without being prompted.")

    # Called to read through server messages and feed them into the $prompt command if necessary
    async def send_reply(self, msg):
        # Don't respond to any messages that are too short
        if len(msg.clean_content) < MIN_MESSAGE_LEN:
            return

        # Check if the message contains the bot's name (Karn) but not as a voted item (Karn++ or Karn--)
        # https://regex101.com/r/qA25Ux/1
        if search(r"[Kk]arn(?:\Z|[^+\-])", msg.clean_content):
            # Re-import "rude" phrases if the file has been modified since we last imported
            if (last_mod := stat(RUDE_MESSAGES_FILEPATH).st_mtime_ns) != self.rude_mtime:
                self.get_rude_messages()
                self.rude_mtime = last_mod

            # If the message contains a rude phrase, reply with a response to rude messages
            if any(i in msg.clean_content.lower() for i in self.rude_messages):
                reply = get_random_response()
                await msg.channel.send(reply)
                await send_tts_if_in_vc(self.bot, msg.author, reply)
                return

            # Re-import "nice" phrases if the file has been modified since we last imported
            if (last_mod := stat(NICE_MESSAGES_FILEPATH).st_mtime_ns) != self.nice_mtime:
                self.get_nice_messages()
                self.nice_mtime = last_mod

            # If the message contains a nice phrase, reply with a response to nice messages
            if any(i in msg.clean_content.lower() for i in self.nice_messages):
                reply = get_random_response(False)
                await msg.channel.send(reply)
                await send_tts_if_in_vc(self.bot, msg.author, reply)
                return

            return await self.prompt(msg.channel, author=msg.author)

        # Don't respond to messages that are only one word
        if len(msg.clean_content.split()) <= 1:
            return

        cursor = get_cursor(self.conn)

        # Ignore users that don't want unprompted responses
        cursor.execute("SELECT respond FROM Users WHERE user_id = %s", [msg.author.id])
        if (result := cursor.fetchall()) and not result[0][0]:
            cursor.close()
            return

        # Ignore channels that don't want unprompted responses
        cursor.execute("SELECT respond FROM Channels WHERE channel_id = %s", [msg.channel.id])
        if (result := cursor.fetchall()) and not result[0][0]:
            cursor.close()
            return

        cursor.close()

        # Don't respond to messages that only contain tags
        # https://regex101.com/r/acF54R/3
        if all(search(r"^<@&*\d+>$|@everyone|@here", word) for word in msg.content.split()):
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
            return await self.prompt(msg.channel, author=msg.author, prompted=False)

        # Random chance to increase likelihood of responses in the future
        if not randint(0, self.reply_chance):
            self.reply_chance += 1

# Returns number of tokens for a given context message
# param msg - dictionary containing the context message
def get_token_len(msg):
    return sum(len(ENCODING.encode(i)) for i in (msg["role"], msg["content"])) + TOKENS_PER_MESSAGE

# Imports responses from the input file, and returns a random line from it
def get_random_response(rude=True):
    filepath = RUDE_RESPONSE_FILEPATH if rude else NICE_RESPONSE_FILEPATH

    with open(filepath, 'r') as in_file:
        return choice(in_file.readlines())
