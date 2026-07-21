from re import search

from src.global_vars import FILE_ROOT_DIR
from src.utils import get_flags
from src.util_objects import TerminalResult as TR


DEFAULT_LINE_COUNT = 10


def cat(guild_id, filename, stdin=None):
    if search(r"\W", filename):
        return TR(stderr=f"Invalid filename: `{filename}`\nPlease only use word characters.", exit_code=1)

    filename = filename.lower()

    try:
        with open(f"{FILE_ROOT_DIR}/{guild_id}/{filename}.txt", "r") as in_file:
            content = in_file.read()
    except FileNotFoundError:
        return TR(stderr=f"No file named \"{filename}\" found! Try using `$tee` first.", exit_code=2)

    return TR(stdout=content, exit_code=0)

def grep(guild_id, filename, pattern, stdin=None):
    if not stdin:
        if search(r"\W", filename):
            return TR(stderr=f"Invalid filename: {filename}\nPlease only use word characters.", exit_code=1)

        filename = filename.lower()

        try:
            with open(f"{FILE_ROOT_DIR}/{guild_id}/{filename}.txt", "r") as in_file:
                lines = [i.rstrip('\n') for i in in_file.readlines()]
        except FileNotFoundError:
            return TR(stderr=f"No file named \"{filename}\" found! Try using `$tee` first.", exit_code=2)
    else:
        lines = stdin.split('\n')

    if matches := [i for i in lines if search(pattern, i[:-1])]:
        return TR(stdout='\n'.join(matches), exit_code=0)

    return TR(stderr=f"No matches found in `{filename if filename else 'stdin'}`", exit_code=3)

# Used by $head and $tail
def get_lines(guild_id, filename, reverse=False, stdin=None):
    flags, files = get_flags(filename, make_dic=True)

    try:
        num_lines = int(flags.get('n', DEFAULT_LINE_COUNT))
    except ValueError:
        return TR(stderr="Bad argument, please only use valid integers.", exit_code=1)

    if not num_lines:
        return TR(stdout="", exit_code=1)

    multiple_files = len(files) > 1 
    response = []

    def get_response_line(file, lines, num_lines):
        return f"{f'\n==> {file} <==\n' if multiple_files else ''}{''.join(lines[-num_lines:] if reverse else lines[:num_lines])}\n"

    if not stdin:
        for file in files:
            try:
                with open(f"{FILE_ROOT_DIR}/{guild_id}/{file}.txt", 'r') as in_file:
                    lines = in_file.readlines()
            except FileNotFoundError:
                response.append(f"Cannot open file `{file}`. Try using `$tee` first!\n")

                continue

            response.append(get_response_line(file, lines, num_lines))
    else:
        response.append(get_response_line("stdin", [i +'\n' for i in stdin.split('\n')], num_lines))

    return TR(stdout=''.join(response).rstrip('\n'), exit_code=0)

def tee(guild_id, filename, data, stdin=None):
	if search(r"\W", filename):
		return TR(stderr=f"Invalid filename: `{filename}`\nPlease only use word characters.", exit_code=1)
	
	data = stdin if stdin else data
	num_lines = len(data.split('\n'))
	filename = filename.lower()

	with open(f"{FILE_ROOT_DIR}/{guild_id}/{filename}.txt", "a") as out_file:
		out_file.write(f"{data}\n")
	
	return TR(stdout=f"Successfully wrote {num_lines} line{'' if num_lines == 1 else 's'} into `{filename}`", exit_code=0) 

def wc(guild_id, args, stdin=None):
    flags, files = get_flags(args)
    mode = "rb" if 'c' in flags else 'r'

    def get_response_string(flags, lines, file):
        response = ''

        if 'c' in flags:
            response += str(sum(len(line) for line in lines)) + ' '
        else:
            if not flags or 'l' in flags:
                response += str(len(lines)) + ' '

            if not flags or 'w' in flags:
                response += str(sum(len(line.split()) for line in lines)) + ' '

            if not flags or 'm' in flags:
                response += str(sum(len(line) for line in lines)) + ' '

        return response + f"{file}\n"
         
    if not stdin:
        response = ''
        
        for file in files:
            file = file.lower()

            if search(r"\W", file):
                return TR(stdout=f"`{file}`: No such file", exit_code=1)
                continue

            try:
                with open(f"{FILE_ROOT_DIR}/{guild_id}/{file}.txt", mode) as in_file:
                    lines = in_file.readlines()
            except FileNotFoundError:
                return TR(stdout=f"{file}: No such file", exit_code=1)

            response += get_response_string(flags, lines, file)
    else:
        response = get_response_string(flags, [i + '\n' for i in stdin.split('\n') if i], '')

    return TR(stdout=response[:-1], exit_code=0)
