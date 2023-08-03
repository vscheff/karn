from discord.ext import commands
from google_images_search import GoogleImagesSearch
from os import getenv

API_KEY = getenv("GCS_DEVELOPER_KEY")
CX_KEY = getenv("GCS_CX")

search_params = {
    'q': '',
    "num": 3,
    "fileType": "jpg|gif|png",
    "rights": "cc_publicdomain|cc_attribute|cc_sharealike|cc_noncommercial|cc_nonderived",
    "safe": "off"
}

class Search(commands.Cog):
    @commands.command(help="Returns images relevant to a given keyword\nExample: `$image Grant MacDonald`",
                      brief="Search the web for an image")
    async def image(self, ctx, *, arg):
        gis = GoogleImagesSearch(API_KEY, CX_KEY)

        search_params['q'] = arg
        gis.search(search_params=search_params)
        for image in gis.results():
            await ctx.send(image.url)
