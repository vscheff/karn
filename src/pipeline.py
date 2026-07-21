import shlex

from src.functions.terminal import *
from src.util_objects import TerminalResult as TR

async def run_pipeline(ctx, pipeline):
    segments = [i.strip() for i in pipeline.split("|") if i.strip()]

    if not segments:
        return TR(stderr="No command provided.", exit_code=1)

    stdin = ''

    for segment in segments:
        try:
            parts = shlex.split(segment)
        except ValueError as e:
            return TR(stderr=f"shell: {e}", exit_code=2)
    
        if not parts:
            continue

        command_name = parts[0].lower().lstrip('$')
        arguments = parts[1:]

        result = await process_command(ctx, command_name, arguments, stdin)

        if not result.succeeded:
            return result

        stdin = result.stdout

    return TR(stdout=stdin, exit_code=0)

async def process_command(ctx, command_name, arguments, stdin):
    match command_name:
        case "cat":
            if len(arguments) != 1:
                return TR(stderr="usage: `cat <filename>`", exit_code=1)

            return cat(ctx.guild.id, arguments[0], stdin)

        case "grep":
            if not arguments:
                return TR(stderr="usage: `grep [filename] <pattern>`", exit_code=1)

            args = arguments if stdin else arguments[1:]

            return grep(ctx.guild.id, arguments[0], ' '.join(args), stdin)

        case "head":
            return get_lines(ctx.guild.id, ' '.join(arguments), reverse=False, stdin=stdin)

        case "tail":
            return get_lines(ctx.guild.id, ' '.join(arguments), reverse=True, stdin=stdin)
       
        case "tee":
            if not arguments:
                return TR(stderr="usage: `tee <filename> [data]`", exit_code=1)

            return tee(ctx.guild.id, arguments[0], '', stdin=stdin) 

        case "wc":
            return wc(ctx.guild.id, ' '.join(arguments), stdin=stdin)

        case _:
            return TR(stderr=f"`{command_name}` does not have pipeline support.", exit_code=2)
