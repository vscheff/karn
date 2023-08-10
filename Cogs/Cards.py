from discord import File
from discord.ext import commands
from os import remove
from os.path import exists
from requests import get as get_req
from PIL import Image


BASE_URL = "https://api.scryfall.com/"
FACE_0 = "./img/face_0.png"
FACE_1 = "./img/face_1.png"
OUTPUT_PNG = "./img/output.png"


class Cards(commands.Cog):
    @commands.command(help="Returns Scryfall data for a given MtG card",
                      brief="Returns data of an MtG card")
    async def card(self, ctx, *, card_name):
        search_name = '+'.join(card_name.split())
        complete_url = f"{BASE_URL}cards/named?fuzzy={search_name}"
        card_json = get_req(complete_url).json()

        if "status" not in card_json:
            await send_card(ctx, card_json)
        elif "type" in card_json:
            complete_url = f"{BASE_URL}cards/search?q={search_name}"
            card_json = get_req(complete_url).json()

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
    async def weather_error(self, ctx, error):
        if isinstance(error, commands.errors.MissingRequiredArgument):
            await ctx.send("You must include a card name or search query with this command.\n"
                           "Example: $card nekusar\n\n"
                           "Please use `$help card` for more information.")


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
        img_file.write(get_req(link0).content)

    with open(FACE_1, "wb") as img_file:
        img_file.write(get_req(link1).content)

    img0 = Image.open(FACE_0)
    output_img = Image.new("RGB", (img0.size[0] * 2, img0.size[1]))
    output_img.paste(img0)
    output_img.paste(Image.open(FACE_1), (img0.size[0], 0))
    output_img.save(OUTPUT_PNG)
