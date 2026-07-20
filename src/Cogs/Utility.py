# Cog that holds all commands related to server/bot utility

from discord.ext.commands import Bot, Cog, command, errors, has_permissions, hybrid_command
from datetime import datetime, timedelta
import discord
import os
import qrcode
from random import choice

from src.calculator import calculator, CONST, FUNCS
import src.help_messages as hlp
from src.tips import TIP_LIST
from src.utils import TEMP_DIR
from src.utils import get_flags, get_id_from_mention, is_slash_command, package_message

# Filename/path for temporary storage of QR image
QR_FILEPATH = f"{TEMP_DIR}/temp_qr.png"


class Utility(Cog):

    # attr bot - our client
    def __init__(self, bot: Bot):
        self.bot = bot

    # $qr command used to generate QR code images
    # param arg - all user input following command-name
    @hybrid_command(help=hlp.QR_FULL,
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
                           "Example: `$qr https://www.linux.org/`\n\n"
                           "Please use `$help qr` for more information.")
            error.handled = True

    # $ping command used to test bot readiness and latency
    @hybrid_command(help=hlp.PING_FULL,
                    brief="Returns \"pong\" if the bot is online.")
    async def ping(self, ctx):
        await ctx.send(f"pong (*{self.bot.latency * 1000:.0f}ms*)")

    # $calc command used for calculating the result of mathematical expressions
    # param args - all user input following the command name
    @hybrid_command(help=hlp.CALC_FULL.format(constants="`, `".join(CONST), functions="`, `".join(FUNCS)),
                    brief="Calculates the result of a mathematical expression")
    async def calc(self, ctx, *, expression:str):
        await ctx.send(calculator(expression))

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
            elif isinstance(error.original, ValueError):
                await ctx.send(str(error.original))
                error.handled = True
            elif isinstance(error.original, OverflowError):
                await ctx.send("Overflow")
                error.handled = True
        elif isinstance(error, errors.MissingRequiredArgument):
            await ctx.send("You must include a mathematical expression with this command.\nPlease use `$help calc` for more information.")
            error.handled = True

    # $ready command used as a "all-systems-go" check for the bot
    @hybrid_command(help=hlp.READY_FULL,
                    brief="Check for \"All-Systems-Go\"")
    async def ready(self, ctx):
        await ctx.send(f"Websocket closed: {self.bot.is_closed()}\n"
                       f"Internal cache ready: {self.bot.is_ready()}\n"
                       f"Websocket rate limited: {self.bot.is_ws_ratelimited()}",
                       ephemeral=True)

    # $purge command used to bulk delete messages from a text channel
    # param before - int representing the number of days, before which messages will be deleted
    # param  after - int representing the number of days, before which messages will NOT be deleted
    @hybrid_command(help=hlp.PURGE_FULL,
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

    @hybrid_command(help=hlp.TIP_FULL,
                    brief="Sends a random bot usage tip")
    async def tip(self, ctx):
        await ctx.send(choice(TIP_LIST))

    # $info command used to provide some info on this bot
    @hybrid_command(help=hlp.INFO_FULL,
                    brief="Provides a brief synopsis of Karn")
    async def info(self, ctx):
        await ctx.send("Hello! I am Karn, your friendly Time-Travelling Golem!\n"
                       "I was developed by Vertical Bar, and am hosted locally in Kalamazoo!\n"
                       "If you would like to know me more intimately my Open Source code can be found here:\n\n"
                       "https://github.com/vscheff/karn")

    @command(hidden=True)
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
