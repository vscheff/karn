from comics import directory, search
from comics.exceptions import InvalidEndpointError
from copy import deepcopy
from discord import Embed, File
from discord.ext.commands import Cog, command, MissingRequiredArgument
from duckduckgo_search import DDGS
from os import getenv, remove
from os.path import exists
from PIL import Image
from random import choice, randint
from requests import get
from re import sub
from wikipedia import DisambiguationError, page, PageError, random
from xkcd import getComic, getLatestComic, getLatestComicNum, getRandomComic

from us_state_abbrev import abbrev_to_us_state as states
from utils import get_flags, is_supported_filetype, get_supported_filetype, package_message


DEFAULT_RESULT_COUNT = 1

# $card constants
FACE_0 = "./img/face_0.png"
FACE_1 = "./img/face_1.png"
OUTPUT_PNG = "./img/output.png"
SCRYFALL_URL = "https://api.scryfall.com/cards"

# $define constants
MAX_DEFINITIONS = 16
WORDNIK_API_KEY = getenv("WORDNIK_TOKEN")
WORDNIK_URL = "https://api.wordnik.com/v4/word.json/"

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
                           "Example: `$card nekusar`\n\n"
                           "Please use `$help card` for more information.")

    @command(help="Returns a random comic strip from a given Comic name.\n"
                  "Example: `$comic Garfield`",
             brief="Returns a random comic strip")
    async def comic(self, ctx, *, args):
        flags, query = get_flags(args, join=True)
        
        try:
            comic = search(query).random_date()
        except InvalidEndpointError:
            if not results := directory.search(query).random_date():
                ctx.send(f"Unknown comic: {query}\nAvailable comics include:\n")
                ctx.send("* " + "\n* ".join(directory.listall()))
                return
            
            comic = search(results[0]).random_date()

        await ctx.send(comic.image_url)

    @comic.error
    async def comic_error(self, ctx, error):
        if isinstance(error, MissingRequiredArgument):
            await ctx.send("You must include a comic name with this command.\n"
                           "Example: `$comic Calvin and Hobbes`\n\n"
                           "Please use `$help comic` for more information.")

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
                  f"* **-c**: Specify a number of images to return [default={DEFAULT_RESULT_COUNT}].\n"
                  f"\tExample: `$image -c 10 Margaery Tyrell`\n"
                  f"* **-r**: Return randomly selected images from the search instead of the most relevant images.\n"
                  f"\tExample: `$image -r Cressida`",
             brief="Search the web for an image",
             aliases=["images"])
    async def image(self, ctx, *, args):
        flags, query = get_flags(args)
        sub_arg = int(query.pop(0)) if 'c' in flags and query and query[0].isnumeric() else None
        randomize = 'r' in flags

        search_query = ' '.join(query)

        if not (results := DDGS().images(keywords=search_query, safesearch="off")):
            return await ctx.send(f"No results found for \"{search_query}\".")

        image_urls = [i["image"] for i in results]

        for _ in range(sub_arg if sub_arg else DEFAULT_RESULT_COUNT):
            if img := get_supported_filetype(image_urls, randomize):
                await ctx.send(img)
            else:
                break

    @image.error
    async def image_error(self, ctx, error):
        if isinstance(error, MissingRequiredArgument):
            await ctx.send("You must include a search term with this command.\n"
                           "Example: `$image Natalie Dormer`\n\n"
                           "Please use `$help image` for more information.")

    @command(help=f"Search the web with a given query"
                  f"Example: `$search Chris Chan`\n\n"
                  f"This command has the following flags:\n"
                  f"* **-c**: Specify a number of results to return [default={DEFAULT_RESULT_COUNT}].\n"
                  f"\tExample: `search -c 10 Sam Hyde`\n",
             brief="Search the web")
    async def search(self, ctx, *, args):
        flags, query = get_flags(args)
        sub_arg = int(query.pop(0)) if 'c' in flags and query and query[0].isnumeric() else None

        search_query = ' '.join(query)

        if not (results := DDGS().text(keywords=search_query, safesearch="off")):
            return await ctx.send(f"No results found for \"{search_query}\".")

        for result in results[:sub_arg if sub_arg else DEFAULT_RESULT_COUNT]:
            embed = Embed(title=result["title"],
                          url=result["href"],
                          description=result["body"],
                          color=randint(0, 0xFFFFFF))
            await ctx.send(embed=embed)

    @search.error
    async def search_error(self, ctx, error):
        if isinstance(error, MissingRequiredArgument):
            await ctx.send("You must include a search term with this command.\n"
                           "Example: `$search Christine Weston Chandler`\n\n"
                           "Please use `$help search` for more information.")

    @command(help=f"Search the web for videos with a given query"
                  f"Example: `$search Dizaster - Love Me Long Time`\n\n"
                  f"This command has the following flags:\n"
                  f"* **-c**: Specify a number of results to return [default={DEFAULT_RESULT_COUNT}].\n"
                  f"\tExample: `search -c 10 Fishtank`\n",
             brief="Search the web for videos")
    async def video(self, ctx, *, args):
        flags, query = get_flags(args)
        sub_arg = int(query.pop(0)) if 'c' in flags and query and query[0].isnumeric() else None

        search_query = ' '.join(query)

        if not (results := DDGS().videos(keywords=search_query, safesearch="off")):
            return await ctx.send(f"No results found for \"{search_query}\".")

        for result in results[:sub_arg if sub_arg else DEFAULT_RESULT_COUNT]:
            await ctx.send(result["content"])

    @video.error
    async def video_error(self, ctx, error):
        if isinstance(error, MissingRequiredArgument):
            await ctx.send("You must include a search term with this command.\n"
                           "Example: `$video dracula flow`\n\n"
                           "Please use `$help video` for more information.")

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

        if 'f' in flags or not result.summary:
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
