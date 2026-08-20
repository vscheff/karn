import shlex

from src.functions.diff import diff
from src.functions.dig import dig
from src.functions.find import find
from src.functions.terminal import *
from src.response_strings import NO_DM_SUPPORT
from src.util_objects import TerminalResult as TR

async def run_pipeline(ctx, pipeline):
    try:
        segments = [i.strip() for i in split_pipeline(pipeline) if i.strip()]
    except ValueError as e:
        return TR(stderr=f"shell: {e}", exit_code=1)

    if not segments:
        return TR(stderr="No command provided.", exit_code=2)

    stdin = ''

    guild_id = None if ctx.guild is None else ctx.guild.id

    for segment in segments:
        command_name, raw_arguments = split_command(segment)

        if not command_name:
            continue

        result = await process_command(guild_id, command_name, raw_arguments, stdin)

        if not result.succeeded:
            return result

        stdin = result.stdout

    return TR(stdout=stdin, formatted_output=result.formatted_output, exit_code=0)

def split_pipeline(command):
    segments = []
    current = []
    quote = None
    escaped = False

    for index, char in enumerate(command):
        if escaped:
            current.append(char)
            escaped = False
            
            continue
        
        if char == '\\':
            current.append(char)
            escaped = True
            
            continue

        if char in {'\'', '"'}:
            current.append(char)

            if quote is None:
                quote = char
            elif quote == char:
                quote = None

            continue

        previous = command[index - 1] if index > 0 else ''
        following = command[index + 1] if index + 1 < len(command) else ''

        if char == '|' and quote is None and previous.isspace() and following.isspace():
            segment = ''.join(current).strip()

            if segment:
                segments.append(segment)
            
            current = []
    
            continue

        current.append(char)
    
    if final_segment := ''.join(current).strip():
        segments.append(final_segment)

    return segments

def split_command(segment):
    command_name, separator, raw_arguments = segment.strip().partition(' ')

    return command_name.lower().lstrip('$'), raw_arguments if separator else ''

def split_first_argument(raw_arguments):
    first, separator, remainder = raw_arguments.strip().partition(' ')

    return first, remainder if separator else ''

def parse_arguments(raw_arguments):
    return shlex.split(raw_arguments)

async def process_command(guild_id, command_name, raw_arguments, stdin):
    match command_name:
        case "cat":
            if guild_id is None and not stdin:
                return TR(stderr=NO_DM_SUPPORT, exit_code=1)

            return cat(guild_id, raw_arguments, stdin=stdin)

        case "diff":
            if guild_id is None and not stdin:
                return TR(stderr=NO_DM_SUPPORT, exit_code=1)

            return diff(guild_id, raw_arguments, stdin=stdin)

        case "dig":
            try:
                arguments = shlex.split(raw_arguments)
            except ValueError as e:
                return TR(stderr=f"shell: {e}", exit_code=1)
            
            if not arguments:
                return TR(stderr="usage: `dig [@DNS] [flags] [options] <domain> [record_type]`", exit_code=1)

            return await dig(' '.join(arguments))

        case "echo":
            return TR(stdout=raw_arguments, exit_code=0)

        case "find":
            if guild_id is None:
                return TR(stderr=NO_DM_SUPPORT, exit_code=1)

            return find(guild_id, raw_arguments)

        case "grep":
            if guild_id is None and not stdin:
                return TR(stderr=NO_DM_SUPPORT, exit_code=1)

            if not raw_arguments:
                return TR(stderr="usage: `grep [filename] <pattern>`", exit_code=1)

            return grep(guild_id, raw_arguments, stdin=stdin)

        case "ls":
            if guild_id is None:
                return TR(stderr=NO_DM_SUPPORT, exit_code=1)

            return ls(guild_id, stdin=stdin)

        case "head":
            if guild_id is None and not stdin:
                return TR(stderr=NO_DM_SUPPORT, exit_code=1)

            return get_lines(guild_id, raw_arguments, reverse=False, stdin=stdin)

        case "nl":
            if guild_id is None and not stdin:
                return TR(stderr=NO_DM_SUPPORT, exit_code=1)

            return nl(guild_id, raw_arguments, stdin=stdin)

        case "sort":
            if guild_id is None and not stdin:
                return TR(stderr=NO_DM_SUPPORT, exit_code=1)

            return sort(guild_id, raw_arguments, stdin=stdin)

        case "tail":
            if guild_id is None and not stdin:
                return TR(stderr=NO_DM_SUPPORT, exit_code=1)

            return get_lines(guild_id, raw_arguments, reverse=True, stdin=stdin)
      
        case "uniq":
            if guild_id is None and not stdin:
                return TR(stderr=NO_DM_SUPPORT, exit_code=1)

            return uniq(guild_id, raw_arguments, stdin=stdin)

        case "tee":
            if guild_id is None:
                return TR(stderr=NO_DM_SUPPORT, exit_code=1)

            return tee(guild_id, raw_arguments, stdin=stdin) 

        case "wc":
            if guild_id is None and not stdin:
                return TR(stderr=NO_DM_SUPPORT, exit_code=1)

            return wc(guild_id, raw_arguments, stdin=stdin)

        case _:
            return TR(stderr=f"`{command_name}` does not have pipeline support.", exit_code=2)
