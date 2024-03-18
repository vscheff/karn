from discord.ext.commands import Cog, command
from random import choice
from re import sub
from wordle import dictionary, Wordle

from utils import get_flags


class Games(Cog):
    def __init__(self):
        self.wordle_games = {}
    
    @command(help="Starts a new game of Wordle in the chat.\n\n"
                  "This command has the following flags:\n"
                  "* **-n**: Quits an ongoing game and starts a new game of Wordle.\n"
                  "* **-q**: Quits an ongoing game of Wordle.",
             brief="Play a game of Wordle")
    async def wordle(self, ctx, *, args=''):
        flags, args = get_flags(args)
        chann_id = ctx.channel.id

        if 'q' in flags:
            if (game := self.wordle_games.pop(chann_id, None)) is None:
                await ctx.send("There is not currently an ongoing Wordle game in this chat.")
            else:
                await ctx.send(f"World game succesfully quit. The word was: {game.word}.")

            return

        if not (game := self.wordle_games.get(chann_id)) or 'n' in flags:
            game = Wordle(word=choice(dictionary.words))
            self.wordle_games[chann_id] = game
            await ctx.send("New game of Wordle started. You have 6 attempts to correctly guess the word.\n"
                           "**Bold** letters are in the correct spot.\n"
                           "__Underlined__ letters are present in the word, but not in the correct spot.\n"
                           "Other letters are not present in the word.\n\n"
                           "Simply type a word into chat to submit a guess!")
        else:
            await ctx.send(f"You have {6 - len(game.individual_guesses)} remaining guesses. Use the `-n` flag to start a new game.")

    async def wordle_listener(self, msg):
        if not (game := self.wordle_games.get(msg.channel.id)):
            return False

        response = game.send_guess(msg.clean_content)

        if isinstance(response, str):
            await msg.channel.send(response)
            
            return True

        if response[1]:
            await msg.channel.send(f"Correct! You succesfully found the word using {len(game.individual_guesses)} guesses.")
            self.wordle_games.pop(msg.channel.id)
            return True

        if len(game.individual_guesses) > 5:
            await msg.channel.send(f"Incorrect! Out of guesses. The word was: {game.word}")
            self.wordle_games.pop(msg.channel.id)

            return True

        result = sub(r"\A([A-Z])| ([A-Z])", r"__\1\2__", response[0])
        result = sub(r"\s+", ' ', result)
        result = sub(r"\*([A-Z])\*", r"**\1**", result)

        await msg.channel.send(result.upper())

        return True
