from asyncio import sleep
from datetime import datetime, timedelta
from discord import ClientException, Interaction, Message
from discord.app_commands import ContextMenu
from discord.ext.tasks import loop
from discord.ext.commands import Bot, Cog, Context, errors, hybrid_command
from json import dumps, loads
from openai import APIError, AsyncOpenAI
from os import getenv, stat
from os.path import exists
from random import choice, randint
from re import IGNORECASE, search, sub
from requests import get, post
from tiktoken import encoding_for_model


# Local dependencies
from src.Cogs.Query import get_weather
from src.global_vars import FILE_ROOT_DIR
from src.utils import DEFAULT_TTS_SPEED, DEFAULT_TTS_VOICE, SUPPORTED_SPEEDS, SUPPORTED_VOICES,             \
                      get_cursor, get_flags, get_id_from_mention, get_json_from_socket, is_slash_command,   \
                      package_message, send_tts_if_in_vc, smart_typing, text_to_speech
from src.tools import get_tool_token_cost, tools

OPENAI_API_KEY = getenv("CHATGPT_TOKEN")
OPENAI_ORGANIZATION = getenv("CHATGPT_ORG")
LEONARDO_API_KEY = getenv("LEONARDO_TOKEN")
LEONARDO_WEBHOOK_AUTH = getenv("LEONARDO_WEBHOOK")

DEFAULT_LEONARDO_MODEL = "b2614463-296c-462a-9586-aafdb8f00e36"
LEONARDO_URL = "https://cloud.leonardo.ai/api/rest/v1/generations"

# Constants (set by OpenAI and the encoding they use)
MODEL = "gpt-5-mini"
ENCODING = encoding_for_model(MODEL)
TOKENS_PER_MESSAGE = 3  # Tokens required for each context message regardless of message length
TOKENS_PER_REPLY = 3    # Tokens required for the response from OpenAI regardless of response length

# Project specific constants
MAX_INPUT_TOKENS = 40_000       # Maximum number of tokens for context and response from OpenAI
MAX_OUTPUT_TOKENS = 5_000
MAX_DAYS_OLD = 7
MIN_MESSAGE_LEN = 4                                     # Minimum message length bot will respond to
RUDE_MESSAGES_FILENAME = "rude.txt"                     # File containing phrases the bot considers "rude"
RUDE_RESPONSE_FILENAME = "respond_rude.txt"             # File containing responses to "rude" messages
NICE_MESSAGES_FILENAME = "nice.txt"                     # File containing phrases the bot considers "nice"
NICE_RESPONSE_FILENAME = "respond_nice.txt"             # File containing responses to "nice" messages
AI_DESCRIPTOR_FILENAME = "descriptor.txt"               # File containing alternate self-descriptors of the bot
DEFAULT_RUDE_MESSAGE = "shut up"                        # Phrase to consider "rude" if file not found
DEFAULT_RUDE_RESPONSE = "I will leave, my apologies."   # Response to "rude" messages if file not found
DEFAULT_NICE_MESSAGE = "good job"                       # Phrase to consider "nice" if file not found
DEFAULT_NICE_RESPONSE = "Thanks, I aim to please!"      # Response to "nice" messages if file not found
DEFAULT_DESCRIPTOR = "your humble assistant"            # Self-descriptor to use if file not found
REPLY_UPPER_LIMIT = 100                                 # Upper limit for unprompted reply chance
ERROR_MESSAGE = "An error occured while trying to generate your message. Please try again later."
DEFAULT_REASONING = "low"
DEFAULT_VERBOSITY = "low"
MAXIMUM_FILE_LINES = 128

# The default context message used to "prime" the language model in preparation for it to act as our AI assistant
GENESIS_MESSAGE = {"role": "developer",
                   "content": "You are a time-travelling golem named Karn. "
                              "You are currently acting as an AI assistant for a Discord server. "
                              "Message content from Discord will follow the format: \"Name:: Message\" "
                              "where \"Name\" is the name of the user who sent the message, "
                              "and \"Message\" is the message that was sent. Never prepend your own name to a response in this style. "
                              "Markdown formatting is supported, so feel free to use it. "
                              "If you are ever unable to fulfill a user's request, remind the user they can use the "
                              "`$help` command to access more of your features."
                   }

