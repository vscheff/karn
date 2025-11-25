# Cog that holds all commands related to server/bot utility

from discord.ext.commands import Bot, Cog, command, errors, has_permissions, hybrid_command
from datetime import datetime, timedelta
import discord
import os
import qrcode
from re import findall

from src.utils import TEMP_DIR
from src.utils import get_as_number, get_flags, get_id_from_mention, is_slash_command, package_message

# Filename/path for temporary storage of QR image
QR_FILEPATH = f"{TEMP_DIR}/temp_qr.png"


class Utility(Cog):

    # attr bot - our client
    def __init__(self, bot: Bot):
        self.bot = bot

    # $qr command used to generate QR code images
    # param arg - all user input following command-name
    @hybrid_command(help="Generate a QR code for input data\nExample: `$qr https://www.gnu.org/`",
                    brief="Generate a QR code")
    async def qr(self, ctx, *, data: str, hidden: bool=False):
        img = make_qr(data)
        img.save(QR_FILEPATH)

        if os.path.exists(QR_FILEPATH):
            await ctx.send(file=discord.File(QR_FILEPATH), ephemeral=hidden)
            os.remove(QR_FILEPATH)
        else:
            print("Error occurred while generating QR code. Temp file not created/deleted.")

    # Called if $qr encounters an unhandled exception
    @qr.error
    async def qr_error(self, ctx, error):
        if isinstance(error, errors.MissingRequiredArgument):
            await ctx.send("You must include a string of data with this command.\n"
                           "Example: `$qr https://www.linux.org/`"
                           "Please use `$help qr` for more information.")
            error.handled = True

    # $ping command used to test bot readiness and latency
    @hybrid_command(help="Returns \"pong\" and the round-trip latency if the bot is online.",
                    brief="Returns \"pong\" if the bot is online.")
    async def ping(self, ctx):
        await ctx.send(f"pong (*{self.bot.latency * 1000:.0f}ms*)")

    # $calc command used for calculating the result of mathematical expressions
    # param args - all user input following the command name
    @hybrid_command(help="Returns the result of a mathematical expression.\n"
                         "Example: `$calc 6 * 7`",
                    brief="Calculates the result of a mathematical expression")
    async def calc(self, ctx, *, expression:str):
        prec = {'+': 0, '-': 0, '*': 1, '/': 1, '^': 2}

        # https://regex101.com/r/rYoPQz/1
        tokens = findall(r"-?\d+\.?\d*|[+\-/*()^]", ''.join(expression))
        values, ops = [], []

        # Shunting Yard alrorithm
        for token in tokens:
            if (result := get_as_number(token)) is not False:
                values.append(result)
            elif token == '(':
                ops.append(token)
            elif token == ')':
                while ops and ops[-1] != '(':
                    apply_operator(ops, values)

                ops.pop()
            else:
                while ops and ops[-1] not in "()" and prec[ops[-1]] > prec[token]:
                    apply_operator(ops, values)

                ops.append(token)

        while ops:
            apply_operator(ops, values)

        await ctx.send(values[0])

    @calc.error
    async def calc_error(self, ctx, error):
        if isinstance(error, errors.CommandInvokeError):
            if isinstance(error.original, IndexError):
                await ctx.send("Unable to calculate result. "
                               "Please ensure your input is a valid mathematical equation.")
                error.handled = True
            elif isinstance(error.original, ZeroDivisionError):
                await ctx.send("Division by zero! Unable to calculate result.")
                error.handled = True
        elif isinstance(error, errors.MissingRequiredArgument):
            await ctx.send("You must include a mathematical expression with this command.\nPlease use `$help calc` for more information.")
            error.handled = True

    # $ready command used as a "all-systems-go" check for the bot
    @hybrid_command(help="Performs an \"All-Systems-Go\" check for the bot, and returns a status report.",
                    brief="Check for \"All-Systems-Go\"")
    async def ready(self, ctx):
        await ctx.send(f"Websocket closed: {self.bot.is_closed()}\n"
                       f"Internal cache ready: {self.bot.is_ready()}\n"
                       f"Websocket rate limited: {self.bot.is_ws_ratelimited()}",
                       ephemeral=True)

    # $purge command used to bulk delete messages from a text channel
    # param before - int representing the number of days, before which messages will be deleted
    # param  after - int representing the number of days, before which messages will NOT be deleted
    @hybrid_command(help="Delete all messages in a channel older than a given number of days.\n"
                         "Example: `$purge 3`\n"
                         "That command will delete all messages older than 3 days.\n\n"
                         "Alternatively, you can include two integers to declare a range.\n"
                         "Example: `$purge 3 42`\n"
                         "That command will delete all messages older than 3 days, "
                         "but not older than 42 days.\n\n",
                    brief="Bulk delete messages in current channel")
    @has_permissions(manage_messages=True)
    async def purge(self, ctx, before: int, after: int = None):
        del_before = datetime.now() - timedelta(days=before)
        
        if after is None:
            await ctx.send(f"Deleting messages sent before **{del_before.isoformat(' ', 'minutes')}**", ephemeral=True)
            deleted = await ctx.channel.purge(before=del_before, bulk=True)
        else:
            if after <= before:
                await ctx.send("Bad argument, second given integer must be larger than the first.")
                return
            
            # Subtract the remaining days to get the lower-limit
            del_after = del_before - timedelta(days=after - before)
            await ctx.send(f"Deleting messages between **{del_after.isoformat(' ', 'minutes')}** "
                           f"and **{del_before.isoformat(' ', 'minutes')}**.", ephemeral=True)
            deleted = await ctx.channel.purge(before=del_before, after=del_after, bulk=True)
        
        await ctx.send(f"Successfully deleted {len(deleted)} messages from this channel!", ephemeral=True)

    # Called if $purge encounters an unhandled exception
    @purge.error
    async def purge_error(self, ctx, error):
        error.handled = True

        if isinstance(error, errors.MissingPermissions):
            await ctx.send("You lack the required permissions to execute this command.")
        elif isinstance(error, errors.MissingRequiredArgument):
            await ctx.send("You must include an integer with this command."
                           "Please use `$help purge` for more information.")
        elif isinstance(error, errors.BadArgument):
            await ctx.send("Bad argument, please only use integers with this command.\n")
        else:
            error.handled = False

    # $info command used to provide some info on this bot
    @hybrid_command(help="Provides a brief synopsis of Karn, including a link to his Open Source code",
                    brief="Provides a brief synopsis of Karn")
    async def info(self, ctx):
        await ctx.send(f"Hello! I am Karn, your friendly Time-Travelling Golem!\n"
                       f"I was developed by Vertical Bar, and am hosted locally in Kalamazoo!\n"
                       f"If you would like to know me more intimately my Open Source code can be found here:\n\n"
                       f"https://github.com/vscheff/karn")

    @command(hidden=True)
    async def verticalbar(self, ctx):
        await ctx.send("01010110 01101111 01101110 "
                       "00100000 01010011 01100011 01101000 01100101 01100110 01100110 01101100 01100101 01110010")

    @hybrid_command(help="Echoes a given string within your current text channel.\n"
                         "Example: `/echo Repeat this back to me`\n\n"
                         "This command has the following flags:\n"
                         "* **-c**: Echoes the message in a different given channel\n"
                         "\tExample: `$echo -c #general Repeat this in the general channel`",
                    brief="Echoes a message.")
    async def echo(self, ctx, *, message: str):
        flags, message = get_flags(message, join=True, make_dic=True)
        
        if 'c' in flags:
            if (channel_id := get_id_from_mention(flags['c'])) is None:
                return await ctx.send("Invalid channel. Please send channel in the format: #channel\n"
                                      "Please use `$help echo` for more information.")
            if is_slash_command(ctx):
                await ctx.send(f"Echoing your message in {flags['c']}", ephemeral=True)

            return await self.bot.get_channel(int(channel_id)).send(message)

        await ctx.send(message)

    @echo.error
    async def echo_error(self, ctx, error):
        if isinstance(error, errors.MissingRequiredArgument):
            await ctx.send("You must include a message to echo with this command.\nPlease use `$help echo` for more information.")
            error.handled = True


# Used by $qr to create a QR code image
# param data - string of data to encode in the QR image
def make_qr(data):
    qr = qrcode.QRCode(version=None,                                       # None type allows dynamic QR size
                       error_correction=qrcode.constants.ERROR_CORRECT_L,  # L <= 7% error correction
                       box_size=10,
                       border=2)
    qr.add_data(data)
    # Construct the QR code with the 'fit' modifier to scale the input data
    qr.make(fit=True)
    return qr.make_image(fill_color="black", back_color="white")

def apply_operator(ops, values):
    right = values.pop()
    left = values.pop()
    values.append(eval(f"{left}{ops.pop().replace('^', "**")}{right}"))
