from discord.ext import commands
from os import getenv
from requests import get as get_req
from us_state_abbrev import abbrev_to_us_state as states

api_key = getenv("WEATHER_TOKEN")
base_url = "https://api.openweathermap.org/data/2.5/weather?"


class Weather(commands.Cog):
    @commands.command(help="Returns the current weather for a given city\n"
                           "The city can be input as any of the following: "
                           "kalamazoo; kalamazoo, mi; kalamazoo, michigan; 49006\n"
                           "Example: $weather 49078",
                      brief="Returns the weather of a city")
    async def weather(self, ctx, *, city):
        city = [i.strip() for i in city.split(',') if i]
        if city[0].isnumeric():
            complete_url = f"{base_url}zip={city[0]}&appid={api_key}&units=imperial"
        else:
            if len(city) == 1:
                city = city[0]
            elif len(city) == 2:
                if len(city[1]) == 2:
                    city[1] = states[city[1].upper()]
                city = f"{city[0]},{city[1]}"
            complete_url = f"{base_url}q={city}&appid={api_key}&units=imperial"
        weather = get_req(complete_url).json()
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
        if isinstance(error, commands.errors.MissingRequiredArgument):
            await ctx.send("You must include a city or zip code with this command.\n"
                           "Example: $weather kalamazoo\n\n"
                           "Please use *$help weather* for more information.")
