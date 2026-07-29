from itertools import groupby
from os import listdir
from re import search

from src.global_vars import FILE_ROOT_DIR
from src.utils import get_flags
from src.util_objects import TerminalResult as TR


DEFAULT_LINE_COUNT = 10


def cat(guild_id, arguments, stdin=None):
    flags, args = get_flags(arguments)
    response = get_lines_from_file(guild_id, None if stdin else args[0], join=False, stdin=stdin)

    if not response.succeeded:
        return response

    skip_blank = 'b' in flags

    output_lines = number_lines(response.stdout, 'n' in flags or skip_blank, skip_blank, 's' in flags)

    if 'E' in flags:
        output_lines = [f"{i[:-1]}$\n" if i.endswith('\n') else f"{i}$" for i in output_lines]

    output = ''.join(output_lines)

    return TR(stdout=output, formatted_output=f"```text\n{output}```", exit_code=0)

def grep(guild_id, arguments, stdin=None):
    flags, args = get_flags(arguments)

    if len(args) < 2:
        if stdin and args:
            filename = None
            pattern = args[0]
        else:
            return TR(stderr="usage: `$grep [filename] <pattern>`", exit_code=1)
    else:
        filename = args[0]
        pattern = ' '.join(args[1:])

    response = get_lines_from_file(guild_id, filename, join=False, stdin=stdin)
    
    if not response.succeeded:
        return response

    lines = response.stdout

    if matches := [i for i in lines if search(pattern, i)]:
        output = ''.join(matches)

        return TR(stdout=output, formatted_output=f"```text\n{output}```", exit_code=0)

    return TR(stderr=f"No matches found in `{'stdin' if stdin else filename}`", exit_code=3)

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

def ls(guild_id, stdin=None):
	file_names = sorted(listdir(f"{FILE_ROOT_DIR}/{guild_id}"))
	files = '\n'.join(i.replace(".txt", '') for i in file_names if i[0] != '.')
																																	
	if not files:
		return TR(stderr="No files exist in your server's directory. Try using `$tee` first!", exit_code=1)

	return TR(stdout=files, formatted_output=f"```\n{files}\n```", exit_code=0)

def sort(guild_id, args, stdin=None):
    def numeric_sort(line):
        stripped_line = line.strip()

        try:
            return 0, float(stripped_line)
        except ValueError:
            return 1, stripped_line.casefold()

    flags, args = get_flags(args)
   
    ignore_case = 'f' in flags
    key = numeric_sort if 'n' in flags else str.casefold if ignore_case else None

    if not stdin:
        if not args:
            return TR(stderr="You must include a filename with this command.\nUse `$help sort` for more usage information.")

        filename = args[0]
        
        if search(r"\W", filename):
            return TR(stderr=f"Invalid filename: `{filename}`\nPlease only use word characters.", exit_code=1)

        filename = filename.lower()

        try:
            with open(f"{FILE_ROOT_DIR}/{guild_id}/{filename}.txt", "r") as in_file:
                lines = in_file.readlines()
        except FileNotFoundError:
            return TR(stderr=f"No file named \"{filename}\" found! Try using `$tee` first.", exit_code=2)
    else:
        lines = [i + '\n' for i in stdin.split('\n')]

    lines.sort(key=key, reverse='r' in flags)

    if 'u' in flags:
        unique_lines = []
        previous_key = object()

        for line in lines:
            if (current_key := line.casefold() if ignore_case else line) != previous_key:
                unique_lines.append(line)
                previous_key = current_key

        lines = unique_lines

    return TR(stdout=''.join(lines), exit_code=0)

def tee(guild_id, arguments, stdin=None):
    flags, args = get_flags(arguments)

    blank_line = 'b' in flags

    if not args or (len(args) < 2 and not blank_line):
        return TR(stderr="Usage: `$tee [filename] [data]`", exit_code=1)

    filename = args[0]

    if search(r"\W", filename):
        return TR(stderr=f"Invalid filename: `{filename}`\nPlease only use word characters.", exit_code=2)

    data = stdin if stdin else f"{'\n' if blank_line else ''}{' '.join(args[1:])}" if len(args) > 1 else ''
    num_lines = len(data.split('\n'))
    filename = filename.lower()

    with open(f"{FILE_ROOT_DIR}/{guild_id}/{filename}.txt", 'w' if 'o' in flags else 'a') as out_file:
        out_file.write(f"{data}\n")

    return TR(stdout=f"Successfully wrote {num_lines} line{'' if num_lines == 1 else 's'} into `{filename}`", exit_code=0) 

def uniq(guild_id, args, stdin=None):
    flags, args = get_flags(args)
    
    repeated_only = 'd' in flags
    unique_only = 'u' in flags
    include_count = 'c' in flags

    def include_group(count):
        nonlocal repeated_only, unique_only

        return (not (repeated_only or unique_only)) or (repeated_only and count > 1) or (unique_only and count == 1)

    if not stdin:
        if not args:
            return TR(stderr="You must include a filename with this command.\nUse `$help uniq` for more usage information.")

        filename = args[0]
        
        if search(r"\W", filename):
            return TR(stderr=f"Invalid filename: `{filename}`\nPlease only use word characters.", exit_code=1)

        filename = filename.lower()

        try:
            with open(f"{FILE_ROOT_DIR}/{guild_id}/{filename}.txt", "r") as in_file:
                lines = in_file.readlines()
        except FileNotFoundError:
            return TR(stderr=f"No file named \"{filename}\" found! Try using `$tee` first.", exit_code=2)
    else:
        lines = [i + '\n' for i in stdin.split('\n')]

    output_lines = []

    for _, group in groupby(lines, key=str.casefold if 'i' in flags else None):
        first_line = next(group)
        count = 1 + sum(1 for _ in group)

        if not include_group(count):
            continue

        prefix = f"{count:7} " if include_count else ''
        output_lines.append(f"{prefix}{first_line}")

    output = ''.join(output_lines)

    return TR(stdout=output, formatted_output=f"```text\n{output}```", exit_code=0)


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

def get_lines_from_file(guild_id, filename, join=False, stdin=None):
    if not stdin:
        if not filename:
            return TR(stderr="You must include a filename with this command.\nUse `$help uniq` for more usage information.")

        filename = filename.lower()

        if search(r"\W", filename):
            return TR(stderr=f"Invalid filename: `{filename}`\nPlease only use word characters.", exit_code=1)

        try:
            with open(f"{FILE_ROOT_DIR}/{guild_id}/{filename}.txt", "r") as in_file:
                lines = in_file.readlines()
        except FileNotFoundError:
            return TR(stderr=f"No file named \"{filename}\" found! Try using `$tee` first.", exit_code=2)
    else:
        lines = stdin.splitlines(keepends=True)

    return TR(stdout=''.join(lines) if join else lines, exit_code=0)

def number_lines(lines, number=True, number_nonblank=False, squeeze_blank=False):
    output = []
    count = 1
    previous_blank = False

    for line in lines:
        is_blank = not line.strip()

        if is_blank and squeeze_blank and previous_blank:
            continue

        if number and not (number_nonblank and is_blank):
            output.append(f"{count:6} {line}")
            count += 1
        else:
            output.append(line)

        previous_blank = is_blank

    return output

