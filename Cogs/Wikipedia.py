from copy import deepcopy
from discord.ext import commands
from random import randint
from re import search
from wikipedia import DisambiguationError, page, PageError, random, summary

from msg_packager import package_message


SUPPORTED_FILE_FORMATS = (".jpg", ".jpeg", ".JPG", ".JPEG", ".png", ".PNG", ".gif", ".gifv", ".webm", ".mp4", ".wav")


class Wikipedia(commands.Cog):
    @commands.command(help="Returns the summary of a given Wikipedia article\nExample: `$wiki Thelema`\n\n\n"
                           "This command has the following flags:\n"
                           "* **-f**: Used to retrieve the full text of the given article.\n"
                           "\tExample: `$wiki -f Jack Parsons`\n"
                           "* **-i**: Used to retrieve all images from the given article.\n"
                           "\tExample: `$wiki -i L. Ron Hubbard`\n"
                           "* **-r**: Used to retrieve a random Wikipedia article.\n"
                           "\tExample: `$wiki -r`",
                      brief="Returns the summary of a given Wikipedia article")
    async def wiki(self, ctx, *, args):
        arg_list = args.split()
        flags = []
        title = []

        while arg_list:
            arg = arg_list.pop(0)
            if arg[0] == '-':
                flags.extend([i.lower() for i in arg[1:]])
            else:
                title.append(arg)

        title = random() if 'r' in flags else ' '.join(title)

        try:
            try:
                result = page(title, auto_suggest=False)
            except PageError:
                try:
                    result = page(title)
                except PageError:
                    await ctx.send(f"Unable to find a Wikipedia article titled '{title}'. "
                                   f"Please check the spelling and try again.")
                    return
        except DisambiguationError as e:
            if 'r' not in flags:
                options = "\n* ".join(e.options)
                await ctx.send(f"\"{title}\" may refer to:\n* {options}\n\n"
                               f"Please repeat the search using one of the options listed above.")
                return
            result = page(e.options[randint(0, len(e.options) - 1)])

        if 'i' in flags:
            supported_images = []

            for image in result.images:
                match = search(r"\.[a-zA-z\d]+\Z", image)
                if match and match.group() in SUPPORTED_FILE_FORMATS:
                    supported_images.append(image)

            if not supported_images:
                await ctx.send(f"Zero supported images found in the article for {result.title}")
                return

            await ctx.send(f"**{result.title}**")

            for image in supported_images:
                await ctx.send(image)

            return

        images = deepcopy(result.images)

        while True:
            if not images:
                img = None
                break
            img = images.pop(randint(0, len(images) - 1))
            match = search(r"\.[a-zA-z\d]+\Z", img)
            if match and match.group() in SUPPORTED_FILE_FORMATS:
                break

        await ctx.send(f"**{result.title}**")
        if 'f' in flags:
            await package_message(result.content.replace(" () ", ' '), ctx)
        else:
            await ctx.send(f"{result.summary[:2000].replace(' () ', ' ')}{'...'if len(result.summary) > 2000 else ''}")
        msg = await ctx.send(result.url)
        await msg.edit(suppress=True)
        if img:
            await ctx.send(img)

    @wiki.error
    async def wiki_error(self, ctx, error):
        if isinstance(error, commands.errors.MissingRequiredArgument):
            await ctx.send('You must include a Wikipedia page title with this command.'
                           'Please use `$help wiki` for more information.')
        else:
            print(f'$wiki command failed with error:\n\n{error}')
