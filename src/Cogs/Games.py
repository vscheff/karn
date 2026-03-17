from collections import Counter
from dataclasses import dataclass, field
from discord.ext.commands import Cog, hybrid_command
from random import choice

from src.utils import get_flags


SOLUTION_FILE_PATH = "./data/wordle_answers.txt"
VALID_WORDS_FILE_PATH = "./data/wordle_valid_words.txt"
WORD_LENGTH = 5
MAX_GUESSES = 6


@dataclass
class WordleGame:
    word: str
    guesses: list[str] = field(default_factory=list)

    @property
    def remaining_guesses(self):
        return MAX_GUESSES - len(self.guesses)

    @property
    def is_over(self):
        return len(self.guesses) >= MAX_GUESSES

    def score_guess(self, guess):
        guess = guess.lower()
        word = self.word.lower()

        result = ["absent"] * WORD_LENGTH
        remaining = Counter(word)

        # Check exact matches
        for i, (g, w) in enumerate(zip(guess, word)):
            if g == w:
                result[i] = "correct"
                remaining[g] -= 1

        # Check present but misplaced matches
        for i, g in enumerate(guess):
            if result[i] == "correct":
                continue

            if remaining[g] > 0:
                result[i] = "present"
                remaining[g] -= 1

        return result

    def format_guess(self, guess):
        statuses = self.score_guess(guess)
        parts = []

        for letter, status in zip(guess.upper(), statuses):
            if status == "correct":
                parts.append(f"**{letter}**")
            elif status == "present":
                parts.append(f"__{letter}__")
            else:
                parts.append(letter)

        return ' '.join(parts)

    def submit_guess(self, guess):
        self.guesses.append(guess.lower())

        won = guess.lower() == self.word.lower()
        lost = not won and len(self.guesses) >= MAX_GUESSES

        return self.format_guess(guess), won, lost


def load_word_file(path):
    with open(path, 'r') as infile:
        return {i.strip().lower() for i in infile if len(i.strip()) == 5 and i.strip().isalpha()}


class WordRepository:
    def __init__(self, word_length=WORD_LENGTH):
        self.word_length = word_length
        self.solution_words = []
        self.valid_guesses = set()

        self.load_words()

    def normalize_word(self, word):
        word = word.strip().lower()

        if len(word) != self.word_length or not word.isalpha():
            return None

        return word

    def load_words(self):
        answers = load_word_file(SOLUTION_FILE_PATH)
        allowed = load_word_file(VALID_WORDS_FILE_PATH)

        self.solution_words = sorted(answers)
        self.valid_guesses = allowed | answers

        if not self.solution_words:
            raise RunTimeError("No valid Wordle words could be loaded.")

    def is_valid_guess(self, guess):
        return guess.lower() in self.valid_guesses

    def random_solution(self):
        return choice(self.solution_words)


class Games(Cog):
    def __init__(self):
        self.wordle_games = {}
        self.word_repo = WordRepository()
    
    @hybrid_command(help="Starts a new game of Wordle in the chat.\n\n"
                         "This command has the following flags:\n"
                         "* **-n**: Quits an ongoing game and starts a new game of Wordle.\n"
                         "* **-q**: Quits an ongoing game of Wordle.",
                    brief="Play a game of Wordle")
    async def wordle(self, ctx, *, flags: str=''):
        flags, _  = get_flags(flags)
        chann_id = ctx.channel.id

        if 'q' in flags:
            if (game := self.wordle_games.pop(chann_id, None)) is None:
                await ctx.send("There is not currently an ongoing Wordle game in this chat.")
            else:
                await ctx.send(f"World game succesfully quit. The word was: {game.word}.")

            return

        existing_game = self.wordle_games.get(chann_id)

        if existing_game:
            if 'n' not in flags:
                await ctx.send(f"There is already an ongoing Wordle game in this chat\n"
                               f"You have {existing_game.remaining_guesses} remaining guesses.\n"
                               f"Use `$wordle -n` to start a new game or `$wordle -q` to quit.")
                
                return

            self.wordle_games.pop(chann_id, None)

        game = WordleGame(word=self.word_repo.random_solution())
        self.wordle_games[chann_id] = game
        await ctx.send("New game of Wordle started. You have 6 attempts to correctly guess the word.\n"
                       "**Bold** letters are in the correct spot.\n"
                       "__Underlined__ letters are present in the word, but not in the correct spot.\n"
                       "Other letters are not present in the word.\n\n"
                       "Simply type a word into chat to submit a guess!")

    async def wordle_listener(self, msg):
        if not (game := self.wordle_games.get(msg.channel.id)):
            return False

        guess = msg.clean_content.strip().lower()

        if len(guess) != WORD_LENGTH or not guess.isalpha():
            return False

        if not self.word_repo.is_valid_guess(guess):
            await msg.channel.send(f"`{guess.upper()}` is not a valid word.")

            return True

        formatted, won, lost = game.submit_guess(guess)

        if won:
            await msg.channel.send(f"Correct! You succesfully found the word using {len(game.individual_guesses)} guesses.")
            self.wordle_games.pop(msg.channel.id, None)
            
            return True

        if lost:
            await msg.channel.send(f"Incorrect! Out of guesses. The word was: {game.word.upper()}")
            self.wordle_games.pop(msg.channel.id, None)

            return True

        await msg.channel.send(formatted)

        return True
