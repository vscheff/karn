# Common collection space for all of the bots cogs
# This file imports the cogs from each file and adds them to the bot

# Local dependencies
from Cogs.DailyLoop import DailyLoop
from Cogs.hat import hat
from Cogs.Query import Query
from Cogs.Random import Random
from Cogs.Utility import Utility

# Adds each cogs to the bot, this is called once the bot is ready for the first time
# param   bot - commands.Bot object containing our client
# param guild - discord.Guild object containing the target server
async def add_cogs(bot, guild):
    await bot.add_cog(DailyLoop(bot, guild))
    await bot.add_cog(Query())
    await bot.add_cog(Random(bot, guild))
    await bot.add_cog(Utility(bot))

    bot.add_command(hat)
