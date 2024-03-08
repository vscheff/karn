# Common collection space for all of the bots cogs
# This file imports the cogs from each file and adds them to the bot

# Local dependencies
from Cogs.AI import AI
from Cogs.DailyLoop import DailyLoop
from Cogs.Games import Games
from Cogs.Hat import Hat
from Cogs.Query import Query
from Cogs.Random import Random
from Cogs.Rating import Rating
from Cogs.Terminal import Terminal
from Cogs.Utility import Utility

# Adds each cogs to the bot, this is called once the bot is ready for the first time
# param   bot - commands.Bot object containing our client
# param guild - discord.Guild object containing the target server
async def add_cogs(bot, conn):
    await bot.add_cog(AI(bot, conn))
    await bot.add_cog(DailyLoop(bot, conn))
    await bot.add_cog(Games())
    await bot.add_cog(Hat(conn))
    await bot.add_cog(Query())
    await bot.add_cog(Random(bot))
    await bot.add_cog(Rating(conn))
    await bot.add_cog(Utility(bot))
    await bot.add_cog(Terminal())
