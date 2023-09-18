import discord
from mysql.connector.errors import OperationalError
import os
from random import randint
from re import search


FILEPATH = './img/msg.txt'
SUPPORTED_FILE_FORMATS = (".jpg", ".jpeg", ".JPG", ".JPEG", ".png", ".PNG", ".gif", ".gifv", ".webm", ".mp4", ".wav")


# Ensures the SQL database is still connected, and returns a cursor from that connection
def get_cursor(conn):
    try:
        return conn.cursor()
    except OperationalError:
        conn.connect()
        return conn.cursor()

def get_flags(args):
    arg_list = args.split()
    flags = []
    not_flags = []

    while arg_list:
        arg = arg_list.pop(0)
        if arg[0] == '-':
            flags.extend([i.lower() for i in arg[1:]])
        else:
            not_flags.append(arg)

    return flags, not_flags

def get_supported_filetype(images, randomize=True):
    while True:
        if not images:
            return None

        img = images.pop(randint(0, len(images) - 1) if randomize else 0)

        if is_supported_filetype(img):
            return img

def is_supported_filetype(filename):
    return (match := search(r"\.[a-zA-z\d]+\Z", filename)) and match.group() in SUPPORTED_FILE_FORMATS

async def package_message(obj, ctx):
    if isinstance(obj, (int, float)):
        obj = str(obj)
    elif isinstance(obj, (list, set, tuple)):
        obj = ', '.join([str(i) for i in obj])
    elif isinstance(obj, dict):
        obj = ', '.join([str(i) for i in obj.items()])

    if len(obj) > 2000:
        with open(FILEPATH, 'w', encoding='utf8') as msg_file:
            msg_file.write(obj)
        if os.path.exists(FILEPATH):
            await ctx.send(file=discord.File(FILEPATH))
            os.remove(FILEPATH)
        else:
            print('Error occurred while packaging message. Temp file not created/deleted.')
    else:
        await ctx.send(obj)
