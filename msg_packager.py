import discord

FILEPATH = './img/msg.txt'

async def package_message(obj, ctx):
    if isinstance(obj, (int, float)):
        obj = str(obj)
    elif isinstance(obj, (list, set, tuple)):
        obj = ', '.join([str(i) for i in obj])
    elif isinstance(obj, dict):
        obj = ', '.join([str(i) for i in obj.items()])

    if len(obj) > 4000:
        with open(FILEPATH, 'w') as msg_file:
            msg_file.write(obj)
        await ctx.send(file=discord.File(FILEPATH))
    else:
        await ctx.send(obj)

