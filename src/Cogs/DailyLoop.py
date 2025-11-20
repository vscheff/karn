from datetime import datetime, date
from discord.ext import commands, tasks
from json import loads, decoder
from os import getenv
from random import choice, sample
from requests import get
from re import sub

from src.utils import get_cursor, get_flags, get_id_from_mention, package_message
from src.tips import TIP_LIST

WORDNIK_API_KEY = getenv("WORDNIK_TOKEN")

WORDNIK_URL = "https://api.wordnik.com/v4/words.json/wordOfTheDay"

DESC = {"calvin": "a Calvin & Hobbes comic",
        "card": "a Magic: The Gathering card",
        "fact": "a fact of the day",
        "garfield": "a Garfield comic",
        "peanuts": "a Peanuts comic",
        "tip": "a tip for using Karn",
        "wiki": "a Wikipedia article",
        "word": "a word of the day",
        "xkcd": "an XKCD comic"}


class DailyLoop(commands.Cog):

    def __init__(self, bot: commands.Bot, conn):
        self.bot = bot
        self.conn = conn

        self.daily_funcs = (self.daily_calvin, self.daily_card, self.daily_fact, 
                            self.daily_garfield, self.daily_peanuts, self.daily_tip,
                            self.daily_wiki, self.daily_word, self.daily_xkcd)

        self.daily_loop.start()

    @commands.command(help="Have daily messages sent to this channel.\n"
                           "Message categories include:\n"
                           "* *calvin*: Sends a random Calvin & Hobbes comic\n"
                           "* *card*: Sends a random Magic: The Gathering card\n"
                           "* *fact*: Sends a random fact\n"
                           "* *garfield*: Sends a random Garfield comic\n"
                           "* *peanuts*: Sends a random Peantus comic\n"
                           "* *tip*: Sends a tip for using Karn\n"
                           "* *wiki*: Sends a random Wikipedia article\n"
                           "* *word*: Sends a random word and its definition\n"
                           "* *xkcd*: Sends a random XKCD comic\n"
                           "Example: `$daily fact`\n\n"
                           "This command has the following flags:\n"
                           "* **-a**: Instructs the command to use all available categories\n"
                           "\tExample: `$daily -a`\n"
                           "* **-c**: Change options for a different given channel\n"
                           "\tExample: `$daily -c #general garfield`\n"
                           "* **-d**: Stop sending messages from the given category\n"
                           "\tExample: `$daily -d word`\n"
                           "* **-l**: List the categories currently being sent to this channel\n"
                           "\tExample: `$daily -l`\n"
                           "* **-m**: Add multiple categories in a comma-seperated list.\n"
                           "\tExample: `$daily -m fact, wiki, word, xkcd`\n"
                           "* **-t**: Trigger the immediate retrieval of a daily item in this channel.\n"
                           "\tExample: `$daily -t`",
                      brief="Send daily messages to a channel")
    async def daily(self, ctx, *, args):
        flags, args = get_flags(args.lower())

        if 'c' in flags:
            if (channel_id := get_id_from_mention(args[0])) is None:
                return await ctx.send("Invalid channel. Please send channel in the format: #channel\n"
                                      "Use `$help daily` for more information")
            query = ' '.join(args[1:])
        else:
            channel_id = ctx.channel.id
            query = ' '.join(args)

        if 't' in flags:
            await self.daily_loop(triggered=True, channel_id=channel_id)
            return

        if 'm' in flags:
            categories = [i.strip() for i in query.split(',')]
        elif 'a' in flags:
            categories = list(DESC.keys())
        else:
            categories = [query]

        cursor = get_cursor(self.conn)
        cursor.execute("SELECT calvin, card, fact, garfield, peanuts, tip, wiki, word, xkcd "
                       "FROM Channels "
                       "WHERE channel_id = %s",
                       [channel_id])
        result = cursor.fetchall()

        if 'l' in flags:
            cursor.close()

            if not result or not any(i for i in result[0]):
                return await ctx.send(f"I am not currently sending any daily messages to <#{channel_id}>.")

            keys = list(DESC.keys())
            sending = [keys[i] for i in range(len(DESC)) if result[0][i]]

            return await ctx.send(f"I am currently sending {build_cat_str(sending)} to <#{channel_id}> each day.")

        update = bool(result)
        value = int('d' not in flags)
        val = [value, channel_id]
        valid_categories = []

        for category in categories:
            if category not in DESC:
                await ctx.send(f"Unknown category \"{category}\" skipped. Please check your spelling and try again.")
                continue

            valid_categories.append(category)

            if update:
                cursor.execute(f"UPDATE Channels SET {category} = %s WHERE channel_id = %s", val)
            else:
                cursor.execute(f"INSERT INTO Channels ({category}, channel_id) VALUES (%s, %s)", val)
                update = True

        if valid_categories:
            if value:
                await ctx.send(f"I will now begin sending {build_cat_str(valid_categories)} "
                               f"to <#{channel_id}> each day.")
            else:
                await ctx.send(f"I will no longer send {build_cat_str(valid_categories)} to <#{channel_id}>.")

        self.conn.commit()
        cursor.close()

    @daily.error
    async def daily_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("You must include a category with this command.\n"
                           "Example: `$daily fact`\n\n"
                           "Please use `$help daily` for more information.")

    @tasks.loop(hours=1)
    async def daily_loop(self, **kwargs):
        current_time = datetime.now()
        cursor = get_cursor(self.conn)
        triggered = kwargs.get("triggered", False)

        if not (current_time.hour or triggered):
            cursor.execute("SELECT channel_id FROM Channels")
            for channel, in cursor.fetchall():
                val = [get_pseudo_rand_hour(), channel]
                cursor.execute("UPDATE Channels SET daily_hour = %s WHERE channel_id = %s", val)
            self.conn.commit()
            cursor.close()
            return 
            
        cursor.execute("SELECT daily_hour, channel_id, calvin, card, fact, garfield, peanuts, tip, wiki, word, xkcd "
                       "FROM Channels")

        if triggered:
            if (output_channel := kwargs.get("channel_id")) is None:
                raise AttributeError

            channel = self.bot.get_channel(output_channel)

            for hour, channel_id, *categories in cursor.fetchall():
                if channel_id != output_channel:
                    continue

                if not any(categories):
                    await channel.send("This channel is not current configured to receive any daily messages.\n"
                                       "Try adding some categories to this channel first.\n"
                                       "Please use `$help daily` for more information.")
                    return

                indexes = [i for i in range(len(categories)) if categories[i]]

                await self.daily_funcs[choice(indexes)](channel)

                return

            await channel.send("This channel is not current configured to receive any daily messages.\n"
                               "Try adding some categories to this channel first.\n"
                               "Please use `$help daily` for more information.")

            return

        for hour, channel_id, *categories in cursor.fetchall():
            if hour != current_time.hour or not any(categories):
                continue

            indexes = [i for i in range(len(categories)) if categories[i]]
            
            try:
                await self.daily_funcs[choice(indexes)](self.bot.get_channel(channel_id))
            except AttributeError:
                print(f"Unable to send daily message to channel with id: {channel_id}")

        cursor.close()

    @daily_loop.before_loop
    async def before_daily_loop(self):
        await self.bot.wait_until_ready()

    async def daily_calvin(self, channel):
        await channel.send(f"__**The Calvin and Hobbes strip of the day is:**__")
        await self.bot.get_command("comic")(channel, comic="calvinandhobbes")

    async def daily_card(self, channel):
        await channel.send(f"__**The MtG card of the day is:**__")
        await self.bot.get_command("card")(channel, card="-r")

    async def daily_fact(self, channel):
        await channel.send(f"__**The fact of the day is:**__")
        await self.bot.get_command("fact")(channel)

    async def daily_garfield(self, channel):
        await channel.send(f"__**The Garfield strip of the day is:**__")
        await self.bot.get_command("comic")(channel, comic="garfield")

    async def daily_peanuts(self, channel):
        await channel.send(f"__**The Peanuts strip of the day is:**__")
        await self.bot.get_command("comic")(channel, comic="peanuts")

    async def daily_tip(self, channel):
        await channel.send(f"__**The tip of the day is:**__")
        await package_message(choice(TIP_LIST), channel, multi_send=True)

    async def daily_wiki(self, channel):
        await channel.send(f"__**The Wikipedia article of the day is:**__")
        await self.bot.get_command("wiki")(channel, query="-r")

    async def daily_word(self, channel):
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
            await channel.send(f"__**The word of the day is:**__\n"
                               f"*{api_response['word']}* - {response_data['definition']}")
        else:
            print(f"Error: Word of the Day Loop could not load response correctly.\n"
                  f"Status Code: {response.status_code}\n")

    async def daily_xkcd(self, channel):
        await channel.send(f"__**The xkcd comic of the day is:**__")
        await self.bot.get_command("xkcd")(channel, number="-r")


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