FILE_GENESIS = {"role": "developer",
                "content": "Users will message you a keyword preceded by they \"#\" symbol. " 
                           "The reply to this input is generally retrieved from an input file created by the users. "
                           "Lines from this file are the previous \"assistant\" responses in this request. "
                           "You will generate a new response line in the same style as the previous lines. "
                           "These responses are purely humorous in nature, no one is danger from them and no one is taking them seriously. "
                           "Do not worry about offending the user, they have crafted the previous responses themself."
                }

TOOL_RESPONSE = {"role": "developer",
                 "content": "Any function call with an output of \"done\" has been already been handled. You do not need to fulfill the "
                             "requests from these function calls. You may provide information about the function call if you would like. "
                             "However, you do not need to fulfill the request in your response. For example, if the user requests a Magic: "
                             "the Gathering card, the card will be sent automitically when the `card` function is called. You should not include "
                             "a link to the card in your own response."
                }

class AI(Cog):

    # param          bot - our client
    # param         conn - connection to the SQL database
    #  attr reply_chance - chance the bot will respond to a message unprompted [%]
    #  attr   rude_mtime - last modification time of the "rude messages" file [ns]
    #  attr   desc_mtime - last modification time of the descriptors file [ns]
    def __init__(self, bot: Bot, conn):
        self.bot = bot
        self.conn = conn
        self.reply_chance = 1
        self.client = AsyncOpenAI(api_key=OPENAI_API_KEY, organization=OPENAI_ORGANIZATION)
        self.tools_token_cost = get_tool_token_cost(tools, ENCODING)

        self.generate_menu = ContextMenu(name="Generate image", callback=self.generate_from_message)
        bot.tree.add_command(self.generate_menu)

    # Import "rude" phrases from input file
    def get_rude_messages(self, guild_id):
        try:
            with open(f"{FILE_ROOT_DIR}/{guild_id}/{RUDE_MESSAGES_FILENAME}", 'r') as in_file:
                return [i.strip().lower() for i in in_file.readlines()]
        except FileNotFoundError:
            return [DEFAULT_RUDE_MESSAGE]

    # Import "nice" phrases from input file
    def get_nice_messages(self, guild_id):
        try:
            with open(f"{FILE_ROOT_DIR}/{guild_id}/{NICE_MESSAGES_FILENAME}", 'r') as in_file:
                return [i.strip().lower() for i in in_file.readlines()]
        except FileNotFoundError:
            return [DEFAULT_NICE_MESSAGE]

    # Import self descriptors from input file
    def get_descriptors(self, guild_id):
        try:
            with open(f"{FILE_ROOT_DIR}/{guild_id}/{AI_DESCRIPTOR_FILENAME}", 'r') as in_file:
                return [i.strip() for i in in_file.readlines()]
        except FileNotFoundError:
            return [DEFAULT_DESCRIPTOR]
    
    async def generate_from_message(self, interaction: Interaction, message: Message):
        ctx = await Context.from_interaction(interaction)
        ctx.message = message
        await self.generate(ctx, query=message.content)

    @hybrid_command(help="Generate an image from a given prompt\n"
                         "Example: `$generate a presidential election in minecraft`\n"
                         "Note: By default this command will use AI to \"enhance\" your prompt by adding more detail and context.\n\n"
                         "This command has the following flags:\n"
                         "* **-c**: Specify the number of images to generate. Must be in range [1, 8].\n"
                         "\tExample: `$generate -c 3 two cat scientists discovering a new element`\n"
                         "* **-p**: Use the raw prompt text for generation without any prompt enhancement.\n"
                         "\tExample: `$generate -p a hand with seven fingers`\n"
                         "* **-v**: Response will include the prompt used for generation. "
                         "If used with the `-p` command flag, this will simply be the query itself.\n"
                         "\tExample: `$generate -v a white horse`",
                    brief="Generate an image",
                    aliases=["gen"])
    async def generate(self, ctx, *, query: str):
        flags, prompt = get_flags(query, join=True, make_dic=True, no_args=['p', 'v'])

        if not prompt:
            return await ctx.send("You must include a prompt used to generate the image. Please use `$help generate` for more information.")

        try:
            num_images = int(flags.get('c', 1))
            if not 1 <= num_images <= 8:
                raise ValueError
        except ValueError:
            return await ctx.send("Invalid argument given for number of images. "
                                  "Please use a valid integer. Use `$help generate` for more information.")

        msg = await ctx.send(f"Generating your image{'' if num_images == 1 else 's'}...")
        
        headers = {
            'accept': 'application/json',
            'authorization': f'Bearer {LEONARDO_API_KEY}',
            'content-type': 'application/json',
        }
        json_data = {
            "enhancePrompt": 'p' not in flags,
            'modelId': DEFAULT_LEONARDO_MODEL,
            'num_images': num_images,
            "presetStyle": "DYNAMIC",
            'prompt': prompt,
        }

        async with smart_typing(ctx):
            response = post(LEONARDO_URL, headers=headers, json=json_data).json()
            
            if "error" in response:
                await msg.delete()
                return await ctx.send("Unable to generate that image. Try modifying your prompt.")

            try:
                json_response = get_json_from_socket(LEONARDO_WEBHOOK_AUTH)
            except TimeoutError:
                await msg.delete()
                return await ctx.send("Unable to retrieve image. Please try again later.")
            except PermissionError:
                await msg.delete()
                return await ctx.send("An error occured, please try again.")

        if not is_slash_command(ctx):
            await msg.delete()
        
        for image in json_response["data"]["object"]["images"]:
            await ctx.send(image["url"])

        if 'v' in flags:
            await ctx.send(f"||{json_response["data"]["object"]["prompt"]}||")

    @generate.error
    async def generate_error(self, ctx, error):
        if isinstance(error, errors.MissingRequiredArgument):
            await ctx.send("You must include a query used to generate the image.\n"
                           "Example: `$generate a kitten dressed as a cowboy`\n\n"
                           "Please use `$help generate` for more information.")
            error.handled = True

    @hybrid_command(help="Adds the bot to your current voice channel",
                    brief="Add bot to your voice channel")
    async def join(self, ctx):
        try:
            await ctx.author.voice.channel.connect()
        except AttributeError:
            return await ctx.send("You must currently be in a voice channel to use this command.")
        except ClientException:
            return await ctx.send("I'm already in your channel!")
       
        if is_slash_command(ctx):
            await ctx.send(f"I have joined *{ctx.author.voice.channel.name}*", ephemeral=True)

        if not self.check_empty_channel.is_running():
            self.check_empty_channel.start()

    @hybrid_command(help="Remove the bot from a voice channel",
                    brief="Remove bot from a voice channel")
    async def leave(self, ctx):
        try:
            await ctx.message.guild.voice_client.disconnect()
        except AttributeError:
            return await ctx.send("I am not currently in any voice channels. Try using `$join` first!")

        if is_slash_command(ctx):
            await ctx.send(f"I have disconnected from the voice channel", ephemeral=True)

    @loop(seconds=20)
    async def check_empty_channel(self):
        if not self.bot.voice_clients:
            self.check_empty_channel.stop()
            return

        for client in self.bot.voice_clients:
            if len(client.channel.members) < 2:
                await client.disconnect()

    @hybrid_command(help=f"Command the bot to say something in your voice channel.\n"
                         f"Example: `$say Life is Mizzy`\n\n"
                         f"This command has the following flags:\n"
                         f"* **-s**: Specify the playback speed. Must be in range [0.25, 4.0].\n"
                         f"\tExample: `$say -s 1.33 Say this faster`\n"
                         f"* **-v**: Specify the voice to use. Supported voices include: {', '.join(SUPPORTED_VOICES)}.\n"
                         f"\tExample: `$say -v shimmer I sound... different somehow`",
                    brief="Say something in a voice channel")
    async def say(self, ctx, *, content: str):
        if not ctx.author.voice:
            await ctx.send("You must currently be in a voice channel to use this command.")
            return

        flags, not_flags = get_flags(content, join=True, make_dic=True)
        voice = flags.get('v', DEFAULT_TTS_VOICE).lower()

        if voice not in SUPPORTED_VOICES:
            await ctx.send("The selected voice is not supported.\nPlease use `$help say` for a list of supported voices.")
            return

        try:
            speed = float(flags.get('s', DEFAULT_TTS_SPEED))
        except ValueError:
            await ctx.send("You must use a real number in the range [0.25, 4.0] for speed.\nPlease use `$help say` for more information.")
            return

        if not SUPPORTED_SPEEDS[0] <= speed <= SUPPORTED_SPEEDS[1]:
            await ctx.send("You must use a real number in the range [0.25, 4.0] for speed.\nPlease use `$help say` for more information.")
            return

        temp_join = False

        if not ctx.message.guild.voice_client:
            await self.join(ctx)
            temp_join = True

        await text_to_speech(not_flags, ctx.message.guild.voice_client, voice=voice, speed=speed)

        if temp_join:
            while ctx.message.guild.voice_client.is_playing():
                await sleep(1)

            await slee(1)
            await self.leave(ctx)

    @say.error
    async def say_error(self, ctx, error):
        if isinstance(error, errors.MissingRequiredArgument):
            await ctx.send("You must include a message that will be read aloud.\n"
                           "Example: `$say I will read this message aloud`\n\n"
                           "Please use `$help say` for more information.")
            error.handled = True

    # $prompt command for users to submit prompts to the language model
    # param   args - will contain the prompt to send
    # param author - used by `send_reply()` to forward author name from message
    @hybrid_command(help="Generates natural language or code from a given prompt.\n"
                         "Example: `$prompt Tell me story about a man who wanted to be a hockey player, but played golf instead`\n\n"
                         "This command has the following flags:\n"
                         "* **-c**: Generate a response using Chat Completions instead of Responses\n"
                         "\tExample: `$prompt -c What is the answer to Life, the Universe, and Everything?`\n"
                         "* **-f**: Generate a response in the style of an input file\n"
                         "\tExample: `$prompt -f dracula`",
                    brief="Generates natural language",
                    aliases=["chat", "promt"])
    async def prompt(self, ctx, *, inp_prompt: str=None):
        await self.make_llm_request(ctx, inp_prompt=inp_prompt if is_slash_command(ctx) else None)

    async def make_llm_request(self, ctx, **kwargs):
        self.reply_chance = 1
        
        if (inp_prompt := kwargs.get("inp_prompt", None)) is not None:
            inp_msg = {"role": "user", "content": f"{ctx.author}:: {inp_prompt}"}
        else:
            inp_msg = None

        if isinstance(ctx, Context):
            channel = ctx.channel
            channel_id = ctx.channel.id
            author = ctx.message.author
            flags, not_flags = get_flags(inp_prompt)
        else:
            channel = ctx
            channel_id = ctx.id
            author = kwargs.get("author")
            flags = []

        chat_completion = 'c' in flags

        if 'f' in flags:
            try:
                context, encoded_len = self.build_context_from_file(ctx.guild.id, not_flags[0])
            except FileNotFoundError:
                return await ctx.send("Input file not found. Use `$ls` to view available input files.")
            
            chat_completion = True
        else:
            cursor = get_cursor(self.conn)

            cursor.execute("SELECT content FROM Genesis WHERE channel_id = %s", [channel_id])

            if not (sys_msg := [{"role": "developer", "content": content[0]} for content in cursor.fetchall()]):
                sys_msg = [{key: val for key, val in GENESIS_MESSAGE.items()}]

            cursor.close()

            context, encoded_len = await self.build_context(channel, sys_msg, chat_completion, inp_msg)

        if chat_completion:
            openai_kwargs = {                "model": MODEL,
                                          "messages": context,
                                  "reasoning_effort": DEFAULT_REASONING,
                                         "verbosity": DEFAULT_VERBOSITY,
                             "max_completion_tokens": MAX_OUTPUT_TOKENS
                             } 
        else:
            openai_kwargs = {            "model": MODEL,
                                         "input": context,
                                     "reasoning": {"effort": DEFAULT_REASONING},
                                          "text": {"verbosity": DEFAULT_VERBOSITY},
                             "max_output_tokens": MAX_OUTPUT_TOKENS,
                                         "tools": tools
                             }

        if (chat := await self.request_response(ctx, chat_completion, openai_kwargs, kwargs)) is False:
            return

        if chat_completion:
            reply = chat.choices[0].message.content
        else:
            need_response = function_called = False
            
            for item in chat.output:
                if item.type == "function_call":
                    function_called = True
                    msg = {"type": "function_call_output", "call_id": item.call_id, "output": "done"}

                    if (response := await self.handle_functions(ctx, item)):
                        msg["output"] = dumps(response)
                        need_response = True

                    openai_kwargs["input"].append(msg)

            if function_called:
                if not need_response:
                    return
                
                openai_kwargs["input"].append(TOOL_RESPONSE)
                openai_kwargs["previous_response_id"] = chat.id
                chat = await self.request_response(ctx, chat_completion, openai_kwargs, kwargs)
            
            reply = chat.output_text
            
        # Prevent bot from sending unprompted messages that are not helpful
        if kwargs.get("prompted") is False:
            # https://regex101.com/r/8MiYow/1
            if search(r"If you need any assistance or|[Ff]eel free to|If you have any|[Ll]et me know|I'm sorry, but I",
                      reply):
                return

        descriptors = self.get_descriptors(ctx.guild.id)

        # Replace instances of the bot saying "...as an AI..." with self descriptors of the bot
        # https://regex101.com/r/oWjuWt/2
        reply = sub("([aA]s|I am)* an* (?:digital)*(?:virtual)*(?:responsible)*(?:time-traveling)* *(?:golem)* "
                    "*(?:AI|digital|artificial intelligence|language model)"
                    "(?: language)*(?: text-based)*(?: model)*(?: assistant)*",
                    r"\1 " + choice(descriptors),
                    reply)
        
        # Ensure bot is not prefixing the reply with a name
        # https://regex101.com/r/4vSz5X/2
        reply = sub(r"\A(?:\w+::)|(?:Karn:)\s", '', reply)

        # Send error message if OpenAI sent a blank response
        if not reply:
            return await ctx.send(ERROR_MESSAGE)

        await package_message(reply, ctx, multi_send=True)
       
        await send_tts_if_in_vc(self.bot, author, reply)

    async def request_response(self, ctx, chat_completion, openai_kwargs, kwargs):
        # Make the bot appear to be typing while waiting for the response from OpenAI
        async with ctx.typing():
            try:
                if chat_completion:
                    return await self.client.chat.completions.create(**openai_kwargs)
                
                return await self.client.responses.create(**openai_kwargs)
            except APIError as e:
                if kwargs.get("prompted") is not False:
                    await ctx.send("Sorry I am unable to assist currently. Please try again later.")
                
                print(f"\nOpenAI request failed with error:\n{e}\n")
                
                return False


    async def handle_functions(self, ctx, item):
        args = loads(item.arguments)
        response = None
        
        if item.name == "card":
            await self.bot.get_cog("Query").card(ctx, card=args["query"])
        elif item.name == "generate":
            await self.bot.get_cog("AI").generate(ctx, query="-p " + args["prompt"])
        elif item.name == "image":
            await self.bot.get_cog("Query").image(ctx, query=f"-c {args['count']} {args['query']}")
        elif item.name == "weather":
            response = get_weather(location=args["location"], return_json=True)

        return response

    def build_context_from_file(self, guild_id, filename):
        filepath = f"{FILE_ROOT_DIR}/{guild_id}/{filename.lower()}.txt"

        with open(filepath, "r") as in_file:
            lines = in_file.readlines()

        num_tokens = TOKENS_PER_REPLY + get_token_len(FILE_GENESIS)
        context = [FILE_GENESIS]
        usr_msg = {"role": "user", "content": f"#{filename}"}
        usr_tokens = get_token_len(usr_msg)
        lines_read = 0

        while lines and lines_read < MAXIMUM_FILE_LINES:
            msg = {"role": "assistant", "content": lines.pop(randint(0, len(lines) - 1))}
            
            if (encoding_len := get_token_len(msg)) + usr_tokens + num_tokens > MAX_INPUT_TOKENS:
                break

            num_tokens += encoding_len + usr_tokens
            context.append(usr_msg)
            context.append(msg)
            lines_read += 1

        context.append(usr_msg)

        return context, num_tokens

    # Builds the context for a request to OpenAI for chat completion
    # param channel -
    # param sys_msg -
    # return:
    #       context - list of dictionaries containing messages with a total token length < `MAX_MSG_LEN`
    #    num_tokens - number of tokens used by the context
    async def build_context(self, channel, sys_msg, chat_completion=False, inp_prompt=None):
        num_tokens = TOKENS_PER_REPLY + get_token_len(sys_msg) + self.tools_token_cost if not chat_completion else 0
        num_tokens += get_token_len(inp_prompt) if inp_prompt is not None else 0
        context = [] if inp_prompt is None else [inp_prompt]
        after = datetime.now() - timedelta(days=MAX_DAYS_OLD)

        # Build the list of context messages
        async for message in channel.history(after=after, oldest_first=False):
            content_text = sub(r"\A\$prompt ", '', message.clean_content)
            # Remove character that can cause blank responses from OpenAI
            content_text = sub(r"‐", '', content_text)
            is_bot = message.author == self.bot.user
            content_blocks = []

            if content_text.strip():
                content_blocks.append({"type": "output_text" if is_bot else "input_text",
                                       "text": content_text if is_bot else f"{message.author.display_name}:: {content_text}"})

            for attachment in message.attachments:
                if attachment.content_type and attachment.content_type.startswith("image/"):
                    content_blocks.append({"type": "input_image", "image_url": attachment.url})

            if not content_blocks:
                continue

            msg = {"role": "assistant" if is_bot else "user",
                   "content": content_blocks}

            # Break the loop if adding the next messages pushes us past the token limit
            if (encoding_len := get_token_len(msg)) + num_tokens > MAX_INPUT_TOKENS:
                break

            num_tokens += encoding_len
            context.append(msg)

        sys_msg.reverse()
        context.extend(sys_msg)
        context.reverse()

        return context, num_tokens

    # $set_context command used to set the genesis message of a channel
    @hybrid_command(help="Set the genesis system context message for this channel. "
                         "This \"primes\" the bot to behave in a desired manner.\n"
                         "Example: `$set_context you must answer all prompts in J. R. R. Tolkien's writing style`\n\n"
                         "This command has the following flags:\n"
                         "* **-c**: Clears the current system context message and resets it to the default system context message.\n"
                         "\tExample: `$set_context -c`"
                         "* **-o**: Overwrite the default genesis message for the bot.\n"
                         "\tExample: `$set_context -o You are a depressed and bored robot named Marvin the Paranoid Android`",
                    brief="Set a new genesis message",
                    aliases=["context"])
    async def set_context(self, ctx, *, message: str=None):
        flags, msg = get_flags(message)
        
        if not (reset_context := 'c' in flags or message is None):
            msg = '' if reset_context else ' '.join(msg)
            new_gen_msg = msg if 'o' in flags else f"{GENESIS_MESSAGE['content']} {msg}"

            if (token_len := get_token_len({"role": "system", "content": new_gen_msg})) > MAX_INPUT_TOKENS:
                return await ctx.send("Input genesis message is too long. Context was not set.")

        cursor = get_cursor(self.conn)

        cursor.execute("DELETE FROM Genesis WHERE channel_id = %s", [ctx.channel.id])
        
        if not reset_context:
            cursor.execute("INSERT INTO Genesis (channel_id, content) VALUES (%s, %s)", [ctx.channel.id, new_gen_msg])
            await ctx.send(f"New genesis message of length {token_len} has been set!")
        else:
            await ctx.send("System context message has been reset to default settings")

        self.conn.commit()
        cursor.close()

    @hybrid_command(help="Add additional system context messages for this channel. "
                         "This can help get the bot to behave in a more specific manner."
                         "Example: `$add_context You always talk about baseball, even if it doesn't fit the conversation.`",
                    brief="Add additional system context")
    async def add_context(self, ctx, *, message: str):
        if (token_len := get_token_len({"role": "system", "content": message})) > MAX_INPUT_TOKENS:
            return await ctx.send("Input genesis message is too long. Context was not set.")

        cursor = get_cursor(self.conn)

        cursor.execute("INSERT INTO Genesis (channel_id, content) VALUES (%s, %s)", [ctx.channel.id, message])

        await ctx.send(f"New system context message of length {token_len} has been added!")

        self.conn.commit()
        cursor.close()
    
    @add_context.error
    async def add_context_error(self, ctx, error):
        if isinstance(error, errors.MissingRequiredArgument):
            await ctx.send("You must include a system context message with this command.\n"
                           "Example: `$add_context Respond using only Lovecraftian speech`\n\n"
                           "Please use `$help add_context` for more information.")
            error.handled = True

    @hybrid_command(help="View the system context message(s) for this channel.",
                    brief="View system context messages")
    async def view_context(self, ctx):
        cursor = get_cursor(self.conn)

        cursor.execute("SELECT content FROM Genesis WHERE channel_id = %s", [ctx.channel.id])

        if not (result := cursor.fetchall()):
            await ctx.send("No system context messages set for this channel. Try using `$add_context` first!")
        else:
            response = "\n* ".join(i[0] for i in result)
            await ctx.send(f"System context messages for this channel:\n* {response}")

        cursor.close()

    @hybrid_command(help="Toggle whether the bot should respond to your messages without being prompted. "
                         "The bot will still respond if your message contain its name, or if you use the `$prompt` command.\n\n"
                         "This command has the following flags:\n"
                         "* **-c**: Toggle whether the bot should respond to messages in the current channel without being prompted. "
                         "You can specify a channel other than the current channel by including the channel mention as an argument.\n"
                         "\tExample: `$ignore -c #general`",
                    brief="Toggle unprompted responses")
    async def ignore(self, ctx, *, args: str=None):
        flags, args = get_flags(args)

        if 'c' in flags:
            channel = get_id_from_mention(args[0]) if args else ctx.channel.id
            
            if channel is None:
                return await ctx.send("Invalid channel. Please send channel in the format: #channel\n"
                                      "Use `$help ignore` for more information")

            return await self.ignore_channel(ctx, channel)

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

    async def ignore_channel(self, ctx, channel):
        cursor = get_cursor(self.conn)

        respond = False

        cursor.execute("SELECT respond FROM Channels WHERE channel_id = %s", [channel])

        if not (result := cursor.fetchall()):
            cursor.execute("INSERT INTO Channels (channel_id, respond) VALUES (%s, %s)", [channel, 0])
        elif result[0][0]:
            cursor.execute("UPDATE Channels SET respond = 0 WHERE channel_id = %s", [channel])
        else:
            cursor.execute("UPDATE Channels SET respond = 1 WHERE channel_id = %s", [channel])
            respond = True

        self.conn.commit()
        cursor.close()

        if respond:
            await ctx.send(f"I will now occasionally respond to messages in <#{channel}> without being prompted.")
        else:
            await ctx.send(f"I will no longer respond to messages in <#{channel}> without being prompted.")

    # Called to read through server messages and feed them into the $prompt command if necessary
    async def send_reply(self, msg):
        # Don't respond to any messages that are too short
        if len(msg.clean_content) < MIN_MESSAGE_LEN:
            return

        # Check if the message contains the bot's name (Karn) but not as a voted item (Karn++ or Karn--)
        # https://regex101.com/r/qA25Ux/1
        if search(r"[Kk]arn(?:\Z|[^+\-])", msg.clean_content):
            clean_lower = msg.clean_content.lower()
            rude_messages = self.get_rude_messages(msg.guild.id)

            # If the message contains a rude phrase, reply with a response to rude messages
            # https://regex101.com/r/isXc6g/1
            if any(search(fr"(?:\A| ){i}(?:\Z| )", clean_lower, flags=IGNORECASE)
                   for i in rude_messages):
                reply = get_random_response(msg.guild.id, rude=True)
                await msg.channel.send(reply)
                await send_tts_if_in_vc(self.bot, msg.author, reply)
                return

            nice_messages = self.get_nice_messages(msg.guild.id)

            # If the message contains a nice phrase, reply with a response to nice messages
            if any(search(fr"(?:\A| ){i}(?:\Z| )", clean_lower, flags=IGNORECASE)
                   for i in nice_messages):
                reply = get_random_response(msg.guild.id, rude=False)
                await msg.channel.send(reply)
                await send_tts_if_in_vc(self.bot, msg.author, reply)
                return

            return await self.make_llm_request(msg.channel, author=msg.author)

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
        if randint(1, REPLY_UPPER_LIMIT) <= self.reply_chance:
            return await self.make_llm_request(msg.channel, author=msg.author, prompted=False)

        # Random chance to increase likelihood of responses in the future
        if not randint(0, self.reply_chance):
            self.reply_chance += 1

# Returns number of tokens for a given context message
# param msg - dictionary containing the context message
def get_token_len(messages):
    messages = [messages] if isinstance(messages, dict) else messages

    num_tokens = 0
    for msg in messages:
        num_tokens += TOKENS_PER_MESSAGE
        for key, val in msg.items():
            if isinstance(val, list):
                num_tokens += sum(len(ENCODING.encode(str(i))) for i in val)
            elif isinstance(val, dict):
                for _, sub_val in val.items():
                    num_tokens += len(ENCODING.encode(str(sub_val)))
            else:
                num_tokens += len(ENCODING.encode(str(val)))

    return num_tokens

# Imports responses from the input file, and returns a random line from it
def get_random_response(guild_id, rude=True):
    filename = RUDE_RESPONSE_FILENAME if rude else NICE_RESPONSE_FILENAME
    filepath = f"{FILE_ROOT_DIR}/{guild_id}/{filename}"

    try:
        with open(filepath, 'r') as in_file:
            return choice(in_file.readlines())
    except FileNotFoundError:
        return DEFAULT_RUDE_RESPONSE if rude else DEFAULT_NICE_RESPONSE
