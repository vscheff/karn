from discord.ext import commands
from json import dump, load
from re import findall
from random import randint

from utils import package_message

HAT_FILEPATH = "./hat.json"

with open(HAT_FILEPATH, 'r') as inFile:
    hat_store = load(inFile)

def check_id(guild_id):
                            
    if guild_id not in hat_store:
        hat_store[guild_id] = {"hats": {"main": []}, "filters": {}}
        store_json()

def store_json():
    with open(HAT_FILEPATH, 'w') as outFile:
        dump(hat_store, outFile, indent=2)

async def hat_listener(msg, bot_id):
    g_id = str(msg.guild.id)
    check_id(g_id)
    this_guild = hat_store[g_id]["filters"]
    if msg.channel.name in this_guild and msg.author.id != bot_id:
        for filter_str in this_guild[msg.channel.name]:
            if match := list(findall(filter_str, msg.content)):
                hat_store[g_id]["hats"][this_guild[msg.channel.name][filter_str]].extend(match)
                store_json()

@commands.command(help="Use this command to interface with the hat pick system.\n"
                       "Usage: `$hat <subcommand> [-flags] [flag arg] <subcommand arg>`\n\n\n"
                       "This command is broken up into the following subcommands:\n\n"
                       "**Add**: Adds an element to the *main* hat.\n"
                       "Example: `$hat add Moonfall`\n\n"
                       "**Choice**: Randomly chooses one element from the *main* hat.\n\n"
                       "**clEar**: Clears all elements from the *main* hat.\n\n"
                       "**Delete**: Deletes a specified hat.\n"
                       "Example: `$hat delete enemies`\n\n"
                       "**Import**: Bulk add elements from current text channel that match given a filter string.\n"
                       "Example: `$hat import \"https://www.imdb.com/\S+\"`\n\n"
                       "**List**: Lists the active hats for this server.\n\n"
                       "**New**: Creates a new a hat.\n"
                       "Example: `$hat new cards`\n\n"
                       "**Pop**: Randomly chooses and removes one element from the *main* hat.\n\n"
                       "**View**: View all elements in the *main* hat\n\n"
                       "**Watch**: Listens to a text channel for elements matching a given filter string\n"
                       "Example: `$hat watch \"\S*www\.\S+\.com\S*\"`\n\n\n"
                       "This command has the following flags:\n\n"
                       "**-c**: Used to specify a channel other than than the context channel.\n"
                       "Example: `$hat import -c general \"www.\S+.com\"`\n\n"
                       "**-h**: Used to specify a hat other than *main*.\n"
                       "Example: `$hat add -h movies Troll 2`\n\n"
                       "**-m**: Indicates your subcommand argument is a comma-seperated list of elements.\n"
                       "Example: `$hat add -m Monster a Go-Go, Birdemic, Batman & Robin`",
                  brief="Interface with the hat pick system")
async def hat(ctx, *, arg):
    check_id(str(ctx.guild.id))
    this_guild = hat_store[str(ctx.guild.id)]["hats"]
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
                break
        for _ in range(flg_args):
            arg_lst.pop(0)

    hat_name = "main" if 'h' not in flags else arg_lst.pop(0)
    if hat_name not in this_guild:
        await ctx.send(f"**Error:** No hat with name *{hat_name}* found in this guild.")
        return

    if command in ('c', "choice", "pick", "choose", "chose"):
        if not this_guild[hat_name]:
            await ctx.send(f"**Error:** Hat with name *{hat_name}* is empty, no element can be chosen.")
            return
        hat_draw = this_guild[hat_name][randint(0, len(this_guild[hat_name])-1)]
        await ctx.send(f"I have randomly selected **{hat_draw}** from the hat!")
        return

    if command in ('e', "clear"):
        this_guild[hat_name] = []
        store_json()
        return

    if command in ('h', "help"):
        await ctx.send(hat.help)
        return

    if command in ('l', "list"):
        hats = '\n'.join([i for i in this_guild])
        await ctx.send(f"**HATS**\n{hats}")
        return

    if command in ('p', "pop"):
        if not this_guild[hat_name]:
            await ctx.send(f"**Error:** Hat with name *{hat_name}* is empty, no element can be removed.")
            return
        hat_draw = this_guild[hat_name].pop(randint(0, len(this_guild[hat_name])-1))
        await ctx.send(f"I have randomly removed **{hat_draw}** from the hat!")
        store_json()
        return

    if command in ('v', "view"):
        await ctx.send(f"**{len(this_guild[hat_name])} Elements in {hat_name}**:")
        if this_guild[hat_name]:
            await package_message('\n'.join(this_guild[hat_name]), ctx)
        return

    if not arg_lst:
        await ctx.send("**Error:** You must include at least one subcommand argument.\n"
                       "Please use `$help hat` for more usage information.")
        return

    if 'c' in flags:
        target_channel = arg_lst.pop(0).lower()
        if not arg_lst:
            await ctx.send("**Error:** You must include a channel name when using the -c flag.")
            return
        channel = list(filter(lambda x: x.name == target_channel, ctx.guild.text_channels))
        if not channel:
            await ctx.send(f"**Error:** Channel with name *{target_channel}* not found in this guild.")
            return
        channel = channel[0]
    else:
        channel = ctx.channel

    if command in ('i', "import"):
        filter_string = ' '.join(arg_lst).strip("'\"")
        matched_messages = []
        async for message in channel.history(limit=None):
            if message == ctx.message:
                continue
            matched_messages.extend(findall(filter_string, message.content))
        this_guild[hat_name].extend(matched_messages)
        await ctx.send(f"Added {len(matched_messages)} elements found in {channel.name} "
                       f"matching \"{filter_string}\" to *{hat_name}*.")
        store_json()
        return

    if command in ('w', "watch"):
        filter_string = ' '.join(arg_lst).strip("'\"")
        filters = hat_store[str(ctx.guild.id)]["filters"]
        if channel.name not in filters:
            filters[channel.name] = {}
        filters[channel.name][filter_string] = hat_name
        await ctx.send(f"Now listening to {channel.name} for elements matching \"{filter_string}\".\n"
                       f"Adding elements to *{hat_name}*.")
        store_json()
        return

    if 'm' in flags:
        args = ' '.join(arg_lst).split(',')
    else:
        args = [' '.join(arg_lst)]

    if command in ('a', "add"):
        this_guild[hat_name].extend(args)
        store_json()
        return

    if command in ('d', "delete"):
        for arg in [i.strip().lower() for i in args]:
            if arg not in this_guild:
                await ctx.send(f"**Error**: No hat with name *{arg}* found in this guild.")
                continue
            if arg == "main":
                await ctx.send(f"**Error**: Unable to delete *main* hat, trying clearing it instead.")
                continue
            this_guild.pop(arg)
        store_json()
        return

    if command in ('n', "new"):
        for arg in [i.strip().lower() for i in args]:
            if arg in this_guild:
                await ctx.send(f"**Error:** Hat with name *{arg}* already exists in this guild.")
                continue
            this_guild[arg] = []
        store_json()
        return

    await ctx.send(f"**Error**: Unknown hat command *{command}*")

# Called if $hat encounters an unhandled exception
@hat.error
async def hat_error(ctx, error):
    if isinstance(error, commands.errors.MissingRequiredArgument):
        await ctx.send("You must include a subcommand to use with $hat.\n"
                       "Example: `$hat add Moonfall`\n\n"
                       "Please use `$help hat` for more information.")
