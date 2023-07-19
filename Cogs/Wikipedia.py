from discord.ext import commands
from random import randint
from wikipedia import page, PageError, random, summary


class Wikipedia(commands.Cog):
    @commands.command(help='Returns the summary of a given Wikipedia article\nExample: `$wiki Thelema`',
                      brief='Returns the summary of a given Wikipedia article')
    async def wiki(self, ctx, *, title: str):
        try:
            result = page(title, auto_suggest=False)
        except PageError:
            await ctx.send(f'Unable to find a Wikipedia article titled "{title}". '
                           f'Please check the spelling and try again.')
            return

        await send_wiki(ctx, result)

    # @commands.command(help='Returns the summary of a random Wikipedia article\nExample: `$rand_wiki`',
    #                   brief='Returns the summary of a random Wikipedia article')
    # async def rand_wiki(self, ctx):
    #     title = random()
    #     await send_wiki(ctx, page(title, auto_suggest=False))

    @wiki.error
    async def wiki_error(self, ctx, error):
        if isinstance(error, commands.errors.MissingRequiredArgument):
            await ctx.send('You must include a Wikipedia page title with this command.'
                           'Please use `$help wiki` for more information.')
        else:
            print(f'$wiki command failed with error:\n\n{error}')


async def send_wiki(ctx, result):
    await ctx.send(f'**{result.title}**')
    await ctx.send(summary(result.title, auto_suggest=False, chars=2000).replace(" () ", " "))
    msg = await ctx.send(result.url)
    await msg.edit(suppress=True)
    await ctx.send(result.images[randint(0, len(result.images) - 1)])
