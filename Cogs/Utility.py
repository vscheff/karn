# Cog that holds all commands related to server/bot utility

from discord.ext import commands
from datetime import datetime, timedelta
import discord
import os
import qrcode
from re import findall

from utils import get_as_number, package_message

# Filename/path for temporary storage of QR image
QR_FILEPATH = "./files/temp_qr.png"


class Utility(commands.Cog):

    # attr bot - our client
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # $qr command used to generate QR code images
    # param arg - all user input following command-name
    @commands.command(help="Generate a QR code for input data\n`Example: $qr https://www.gnu.org/`",
                      brief="Generate a QR code")
    async def qr(self, ctx, *, arg):
        img = make_qr(arg)
        img.save(QR_FILEPATH)
        if os.path.exists(QR_FILEPATH):
            await ctx.send(file=discord.File(QR_FILEPATH))
            os.remove(QR_FILEPATH)
        else:
            print("Error occurred while generating QR code. Temp file not created/deleted.")

    # Called if $qr encounters an unhandled exception
    @qr.error
    async def qr_error(self, ctx, error):
        if isinstance(error, commands.errors.MissingRequiredArgument):
            await ctx.send("You must include a string of data with this command.\n"
                           "Example: `$qr https://www.linux.org/`"
                           "Please use `$help qr` for more information.")

    # $ping command used to test bot readiness and latency
    @commands.command(help="Returns \"pong\" and the round-trip latency if the bot is online.",
                      brief="Returns \"pong\" if the bot is online.")
    async def ping(self, ctx):
        await ctx.send(f"pong (*{self.bot.latency * 1000:.0f}ms*)")

    # $calc command used for calculating the result of mathematical expressions
    # param args - all user input following the command name
    @commands.command(help="Returns the result of a mathematical expression.\n"
                           "Example: `$calc 6 * 7`",
                      brief="Executes given Python code")
    async def calc(self, ctx, *, args):
        prec = {'+': 0, '-': 0, '*': 1, '/': 1, '^': 2}

        # https://regex101.com/r/rYoPQz/1
        tokens = findall(r"-?\d+\.?\d*|[+\-/*()^]", ''.join(args))
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
        await ctx.send("Unable to calculate result. "
                       "Please ensure your input is a valid mathematical equation.")

    # $ready command used as a "all-systems-go" check for the bot
    @commands.command(help="Performs an \"All-Systems-Go\" check for the bot, and returns a status report.",
                      brief="Check for \"All-Systems-Go\"")
    async def ready(self, ctx):
        await ctx.send(f"Websocket closed: {self.bot.is_closed()}\n"
                       f"Internal cache ready: {self.bot.is_ready()}\n"
                       f"Websocket rate limited: {self.bot.is_ws_ratelimited()}")

    # $purge command used to bulk delete messages from a text channel
    # param before - int representing the number of days, before which messages will be deleted
    # param  after - int representing the number of days, before which messages will NOT be deleted
    @commands.command(help="Delete all messages in a channel older than a given number of days.\n"
                           "Example: `$purge 3`\n"
                           "That command will delete all messages older than 3 days.\n\n"
                           "Alternatively, you can include two integers to declare a range.\n"
                           "Example: `$purge 3 42`\n"
                           "That command will delete all messages older than 3 days, "
                           "but not older than 42 days.\n\n",
                      brief="Bulk delete messages in current channel")
    @commands.has_permissions(manage_messages=True)
    async def purge(self, ctx, before: int, after: int = None):
        del_before = datetime.now() - timedelta(days=before)
        if after is None:
            await ctx.send(f"Deleting messages sent before **{del_before.isoformat(' ', 'minutes')}**")
            deleted = await ctx.channel.purge(before=del_before, bulk=True)
        else:
            if after <= before:
                await ctx.send("Bad argument, second given integer must be larger than the first.")
                return
            # Subtract the remaining days to get the lower-limit
            del_after = del_before - timedelta(days=after - before)
            await ctx.send(f"Deleting messages between **{del_after.isoformat(' ', 'minutes')}** "
                           f"and **{del_before.isoformat(' ', 'minutes')}**.")
            deleted = await ctx.channel.purge(before=del_before, after=del_after, bulk=True)
        await ctx.send(f"Successfully deleted {len(deleted)} messages from this channel!")

    # Called if $purge encounters an unhandled exception
    @purge.error
    async def purge_error(self, ctx, error):
        if isinstance(error, commands.errors.MissingPermissions):
            print(f"$purge command failed: User {ctx.author.name} lacks permissions")
        elif isinstance(error, commands.errors.MissingRequiredArgument):
            await ctx.send("You must include an integer with this command."
                           "Please use `$help purge` for more information.")
        elif isinstance(error, commands.errors.BadArgument):
            await ctx.send("Bad argument, please only use integers with this command.\n")

    # $info command used to provide some info on this bot
    @commands.command(help="Provides a brief synopsis of Karn, including a link to his Open Source code",
                      brief="Provides a brief synopsis of Karn")
    async def info(self, ctx):
        await ctx.send(f"Hello! I am Karn, your friendly Time-Travelling Golem!\n"
                       f"I was developed by Vertical Bar, and am hosted locally in Kalamazoo!\n"
                       f"If you would like to know me more intimately my Open Source code can be found here:\n\n"
                       f"https://github.com/vscheff/karn")

    @commands.command(hidden=True)
    async def verticalbar(self, ctx):
        await ctx.send("01010110 01101111 01101110 "
                       "00100000 01010011 01100011 01101000 01100101 01100110 01100110 01101100 01100101 01110010")


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
