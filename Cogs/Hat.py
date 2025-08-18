from discord.ext.commands import Cog, command, MissingRequiredArgument
from random import randint

from utils import get_cursor, get_flags, package_message


DEFAULT_HAT = "main"


class Hat(Cog):
    def __init__(self, conn):
        self.conn = conn

    @command(help="Add an item to the hat.\n"
                  "Example: `$add The Room`\n\n"
                  "This command has the following flags:\n"
                  "* **-h**: Used to specify a hat other than the channel's default hat.\n"
                  "\tExample: `$add -h movies Troll 2`\n"
                  "* **-m**: Indicates your subcommand argument is a comma-seperated list of elements.\n"
                  "\tExample: `$add -m Monster a Go-Go, Birdemic, Batman & Robin`",
             brief="Add an item to the hat")
    async def add(self, ctx, *, args):
        cursor = get_cursor(self.conn)

        flags, arg = get_flags(args)
        hat = get_hat(flags, arg, cursor, ctx.channel.id)

        items = [i.strip() for i in ' '.join(arg).split(',')] if 'm' in flags else [' '.join(arg)]

        for item in items:
            cursor.execute("INSERT INTO Hat (guild_id, hat_name, item) VALUES (%s, %s, %s)", [ctx.guild.id, hat, item])

        await ctx.send(f"Successfully added {len(items)} item(s) to **{hat}**.")

        self.conn.commit()
        cursor.close()

    @add.error
    async def add_error(self, ctx, error):
        if isinstance(error, MissingRequiredArgument):
            await ctx.send("You must include an item to add to the hat.\n"
                           "Example: `$add Moonfall`\n\n"
                           "Please use `$help add` for more information.")

    @command(help="Clear all items from the hat.\n\n"
                  "To clear a hat other than the channel's default hat, include it as an argument:\n"
                  "Example: `$clear movies`",
             brief="Clear all items from the hat")
    async def clear(self, ctx, hat=None):
        cursor = get_cursor(self.conn)

        hat = hat if hat else get_hat([], [], cursor, ctx.channel.id)

        cursor.execute("DELETE FROM Hat WHERE guild_id = %s AND hat_name = %s", [ctx.guild.id, hat])

        await ctx.send(f"Deleted {cursor.rowcount} items from **{hat}**.")

        self.conn.commit()
        cursor.close()

    @command(help="List all active hats for this server.\n\n",
             brief="List all active hats for this server")
    async def list(self, ctx):
        cursor = get_cursor(self.conn)

        cursor.execute("SELECT DISTINCT hat_name FROM Hat WHERE guild_id = %s", [ctx.guild.id])

        if not (result := cursor.fetchall()):
            await ctx.send(f"No active hats found for this server. Try using the `$add` command first!")
        else:
            await ctx.send("* " + "\n* ".join(i[0] for i in result))

        cursor.close()

    @command(help="Randomly picks an item from the hat.\n\n"
                  "To pick more than one item, include the desired number of items as an argument:\n"
                  "Example: `$pick 3`\n\n"
                  "This command has the following flags:\n"
                  "* **-h**: Used to specify a hat other than the channel's default hat.\n"
                  "\tExample: `$pick -h movies`\n",
             brief="Pick an item from the hat")
    async def pick(self, ctx, *, args=None):
        await self.choose(ctx, args, False)

    @command(help="Randomly chose and remove an item from the hat.\n\n"
                  "To pop more than one item, include the desired number of items as an argument:\n"
                  "Example: `$pop 3`\n\n"
                  "This command has the following flags:\n"
                  "* **-h**: Used to specify a hat other than the channel's default hat.\n"
                  "\tExample: `$pop -h movies`\n",
             brief="Pick and remove an item from the hat")
    async def pop(self, ctx, *, args=None):
        await self.choose(ctx, args, True)

    async def choose(self, ctx, args, delete):
        cursor = get_cursor(self.conn)

        if args:
            flags, arg = get_flags(args)
            hat = get_hat(flags, arg, cursor, ctx.channel.id)
            if arg:
                try:
                    num = int(arg.pop(0))
                except ValueError:
                    cursor.close()
                    await ctx.send("Invalid argument, please only use integer values!")
                    return None
            else:
                num = 1
        else:
            hat = DEFAULT_HAT
            num = 1

        cursor.execute("SELECT item FROM Hat WHERE guild_id = %s AND hat_name = %s", [ctx.guild.id, hat])

        if not (result := cursor.fetchall()):
            cursor.close()
            await ctx.send(f"No items found in \"{hat}\". Try using the `$add` command first!")
            return None

        if num > len(result):
            cursor.close()
            await ctx.send(f"Not enough items in **{hat}**. Try adding more items, or select a smaller amount!")
            return None

        choices = []
        for _ in range(num):
            choices.append(result.pop(randint(0, len(result) - 1))[0])

        if num == 1:
            await ctx.send(choices[0])
        else:
            await ctx.send("* " + "\n* ".join(choices))

        if delete:
            values = [ctx.guild.id, hat, None]
            for item in choices:
                values[2] = item
                cursor.execute("DELETE FROM Hat WHERE guild_id = %s and hat_name = %s and item = %s", values)

        self.conn.commit()
        cursor.close()

    @command(help="Remove an item from the hat.\n"
                  "Example: `$remove 3`\n"
                  "To view the indexes for a hat, use the `$view` command.\n\n"
                  "This command has the following flags:\n"
                  "* **-h**: Used to specify a hat other than the channel's default hat.\n"
                  "\tExample: `$remove -h movies 3`\n",
             brief="Remove an item from the hat")
    async def remove(self, ctx, *, args):
        cursor = get_cursor(self.conn)
        flags, arg = get_flags(args)
        hat = get_hat(flags, arg, cursor, ctx.channel.id)

        if not arg:
            await ctx.send(f"You must include an index to remove. Use `$view` to see the indexes.")
            cursor.close()
            return

        try:
            index = int(arg[0])
        except ValueError:
            await ctx.send("Invalid argument, please only use integer values.\n"
                           "Example: `$remove 3`\n\n"
                           "Use`$help remove` for more information.")
            cursor.close()
            return

        cursor.execute("SELECT item FROM Hat WHERE guild_id = %s AND hat_name = %s", [ctx.guild.id, hat])

        if not (result := cursor.fetchall()):
            await ctx.send(f"No items found in \"{hat}\". Try using the `$add` command first!")
        elif index < 1 or index > len(result):
            await ctx.send(f"Invalid index, please use an integer in the range [1, {len(result)}]")
        else:
            removed = result.pop(index - 1)
            values = [ctx.guild.id, hat, removed[0]]
            cursor.execute("DELETE FROM Hat WHERE guild_id = %s AND hat_name = %s AND item = %s", values)
            await ctx.send(f"Successfully removed \"*{removed[0]}*\" from **{hat}**.")

        self.conn.commit()
        cursor.close()

    @remove.error
    async def remove_error(self, ctx, error):
        if isinstance(error, MissingRequiredArgument):
            await ctx.send("You must include an index to remove from the hat.\n"
                           "Example: `$remove 3`\n\n"
                           "Please use `$help remove` for more information.")

    @command(help="View all items in the hat.\n\n"
                  "To view a hat other than the channel's default hat, include it as an argument:\n"
                  "Example: `$view movies`",
             brief="View all items from the hat")
    async def view(self, ctx, hat=None):
        cursor = get_cursor(self.conn)

        hat = hat if hat else get_hat([], [], cursor, ctx.channel.id)

        cursor.execute("SELECT item FROM Hat WHERE guild_id = %s AND hat_name = %s", [ctx.guild.id, hat])

        if not (result := cursor.fetchall()):
            await ctx.send(f"No items found in \"{hat}\". Try using the `$add` command first!")
        else:
            message = f"# {hat}\n" + '\n'.join(f"{i[1]}. {i[0][0]}" for i in zip(result, range(1, len(result) + 1)))
            await package_message(message, ctx, multi_send=True)

        cursor.close()

    @command(help="Set the default hat for this channel.\n"
                  "Example: `$set_default movies`",
             brief="Set the default hat")
    async def set_default(self, ctx, hat=DEFAULT_HAT):
        cursor = get_cursor(self.conn)

        cursor.execute("DELETE FROM Channels WHERE channel_id = %s", [ctx.channel.id])
        cursor.execute("INSERT INTO Channels (channel_id, default_hat) VALUES (%s, %s)", [ctx.channel.id, hat])

        await ctx.send(f"Successfully set **{hat}** as the default hat for {ctx.channel.name}!")

        self.conn.commit()
        cursor.close()

def get_hat(flags, arg, cursor, channel_id):
    if 'h' in flags:
        return arg.pop(0)

    cursor.execute("SELECT default_hat FROM Channels WHERE channel_id = %s", [channel_id])

    if not (result := cursor.fetchall()):
        cursor.execute("INSERT INTO Channels (default_hat, channel_id) VALUES(%s, %s)", [DEFAULT_HAT, channel_id])
        return DEFAULT_HAT
    else:
        return result[0][0]
