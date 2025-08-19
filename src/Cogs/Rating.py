from discord.ext.commands import Cog, command, errors
from re import findall

from src.utils import get_cursor, package_message


DEFAULT_RATING_COUNT = 5


class Rating(Cog):
    def __init__(self, conn):
        self.conn = conn

    @command(help=f"Returns the least voted items\n\n"
                  f"Include an integer argument to specify the number of "
                  f"results to return (default={DEFAULT_RATING_COUNT})\n"
                  f"Example: `$bot 3`",
             brief="Show the least voted items")
    async def bot(self, ctx, num=DEFAULT_RATING_COUNT):
        await self.send_ratings(ctx, num, False)

    @command(help="Returns the top voted items\n\n"
                  f"Include an integer argument to specify the number of "
                  f"results to return (default={DEFAULT_RATING_COUNT})\n"
                  f"Example: `$top 3`",
             brief="Show the top voted items",
             aliases=["scores"])
    async def top(self, ctx, num=DEFAULT_RATING_COUNT):
        await self.send_ratings(ctx, num, True)

    async def send_ratings(self, ctx, num, reverse):
        cursor = get_cursor(self.conn)

        cursor.execute("SELECT name, score FROM Rating WHERE guild_id = %s", [ctx.guild.id])

        if not (results := sorted(cursor.fetchall(), key=lambda x: x[1], reverse=reverse)):
            return await ctx.send("No scores exist for this guild. Try adding `++` to any item you'd like to upvote!")

        msg = '\n'.join(f"{j}. *{i[0]}* **[{i[1]}]**" for i, j in zip(results[:num], range(1, num + 1)))
        await package_message(msg, ctx)

    @bot.error
    async def bot_error(self, ctx, error):
        if isinstance(error, errors.BadArgument):
            await ctx.send("Bad argument, use only integers with this command.\n\n"
                           "Please use `$help bot` for more information.")

    @top.error
    async def top_error(self, ctx, error):
        if isinstance(error, errors.BadArgument):
            await ctx.send("Bad argument, use only integers with this command.\n\n"
                           "Please use `$help top` for more information.")

    @command(help="Show the score for a given item.\n"
                  "Example: `$show linux`",
             brief="Show the score for an item")
    async def show(self, ctx, *, args):
        if not args:
            return await ctx.send("You must include an item with this command.\n\n"
                                  "Please use `$help show` for more information.")

        cursor = get_cursor(self.conn)
        cursor.execute("SELECT score FROM Rating WHERE name = %s AND guild_id = %s", [args, ctx.guild.id])

        if not (result := cursor.fetchall()):
            await ctx.send(f"No score exists for \"{args}\". Try using `--` or `++` to vote for this item first.")
        else:
            await ctx.send(f"*{args}* **[{result[0][0]}]**")

        cursor.close()

    def rate_listener(self, msg):
        # https://regex101.com/r/s8gfoV/5
        matches = findall(r"\([\w\s']+\)(?:\+\+|--)|[\w]+(?:\+\+|--)", msg.content)

        if not matches:
            return

        cursor = get_cursor(self.conn)

        for match in matches:
            positive = match[-1] == '+'
            name = match[:-2].strip("()").lower()
            cursor.execute("SELECT score FROM Rating WHERE name = %s AND guild_id = %s", [name, msg.guild.id])

            if not (result := cursor.fetchall()):
                val = [name, 1 if positive else -1, msg.guild.id]
                cursor.execute("INSERT INTO Rating (name, score, guild_id) VALUES (%s, %s, %s)", val)
            else:
                val = [result[0][0] + (1 if positive else -1), name, msg.guild.id]
                cursor.execute("UPDATE Rating SET score = %s WHERE name = %s AND guild_id = %s", val)

        self.conn.commit()
        cursor.close()
