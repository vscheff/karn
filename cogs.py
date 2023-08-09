# Common collection space for all of the bots cogs
# This file imports the cogs from each file and adds them to the bot

# Local dependencies
from Cogs.Cards import Cards
from Cogs.Dictionary import Dictionary
from Cogs.hat import hat
from Cogs.Random import Random
from Cogs.Search import Search
from Cogs.Utility import Utility
from Cogs.Weather import Weather
from Cogs.Wikipedia import Wikipedia

# Adds each cogs to the bot, this is called once the bot is ready for the first time
# param   bot - commands.Bot object containing our client
# param guild - discord.Guild object containing the target server
def add_cogs(bot, guild):
    bot.add_cog(Cards())
    bot.add_cog(Dictionary(bot, guild))
    bot.add_cog(Random(bot, guild))
    bot.add_cog(Search())
    bot.add_cog(Utility(bot))
    bot.add_cog(Weather())
    bot.add_cog(Wikipedia())

    bot.add_command(hat)
