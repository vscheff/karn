from datetime import datetime, date
from discord.ext import commands, tasks
from json import loads, decoder
from os import getenv
from requests import get as get_req
from re import sub
import discord

api_key = getenv('WORDNIK_TOKEN')
main_channel = int(getenv('GENERAL_CH_ID'))


class Dictionary(commands.Cog):

    def __init__(self, bot: commands.Bot, guild: discord.Guild):
        self.bot = bot
        self.guild = guild
        self.ch_general = None

        self.word_of_the_day.start()

    @commands.command(help='Returns several definitions for a given word\nExample: `$define love`',
                      brief='Returns several definitions for a given word')
    async def define(self, ctx, word: str):
        url = f'https://api.wordnik.com/v4/word.json/{word}/definitions?' \
              f'limit=6&sourceDictionaries=all&includeTags=false&api_key={api_key}'
        response = get_req(url)
        api_response = loads(response.text)
        if 'statusCode' in api_response:
            await ctx.send(f'{word} not found in the dictionary. Please check the spelling.')
            return
        definitions = []
        def_num = 1
        for dic in api_response:
            try:
                definition = sub(r'<[^<>]+>', '', dic['text'])
            except KeyError:
                continue
            try:
                part_of_speech = f' (*{dic["partOfSpeech"]}*)'
            except KeyError:
                part_of_speech = ''
            definitions.append(f'{def_num}. {definition}{part_of_speech}\n')
            def_num += 1
            if def_num > 3:
                break
        await ctx.send(''.join(definitions))

    @tasks.loop(hours=1)
    async def word_of_the_day(self):
        current_time = datetime.now()
        if current_time.hour != 11:
            return
        url = f'https://api.wordnik.com/v4/words.json/wordOfTheDay?date={date.today()}&api_key={api_key}'
        response = get_req(url)
        try:
            api_response = loads(response.text)
        except decoder.JSONDecodeError:
            print(f"{current_time}\n"
                  f"WotD Error: Bad API response!\n"
                  f"URL: {url}\n"
                  f"Response:\n"
                  f"{response.text}")
            return
        response_data = {}
        if response.status_code == 200:
            response_data['word'] = api_response['word']
            for definition in api_response['definitions']:
                response_data['definition'] = sub(r'<[^<>]+>', '', definition['text'])
                break
            await self.ch_general.send(f'**The word of the day is:**\n'
                                       f'*{api_response["word"]}* - {response_data["definition"]}')
        else:
            print(f'Error: Word of the Day Loop could not load response correctly.\n'
                  f'Status Code: {response.status_code}\n')

    @word_of_the_day.before_loop
    async def before_WotD(self):
        await self.bot.wait_until_ready()
        print('Starting Word of the Day hourly loop.')
        self.ch_general = self.guild.get_channel(main_channel)
        if self.ch_general is None:
            print('WARNING: General channel not found. Loop not started.')
            self.word_of_the_day.cancel()
            return
        print('Loop successfully started!\n')
    	
