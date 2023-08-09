from discord.ext import commands
from requests import get as get_req


BASE_URL = "https://api.scryfall.com/"


class Cards(commands.Cog):
    @commands.command(help="Returns Scryfall data for a given MtG card",
                      brief="Returns data of an MtG card")
    async def card(self, ctx, *, card_name):
        search_name = '+'.join(card_name.split())
        complete_url = f"{BASE_URL}cards/named?fuzzy={search_name}"
        card_json = get_req(complete_url).json()

        if "status" not in card_json:
            await ctx.send(card_json["image_uris"]["png"])
            await ctx.send(f"**Price:** ${card_json['prices']['usd']}")
        elif "type" in card_json:
            complete_url = f"{BASE_URL}cards/search?q={search_name}"
            card_json = get_req(complete_url).json()
            for card_data in card_json["data"]:
                await ctx.send(card_data["image_uris"]["png"])
                await ctx.send(f"**Price:** ${card_data['prices']['usd']}")
        else:
            await ctx.send(card_json["details"])
