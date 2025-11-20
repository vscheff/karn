# Main starting file for Karn
# This file creates the Bot object, loads the cogs, and starts the event loop

import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv
from mysql.connector.errors import InterfaceError
from os import getenv
from random import choice

# env must be loaded before importing ./cogs.py
load_dotenv()
TOKEN = getenv("DISCORD_TOKEN")  # API token for the bot
if TOKEN is None:
    exit("Environment file missing/corrupted. Halting now!")

# Local dependencies
from src.cogs import add_cogs
from src.activities import activities
from src.Cogs.Terminal import send_line
from src.help_command import CustomHelpCommand
from src.sql import connect_to_sql_database
from src.utils import make_guild_dir

activity = discord.Activity(type=discord.ActivityType.streaming,
                            name="",
                            state="Listening for $help"
                           )

bot = commands.Bot(command_prefix='$',
                   case_insensitive=True,
                   help_command=CustomHelpCommand(),
                   intents=discord.Intents.all(),
                   activity=activity)

# Add brief help text for the help command
next(filter(lambda x: x.name == "help", bot.commands)).brief = "Shows this message"

try:
    sql_connection = connect_to_sql_database()
except InterfaceError:
    exit("Database connection failed.\nPlease ensure your .env file is correct.")


# Runs when bot has successfully logged in
# Note: This can and will be called multiple times during the bot's up-times
@bot.event
async def on_ready():
    # Only add cogs if no cogs are currently present on the bot
    # This prevents the recurring CommandRegistrationError exception
    if not bot.cogs:
        await add_cogs(bot, sql_connection)
        change_activity.start()

    print(f"\n{bot.user} is connected to the following guild(s):\n")
    for guild in bot.guilds:
        print(f"{guild.name} (ID: {guild.id})\nGuild Members: {len(guild.members)}\n")

    await bot.tree.sync()

@tasks.loop(hours=1)
async def change_activity():
    activity.name = choice(activities)
    await bot.change_presence(activity=activity)

@bot.event
async def on_guild_join(guild):
    make_guild_dir(guild.id)

@bot.event
async def on_message(msg):
    if msg.author.bot or not msg.content:
        return

    if msg.content[0] == bot.command_prefix:
        return await bot.process_commands(msg)
    
    if not await send_line(msg, bot):
        if not await bot.get_cog("Games").wordle_listener(msg):
            await bot.get_cog("AI").send_reply(msg)

    bot.get_cog("Rating").rate_listener(msg)

@bot.event
async def on_command_error(ctx, error):
    if hasattr(error, "handled") and error.handled:
        return

    try:
        author = f"{ctx.author} (a.k.a. {ctx.author.nick})"
    except AttributeError:
        author = f"{ctx.author}"

    print(f"\nCommand error triggered\n"
          f"\t Author: {author}\n"
          f"\t  Guild: {ctx.guild}\n"
          f"\tChannel: {ctx.message.channel}\n"
          f"\tMessage: {ctx.message.content}\n"
          f"Error:\n{error}")


# Begin the bot's event loop
bot.run(TOKEN)
