from discord.ext.commands import Cog, command, MissingRequiredArgument
from os import listdir
from random import choice
from re import search

from utils import package_message


FILE_ROOT_DIRECTORY = "./files"
SEND_LINE_CHAR = '#'


class Terminal(Cog):

    @command(help="Returns the entire contents of a given text file\n"
                  "Example: `cat parody_bands`",
             brief="Read from a file")
    async def cat(self, ctx, filename):
        if search(r"\W", filename):
            return await ctx.send(f"Invalid filename: `{filename}`\nPlease only use word characters.")

        filename = filename.lower()

        try:
            with open(f"{FILE_ROOT_DIRECTORY}/{filename}.txt", "r") as in_file:
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

    @command(help="Returns the entire contents of a given text file\n"
                  "Example: `cat parody_bands`",
             brief="Read from a file")
    async def grep(self, ctx, *, args):
        file, pattern = args.split(maxsplit=1)

        if search(r"\W", file):
            return await ctx.send(f"Invalid filename: {file}\nPlease only use word characters.")

        file = file.lower()

        try:
            with open(f"{FILE_ROOT_DIRECTORY}/{file}.txt", "r") as in_file:
                lines = in_file.readlines()
        except FileNotFoundError:
            return await ctx.send(f"No file named {file} found! Try using `$tee` first!")

        if matches := [i for i in lines if search(pattern, i[:-1])]:
            return await package_message(''.join(matches), ctx)

        await ctx.send(f"No matches found in {file}")

    @command(help="Lists the text files currently present in the directory",
             brief="Lists present text files")
    async def ls(self, ctx):
        files = '\n'.join(i.replace(".txt", '') for i in listdir(FILE_ROOT_DIRECTORY) if i[0] != '.')
        await ctx.send(f"```\n{files}\n```")

    @command(help="Writes user input into a given text file\n"
                  "Example: `tee parody_bands Jon Von Jovi`",
             brief="Write to a file")
    async def tee(self, ctx, *, args):
        file, inp = args.split(maxsplit=1)

        if search(r"\W", file):
            return await ctx.send(f"Invalid filename: `{file}`\nPlease only use word characters.")

        file = file.lower()

        with open(f"{FILE_ROOT_DIRECTORY}/{file}.txt", "a") as out_file:
            out_file.write(f"{inp}\n")

        await ctx.send(f"Successfully wrote line into `{file}`")


async def send_line(msg, bot):
    if msg.author.bot or not msg.content:
        return False

    if msg.content[0] == SEND_LINE_CHAR:
        file = msg.content[1:].strip().split(maxsplit=1)[0]
    elif msg.content[0] == '<':
        match = search(r"<#\d+>", msg.content)
        file = f"{bot.get_channel(int(match.group()[2:-1]))}{msg.content[match.span()[1]:]}"
    else:
        return False

    if search(r"\W", file):
        await msg.channel.send(f"Invalid filename: `{file}`\nPlease only use word characters.")
        return False

    try:
        with open(f"{FILE_ROOT_DIRECTORY}/{file}.txt", "r") as in_file:
            lines = in_file.readlines()
    except FileNotFoundError:
        return False

    await msg.channel.send(choice(lines))

    return True
