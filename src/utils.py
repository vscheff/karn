from asyncio import get_running_loop, sleep
import discord
from gtts import gTTS
from json import loads
from mysql.connector.errors import OperationalError
from openai import OpenAI
import os
from random import choices, randint
from re import search
from socket import socket
from string import ascii_letters, digits

from src.global_vars import FILE_ROOT_DIR, TEMP_DIR

OPENAI_CLIENT = OpenAI(api_key=os.getenv("CHATGPT_TOKEN"), organization=os.getenv("CHATGPT_ORG"))

PACKAGE_FILEPATH = f"{TEMP_DIR}/msg.txt"
SUPPORTED_FILE_FORMATS = (".jpg", ".jpeg", ".JPG", ".JPEG", ".png", ".PNG", ".gif", ".gifv", ".webm", ".mp4", ".wav")
TTS_RAND_STR_LEN = 8

MAX_MSG_LEN = 2000

SUPPORTED_VOICES = ("alloy", "ash", "coral", "echo", "fable", "onyx", "nova", "sage", "shimmer")
SUPPORTED_SPEEDS = (0.25, 4.0)
DEFAULT_TTS_VOICE = "onyx"
DEFAULT_TTS_SPEED = 1.05

SOCKET_PORT = 8008
SOCKET_TIMEOUT = 8
SOCKET_BUFF_SIZE = 1024


def get_as_number(string):
    try:
        return int(string)
    except ValueError:
        try:
            return float(string)
        except ValueError:
            return False

# Ensures the SQL database is still connected, and returns a cursor from that connection
def get_cursor(conn):
    try:
        return conn.cursor()
    except OperationalError:
        conn.connect()
        return conn.cursor()

def get_flags(args, join=False, make_dic=False, no_args=None):
    if args is None:
        return [], []

    arg_list = args.split()
    flags = []
    not_flags = []
    flag_dic = {}
    no_args = [] if no_args is None else no_args

    while arg_list:
        arg = arg_list.pop(0)
        if arg[0] == '-':
            if len(arg) == 2 and make_dic:
                flag_dic[arg[1]] = None if arg[1] in no_args else arg_list.pop(0)
            else:
                flags.extend([i.lower() for i in arg[1:]])
        else:
            not_flags.append(arg)

    if join:
        not_flags = ' '.join(not_flags)

    if make_dic:
        return flag_dic, not_flags

    return flags, not_flags
    
def get_id_from_mention(mention):
    # regex101.com/r/OeJ1dG/1
    if not (match := search(r"<#(\d+)>", mention)):
        return None

    return match.group(1)

def get_json_from_socket(auth):
    with socket() as sock:
        sock.settimeout(SOCKET_TIMEOUT)
        sock.bind(("127.0.0.1", SOCKET_PORT))
        sock.listen(1)
        data = []
        conn, addr = sock.accept()
        
        with conn:
            while True:
                if (message := conn.recv(SOCKET_BUFF_SIZE)):
                    data.append(message.decode())
                else:
                    break

    json_data = loads(''.join(data))

    auth_type, auth_in = json_data["authorization"].split()

    if auth_type != "Bearer" or auth_in != auth:
        print(f"Bad webhook authorization detected: {json_data['authorization']}")
        raise PermissionError

    return json_data["content"]

def get_supported_filetype(images, randomize=True):
    while True:
        if not images:
            return None

        img = images.pop(randint(0, len(images) - 1) if randomize else 0)

        if is_supported_filetype(img):
            return img

def is_supported_filetype(filename):
    return (match := search(r"\.[a-zA-z\d]+\Z", filename)) and match.group() in SUPPORTED_FILE_FORMATS

def make_guild_dir(guild_id):
    filepath = f"{FILE_ROOT_DIR}/{guild_id}"
    if not os.path.isdir(filepath):
        os.makedirs(filepath)

async def package_message(obj, ctx, multi_send=False):
    if isinstance(obj, (int, float)):
        obj = str(obj)
    elif isinstance(obj, (list, set, tuple)):
        obj = ', '.join([str(i) for i in obj])
    elif isinstance(obj, dict):
        obj = ', '.join([str(i) for i in obj.items()])

    if len(obj) <= MAX_MSG_LEN:
        await ctx.send(obj)

        return

    if multi_send:
        i = 0
        while i < len(obj):
            end_index = i + MAX_MSG_LEN

            if end_index <= len(obj):
                end_index = obj[i:i + MAX_MSG_LEN].rfind('\n')
                end_index = MAX_MSG_LEN if end_index == -1 else end_index

            await ctx.send(obj[i:i + end_index])
            i += end_index + 1

        return

    with open(PACKAGE_FILEPATH, 'w', encoding='utf8') as msg_file:
        msg_file.write(obj)
    if os.path.exists(PACKAGE_FILEPATH):
        await ctx.send(file=discord.File(PACKAGE_FILEPATH))
        os.remove(PACKAGE_FILEPATH)
    else:
        print('Error occurred while packaging message. Temp file not created/deleted.')


async def run_blocking(func, *args, **kwargs):
    return await get_running_loop().run_in_executor(None, lambda: func(*args, **kwargs))

async def send_tts_if_in_vc(bot, author, text):
    for client in bot.voice_clients:
        if client.channel == author.voice.channel:
            await text_to_speech(text, client)

async def text_to_speech(text, client, voice=DEFAULT_TTS_VOICE, speed=DEFAULT_TTS_SPEED):
    response = OPENAI_CLIENT.audio.speech.create(model="tts-1", input=text, voice=voice, speed=speed)
    
    filename = f"output_{''.join(choices(ascii_letters + digits, k=TTS_RAND_STR_LEN))}.mp3"
    TTS_TEMP_FILE = f"{TEMP_DIR}/{filename}"

    response.stream_to_file(TTS_TEMP_FILE)

    while client.is_playing():
        await sleep(1)

    client.play(discord.FFmpegPCMAudio(executable="ffmpeg",  source=TTS_TEMP_FILE))

    while client.is_playing():
        await sleep(1)

    os.remove(TTS_TEMP_FILE)
