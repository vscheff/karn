from bs4 import BeautifulSoup
from discord.ext.commands import Cog, command, MissingRequiredArgument
from json import dumps, loads
from random import randint
from requests import get
from re import findall, sub

from utils import get_flags, is_supported_filetype


BASE_URL = "https://www.google.com/search"
HEADER = {
    "User-Agent":
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/103.0.5060.114 Safari/537.36"
}
DEFAULT_IMAGE_COUNT = 1


class Search(Cog):
    @command(help=f"Returns images relevant to a given keyword\nExample: `$image Grant MacDonald`\n\n"
                  f"This command has the following flags:\n"
                  f"* **-c**: Specify a number of images to return [default={DEFAULT_IMAGE_COUNT}].\n"
                  f"\tExample: `$image -c 10 Margaery Tyrell`\n",
             brief="Search the web for an image")
    async def image(self, ctx, *, arg):
        flags, query = get_flags(arg)
        sub_arg = int(query.pop(0)) if 'c' in flags and query and query[0].isnumeric() else None

        params = {'q': ' '.join(query), "hl": "en", "gl": "us", "tbm": "isch"}
        html = get(BASE_URL, params=params, headers=HEADER)
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
        # https://stackoverflow.com/a/19821774/15164646
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
