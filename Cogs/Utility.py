# Cog that holds all commands related to server/bot utility

from discord.ext import commands
from datetime import datetime, timedelta
import discord
import os
import qrcode

from msg_packager import package_message


class Utility(commands.Cog):

    # attr      bot - our client
    # attr inv_file - filename/path for storage of invite link QR image
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # $qr command used to generate QR code images
    # param arg - all user input following command-name
    @commands.command(help='Generate a QR code for input data\n`Example: $qr https://www.gnu.org/`',
                      brief='Generate a QR code')
    async def qr(self, ctx, *, arg):
        # Filename/path for temporary storage of QR image
        temp_store = './img/temp_qr.png'
        img = self.make_qr(arg)
        img.save(temp_store)
        if os.path.exists(temp_store):
            await ctx.send(file=discord.File(temp_store))
            os.remove(temp_store)
        else:
            print('Error occurred while generating QR code. Temp file not created/deleted.')

    # Called if $qr encounters an unhandled exception
    @qr.error
    async def qr_error(self, ctx, error):
        if isinstance(error, commands.errors.MissingRequiredArgument):
            await ctx.send('You must include a string of data with this command.\n'
                           'Example: `$qr https://www.linux.org/`')
        else:
            print(f'$qr command failed with error:\n\n{error}')

    # Used by $qr and $set_invite to creat a QR code image
    # param data - string of data to encode in the QR image
    def make_qr(self, data):
        qr = qrcode.QRCode(version=None,                                       # Nonetype allows dynamic QR size
                           error_correction=qrcode.constants.ERROR_CORRECT_L,  # L <= 7% error correction
                           box_size=10,
                           border=2)
        qr.add_data(data)
        # Construct the QR code with the 'fit' modifier to scale the input data
        qr.make(fit=True)
        return qr.make_image(fill_color='black', back_color='white')

    # $ping command used to test bot readiness and latency
    @commands.command(help='Returns "pong" and the round-trip latency if the bot is online.',
                      brief='Returns "pong" if the bot is online.')
    async def ping(self, ctx):
        await ctx.send(f'pong (*{round(self.bot.latency * 1000)}ms*)')

    # $execute command used for ACE
    # param arg - all user input following the command-name
    @commands.command(help='Attempts to execute the given code in Python\n'
                           'This command will only accept one-line statements\n'
                           'Example: `$execute 6 * 7`',
                      brief='Executes given Python code')
    async def execute(self, ctx, *, arg):
        try:
            compiled = compile(arg, '<string>', 'eval')
            obj = eval(compiled)
            await package_message(obj, ctx)
        except SyntaxError as e:
            await ctx.send(f'Bad Syntax: Error occurred at Index [{e.offset-1}], '
                           f'Character ({e.text[e.offset-1]})')
        except Exception as e:
            await ctx.send(str(e))

    # $ready command used as a "all-systems-go" check for the bot
    @commands.command(hidden=True,
                      help='Performs an "All-Systems-Go" check for the bot, and returns a status report.',
                      brief='Check for "All-Systems-Go"')
    async def ready(self, ctx):
        await ctx.send(f'Websocket closed: {self.bot.is_closed()}\n'
                       f'Internal cache ready: {self.bot.is_ready()}\n'
                       f'Websocket rate limited: {self.bot.is_ws_ratelimited()}')

    # $purge command used to bulk delete messages from a text channel
    # param before - int representing the number of days, before which messages will be deleted
    # param  after - int representing the number of days, before which messages will NOT be deleted
    @commands.command(hidden=True,
                      help='Delete all messages in a channel older than a give number of days.\n'
                           'Example: `$purge 3`\n'
                           'That command will delete all messages older than 3 days.\n\n'
                           'Alternatively, you can include two integers to declare a range.\n'
                           'Example: `$purge 3 42`\n'
                           'That command will delete all messages older than 3 days, '
                           'but not older than 42 days.\n\n',
                      brief='Bulk delete messages in current channel')
    @commands.has_permissions(manage_messages=True)
    async def purge(self, ctx, before: int, after: int = None):
        del_before = datetime.now() - timedelta(days=before)
        if after is None:
            await ctx.send(f'Deleting messages sent before **{del_before.isoformat(" ", "minutes")}**')
            deleted = await ctx.channel.purge(before=del_before)
        else:
            if after <= before:
                await ctx.send('Bad argument, second given integer must be larger than the first.')
                return
            # Subtract the remaining days to get the lower-limit
            del_after = del_before - timedelta(days=after - before)
            await ctx.send(f'Deleting messages between **{del_after.isoformat(" ", "minutes")}** '
                           f'and **{del_before.isoformat(" ", "minutes")}**.')
            deleted = await ctx.channel.purge(before=del_before, after=del_after)
        await ctx.send(f'Successfully deleted {len(deleted)} messages from this channel!')

    # Called if $purge encounters an unhandled exception
    @purge.error
    async def purge_error(self, ctx, error):
        if isinstance(error, commands.errors.MissingPermissions):
            print(f'$purge command failed: User {ctx.author.name} lacks permissions')
        elif isinstance(error, commands.errors.MissingRequiredArgument):
            await ctx.send('You must include an integer with this command.'
                           'Please use `$help purge` for more information.')
        elif isinstance(error, commands.errors.BadArgument):
            await ctx.send('Bad argument, please only use integers with this command.\n')
        else:
            print(f'$purge command failed with error:\n\n{error}')
