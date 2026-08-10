from difflib import SequenceMatcher
from itertools import groupby
from os import listdir
from re import search

from src.global_vars import FILE_ROOT_DIR
from src.utils import get_flags
from src.util_objects import TerminalResult as TR


DEFAULT_LINE_COUNT = 10
DEFAULT_NUMBER_FORMAT = "rn"
DEFAULT_NUMBER_WIDTH = 6
DEFAULT_NUMBER_SEP = ' '


def cat(guild_id, arguments, stdin=None):
    flags, args = get_flags(arguments)
    response = get_lines_from_file(guild_id, None if stdin else args[0], join=False, stdin=stdin)

    if not response.succeeded:
        return response

    number_blank = 'n' in flags

    output_lines = number_lines(response.stdout, number_nonblank='b' in flags or number_blank, number_blank=number_blank, squeeze_blank='s' in flags)

    if 'E' in flags:
        output_lines = [f"{i[:-1]}$\n" if i.endswith('\n') else f"{i}$" for i in output_lines]

    output = ''.join(output_lines)

    return TR(stdout=output, formatted_output=f"```text\n{output}\n```", exit_code=0)

def normal_diff(left, right):
    def format_range(start, stop):
        if (first := start + 1) == stop:
            return str(first)

        return f"{first},{stop}"

    matcher = SequenceMatcher(None, left, right)
    output = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue

        if tag == "replace":
            output.append(f"{format_range(i1, i2)}c{format_range(j1, j2)}\n")
            output.extend(f"< {line}" for line in left[i1:i2])
            output.append("---\n")
            output.extend(f"> {line}" for line in right[j1:j2])
        elif tag == "delete":
            output.append(f"{format_range(i1, i2)}d{j1}\n")
            output.extend(f"< {line}" for line in left[i1:i2])
        elif tag == "insert":
            output.append(f"{i1}a{format_range(j1, j2)}\n")
            output.extend(f"> {line}" for line in right[j1:j2])

    return ''.join(output)

def diff(guild_id, arguments, stdin=None):
    flags, args = get_flags(arguments)

    if len(args) != 2:
        return TR(stderr="You must provide exactly two files.\nUse `$help diff` for more usage information.", exit_code=2)

    left = get_lines_from_file(guild_id, args[0], stdin=stdin if args[0] == '-' else None)

    if not left.succeeded:
        return left

    right = get_lines_from_file(guild_id, args[1], stdin=stdin if args[1] == '-' else None)

    if not right.succeeded:
        return right

    output = normal_diff(left.stdout, right.stdout)

    return TR(stdout=output, formatted_output=f"```text\n{output}\n```" if output else None, exit_code=0)

def nl(guild_id, arguments, stdin=None):
    flags, args = get_flags(arguments, make_dic=True, shell=True)

    if len(args) < 1 and not stdin:
        return TR(stderr="You must include a filename with this command.\nUse `$help nl` for more information.", exit_code=1)

    response = get_lines_from_file(guild_id, None if stdin else args[0], join=False, stdin=stdin)

    if not response.succeeded:
        return response

    number_nonblank = True
    number_blank = False
    right_justified = True
    zero_padded = False
    separator = flags['s'] if 's' in flags else DEFAULT_NUMBER_SEP

    for char in flags.get('b', ''):
        match char:
            case 'a':
                number_nonblank = number_blank = True
            case 't':
                number_nonblank = True
                number_blank = False
            case 'n':
                number_nonblank = number_blank = False

    try:
        increment = int(flags.get('i', 1))
    except ValueError:
        return TR(stderr="Bad subargument given for line increment. Please only use valid integers.\n"
                         "Use `$help nl` for more information.",
                  exit_code=2)

    match flags.get('n', DEFAULT_NUMBER_FORMAT):
        case 'ln':
            right_justified = False
        case 'rn':
            right_justified = True
        case 'rz':
            zero_padded = True
        case _:
            return TR(stderr="Bad subargument given for number format. Supported options include: `ln`, `rn`, and `rz`.\n"
                             "Use `$help nl` for more information.",
                      exit_code=3)

    try:
        start = int(flags.get('v', 1))
    except ValueError:
        return TR(stderr="Bad subargument given for starting line number. Please only use valid integers.\n"
                         "Use `$help nl` for more information.",
                  exit_code=4)

    try:
        if (width := int(flags.get('w', DEFAULT_NUMBER_WIDTH))) < 0:
            raise ValueError
    except ValueError:
        return TR(stderr="Bad subargument given for number width. Please only use valid nonnegative integers.\n"
                         "Use `$help nl` for more information.",
                  exit_code=5)

    output_lines = number_lines(
                                response.stdout,
                                number_nonblank=number_nonblank,
                                number_blank=number_blank,
                                width=width,
                                separator=separator,
                                start=start,
                                increment=increment,
                                right_justified=right_justified,
                                zero_padded=zero_padded
                               )

    output = ''.join(output_lines)

    return TR(stdout=output, formatted_output=f"```text\n{output}\n```", exit_code=0)

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

        return TR(stdout=output, formatted_output=f"```text\n{output}\n```", exit_code=0)

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

	return TR(stdout=files, formatted_output=f"```text\n{files}\n```", exit_code=0)

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
    response = get_lines_from_file(guild_id, None if stdin else args[0], join=False, stdin=stdin)
    
    if not response.succeeded:
        return response
    
    lines = response.stdout
    lines.sort(key=key, reverse='r' in flags)

    if 'u' in flags:
        unique_lines = []
        previous_key = object()

        for line in lines:
            if (current_key := line.casefold() if ignore_case else line) != previous_key:
                unique_lines.append(line)
                previous_key = current_key

        lines = unique_lines
    output = ''.join(lines)
    return TR(stdout=output, formatted_output=f"```text\n{output}\n```", exit_code=0)

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

    response = get_lines_from_file(guild_id, None if stdin else args[0], join=False, stdin=stdin)
    
    if not response.succeeded:
        return response
    
    lines = response.stdout
    output_lines = []

    for _, group in groupby(lines, key=str.casefold if 'i' in flags else None):
        first_line = next(group)
        count = 1 + sum(1 for _ in group)

        if not include_group(count):
            continue

        prefix = f"{count:7} " if include_count else ''
        output_lines.append(f"{prefix}{first_line}")

    output = ''.join(output_lines)

    return TR(stdout=output, formatted_output=f"```text\n{output}\n```", exit_code=0)


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

    output = response[:-1]

    return TR(stdout=output, formatted_response=f"```text\n{formatted_response}\n```", exit_code=0)

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

def number_lines(
        lines,
        number_nonblank=True,
        number_blank=False,
        squeeze_blank=False,
        width=DEFAULT_NUMBER_WIDTH,
        separator=DEFAULT_NUMBER_SEP,
        start=1,
        increment=1,
        right_justified=True,
        zero_padded=False
):
    output = []
    count = start
    previous_blank = False

    for line in lines:
        is_blank = not line.strip()

        if is_blank and squeeze_blank and previous_blank:
            continue

        if (number_nonblank and not is_blank) or (number_blank and is_blank):
            output.append(f"{count:{0 if zero_padded else ''}{'>' if right_justified else '<'}{width}}{separator}{line}")
            count += increment
        else:
            output.append(line)

        previous_blank = is_blank

    return output

