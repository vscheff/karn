from discord.ext.commands import Cog, command, MissingRequiredArgument
from os import listdir, remove
from random import choice
from re import search

from src.global_vars import FILE_ROOT_DIR, SEND_LINE_CHAR
from src.utils import get_flags, package_message, send_tts_if_in_vc


class Terminal(Cog):

    @command(help="Returns the entire contents of a given text file\n"
                  "Example: `cat parody_bands`",
             brief="Read from a file")
    async def cat(self, ctx, filename):
        if search(r"\W", filename):
            return await ctx.send(f"Invalid filename: `{filename}`\nPlease only use word characters.")

        filename = filename.lower()

        try:
            with open(f"{FILE_ROOT_DIR}/{ctx.guild.id}/{filename}.txt", "r") as in_file:
                content = in_file.read()
        except FileNotFoundError:
            return await ctx.send(f"No file named {filename} found! Try using `$tee` first!")

        await package_message(content, ctx)

    @cat.error
    async def cat_error(self, ctx, error):
        if isinstance(error, MissingRequiredArgument):
            await ctx.send("You must include a filename with this command.\n"
                           "Example: `$cat jokes`\n\n"
                           "Please use `$help cat` for more information.")

    @command(help="Return lines from a file that match a given pattern string\n"
                  "Example: `grep parody_bands Von`",
             brief="Search a file")
    async def grep(self, ctx, *, args):
        file, pattern = args.split(maxsplit=1)

        if search(r"\W", file):
            return await ctx.send(f"Invalid filename: {file}\nPlease only use word characters.")

        file = file.lower()

        try:
            with open(f"{FILE_ROOT_DIR}/{ctx.guild.id}/{file}.txt", "r") as in_file:
                lines = in_file.readlines()
        except FileNotFoundError:
            return await ctx.send(f"No file named {file} found! Try using `$tee` first!")

        if matches := [i for i in lines if search(pattern, i[:-1])]:
            return await package_message(''.join(matches), ctx)

        await ctx.send(f"No matches found in {file}")

    @grep.error
    async def grep_error(self, ctx, error):
        if isinstance(error, MissingRequiredArgument):
            await ctx.send("You must include a filename and search query with this command.\n"
                           "Example: `$grep mud dracula`\n\n"
                           "Please use `$help grep` for more information.")
    
    @command(help="Lists the text files currently present in the directory",
             brief="Lists present text files")
    async def ls(self, ctx):
        file_names = sorted(listdir(f"{FILE_ROOT_DIR}/{ctx.guild.id}"))
        files = '\n'.join(i.replace(".txt", '') for i in file_names if i[0] != '.')
        
        if not files:
            return await ctx.send("No files exist in your server's directory. Try using `$tee` first!")

        await ctx.send(f"```\n{files}\n```")

    @command(help="Removes a text file from the directory",
             brief="Remove a text file")
    async def rm(self, ctx, filename):
        filename = filename.lower()

        try:
            remove(f"{FILE_ROOT_DIR}/{ctx.guild.id}/{filename}.txt")
        except FileNotFoundError:
            return await ctx.send(f"No file named {filename} found! Try using `$tee` first!")

        await ctx.send(f"Successfully removed {filename}!")

    @rm.error
    async def rm_error(self, ctx, error):
        if isinstance(error, MissingRequiredArgument):
            await ctx.send("You must include a filename with this command.\n"
                           "Example: `$grep johnny`\n\n"
                           "Please use `$help grep` for more information.")
    
    @command(help="Writes user input into a given text file\n"
                  "Example: `tee parody_bands Jon Von Jovi`",
             brief="Write to a file")
    async def tee(self, ctx, *, args):
        file, inp = args.split(maxsplit=1)

        if search(r"\W", file):
            return await ctx.send(f"Invalid filename: `{file}`\nPlease only use word characters.")

        file = file.lower()

        with open(f"{FILE_ROOT_DIR}/{ctx.guild.id}/{file}.txt", "a") as out_file:
            out_file.write(f"{inp}\n")

        await ctx.send(f"Successfully wrote line into `{file}`")
    
    @tee.error
    async def tee_error(self, ctx, error):
        if isinstance(error, MissingRequiredArgument):
            await ctx.send("You must include a filename with this command.\n"
                           "Example: `$tee silverhand`\n\n"
                           "Please use `$help tee` for more information.")

    @command(help="Returns the line count, word count, and character count for a given file. Multiple files can be specified in the same command.\n\n"
                  "This command has the following flags:\n"
                  "* **-c**: Return the number of bytes in the file\n"
                  "\tExample: `$wc -c dracula`\n"
                  "* **-l**: Return the line count for the file\n"
                  "\tExample: `$wc -l johnny`\n"
                  "* **-m**: Return the character count for the file\n"
                  "\tExample: `$wc -m silverhand`\n"
                  "* **-w**: Return the word count for the file\n"
                  "\tExample: `$wc -w jules`",
             brief="Returns various counts for a file")
    async def wc(self, ctx, *, args):
        flags, files = get_flags(args)
        response = ""
        mode = "rb" if 'c' in flags else 'r'

        for file in files:
            file = file.lower()

            if search(r"\W", file):
                await ctx.send(f"`{file}`: No such file")
                continue

            try:
                with open(f"{FILE_ROOT_DIR}/{ctx.guild.id}/{file}.txt", mode) as in_file:
                    lines = in_file.readlines()
            except FileNotFoundError:
                await ctx.send(f"{file}: No such file")

            if 'c' in flags:
                response += str(sum(len(line) for line in lines)) + ' '
            else:
                if not flags or 'l' in flags:
                    response += str(len(lines)) + ' '

                if not flags or 'w' in flags:
                    response += str(sum(len(line.split()) for line in lines)) + ' '

                if not flags or 'm' in flags:
                    response += str(sum(len(line) for line in lines)) + ' '

            response += f"{file}\n"

        await ctx.send(response)

    @wc.error
    async def wc_error(self, ctx, error):
        if isinstance(error, MissingRequiredArgument):
            await ctx.send("You must include at least one filename with this command.\n"
                           "Example: `$wc jules`\n\n"
                           "Please use `$help wc` for more information.")

async def send_line(msg, bot):
    if msg.content[0] == SEND_LINE_CHAR:
        file = msg.content[1:].strip().split(maxsplit=1)[0]
    elif msg.content[0] == '<':
        if not (match := search(r"<#\d+>", msg.content)):
            return False
        file = f"{bot.get_channel(int(match.group()[2:-1]))}{msg.content[match.span()[1]:]}"
    else:
        return False

    if search(r"\W", file):
        return False

    try:
        with open(f"{FILE_ROOT_DIR}/{msg.guild.id}/{file}.txt", "r") as in_file:
            lines = in_file.readlines()
    except FileNotFoundError:
        return False

    response = choice(lines)

    await msg.channel.send(response)

    await send_tts_if_in_vc(bot, msg.author, response)

    return True
