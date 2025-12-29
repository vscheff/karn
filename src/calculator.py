from math import acos, asin, atan, cos, degrees, e, factorial, log, log10, pi, radians, sin, tan
from random import random
from re import findall, fullmatch, IGNORECASE


FUNCS = {"log", "ln", "sin", "cos", "tan", "asin", "acos", "atan", "sqrt", "abs", "rand", "answer", "deg", "rad"}
CONST = {"pi", "e", "tau"}

def calculator(expression):
    prec = {'+': 0, '-': 0, '*': 1, '/': 1, '%': 1, 'u-': 2, '^': 3, '!': 4}
    right_assoc = {'^': True, 'u-': True}

    # https://regex101.com/r/rYoPQz/2
    tokens = findall(rf"\d+\.?\d*|{'|'.join(CONST)}|{'|'.join(FUNCS)}|[+\-/*%()^!]", expression.replace(' ', ''), flags=IGNORECASE)
    tokens = inject_implicit_mul([i.lower() for i in tokens])

    def should_pop(top, incoming):
        if top in "()":
            return False
        
        if incoming == "u-" and top == '^':
            return False

        prec_t, prec_i = prec.get(top, -1), prec.get(incoming, -1)

        if prec_t > prec_i:
            return True

        if prec_t == prec_i and not right_assoc.get(incoming, False):
            return True

        return False

    values, ops = [], []
    prev = None

    # Shunting Yard alrorithm
    for token in tokens:
        if (result := get_as_number(token)) is not False:
            values.append(result)
            prev = "num"
            continue

        if token in FUNCS:
            ops.append(token)
            prev = "op"
            continue
        
        if token == '!':
            apply_operator(['!'], values)
            prev = "num"
            continue;

        if token == '(':
            ops.append(token)
            prev = token
            continue

        if token == ')':
            while ops and ops[-1] != '(':
                apply_operator(ops, values)

            ops.pop()

            if ops and ops[-1] in FUNCS:
                apply_operator(ops, values)

            prev = token
            continue

        if token == '-' and (prev is None or prev in ("op", '(')):
            token = "u-"

        while ops and should_pop(ops[-1], token):
            apply_operator(ops, values)

        ops.append(token)
        prev = 'op'

    while ops:
        apply_operator(ops, values)

    return format_result(values[0])

def is_number(tok):
    return fullmatch(r"\d+\.?\d*", tok) is not None or tok in CONST

def is_value(tok):
    return tok == ')' or is_number(tok)

def starts_value(tok):
    return tok == '(' or tok in FUNCS or is_number(tok)

def inject_implicit_mul(tokens):
    out = []

    for tok in tokens:
        if out:
            prev = out[-1]

            if is_value(prev) and starts_value(tok):
                out.append('*')

        out.append(tok)

    return out

def get_as_number(string):
    string = string.lower()

    if string == "pi":
        return pi

    if string == 'e':
        return e

    if string == "tau":
        return pi * 2

    try:
        return int(string)
    except ValueError:
        try:
            return float(string)
        except ValueError:
            return False

def apply_operator(ops, values):
    op = ops.pop()

    if op == '!':
        val = values.pop()
        
        if not float(val).is_integer() or val < 0:
            raise ValueError("Factorial is only defined for non-negative integers")

        values.append(factorial(int(val)))
        
        return

    if op == "ln":
        values.append(log(values.pop())); return
    if op == "log":
        values.append(log10(values.pop())); return
    if op == "sin":
        values.append(sin(values.pop())); return
    if op == "cos":
        values.append(cos(values.pop())); return
    if op == "tan":
        values.append(tan(values.pop())); return
    if op == "asin":
        values.append(asin(values.pop())); return
    if op == "acos":
        values.append(acos(values.pop())); return
    if op == "atan":
        values.append(atan(values.pop())); return
    if op == "sqrt":
        values.append(values.pop() ** 0.5); return
    if op == "abs":
        values.append(abs(values.pop())); return
    if op == "rand":
        values.append(random()); return
    if op == "answer":
        values.append(42); return
    if op == "deg":
        values.append(degrees(values.pop())); return
    if op == "rad":
        values.append(radians(values.pop())); return
    if op == "u-":
        values.append(-1 * values.pop()); return

    right = values.pop()
    left = values.pop()

    if op == '+':
        values.append(left + right)
    elif op == '-':
        values.append(left - right)
    elif op == '*':
        values.append(left * right)
    elif op == '/':
        values.append(left / right)
    elif op == '^':
        values.append(left ** right)
    elif op == "%":
        values.append(left % right)
    else:
        raise ValueError(f"Unknown operator: {op}")

def format_result(x, sig=15, eps=1e-12):
    if abs(x) < eps:
        return "0"

    nearest = round(x)

    if abs(x - nearest) < eps * max(1.0, abs(x)):
        return str(nearest)

    s = format(x, f".{sig}g")

    if "e" not in s and "." in s:
        s = s.rstrip("0").rstrip(".")
    
    return s
