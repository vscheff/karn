# Cog that holds all commands related to RNG

from datetime import datetime
from discord.ext import commands, tasks
from os import getenv
from randfacts import get_fact
from random import choice, randint, shuffle
import discord

from msg_packager import package_message

MAX_ROLL = 2 ** 18
main_channel = int(getenv("GENERAL_CH_ID"))


class Random(commands.Cog):

    def __init__(self, bot: commands.Bot, guild: discord.Guild):
        self.bot = bot
        self.guild = guild
        self.ch_general = None

        self.daily_fact.start()

    @tasks.loop(hours=1)
    async def daily_fact(self):
        current_time = datetime.now()
        if current_time.hour != 13:
            return
        await self.ch_general.send(f"**The fact of the day is:**\n{get_fact(filter_enabled=False)}")

    @daily_fact.before_loop
    async def before_daily_fact(self):
        await self.bot.wait_until_ready()
        print("Starting Daily Fact hourly loop.")
        self.ch_general = self.guild.get_channel(main_channel)
        if self.ch_general is None:
            print("WARNING: General channel not found. Loop not started.\n")
            self.daily_fact.cancel()
            return
        print("Loop successfully started!\n")

    @commands.command(help="Returns a randomly selected fact",
                      brief="Returns a random fact")
    async def fact(self, ctx):
        await ctx.send(get_fact(filter_enabled=False))

    @commands.command(help="Returns a randomly selected NSFW fact",
                      brief="Returns a random NSFW fact",
                      aliases=["nsfwfact", "nsfw_fact"])
    async def fact_nsfw(self, ctx):
        await ctx.send(get_fact(only_unsafe=True))

    # $flip command sends either "heads" or "tails" in the channel
    @commands.command(help="Returns either \"heads\" or \"tails\" via random selection.",
                      brief="Returns either \"heads\" or \"tails\"")
    async def flip(self, ctx):
        await ctx.send(choice(("heads", "tails")))

    # $number command used to generate a random integer within a given range
    @commands.command(help="Returns a randomly chosen number between two given integers\n"
                           "Example: `$number 1 10`\n\n"
                           "If only one integer is given, "
                           "then a number between 1 and that integer will be chosen\n"
                           "Example: `$number 10`",
                      brief="Returns a random number")
    async def number(self, ctx, lower: int, upper: int = None):
        if upper is None:
            lower, upper = 1, lower
        await ctx.send(randint(lower, upper))

    # Called if $number encounters an unhandled exception
    @number.error
    async def number_error(self, ctx, error):
        if isinstance(error, commands.errors.MissingRequiredArgument):
            await ctx.send("You must include at least 1 integer to serve as an upper bound\n"
                           "Example: `$number 4`2\n\n"
                           "Please use `$help number` for more information.")
        elif isinstance(error, commands.errors.BadArgument):
            await ctx.send("Bad argument, use only integers with this command.\n\n"
                           "Please use `$help number` for more information.")

    # $choice command used to randomly select one item from a list
    # param arg - all user input following command-name
    @commands.command(help="Returns 1 chosen item from a given list\n"
                           "The list can be of any size, with each item seperated by a comma\n"
                           "Example: `$choice Captain Kirk, Captain Picard, Admiral Adama`",
                      brief="Returns 1 randomly chosen item")
    async def choice(self, ctx, *, arg):
        await ctx.send(choice([item.strip() for item in arg.split(',') if item]))

    # Called if $choice encounters an unhandled exception
    @choice.error
    async def choice_error(self, ctx, error):
        if isinstance(error, commands.errors.MissingRequiredArgument):
            await ctx.send("You must include a comma-seperated list of items.\n"
                           "Example: `$choice me, myself, I`\n\n"
                           "Please use `$help choice` for more information.")
        else:
            print(f"$choice command failed with error:\n\n{error}")

    @commands.command(help="Returns a given list in a randomized order.\n"
                           "The list can be of any size, with each item seperated by a comma\n"
                           "Example: `$shuffle Cryzel Rosechu, Magi-Chan, Mewtwo, Sylvana`",
                      brief="Returns a given list in a randomized order")
    async def shuffle(self, ctx, *, arg):
        lst = [item.strip() for item in arg.split(',') if item]
        shuffle(lst)
        await ctx.send(", ".join(lst))

    @shuffle.error
    async def shuffle_error(self, ctx, error):
        if isinstance(error, commands.errors.MissingRequiredArgument):
            await ctx.send("You must include a comma-seperated list of items.\n"
                           "Example: `$choice me, myself, I`\n\n"
                           "Please use `$help shuffle` for more information.")

    # $roll command used to simulate the rolling of dice
    # param dice - string representing dice to be rolled in xDn format
    @commands.command(help="Rolls any number of n-sided dice in the classic \"xDn\" format\n"
                           "Where *x* is the quantity of dice being rolled, "
                           "and *n* is the number of sides on the die\n"
                           "Example: `$roll 3d20`",
                      brief="Rolls dice in the classic \"xDn\" format")
    async def roll(self, ctx, dice):
        try:
            # Remove spaces from the input, and split it at the character "d", then cast to int
            quantity, size = dice.lower().replace(' ', '').split('d')
            quantity, size = int(quantity), int(size)
        except ValueError:
            await ctx.send("Please format your dice in the classic \"xDy\" style. "
                           "For example, 1d20 rolls one 20-sided die.")
            return
        if quantity < 1 or size < 1:
            await ctx.send("Please use only positive integers for dice quantity and number of sides.")
            return
        if quantity >= MAX_ROLL or size >= MAX_ROLL:
            await ctx.send(f"Please only use integers smaller than {MAX_ROLL}.")
            return
        roll_list = []
        total = 0
        for i in range(quantity):
            roll = randint(1, size)
            total += roll
            roll_list.append(f"Roll #{i+1}: {roll}")
        roll_list.append(f"**Total:** {total}")
        await package_message('\n'.join(roll_list), ctx)
