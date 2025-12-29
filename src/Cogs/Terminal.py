from discord.ext.commands import Cog, errors, hybrid_command
from os import listdir, remove
from random import choice
from re import search, sub

from src.global_vars import FILE_ROOT_DIR, SEND_LINE_CHAR
from src.utils import get_flags, package_message, send_tts_if_in_vc


DEFAULT_LINE_COUNT = 10

class Terminal(Cog):

    @hybrid_command(help="Returns the entire contents of a given text file\n"
                         "Example: `cat parody_bands`",
                    brief="Read from a file")
    async def cat(self, ctx, filename: str):
        if search(r"\W", filename):
            return await ctx.send(f"Invalid filename: `{filename}`\nPlease only use word characters.")

        filename = filename.lower()

        try:
            with open(f"{FILE_ROOT_DIR}/{ctx.guild.id}/{filename}.txt", "r") as in_file:
                content = in_file.read()
        except FileNotFoundError:
            return await ctx.send(f"No file named \"{filename}\" found! Try using `$tee` first.")

        await package_message(content, ctx)

    @cat.error
    async def cat_error(self, ctx, error):
        if isinstance(error, errors.MissingRequiredArgument):
            await ctx.send("You must include a filename with this command.\n"
                           "Example: `$cat jokes`\n\n"
                           "Please use `$help cat` for more information.")
            error.handled = True

    @hybrid_command(help="Return lines from a file that match a given pattern string\n"
                         "Example: `grep parody_bands Von`",
                    brief="Search a file")
    async def grep(self, ctx, filename: str, *, pattern: str):
        if search(r"\W", filename):
            return await ctx.send(f"Invalid filename: {filename}\nPlease only use word characters.")

        filename = filename.lower()

        try:
            with open(f"{FILE_ROOT_DIR}/{ctx.guild.id}/{filename}.txt", "r") as in_file:
                lines = in_file.readlines()
        except FileNotFoundError:
            return await ctx.send(f"No file named \"{filename}\" found! Try using `$tee` first.")

        if matches := [i for i in lines if search(pattern, i[:-1])]:
            return await package_message(''.join(matches), ctx)

        await ctx.send(f"No matches found in `{filename}`")

    @grep.error
    async def grep_error(self, ctx, error):
        if isinstance(error, errors.MissingRequiredArgument):
            await ctx.send("You must include a filename and search query with this command.\n"
                           "Example: `$grep mud dracula`\n\n"
                           "Please use `$help grep` for more information.")
            error.handled = True

    @hybrid_command(help=f"Returns the first {DEFAULT_LINE_COUNT} lines of a given file.\n"
                         f"Example: `$head fleshsim`\n"
                         f"You can include multiple filenames with this command"
                         f"This command has the following flags\n"
                         f"* **-c**: Specifies the number of lines to return\n"
                         f"\tExample: `$head -c 5 johnny`",
                    brief=f"Returns the first {DEFAULT_LINE_COUNT} lines of a given file.")
    async def head(self, ctx, *, filename: str):
        await self.get_lines(ctx, filename, reverse=False)

    @hybrid_command(help=f"Returns the last {DEFAULT_LINE_COUNT} lines of a given file.\n"
                         f"Example: `$tail silverhand`\n"
                         f"You can include multiple filenames with this command"
                         f"This command has the following flags\n"
                         f"* **-c**: Specifies the number of lines to return\n"
                         f"\tExample: `$tail -c 5 dracula`",
                    brief=f"Returns the last {DEFAULT_LINE_COUNT} lines of a given file.")
    async def tail(self, ctx, *, filename: str):
        await self.get_lines(ctx, filename, reverse=True)
    
    async def get_lines(self, ctx, filename, reverse=False):
        flags, files = get_flags(filename, make_dic=True)
        
        try:
            num_lines = int(flags.get('c', DEFAULT_LINE_COUNT))
        except ValueError:
            return await ctx.send(f"Bad argument, please only use valid integers.")

        if not num_lines:
            return

        multiple_files = len(files) > 1
        response = []

        for file in files:
            try:
                with open(f"{FILE_ROOT_DIR}/{ctx.guild.id}/{file}.txt", 'r') as in_file:
                    lines = in_file.readlines()
            except FileNotFoundError:
                response.append(f"Cannot open file `{file}`. Try using `$tee` first!\n")

                continue

            response.append(f"{f'\n==> {file} <==\n' if multiple_files else ''}{''.join(lines[-num_lines:] if reverse else lines[:num_lines])}\n")
        
        await package_message(''.join(response), ctx)

    @hybrid_command(help="Lists the text files currently present in the directory",
                    brief="Lists present text files")
    async def ls(self, ctx):
        file_names = sorted(listdir(f"{FILE_ROOT_DIR}/{ctx.guild.id}"))
        files = '\n'.join(i.replace(".txt", '') for i in file_names if i[0] != '.')
        
        if not files:
            return await ctx.send("No files exist in your server's directory. Try using `$tee` first!")

        await ctx.send(f"```\n{files}\n```")

    @hybrid_command(help="Removes a text file from the directory",
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

    @hybrid_command(help="Writes user input into a given text file\n"
                         "Example: `tee parody_bands Jon Von Jovi`",
                    brief="Write to a file")
    async def tee(self, ctx, filename: str, *, data: str):
        if search(r"\W", filename):
            return await ctx.send(f"Invalid filename: `{filename}`\nPlease only use word characters.")

        filename = filename.lower()

        with open(f"{FILE_ROOT_DIR}/{ctx.guild.id}/{filename}.txt", "a") as out_file:
            out_file.write(f"{data}\n")

        await ctx.send(f"Successfully wrote line into `{filename}`")
    
    @tee.error
    async def tee_error(self, ctx, error):
        if isinstance(error, errors.MissingRequiredArgument):
            await ctx.send("You must include a filename with this command.\n"
                           "Example: `$tee silverhand`\n\n"
                           "Please use `$help tee` for more information.")
            error.handled = True

    @hybrid_command(help="Returns the line count, word count, and character count for a given file. "
                         "Multiple files can be specified in the same command.\n\n"
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
    async def wc(self, ctx, *, args: str):
        flags, files = get_flags(args)
        mode = "rb" if 'c' in flags else 'r'
        response = ""

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

    response = sub(r"#\w+", sub_line, msg.clean_content)
    
    if not msg_altered:
        return False

    await msg.channel.send(response)
    await send_tts_if_in_vc(bot, msg.author, response)

    return True

