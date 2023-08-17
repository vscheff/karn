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

from us_state_abbrev import abbrev_to_us_state as states
from utils import get_flags, is_supported_filetype, package_message


WEATHER_API_KEY = getenv("WEATHER_TOKEN")
WORDNIK_API_KEY = getenv("WORDNIK_TOKEN")

# $card constants
FACE_0 = "./img/face_0.png"
FACE_1 = "./img/face_1.png"
OUTPUT_PNG = "./img/output.png"
SCRYFALL_URL = "https://api.scryfall.com/cards"

# $image constants
DEFAULT_IMAGE_COUNT = 1
GOOGLE_URL = "https://www.google.com/search"
HEADER = {
    "User-Agent":
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/103.0.5060.114 Safari/537.36"
}

# $weather constants
WEATHER_URL = "https://api.openweathermap.org/data/2.5/weather?"


class Query(Cog):
    @command(help="Returns Scryfall data for a given MtG card"
                  f"This command has the following flags:\n"
                  f"* **-r**: Returns a random MtG card.\n"
                  f"\tExample: `$card -r`\n",
             brief="Returns data of an MtG card")
    async def card(self, ctx, *, args):
        flags, query = get_flags(args)
        card_name = ' '.join(query)

        if 'r' in flags:
            card_json = get(f"{SCRYFALL_URL}/random").json()
        else:
            card_json = get(f"{SCRYFALL_URL}/named", params={"fuzzy": card_name}).json()

        if "status" not in card_json:
            await send_card(ctx, card_json)
        elif "type" in card_json:
            card_json = get(f"{SCRYFALL_URL}/search", params={'q': card_name}).json()

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

    @command(help="Returns several definitions for a given word\nExample: `$define love`",
             brief="Returns several definitions for a given word")
    async def define(self, ctx, word: str):
        url = f"https://api.wordnik.com/v4/word.json/{word}/definitions?" \
              f"limit=16&sourceDictionaries=wiktionary&includeTags=false&api_key={WORDNIK_API_KEY}"
        response = get(url)
        api_response = loads(response.text)

        if "statusCode" in api_response:
            await ctx.send(f"{word} not found in the dictionary. Please check the spelling.")
            return

        definitions = {}

        for dic in api_response:
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

    @command(help=f"Returns images relevant to a given keyword\nExample: `$image Grant MacDonald`\n\n"
                  f"This command has the following flags:\n"
                  f"* **-c**: Specify a number of images to return [default={DEFAULT_IMAGE_COUNT}].\n"
                  f"\tExample: `$image -c 10 Margaery Tyrell`\n",
             brief="Search the web for an image",
             aliases=["images", "search"])
    async def image(self, ctx, *, arg):
        flags, query = get_flags(arg)
        sub_arg = int(query.pop(0)) if 'c' in flags and query and query[0].isnumeric() else None

        params = {'q': ' '.join(query), "hl": "en", "gl": "us", "tbm": "isch"}
        html = get(GOOGLE_URL, params=params, headers=HEADER)
        soup = BeautifulSoup(html.text, "lxml")

        all_script_tags = soup.select("script")
        # https://regex101.com/r/48UZhY/4
        matched_images_data = "".join(findall(r"AF_initDataCallback\(([^<]+)\);", str(all_script_tags)))

        # Must dumps before loads to avoid JSONDecodeError
        matched_images_data_fix = dumps(matched_images_data)
        matched_images_data_json = loads(matched_images_data_fix)

        # https://regex101.com/r/VPz7f2/1
        matched_data = findall(r"\"b-GRID_STATE0\"(.*)sideChannel:\s?{}}", matched_images_data_json)

        # removing previously matched thumbnails for easier full resolution image matches.
        removed_img = sub(r"\[\"(https://encrypted-tbn0\.gstatic\.com/images\?.*?)\",\d+,\d+]", '', str(matched_data))

        # https://regex101.com/r/fXjfb1/4
        matched_google_images = findall(r"[',],\[\"(https:|http.*?)\",\d+,\d+]", removed_img)

        for _ in range(sub_arg if sub_arg else DEFAULT_IMAGE_COUNT):
            img = matched_google_images.pop(randint(0, len(matched_google_images) - 1))
            while not is_supported_filetype(img):
                img = matched_google_images.pop(randint(0, len(matched_google_images) - 1))

            await ctx.send(bytes(bytes(img, "ascii").decode("unicode-escape"), "ascii").decode("unicode-escape"))

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
             brief="Returns the summary of a given Wikipedia article")
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
        if isinstance(error, MissingRequiredArgument):
            await ctx.send("You must include a Wikipedia page title with this command."
                           "Please use `$help wiki` for more information.")

    @command(help="Returns the current weather for a given city\n"
                  "The city can be input as any of the following: "
                  "kalamazoo; kalamazoo, mi; kalamazoo, michigan; 49006\n"
                  "Example: $weather 49078",
             brief="Returns the weather of a city")
    async def weather(self, ctx, *, city):
        city = [i.strip() for i in city.split(',') if i]
        if city[0].isnumeric():
            complete_url = f"{WEATHER_URL}zip={city[0]}&appid={WEATHER_API_KEY}&units=imperial"
        else:
            if len(city) == 1:
                city = city[0]
            elif len(city) == 2:
                if len(city[1]) == 2:
                    city[1] = states[city[1].upper()]
                city = f"{city[0]},{city[1]}"
            complete_url = f"{WEATHER_URL}q={city}&appid={WEATHER_API_KEY}&units=imperial"
        weather = get(complete_url).json()
        if weather["cod"] != "404":
            main = weather["main"]
            temperature = round(main["temp"])
            feels_like = round(main["feels_like"])
            pressure = round(main["pressure"] / 33.863886666667, 2)
            humidity = main["humidity"]
            visibility = round(weather["visibility"] / 1609)
            description = weather["weather"][0]["description"]
            wind = round(weather["wind"]["speed"])
            await ctx.send(f"**Temperature:** {temperature}°F (*Feels Like* {feels_like}°)\n"
                           f"**Wind:** {wind} mph\n"
                           f"**Description:** {description}\n"
                           f"**Pressure:** {pressure} in\n"
                           f"**Humidity:** {humidity}%\n"
                           f"**Visibility:** {visibility} mi")
        else:
            await ctx.send("City not found")

    @weather.error
    async def weather_error(self, ctx, error):
        if isinstance(error, MissingRequiredArgument):
            await ctx.send("You must include a city or zip code with this command.\n"
                           "Example: $weather kalamazoo\n\n"
                           "Please use `$help weather` for more information.")


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
