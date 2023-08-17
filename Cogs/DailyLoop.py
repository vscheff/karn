from datetime import datetime, date
from discord.ext import commands, tasks
from json import loads, decoder
from os import getenv
from random import choice, randint
from requests import get as get_req
from re import sub
import discord

api_key = getenv("WORDNIK_TOKEN")
MAIN_CHANNEL = int(getenv("GENERAL_CH_ID"))


class DailyLoop(commands.Cog):

    def __init__(self, bot: commands.Bot, guild: discord.Guild):
        self.bot = bot
        self.guild = guild
        self.ch_general = None

        self.daily_sent = False
        self.daily_funcs = (self.daily_card, self.daily_fact, self.daily_word)

        self.daily_loop.start()

    @tasks.loop(hours=1)
    async def daily_loop(self):
        current_time = datetime.now()

        if current_time.hour == 0:
            self.daily_sent = False

        if self.daily_sent or randint(0, 23 - current_time.hour):
            return

        await choice(self.daily_funcs)()

        self.daily_sent = True

    @daily_loop.before_loop
    async def before_daily_loop(self):
        await self.bot.wait_until_ready()

        print("Starting daily loop...")
        self.ch_general = self.guild.get_channel(MAIN_CHANNEL)

        if self.ch_general is None:
            print("WARNING: General channel not found. Loop not started.")
            return self.before_daily_loop.cancel()

        print("Loop successfully started!\n")

    async def daily_card(self):
        await self.ch_general.send(f"__**The MtG card of the day is:**__")
        await self.bot.get_command("card")(self.ch_general, args="-r")

    async def daily_fact(self):
        await self.ch_general.send(f"__**The fact of the day is:**__")
        await self.bot.get_command("fact")(self.ch_general)

    async def daily_wiki(self):
        await self.ch_general.send(f"__**The Wikipedia article of the day is:**__")
        await self.bot.get_command("wiki")(self.ch_general, args="-r")

    async def daily_word(self):
        url = f"https://api.wordnik.com/v4/words.json/wordOfTheDay?date={date.today()}&api_key={api_key}"
        response = get_req(url)
        try:
            api_response = loads(response.text)
        except decoder.JSONDecodeError:
            print(f"WotD Error: Bad API response!\n"
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
            await self.ch_general.send(f"__**The word of the day is:**__\n"
                                       f"*{api_response['word']}* - {response_data['definition']}")
        else:
            print(f"Error: Word of the Day Loop could not load response correctly.\n"
                  f"Status Code: {response.status_code}\n")
