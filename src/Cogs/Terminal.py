from discord.ext.commands import Cog, errors, hybrid_command
from os import listdir, remove
from random import choice
from re import search, sub

from src.dig import dig
from src.functions.terminal import *
from src.global_vars import FILE_ROOT_DIR, SEND_LINE_CHAR
import src.help_messages as hlp
from src.utils import get_flags, package_message, send_tts_if_in_vc


DEFAULT_LINE_COUNT = 10

class Terminal(Cog):

    @hybrid_command(help=hlp.CAT_FULL,
                    brief="Read from a file")
    async def cat(self, ctx, filename: str):
        result = cat(ctx.guild.id, filename)

        await result.send(ctx)

    @cat.error
    async def cat_error(self, ctx, error):
        if isinstance(error, errors.MissingRequiredArgument):
            await ctx.send("You must include a filename with this command.\n"
                           "Example: `$cat jokes`\n\n"
                           "Please use `$help cat` for more information.")
            error.handled = True

    @hybrid_command(help=hlp.DIG_FULL,
                    brief="Perform a DNS lookup")
    async def dig(self, ctx, *, query):
        await dig(ctx, query)

    @dig.error
    async def dig_error(self, ctx, error):
        if isinstance(error, errors.MissingRequiredArgument):
            await ctx.send("You must include a domain name to lookup.\n"
                           "Exampe: `$dig gnu.org`\n\n"
                           "Please use `$help dig` for more usage information on this command.")
            error.handled = True

    @hybrid_command(help=hlp.ECHO_FULL,
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

    @hybrid_command(help=hlp.GREP_FULL,
                    brief="Search a file")
    async def grep(self, ctx, filename: str, *, pattern: str):
        result = grep(ctx.guild.id, filename, pattern)

        await result.send(ctx)

    @hybrid_command(help=hlp.HEAD_FULL.format(line_count=DEFAULT_LINE_COUNT),
                    brief=f"Returns the first {DEFAULT_LINE_COUNT} lines of a given file.")
    async def head(self, ctx, *, filename: str):
        result = get_lines(ctx.guild.id, filename, reverse=False)

        await result.send(ctx)

    @hybrid_command(help=hlp.TAIL_FULL.format(line_count=DEFAULT_LINE_COUNT),
                    brief=f"Returns the last {DEFAULT_LINE_COUNT} lines of a given file.")
    async def tail(self, ctx, *, filename: str):
        result = get_lines(ctx.guild.id, filename, reverse=True)
    
        await result.send(ctx)

    @hybrid_command(help=hlp.LS_FULL,
                    brief="Lists present text files")
    async def ls(self, ctx):
        file_names = sorted(listdir(f"{FILE_ROOT_DIR}/{ctx.guild.id}"))
        files = '\n'.join(i.replace(".txt", '') for i in file_names if i[0] != '.')
        
        if not files:
            return await ctx.send("No files exist in your server's directory. Try using `$tee` first!")

        await ctx.send(f"```\n{files}\n```")

    @hybrid_command(help=hlp.RM_FULL,
                    brief="Remove a text file")
    async def rm(self, ctx, filename: str):
        filename = filename.lower()

        try:
            remove(f"{FILE_ROOT_DIR}/{ctx.guild.id}/{filename}.txt")
        except FileNotFoundError:
            return await ctx.send(f"No file named \"{filename}\" found! Try using `$tee` first.")

        await ctx.send(f"Successfully removed `{filename}`!")

    @rm.error
    async def rm_error(self, ctx, error):
        if isinstance(error, errors.MissingRequiredArgument):
            await ctx.send("You must include a filename with this command.\n"
                           "Example: `$grep johnny`\n\n"
                           "Please use `$help grep` for more information.")
            error.handled = True

    @hybrid_command(help=hlp.TEE_FULL,
                    brief="Write to a file")
    async def tee(self, ctx, filename: str, *, data: str):
        result = tee(ctx.guild.id, filename, data)

        await result.send(ctx)

    @tee.error
    async def tee_error(self, ctx, error):
        if isinstance(error, errors.MissingRequiredArgument):
            await ctx.send("You must include a filename with this command.\n"
                           "Example: `$tee silverhand`\n\n"
                           "Please use `$help tee` for more information.")
            error.handled = True

    @hybrid_command(help=hlp.WC_FULL,
                    brief="Returns various counts for a file")
    async def wc(self, ctx, *, args: str):
        response = wc(ctx.guild.id, args)

        await response.send(ctx)

    @wc.error
    async def wc_error(self, ctx, error):
        if isinstance(error, errors.MissingRequiredArgument):
            await ctx.send("You must include at least one filename with this command.\n"
                           "Example: `$wc jules`\n\n"
                           "Please use `$help wc` for more information.")
            error.handled = True

async def send_line(msg, bot):
    msg_altered = False

    def sub_line(match_obj):
        nonlocal msg_altered
        
        try:
            with open(f"{FILE_ROOT_DIR}/{msg.guild.id}/{match_obj[0][1:]}.txt", "r") as in_file:
                msg_altered = True
                return choice(in_file.readlines()).strip()
        except FileNotFoundError:
            return match_obj[0]

    response = sub(fr"{SEND_LINE_CHAR}\w+", sub_line, msg.clean_content)
    
    if not msg_altered:
        return False

    await msg.channel.send(response)
    await send_tts_if_in_vc(bot, msg.author, response)

    return True

