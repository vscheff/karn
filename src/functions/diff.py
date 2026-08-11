from difflib import SequenceMatcher
from re import sub

from src.utils import get_flags, get_lines_from_file
from src.util_objects import TerminalResult as TR


DEFAULT_CONTEXT_LINES = 3


def is_blank_change(opcode, left, right):
    _, i1, i2, j1, j2 = opcode

    return all(not line.strip() for line in left[i1:i2] + right[j1:j2])

def format_normal_diff(matcher, left, right, ignore_blank_lines=False):
    def format_range(start, stop):
        if (first := start + 1) == stop:
            return str(first)

        return f"{first},{stop}"

    output = []

    for opcode in matcher.get_opcodes():
        tag, i1, i2, j1, j2 = opcode

        if tag == "equal" or (ignore_blank_lines and is_blank_change(opcode, left, right)):
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

def format_unified_diff(matcher, left, right, left_name, right_name, context, ignore_blank_lines=False):
    def format_range(start, stop):
        length = stop - start

        return f"{start},0" if length == 0 else str(start + 1) if length == 1 else f"{start + 1},{length}"

    groups = list(matcher.get_grouped_opcodes(context))

    if ignore_blank_lines:
        def has_nonblank_change(group, left, right):
            return any(opcode[0] != "equal" and not is_blank_change(opcode, left, right) for opcode in group)

        groups = [group for group in groups if has_nonblank_change(group, left, right)]

    if not groups:
        return ''

    output = [f"--- {left_name}\n", f"+++ {right_name}\n"]
    
    for group in groups:
        first = group[0]
        last = group[-1]

        output.append(f"@@ -{format_range(first[1], last[2])} +{format_range(first[3], last[4])} @@\n")

        for tag, i1, i2, j1, j2 in group:
            if tag == "equal":
                output.extend(f" {line}" for line in left[i1:i2])
            elif tag == "delete":
                output.extend(f"-{line}" for line in left[i1:i2])
            elif tag == "insert":
                output.extend(f"+{line}" for line in right[j1:j2])
            elif tag == "replace":
                output.extend(f"-{line}" for line in left[i1:i2])
                output.extend(f"+{line}" for line in right[j1:j2])

    return ''.join(output)

def normalize_line(line, ignore_case=False, ignore_space_changes=False, ignore_all_space=False):
    has_newline = line.endswith('\n')
    content = line.rstrip('\n')

    if ignore_all_space:
        content = sub(r"\s+", '', content)
    elif ignore_space_changes:
        content = sub(r"\s+", ' ', content).strip()

    if ignore_case:
        content = content.casefold()

    return content + ('\n' if has_newline else '')

def diff(guild_id, arguments, stdin=None):
    flags, args = get_flags(arguments, make_dic=True, no_args=['B', 'b', 'i', 'u', 'w'])

    if len(args) != 2:
        return TR(stderr="You must provide exactly two files.\nUse `$help diff` for more usage information.", exit_code=2)

    left = get_lines_from_file(guild_id, args[0], stdin=stdin if args[0] == '-' else None)

    if not left.succeeded:
        return left

    right = get_lines_from_file(guild_id, args[1], stdin=stdin if args[1] == '-' else None)

    if not right.succeeded:
        return right
    
    ignore_blank_lines = 'B' in flags
    ignore_space_changes = 'b' in flags
    ignore_case = 'i' in flags
    ignore_all_space = 'w' in flags
    compare_left = [normalize_line(line, ignore_case, ignore_space_changes, ignore_all_space) for line in left.stdout]
    compare_right = [normalize_line(line, ignore_case, ignore_space_changes, ignore_all_space) for line in right.stdout]
    matcher = SequenceMatcher(None, compare_left, compare_right)

    if 'u' in flags or 'U' in flags:
        try:
            if (context_lines := int(flags.get('U', DEFAULT_CONTEXT_LINES))) < 0:
                raise ValueError
        except ValueError:
            return TR(stderr="Bad subargument given for context lines. Please only use valid nonnegative integers.\n"
                             "Use `$help nl` for more information.",
                      exit_code=2)

        output = format_unified_diff(matcher, left.stdout, right.stdout, args[0], args[1], context_lines, ignore_blank_lines=ignore_blank_lines)
    else:
        output = format_normal_diff(matcher, left.stdout, right.stdout, ignore_blank_lines=ignore_blank_lines)

    return TR(stdout=output, formatted_output=f"```text\n{output}\n```" if output else None, exit_code=1 if output else 0)
