# Common collection space for all of the bots cogs
# This file imports the cogs from each file and adds them to the bot

# Local dependencies
from src.help_command import SlashHelp
from src.Cogs.AI import AI
from src.Cogs.DailyLoop import DailyLoop
from src.Cogs.Games import Games
from src.Cogs.Hat import Hat
from src.Cogs.Query import Query
from src.Cogs.Random import Random
from src.Cogs.Rating import Rating
from src.Cogs.Terminal import Terminal
from src.Cogs.Utility import Utility

# Adds each cogs to the bot, this is called once the bot is ready for the first time
# param   bot - commands.Bot object containing our client
# param guild - discord.Guild object containing the target server
async def add_cogs(bot, conn):
    await bot.add_cog(SlashHelp(bot))
    await bot.add_cog(AI(bot, conn))
    await bot.add_cog(DailyLoop(bot, conn))
    await bot.add_cog(Games())
    await bot.add_cog(Hat(conn))
    await bot.add_cog(Query())
    await bot.add_cog(Random(bot))
    await bot.add_cog(Rating(conn))
    await bot.add_cog(Terminal())
    await bot.add_cog(Utility(bot))
