from fnmatch import fnmatch
from operator import eq, gt, lt
from pathlib import Path
from re import compile, error, IGNORECASE, search
from shlex import split
from time import time

from src.global_vars import FILE_ROOT_DIR
from src.util_objects import TerminalResult as TR


SECONDS_PER_MINUTE = 60
SECONDS_PER_DAY = 86400


def find(guild_id, args):
    directory = Path(FILE_ROOT_DIR) / str(guild_id)
    files = [i for i in directory.iterdir() if i.is_file() and i.suffix == ".txt"]

    if not (arguments := split(args)):
        output = '\n'.join(f"./{i.stem}" for i in files)
        return TR(stdout=output, formatted_output=f"```text\n{output}\n```", exit_code=0)

    try:
        predicate = FindParser(arguments, directory).parse()
    except ValueError as e:
        return TR(stderr=str(e), exit_code=1)

    output = '\n'.join(f"./{i.stem}" for i in [path for path in files if predicate(path)])
    
    return TR(stdout=output, formatted_output=f"```text\n{output}\n```", exit_code=0)

class FindParser:
    def __init__(self, arguments, directory):
        self.arguments = arguments
        self.directory = directory
        self.position = 0

    def parse(self):
        predicate = self.parse_expression()

        if self.position != len(self.arguments):
            raise ValueError(f"Unexpected token: `{self.peek()}`.")

        return predicate

    def peek(self):
        return self.arguments[self.position] if self.position < len(self.arguments) else None

    def consume(self):
        if (token := self.peek()) is not None:
            self.position += 1

        return token

    def parse_expression(self):
        predicates = [self.parse_and()]

        while self.peek() == "-o":
            self.consume()

            if self.peek() in (None, ')'):
                raise ValueError("`-o` requires an expression.")

            predicates.append(self.parse_and())

        return lambda path, predicates=predicates: any(x(path) for x in predicates)

    def parse_and(self):
        predicates = [self.parse_unary()]

        while self.peek() not in (None, "-o", ')'):
            predicates.append(self.parse_unary())

        return lambda path, predicates=predicates: all(x(path) for x in predicates)

    def parse_unary(self):
        if (token := self.peek()) == "-not":
            self.consume()

            if self.peek() in (None, "-o", ')'):
                raise ValueError("`-not` requires an expression.")

            predicate = self.parse_unary()

            return lambda path, predicate=predicate: not predicate(path)

        if token == '(':
            self.consume()

            if self.peek() == ')':
                raise ValueError("Empty parenthesized expression.")

            predicate = self.parse_expression()

            if self.peek() != ')':
                raise ValueError("Missing closing `)`.")

            self.consume()

            return predicate

        return self.parse_predicate()

    def parse_predicate(self):
        def parse_comparison(value, parser=int):
            return (gt, parser(value[1:])) if value.startswith('+') else (lt, parser(value[1:])) if value.startswith('-') else (eq, parser(value))

        def get_age(path, unit):
            return int((time() - path.stat().st_mtime) / unit)

        def get_size(size_arg):
            if not size_arg:
                raise ValueError

            units = {'c': 1, 'k': 1024, 'M': 1024 ** 2, 'G': 1024 ** 3}

            if (unit := size_arg[-1]) in units:
                return int(size_arg[:-1]) * units[unit]

            return int(size_arg)

        expression = self.consume()

        match expression:
            case "-empty":
                # Visually empty files are 1 byte, the use of 1 in this comparison is deliberate
                return lambda path: path.stat().st_size <= 1
            
            case "-iname" | "-name":
                if self.peek() is None:
                    raise ValueError(f"`{expression}` requires a pattern.")

                pattern = self.consume()

                if expression == "-name":
                    return lambda path, pattern=pattern: fnmatch(path.stem, pattern)
                
                pattern = pattern.lower()

                return lambda path, pattern=pattern: fnmatch(path.stem.lower(), pattern)

            case "-iregex" | "-regex":
                if self.peek() is None:
                    raise ValueError(f"`{expression}` requires a pattern.")

                pattern = self.consume()

                try:
                    regex = compile(pattern, IGNORECASE if expression == "-iregex" else 0)
                except error:
                    raise ValueError(f"Invalid regular expression: `{pattern}`.")

                return lambda path, regex=regex: regex.fullmatch(path.stem) is not None

            case "-mmin" | "-mtime":
                if self.peek() is None:
                    raise ValueError(f"`{expression}` requires a number of {'days' if expression == '-mtime' else 'minutes'}.")

                time_arg = self.consume()

                try:
                    comparison, days = parse_comparison(time_arg)
                except ValueError:
                    raise ValueError("Invalid modification time: `{time_arg}`.")

                unit = SECONDS_PER_DAY if expression == "-mtime" else SECONDS_PER_MINUTE

                return lambda path, comparison=comparison, days=days: comparison(get_age(path, unit), days)

            case "-newer":
                if self.peek() is None:
                   raise ValueError("`-newer` requires a filename")

                filename = self.consume()
                reference = self.directory / f"{filename}.txt"

                if search(r"\W", filename) or not reference.is_file():
                   raise ValueError(f"No file named \"{filename}\" found.")

                reference_mtime = reference.stat().st_mtime

                return lambda path, reference_mtime=reference_mtime: path.stat().st_mtime > reference_mtime

            case "-size":
                if self.peek() is None:
                    raise ValueError("`-size` requires a size.")

                size_arg = self.consume()

                try:
                    comparison, size = parse_comparison(size_arg, parser=get_size)
                except ValueError:
                    raise ValueError(f"Invalid size: `{size_arg}`.")

                return lambda path, comparison=comparison, size=size: comparison(path.stat().st_size, size)

            case _:
                raise ValueError(f"Unknown expression: `{expression}`.")
