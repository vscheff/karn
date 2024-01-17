from bs4 import BeautifulSoup
from copy import deepcopy
from discord import File
from discord.ext.commands import Cog, command, MissingRequiredArgument
from json import dumps, loads
from os import getenv, remove
from os.path import exists
from PIL import Image
from random import choice, randint
from requests import get
from re import findall, sub
from wikipedia import DisambiguationError, page, PageError, random
from xkcd import getComic, getLatestComic, getLatestComicNum, getRandomComic

from us_state_abbrev import abbrev_to_us_state as states
from utils import get_flags, is_supported_filetype, get_supported_filetype, package_message


# $card constants
FACE_0 = "./img/face_0.png"
FACE_1 = "./img/face_1.png"
OUTPUT_PNG = "./img/output.png"
SCRYFALL_URL = "https://api.scryfall.com/cards"

# $define constants
MAX_DEFINITIONS = 16
WORDNIK_API_KEY = getenv("WORDNIK_TOKEN")
WORDNIK_URL = "https://api.wordnik.com/v4/word.json/"

# $image constants
DEFAULT_IMAGE_COUNT = 1
GOOGLE_URL = "https://www.google.com/search"
HEADER = {
    "User-Agent":
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/103.0.5060.114 Safari/537.36"
}

# $weather constants
WEATHER_API_KEY = getenv("WEATHER_TOKEN")
WEATHER_URL = "https://api.openweathermap.org/data/2.5/weather?"


