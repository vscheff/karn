from io import StringIO
import tokenize as t


EXCLUDED_DIRS = {".git", ".venv", "venv", "__pycache__"}


def count_physical_lines(path):
    with path.open('r') as infile:
        return sum(1 for _ in infile)

def count_significant_lines(path):
    source = path.read_text()
    ignored_tokens = {t.ENCODING, t.COMMENT, t.NL, t.NEWLINE, t.INDENT, t.DEDENT, t.ENDMARKER}
    lines = set()

    try:
        tokens = t.generate_tokens(StringIO(source).readline)

        for token in tokens:
            if token.type not in ignored_tokens:
                lines.update(range(token.start[0], token.end[0] + 1))
    except (IndentationError, t.TokenError, SyntaxError):
        return 0
    
    return len(lines)

def count_project_lines(root):
    files =  [i for i in root.rglob("*.py") if not any(j in EXCLUDED_DIRS for j in i.parts)]
    physical_lines = sum(count_physical_lines(i) for i in files)
    significant_lines = sum(count_significant_lines(i) for i in files)

    return len(files), physical_lines, significant_lines
