from datetime import datetime, date
from discord.ext import commands, tasks
from json import loads, decoder
from os import getenv
from requests import get as get_req
from re import sub
import discord

api_key = getenv("WORDNIK_TOKEN")
main_channel = int(getenv("GENERAL_CH_ID"))


class Dictionary(commands.Cog):

    def __init__(self, bot: commands.Bot, guild: discord.Guild):
        self.bot = bot
        self.guild = guild
        self.ch_general = None

        self.word_of_the_day.start()

    @commands.command(help="Returns several definitions for a given word\nExample: `$define love`",
                      brief="Returns several definitions for a given word")
    async def define(self, ctx, word: str):
        url = f"https://api.wordnik.com/v4/word.json/{word}/definitions?" \
              f"limit=16&sourceDictionaries=wiktionary&includeTags=false&api_key={api_key}"
        response = get_req(url)
        api_response = loads(response.text)

        if "statusCode" in api_response:
            await ctx.send(f"{word} not found in the dictionary. Please check the spelling.")
            return

        definitions = {}

        for dic in api_response:
            try:
                definition = sub(r"<[^<>]+>", '', dic["text"])
            except KeyError:
                continue

            if dic["partOfSpeech"] in definitions:
                definitions[dic["partOfSpeech"]].append(definition)
            else:
                definitions[dic["partOfSpeech"]] = [definition]

        msg = []

        for part_of_speech in definitions:
            msg.append(f"\n\n{part_of_speech.capitalize()}")
            def_num = 0
            for definition in definitions[part_of_speech]:
                def_num += 1
                msg.append(f"\n    {def_num}. {definition}")

        await ctx.send(f"**{word.capitalize()}**```{''.join(msg)}```")

    @define.error
    async def define_error(self, ctx, error):
        if isinstance(error, commands.errors.MissingRequiredArgument):
            await ctx.send("You must include a word to define.\n"
                           "Example: `$define hate`\n\n"
                           "Please use `$help define` for more information.")

    @tasks.loop(hours=1)
    async def word_of_the_day(self):
        current_time = datetime.now()
        if current_time.hour != 11:
            return
        url = f"https://api.wordnik.com/v4/words.json/wordOfTheDay?date={date.today()}&api_key={api_key}"
        response = get_req(url)
        try:
            api_response = loads(response.text)
        except decoder.JSONDecodeError:
            print(f"{current_time}\n"
                  f"WotD Error: Bad API response!\n"
                  f"URL: {url}\n"
                  f"Response:\n"
                  f"{response.text}")
            return
        response_data = {}
        if response.status_code == 200:
            response_data["word"] = api_response["word"]
            for definition in api_response["definitions"]:
                response_data["definition"] = sub(r"<[^<>]+>", '', definition["text"])
                break
            await self.ch_general.send(f"**The word of the day is:**\n"
                                       f"*{api_response['word']}* - {response_data['definition']}")
        else:
            print(f"Error: Word of the Day Loop could not load response correctly.\n"
                  f"Status Code: {response.status_code}\n")

    @word_of_the_day.before_loop
    async def before_WotD(self):
        await self.bot.wait_until_ready()
        print("Starting Word of the Day hourly loop.")
        self.ch_general = self.guild.get_channel(main_channel)
        if self.ch_general is None:
            print("WARNING: General channel not found. Loop not started.")
            self.word_of_the_day.cancel()
            return
        print("Loop successfully started!\n")
