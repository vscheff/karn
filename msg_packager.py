import discord
import os

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
        if os.path.exists(FILEPATH):
            await ctx.send(file=discord.File(FILEPATH))
            os.remove(FILEPATH)
        else:
            print('Error occurred while packaging message. Temp file not created/deleted.')
    else:
        await ctx.send(obj)
