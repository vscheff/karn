from copy import deepcopy
from discord.ext import commands
from random import choice, randint
from re import search
from wikipedia import DisambiguationError, page, PageError, random

from msg_packager import package_message


SUPPORTED_FILE_FORMATS = (".jpg", ".jpeg", ".JPG", ".JPEG", ".png", ".PNG", ".gif", ".gifv", ".webm", ".mp4", ".wav")


class Wikipedia(commands.Cog):
    @commands.command(help="Returns the summary of a given Wikipedia article\nExample: `$wiki Thelema`\n\n"
                           "This command has the following flags:\n"
                           "* **-f**: Used to retrieve the full text of the given article.\n"
                           "\tExample: `$wiki -f Jack Parsons`\n"
                           "* **-i**: Used to retrieve all images from the given article.\n"
                           "\tExample: `$wiki -i L. Ron Hubbard`\n"
                           "\tOptionally, you may provide an integer sub-argument to limit the number of images sent.\n"
                           "\tExample: `$wiki -i 3 L. Ron Hubbard` will only result in three images sent.\n"
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

        sub_arg = int(title.pop(0)) if 'i' in flags and title and title[0].isnumeric() else None

        title = random() if 'r' in flags else ' '.join(title)

        try:
            try:
                result = page(title, auto_suggest=False)
            except PageError:
                try:
                    result = page(title)
                except PageError:
                    return await ctx.send(f"Unable to find a Wikipedia article titled \"{title}\". "
                                          f"Please check the spelling and try again.")
        except DisambiguationError as e:
            if 'r' not in flags:
                options = "\n* ".join(e.options)
                return await ctx.send(f"\"{title}\" may refer to:\n* {options}\n\n"
                                      f"Please repeat the search using one of the options listed above.")

            result = page(choice(e.options))

        if 'i' in flags:
            supported_images = []

            for image in result.images:
                if is_supported_filetype(image):
                    supported_images.append(image)

            if not supported_images:
                return await ctx.send(f"Zero supported images found in the article for {result.title}")

            num_images = min(len(supported_images), sub_arg) if sub_arg else len(supported_images)

            await ctx.send(f"**{result.title}**")

            for _ in range(num_images):
                await ctx.send(supported_images.pop(randint(0, len(supported_images) - 1)))

            return

        images = deepcopy(result.images)

        while True:
            if not images:
                img = None
                break
            img = images.pop(randint(0, len(images) - 1))
            if is_supported_filetype(img):
                break

        await ctx.send(f"**{result.title}**")

        if 'f' in flags:
            await package_message(result.content.replace(" () ", ' '), ctx)
        else:
            await ctx.send(f"{result.summary[:1997].replace(' () ', ' ')}{'...'if len(result.summary) > 1997 else ''}")

        msg = await ctx.send(result.url)
        await msg.edit(suppress=True)

        if img:
            await ctx.send(img)

    @wiki.error
    async def wiki_error(self, ctx, error):
        if isinstance(error, commands.errors.MissingRequiredArgument):
            await ctx.send("You must include a Wikipedia page title with this command."
                           "Please use `$help wiki` for more information.")


def is_supported_filetype(filename):
    return (match := search(r"\.[a-zA-z\d]+\Z", filename)) and match.group() in SUPPORTED_FILE_FORMATS
