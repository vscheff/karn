# Cog that holds all commands related to RNG

from datetime import datetime, timedelta
from discord.ext import commands, tasks
from json import dump, load
from os import getenv
from randfacts import get_fact
from random import choice, randint
from re import findall
import discord

main_channel = int(getenv('GENERAL_CH_ID'))


class Random(commands.Cog):

    def __init__(self, bot: commands.Bot, guild: discord.Guild):
        self.bot = bot
        self.guild = guild
        self.ch_general = None

        self.daily_fact.start()

        with open('./hat.json', 'r') as inFile:
            self.hat_store = load(inFile)

        for guild in bot.guilds:
            if str(guild.id) not in self.hat_store:
                self.hat_store[str(guild.id)] = {'main': []}

    @commands.command(help='Use this command to interface with the hat pick system.\n'
                           'Usage: `$hat <subcommand> [-flags] [flag arg] <subcommand arg>`\n\n\n'
                           'This command is broken up into the following subcommands:\n\n'
                           '**Add**: Adds an element to the *main* hat.\n'
                           'Example: `$hat add Moonfall`\n\n'
                           '**Choice**: Randomly chooses one element from the *main* hat.\n\n'
                           '**clEar**: Clears all elements from the *main* hat.\n\n'
                           '**Delete**: Deletes a specified hat.\n'
                           'Example: `$hat delete enemies`\n\n'
                           '**Import**: Bulk add elements from current text channel that match given a filter string.\n'
                           'Example: $hat import "https://www.imdb.com/\S+"\n\n'
                           '**List**: Lists the active hats for this server.\n\n'
                           '**New**: Creates a new a hat.\n'
                           'Example: `$hat new cards`\n\n'
                           '**Pop**: Randomly chooses and removes one element from the *main* hat.\n\n'
                           '**View**: View all elements in the *main* hat\n\n\n'
                           'This command has the following flags:\n\n'
                           '**-c**: Used to specify a channel other than than the context channel.\n'
                           'Example: `$hat import -c general "www.\S+.com"`'
                           '**-h**: Used to specify a hat other than *main*.\n'
                           'Example: `$hat add -h movies Troll 2`\n\n'
                           '**-m**: Indicates your subcommand argument is a comma-seperated list of elements.\n'
                           'Example: `$hat add -m Monster a Go-Go, Birdemic, Batman & Robin`',
                      brief='Interface with the hat pick system')
    async def hat(self, ctx, *, arg):
        this_guild = self.hat_store[str(ctx.guild.id)]
        arg_lst = arg.split()
        command = arg_lst.pop(0).lower()

        flags = []
        if arg_lst:
            flg_args = 0
            for arg in arg_lst:
                if arg[0] == '-':
                    flags.extend([i.lower() for i in arg[1:]])
                    flg_args += 1
                else:
                    for i in range(flg_args):
                        arg_lst.pop(i)
                    break

        hat_name = 'main' if 'h' not in flags else arg_lst.pop(0)

        if command in ('a', 'add'):
            if not arg_lst:
                await ctx.send('**Error:** You must include the element name you wish to add with this command.')
                return
            if hat_name not in this_guild:
                this_guild[hat_name] = []
            if 'm' in flags:
                this_guild[hat_name].extend(' '.join(arg_lst).split(','))
            else:
                this_guild[hat_name].append(' '.join(arg_lst))
            await self.store_json()
        elif command in ('c', 'choice'):
            if hat_name not in this_guild:
                await ctx.send(f'**Error:** No hat with name *{hat_name}* found in this guild.')
                return
            if not this_guild[hat_name]:
                await ctx.send(f'**Error:** Hat with name *{hat_name}* is empty, no element can be chosen.')
                return
            hat_draw = this_guild[hat_name][randint(0, len(this_guild[hat_name]))]
            await ctx.send(f'I have randomly selected **{hat_draw}** from the hat!')
        elif command in ('d', 'delete'):
            if not arg_lst:
                await ctx.send('**Error:** You must include a hat name with this subcommand.')
                return
            if 'm' in flags:
                hats = [i.strip() for i in ' '.join(arg_lst).lower().split(',')]
            else:
                hats = [arg_lst.pop(0).lower()]
            for del_hat in hats:
                if del_hat not in this_guild:
                    await ctx.send(f'**Error**: No hat with name *{del_hat}* found in this guild.')
                    continue
                this_guild.pop(del_hat)
            await self.store_json()
        elif command in ('e', 'clear'):
            this_guild[hat_name] = []
            await self.store_json()
        elif command in ('h', 'help'):
            await ctx.send(self.hat.help)
        elif command in ('i', 'import'):
            if hat_name not in this_guild:
                await ctx.send(f'**Error:** No hat with name *{hat_name}* found in this guild.')
                return
            if 'c' in flags:
                if not arg_lst:
                    await ctx.send('**Error:** You must include a channel name to use the *-c* flag.')
                    return
                target_channel = arg_lst.pop(0).lower()
                channel = list(filter(lambda x: x.name == target_channel, ctx.guild.text_channels))
                if not channel:
                    await ctx.send(f'**Error:** Channel with name *{target_channel}* not found in this guild.')
                    return
                channel = channel[0]
            else:
                channel = ctx.channel
            if not arg_lst:
                await ctx.send('**Error:** You must include a filter string to use with this command.')
                return
            filter_string = ' '.join(arg_lst).strip('\'"')

            matched_messages = []
            async for message in channel.history(limit=100000):
                if message == ctx.message:
                    continue
                matched_messages.extend(findall(filter_string, message.content))

            this_guild[hat_name].extend(matched_messages)

            await ctx.send(f'Added {len(matched_messages)} elements found in {channel.name} '
                           f'matching "{filter_string}" to *{hat_name}*.')

        elif command in ('l', 'list'):
            hats = '\n'.join([i for i in this_guild])
            await ctx.send(f'**HATS**\n{hats}')
        elif command in ('n', 'new'):
            if not arg_lst:
                await ctx.send('**Error:** You must include a hat name with this subcommand.')
                return
            if 'm' in flags:
                hats = [i.strip() for i in ' '.join(arg_lst).lower().split(',')]
            else:
                hats = [arg_lst.pop(0).lower()]
            for new_hat in hats:
                if new_hat in this_guild:
                    await ctx.send(f'**Error:** Hat with name *{new_hat}* already exists in this guild.')
                    continue
                this_guild[new_hat] = []
            await self.store_json()
        elif command in ('p', 'pop'):
            if hat_name not in this_guild:
                await ctx.send(f'**Error:** No hat with name *{hat_name}* found in this guild.')
                return
            if not this_guild[hat_name]:
                await ctx.send(f'**Error:** Hat with name *{hat_name}* is empty, no element can be chosen.')
            hat_draw = this_guild[hat_name].pop(randint(0, len(this_guild[hat_name])))
            await self.store_json()
            await ctx.send(f'I have randomly selected **{hat_draw}** from the hat!')
        elif command in ('v', 'view'):
            if not arg_lst:
                this_hat = 'main'
            else:
                this_hat = arg_lst.pop(0).lower()
            if this_hat not in this_guild:
                await ctx.send(f'**Error**: No hat with name {this_hat} found in this guild.')
                return
            await ctx.send(f'**Elements in {this_hat}**:\n{", ".join(this_guild[this_hat])}')

    # Called if $hat encounters an unhandled exception
    @hat.error
    async def hat_error(self, ctx, error):
        if isinstance(error, commands.errors.MissingRequiredArgument):
            await ctx.send('You must include a subcommand to use with $hat.\n'
                           'Example: `$hat add Moonfall`\n\n'
                           'Please use `$help hat` for more information.')
        else:
            print(f'$hat command failed with error:\n\n{error}')

    async def store_json(self):
        with open('./hat.json', 'w') as outFile:
            dump(self.hat_store, outFile, indent=2)

    @tasks.loop(hours=1)
    async def daily_fact(self):
        current_time = datetime.now()
        if current_time.hour != 13:
            return
        await self.ch_general.send(f'**The fact of the day is:**\n{get_fact(filter_enabled=False)}')

    @daily_fact.before_loop
    async def before_daily_fact(self):
        await self.bot.wait_until_ready()
        print('Starting Daily Fact hourly loop.')
        self.ch_general = self.guild.get_channel(main_channel)
        if self.ch_general is None:
            print('WARNING: General channel not found. Loop not started.\n')
            self.daily_fact.cancel()
            return
        print('Loop successfully started!\n')

    @commands.command(help='Returns a randomly selected fact',
                      brief='Returns a random fact')
    async def fact(self, ctx):
        await ctx.send(get_fact(filter_enabled=False))

    @commands.command(help='Returns a randomly selected NSFW fact',
                      brief='Returns a random NSFW fact',
                      aliases=['nsfwfact', 'nsfw_fact'])
    async def fact_nsfw(self, ctx):
        await ctx.send(get_fact(only_unsafe=True))

    # $flip command sends either "heads" or "tails" in the channel
    @commands.command(help='Returns either "heads" or "tails" via random selection.',
                      brief='Returns either "heads" or "tails"')
    async def flip(self, ctx):
        await ctx.send(choice(('heads', 'tails')))

    # $number command used to generate a random integer within a given range
    @commands.command(help='Returns a randomly chosen number between two given integers\n'
                           'Example: `$number 1 10`\n\n'
                           'If only one integer is given, '
                           'then a number between 1 and that integer will be chosen\n'
                           'Example: `$number 10`',
                      brief='Returns a random number')
    async def number(self, ctx, lower: int, upper: int = None):
        if upper is None:
                lower, upper = 1, lower
        await ctx.send(randint(lower, upper))

    # Called if $number encounters an unhandled exception
    @number.error
    async def number_error(self, ctx, error):
        if isinstance(error, commands.errors.MissingRequiredArgument):
            await ctx.send('You must include at least 1 integer to serve as an upper bound\n'
                           'Example: `$number 4`2\n\n'
                           'Please use `$help number` for more information.')
        elif isinstance(error, commands.errors.BadArgument):
            await ctx.send('Bad argument, use only integers with this command.\n\n'
                           'Please use `$help number` for more information.')
        else:
            print(f'$number command failed with error:\n\n{error}')

    # $choice command used to randomly select one item from a list
    # param arg - all user input following command-name
    @commands.command(help='Returns 1 chosen item from a given list\n'
                           'The list can be of any size, with each item seperated by a comma\n'
                           'Example: `$choice Captain Kirk, Captain Picard, Admiral Adama`',
                      brief='Returns 1 randomly chosen item')
    async def choice(self, ctx, *, arg):
        await ctx.send(choice([item.strip() for item in arg.split(',') if item]))

    # Called if $choice encounters an unhandled exception
    @choice.error
    async def choice_error(self, ctx, error):
        if isinstance(error, commands.errors.MissingRequiredArgument):
            await ctx.send('You must include a comma-seperated list of items.\n'
                           'Example: `$choice me, myself, I`\n\n'
                           'Please use `$help choice` for more information.')
        else:
            print(f'$choice command failed with error:\n\n{error}')

    # $roll command used to simulate the rolling of dice
    # param dice - string representing dice to be rolled in xDn format
    @commands.command(help='Rolls any number of n-sided dice in the classic "xDn"" format\n'
                           'Where *x* is the quantity of dice being rolled, '
                           'and *n* is the number of sides on the die\n'
                           'Example: `$roll 3d20`',
                      brief='Rolls dice in the classic "xDn" format')
    async def roll(self, ctx, dice):
        try:
            # Remove spaces from the input, and split it at the character "d", then cast to int
            quantity, size = dice.lower().replace(' ', '').split('d')
            quantity, size = int(quantity), int(size)
        except ValueError:
            await ctx.send('Please format your dice in the classic "xDy" style. '
                           'For example, 1d20 rolls one 20-sided die.')
            return
        if quantity < 1 or size < 1:
            await ctx.send('Please use only positive integers for dice quantity and number of sides')
            return
        roll_list = []
        total = 0
        for i in range(quantity):
            roll = randint(1, size)
            total += roll
            roll_list.append(f'Roll #{i+1}: {roll}')
        roll_list.append(f'**Total:** {total}')
        await ctx.send('\n'.join(roll_list))
