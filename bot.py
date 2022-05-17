# Main starting file for BUSTER.
# This file creates the Bot object, loads the cogs, and starts the event loop

from discord.ext import commands
from dotenv import load_dotenv
from os import getenv
import discord

# env must be loaded before importing ./cogs.py
load_dotenv()
TOKEN = getenv('DISCORD_TOKEN')  # API token for the bot
GUILD = getenv('DISCORD_GUILD')  # ID of desired guild for bot to interact with
if TOKEN is None or GUILD is None:
    exit('Environment file missing/corrupted. Halting now!')

# Local dependencies
from cogs import add_cogs
from help_command import CustomHelpCommand

bot = commands.Bot(command_prefix='$', help_command=CustomHelpCommand(), intents=discord.Intents.all())

# Runs when bot has successfully logged in
# Note: This can and will be called multiple times during the bot's up-times
@bot.event
async def on_ready():
    my_guild = discord.utils.get(bot.guilds, name=GUILD)

    # Only add cogs if no cogs are currently present on the bot
    # This prevents the recurring CommandRegistrationError exception
    if not bot.cogs:
        add_cogs(bot, my_guild)

    for guild in bot.guilds:
        print(f'{bot.user} is connected to the following guild:\n'
              f'{guild.name} (ID: {guild.id})\n'
              f'Guild Members: {len(guild.members)}\n\n')

# Begin the bot's event loop
bot.run(TOKEN)
