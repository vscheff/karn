# Cog that holds all commands related to RNG
from discord.ext import commands
from os import getenv
from randfacts import get_fact
from random import choice, randint, shuffle
import discord

from src.utils import get_flags, package_message


MAX_ROLL = 2 ** 18


class Random(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(help="Returns a randomly selected fact\n\n"
                           "This command has the following flags:\n"
                           "* **-n**: Returns only not safe for work facts"
                           "\tExample: `$fact -n`",
                      brief="Returns a random fact")
    async def fact(self, ctx, *, args=None):
        flags, = get_flags(args.lower()) if args is not None else [],

        await ctx.send(get_fact(filter_enabled=False, only_unsafe='c' in flags))

    # $flip command sends either "heads" or "tails" in the channel
    @commands.command(help="Returns either \"heads\" or \"tails\" via random selection.\n"
                           "To flip multiple coins simultaneously, include an integer argument.\n"
                           "Example: `$flip 3`",
                      brief="Returns either \"heads\" or \"tails\"")
    async def flip(self, ctx, *, args=None):
        if args is None:
            return await ctx.send(choice(("heads", "tails")))

        try:
            num_flip = int(args)
        except ValueError:
            await ctx.send("Bad argument, use only integers with this command.\n"
                           "Example: `$flip 3`")
            return

        result = ''.join(choice(("H","T")) for _ in range(num_flip))
        
        await ctx.send(f"{result}\nHeads = {result.count('H')}\nTails = {result.count('T')}")

    # $number command used to generate a random integer within a given range
    @commands.command(help="Returns a randomly chosen number between two given integers\n"
                           "Example: `$number 1 10`\n\n"
                           "If only one integer is given, "
                           "then a number between 1 and that integer will be chosen\n"
                           "Example: `$number 10`",
                      brief="Returns a random number")
    async def number(self, ctx, lower: int, upper: int = None):
        if upper is None:
            lower, upper = 1, lower if lower > 0 else lower, 0
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

    @commands.command(help="Returns a given list in a randomized order.\n"
                           "The list can be of any size, with each item seperated by a comma\n"
                           "Example: `$shuffle Cryzel Rosechu, Magi-Chan, Mewtwo, Sylvana`",
                      brief="Randomizes a given list")
    async def shuffle(self, ctx, *, arg):
        lst = [item.strip() for item in arg.split(',') if item]
        shuffle(lst)
        await ctx.send(", ".join(lst))

    @shuffle.error
    async def shuffle_error(self, ctx, error):
        if isinstance(error, commands.errors.MissingRequiredArgument):
            await ctx.send("You must include a comma-seperated list of items.\n"
                           "Example: `$shuffle me, myself, I`\n\n"
                           "Please use `$help shuffle` for more information.")

    # $roll command used to simulate the rolling of dice
    # param dice - string representing dice to be rolled in xDn format
    @commands.command(help="Rolls any number of n-sided dice in the classic \"xDn\" format.\n"
                           "Where *x* is the quantity of dice being rolled, "
                           "and *n* is the number of sides on the die.\n"
                           "Example: `$roll 3d20`\n"
                           "If rolling only one die, you may ommit the '1'.\n"
                           "Example: `$roll d6`\n\n"
                           "This command has the following flags:\n"
                           "* **-m**: Indicates your argument is a comma-seperated list of dice.\n"
                           "\tExample: `$roll -m 4d20, d3, 6d9`",
                      brief="Rolls dice in the classic \"xDn\" format")
    async def roll(self, ctx, *, args):
        flags, query = get_flags(args, True)

        if 'm' in flags:
            query = [i.strip() for i in query.split(',')]
        else:
            query = [query]

        dice = []

        for die in query:
            if die[0] in "Dd":
                die = '1' + die

            try:
                quantity, size = [int(i) for i in die.lower().split('d')]
            except ValueError:
                await ctx.send("Please format your dice in the classic \"XdY\" style. "
                               "For example, 1d20 rolls *one* 20-sided die.")
                return

            if quantity < 1 or size < 1:
                await ctx.send("Please use only positive integers for dice quantity and number of sides.")
                return
            
            if quantity >= MAX_ROLL or size >= MAX_ROLL:
                await ctx.send(f"Please only use integers smaller than {MAX_ROLL}.")
                return
            
            dice.append({"quantity": quantity, "size": size})
           
        if len(dice) == 1 and dice[0]["quantity"] == 1:
            return await ctx.send(randint(1, dice[0]["size"]))

        roll_list = []
        grand_total = 0
        
        for die in dice:
            roll_list.append(f"\n__Rolling **{die['quantity']}d{die['size']}**__:")
            total = 0

            for i in range(die["quantity"]):
                roll = randint(1, die["size"])
                total += roll
                roll_list.append(f"Roll #{i+1}: {roll}")
            
            roll_list.append(f"**Total:** {total}")
            grand_total += total

        if len(dice) > 1:
            roll_list.append(f"\n**Grand Total:** {grand_total}")

        await package_message('\n'.join(roll_list), ctx)

    @roll.error
    async def roll_error(self, ctx, error):
        if isinstance(error, commands.errors.MissingRequiredArgument):
            await ctx.send("You must include a dice to roll.\n"
                           "Example: `$roll 4d20`\n\n"
                           "Please use `$help roll` for more information.")

