from datetime import datetime, date
import discord
from discord.ext import commands, tasks
from json import loads, decoder
from os import getenv
from random import randint, sample
from requests import get
from re import sub

from utils import get_cursor, get_flags

WORDNIK_API_KEY = getenv("WORDNIK_TOKEN")
MAIN_CHANNEL = int(getenv("GENERAL_CH_ID"))

WORDNIK_URL = "https://api.wordnik.com/v4/words.json/wordOfTheDay"

DESC = {"card": "a Magic: The Gathering card",
        "fact": "a fact of the day",
        "wiki": "a Wikipedia article",
        "word": "a word of the day",
        "xkcd": "an XKCD comic"}


class DailyLoop(commands.Cog):

    def __init__(self, bot: commands.Bot, guild: discord.Guild, conn):
        self.bot = bot
        self.guild = guild
        self.conn = conn

        self.ch_general = None

        self.rand_hour = get_pseudo_rand_hour()
        self.daily_funcs = (self.daily_card, self.daily_fact, self.daily_wiki, self.daily_word, self.daily_xkcd)
        self.today_funcs = [i for i in self.daily_funcs]

        self.daily_loop.start()

    @commands.command(help="Have daily messages sent to this channel.\n"
                           "Message categories include:\n"
                           "* *card*: Sends a random Magic: The Gathering card\n"
                           "* *fact*: Sends a random fact\n"
                           "* *wiki*: Sends a random Wikipedia article\n"
                           "* *word*: Sends a random word and its definition\n"
                           "* *xkcd*: Sends a random XKCD comic\n"
                           "Example: `$daily fact`\n\n"
                           "This command has the following flags:\n"
                           "* **-a**: Instructs the command to use all available categories\n"
                           "\tExample: `$daily -a`"
                           "* **-d**: Stop sending messages from the given category\n"
                           "\tExample: `$daily -d word`\n"
                           "* **-l**: List the categories currently being sent to this channel\n"
                           "\tExample: `$daily -l`\n"
                           "* **-m**: Add multiple categories in a comma-seperated list.\n"
                           "\tExample: `$daily fact, wiki, word, xkcd`",
                      brief="Send daily messages to a channel")
    async def daily(self, ctx, *, args):
        flags, args = get_flags(args)
        args = ' '.join(args).lower()

        if 'm' in flags:
            categories = [i.strip() for i in args.split(',')]
        elif 'a' in flags:
            categories = list(DESC.keys())
        else:
            categories = [args]

        cursor = get_cursor(self.conn)
        cursor.execute("SELECT card, fact, wiki, word, xkcd FROM Channels WHERE channel_id = %s", [ctx.channel.id])
        result = cursor.fetchall()

        if 'l' in flags:
            cursor.close()

            if not result or not any(i for i in result[0]):
                return await ctx.send("I am not currently sending any daily messages to this channel.")

            keys = list(DESC.keys())
            sending = [keys[i] for i in range(len(DESC)) if result[0][i]]

            return await ctx.send(f"I am currently sending {build_cat_str(sending)} to this channel each day.")

        update = bool(result)
        value = int('d' not in flags)
        valid_categories = []

        for category in categories:
            if category not in ("card", "fact", "wiki", "word", "xkcd"):
                await ctx.send(f"Unknown category \"{category}\" skipped. Please check your spelling and try again.")
                continue

            valid_categories.append(category)
            val = [value, ctx.channel.id]

            if update:
                cursor.execute(f"UPDATE Channels SET {category} = %s WHERE channel_id = %s", val)
            else:
                cursor.execute(f"INSERT INTO Channels ({category}, channel_id) VALUES (%s, %s)", val)
                update = True

        if valid_categories:
            if value:
                await ctx.send(f"I will now begin sending {build_cat_str(valid_categories)} to this channel each day.")
            else:
                await ctx.send(f"I will no longer send {build_cat_str(valid_categories)} to this channel.")

        self.conn.commit()
        cursor.close()

    @daily.error
    async def daily_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("You must include a category with this command.\n"
                           "Example: `$daily fact`\n\n"
                           "Please use `$help daily` for more information.")

    @tasks.loop(hours=1)
    async def daily_loop(self):
        current_time = datetime.now()

        if not current_time.hour:
            self.today_funcs = [i for i in self.daily_funcs]

        if current_time.hour != self.rand_hour:
            return

        await self.today_funcs.pop(randint(0, len(self.today_funcs) - 1))()

        self.rand_hour = get_pseudo_rand_hour()

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
        response = get(WORDNIK_URL, params={"date": date.today(), "api_key": WORDNIK_API_KEY})
        try:
            api_response = loads(response.text)
        except decoder.JSONDecodeError:
            print(f"WotD Error: Bad API response!\n"
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

    async def daily_xkcd(self):
        await self.ch_general.send(f"__**The xkcd comic of the day is:**__")
        await self.bot.get_command("xkcd")(self.ch_general, args="-r")


def build_cat_str(categories):
    if not categories:
        return ''

    if len(categories) == 1:
        cat_str = DESC[categories[0]]
    elif len(categories) == 2:
        cat_str = f"{DESC[categories[0]]} or {DESC[categories[1]]}"
    else:
        cat_str = ", ".join([DESC[i] for i in categories[:-1]] + [f"or {DESC[categories[-1]]}"])

    return cat_str

def get_pseudo_rand_hour():
    return sample(range(1, 24), 1, counts=[12 - abs((12 - i)) for i in range(1, 24)])[0]