class Query(Cog):
    @command(help="Returns Scryfall data for a given MtG card"
                  f"\n\nThis command has the following flags:\n"
                  f"* **-r**: Returns a random MtG card.\n"
                  f"\tExample: `$card -r`\n",
             brief="Returns data of an MtG card")
    async def card(self, ctx, *, args):
        flags, query = get_flags(args)
        card_name = ' '.join(query)

        if 'r' in flags:
            card_json = get(f"{SCRYFALL_URL}/random", params={'q': "game:paper -stamp:acorn"})
            card_json = card_json.json()
        else:
            card_json = get(f"{SCRYFALL_URL}/named", params={"fuzzy": card_name}).json()

        if "status" not in card_json:
            await send_card(ctx, card_json)
        elif "type" in card_json:
            card_json = get(f"{SCRYFALL_URL}/search", params={'q': f"{card_name} game:paper"}).json()

            if "status" in card_json:
                return await ctx.send(card_json["details"])

            for card_data in card_json["data"]:
                await send_card(ctx, card_data)
        else:
            return await ctx.send(card_json["details"])

        if exists(OUTPUT_PNG):
            remove(FACE_0)
            remove(FACE_1)
            remove(OUTPUT_PNG)

    @card.error
    async def card_error(self, ctx, error):
        if isinstance(error, MissingRequiredArgument):
            await ctx.send("You must include a card name or search query with this command.\n"
                           "Example: $card nekusar\n\n"
                           "Please use `$help card` for more information.")

    @command(help="Returns definitions for a given word\nExample: `$define love`",
             brief="Returns definitions for a given word")
    async def define(self, ctx, word: str):
        params = {"limit": MAX_DEFINITIONS, "sourceDictionaries": "wiktionary",
                  "includeTags": "false", "api_key": WORDNIK_API_KEY}
        response = get(f"{WORDNIK_URL}{word}/definitions", params=params).json()

        if "statusCode" in response:
            await ctx.send(f"{word} not found in the dictionary. Please check the spelling.")
            return

        definitions = {}

        for dic in response:
            try:
                definition = sub(r"<[^<>]+>", '', dic["text"])
            except KeyError:
                continue

            if dic["partOfSpeech"] in definitions:
                definitions[dic["partOfSpeech"]].append(definition)
            else:
                definitions[dic["partOfSpeech"]] = [definition]

        msg = []

        for part_of_speech in definitions:
            msg.append(f"\n\n{part_of_speech.capitalize()}")
            def_num = 0
            for definition in definitions[part_of_speech]:
                def_num += 1
                msg.append(f"\n    {def_num}. {definition}")

        await ctx.send(f"**{word.capitalize()}**```{''.join(msg)}```")

    @define.error
    async def define_error(self, ctx, error):
        if isinstance(error, MissingRequiredArgument):
            await ctx.send("You must include a word to define.\n"
                           "Example: `$define hate`\n\n"
                           "Please use `$help define` for more information.")

    @command(help=f"Returns images relevant to a given query\n"
                  f"Example: `$image Grant MacDonald`\n\n"
                  f"This command has the following flags:\n"
                  f"* **-c**: Specify a number of images to return [default={DEFAULT_IMAGE_COUNT}].\n"
                  f"\tExample: `$image -c 10 Margaery Tyrell`\n"
                  f"* **-r**: Return randomly selected images from the search instead of the most relevant images.\n"
                  f"\tExample: `$image -r Cressida`",
             brief="Search the web for an image",
             aliases=["images", "search"])
    async def image(self, ctx, *, arg):
        flags, query = get_flags(arg)
        sub_arg = int(query.pop(0)) if 'c' in flags and query and query[0].isnumeric() else None
        randomize = 'r' in flags

        search_query = ' '.join(query)

        html = get(GOOGLE_URL, params={'q': search_query, "hl": "en", "gl": "us", "tbm": "isch"}, headers=HEADER)

        all_script_tags = BeautifulSoup(html.text, "lxml").select("script")
        # https://regex101.com/r/48UZhY/4
        matched_images_data = ''.join(findall(r"AF_initDataCallback\(([^<]+)\);", str(all_script_tags)))

        # Must dumps before loads to avoid JSONDecodeError
        # https://regex101.com/r/VPz7f2/1
        matched_data = findall(r"\"b-GRID_STATE0\"(.*)sideChannel:\s?{}}", loads(dumps(matched_images_data)))

        # removing previously matched thumbnails for easier full resolution image matches.
        removed_img = sub(r"\[\"(https://encrypted-tbn0\.gstatic\.com/images\?.*?)\",\d+,\d+]", '', str(matched_data))

        # https://regex101.com/r/fXjfb1/4
        matched_google_images = findall(r"[',],\[\"(https:|http.*?)\",\d+,\d+]", removed_img)

        if not matched_google_images:
            return await ctx.send(f"No results found for \"{search_query}\".")

        for _ in range(sub_arg if sub_arg else DEFAULT_IMAGE_COUNT):
            if img := get_supported_filetype(matched_google_images, randomize):
                await ctx.send(bytes(bytes(img, "ascii").decode("unicode-escape"), "ascii").decode("unicode-escape"))
            else:
                break

    @image.error
    async def image_error(self, ctx, error):
        if isinstance(error, MissingRequiredArgument):
            await ctx.send("You must include a search term with this command.\n"
                           "Example: `$image Natalie Dormer`\n\n"
                           "Please use `$help image` for more information.")

    @command(help="Returns the summary of a given Wikipedia article\nExample: `$wiki Thelema`\n\n"
                  "This command has the following flags:\n"
                  "* **-f**: Used to retrieve the full text of the given article.\n"
                  "\tExample: `$wiki -f Jack Parsons`\n"
                  "* **-i**: Used to retrieve all images from the given article.\n"
                  "\tExample: `$wiki -i L. Ron Hubbard`\n"
                  "\tOptionally, you may provide an integer sub-argument to limit the number of images sent.\n"
                  "\tExample: `$wiki -i 3 L. Ron Hubbard` will only result in three images sent.\n"
                  "* **-r**: Used to retrieve a random Wikipedia article.\n"
                  "\tExample: `$wiki -r`",
             brief="Search for a Wikipedia article")
    async def wiki(self, ctx, *, args):
        flags, query = get_flags(args)

        sub_arg = int(query.pop(0)) if 'i' in flags and query and query[0].isnumeric() else None

        title = random() if 'r' in flags else ' '.join(query)

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

        try:
            img = get_supported_filetype(deepcopy(result.images))
        except KeyError:
            img = None

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
        if isinstance(error, MissingRequiredArgument):
            await ctx.send("You must include a Wikipedia page title with this command."
                           "Please use `$help wiki` for more information.")

    @command(help="Returns the current weather for a given city\n"
                  "The city can be input in any of the following formats: "
                  "kalamazoo; kalamazoo, mi; kalamazoo, michigan; 49006\n"
                  "Example: $weather 49078",
             brief="Returns the weather of a city")
    async def weather(self, ctx, *, city):
        city = [i.strip() for i in city.split(',') if i]
        params = {"appid": WEATHER_API_KEY, "units": "imperial"}

        if city[0].isnumeric():
            params["zip"] = city[0]
        else:
            if len(city) == 1:
                city = city[0]
            elif len(city) == 2:
                if len(city[1]) == 2:
                    city[1] = states[city[1].upper()]
                city = f"{city[0]},{city[1]}"
            params['q'] = city

        weather = get(WEATHER_URL, params=params).json()

        if weather["cod"] != "404":
            main = weather["main"]
            await ctx.send(f"**Temperature:** {main['temp']:.0f}°F (*Feels Like* {main['feels_like']:.0f}°)\n"
                           f"**Wind:** {weather['wind']['speed']:.0f} mph\n"
                           f"**Description:** {weather['weather'][0]['description']}\n"
                           f"**Pressure:** {main['pressure'] / 33.863886666667:.2f} in\n"
                           f"**Humidity:** {main['humidity']}%\n"
                           f"**Visibility:** {weather['visibility'] // 1609} mi")
        else:
            await ctx.send("City not found")

    @weather.error
    async def weather_error(self, ctx, error):
        if isinstance(error, MissingRequiredArgument):
            await ctx.send("You must include a city or zip code with this command.\n"
                           "Example: $weather kalamazoo\n\n"
                           "Please use `$help weather` for more information.")

    @command(help="Returns the XKCD comic of a given comic number.\n\n"
                  "This command has the following flags:\n"
                  "* **-r**: Returns a random XKCD comic\n"
                  "* **-l**: Returns the latest XKCD comic",
             brief="Return an XKCD comic")
    async def xkcd(self, ctx, args="-l"):
        flags, arg = get_flags(args)

        if 'r' in flags:
            comic = getRandomComic()
        elif 'l' in flags:
            comic = getLatestComic()
        else:
            try:
                comic = getComic(int(arg[0]))
            except ValueError:
                return await ctx.send("Invalid argument, please only input integer values for comic number.")
            except IndexError:
                return await ctx.send("You must include a comic number with this command.\n"
                                      "Example: `$xkcd 327`\n\nPlease use `$help xkcd` for more information.")

        if comic.number == -1:
            await ctx.send(f"Invalid comic number, please use an integer in the range [1, {getLatestComicNum()}].")
            return

        await ctx.send(f"# {comic.title}")
        await ctx.send(comic.imageLink)
        await ctx.send(f"||*{comic.altText}*||")

async def send_card(ctx, card_json):
    if img_links := card_json.get("image_uris"):
        await ctx.send(img_links["png"])
    else:
        merge_double(card_json["card_faces"][0]["image_uris"]["png"], card_json["card_faces"][1]["image_uris"]["png"])
        await ctx.send(file=File(OUTPUT_PNG))

    if price := card_json['prices']['usd']:
        await ctx.send(f"**Price:** ${price}")

def merge_double(link0, link1):
    with open(FACE_0, "wb") as img_file:
        img_file.write(get(link0).content)

    with open(FACE_1, "wb") as img_file:
        img_file.write(get(link1).content)

    img0 = Image.open(FACE_0)
    output_img = Image.new("RGB", (img0.size[0] * 2, img0.size[1]))
    output_img.paste(img0)
    output_img.paste(Image.open(FACE_1), (img0.size[0], 0))
    output_img.save(OUTPUT_PNG)
