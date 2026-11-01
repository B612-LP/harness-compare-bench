import re


class StackUnderflowError(Exception):
    pass


NUMBER_RE = re.compile(r"^-?\d+$")


def _require(stack, n):
    if len(stack) < n:
        raise StackUnderflowError("Insufficient number of items in stack")


def _binary(stack, op):
    _require(stack, 2)
    b = stack.pop()
    a = stack.pop()
    stack.append(op(a, b))


def _add(a, b):
    return a + b


def _sub(a, b):
    return a - b


def _mul(a, b):
    return a * b


def _div(a, b):
    if b == 0:
        raise ZeroDivisionError("divide by zero")
    return a // b


def _dup(stack):
    _require(stack, 1)
    stack.append(stack[-1])


def _drop(stack):
    _require(stack, 1)
    stack.pop()


def _swap(stack):
    _require(stack, 2)
    stack[-1], stack[-2] = stack[-2], stack[-1]


def _over(stack):
    _require(stack, 2)
    stack.append(stack[-2])


BUILTINS = {
    "+": lambda s: _binary(s, _add),
    "-": lambda s: _binary(s, _sub),
    "*": lambda s: _binary(s, _mul),
    "/": lambda s: _binary(s, _div),
    "DUP": _dup,
    "DROP": _drop,
    "SWAP": _swap,
    "OVER": _over,
}


def _execute(token, stack, words):
    if NUMBER_RE.match(token):
        stack.append(int(token))
        return
    name = token.upper()
    if name in words:
        for t in words[name]:
            _execute(t, stack, words)
        return
    if name in BUILTINS:
        BUILTINS[name](stack)
        return
    raise ValueError("undefined operation")


def evaluate(input_data):
    tokens = " ".join(input_data).split()
    stack = []
    words = {}
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if token == ":":
            j = i + 1
            body = []
            while j < len(tokens) and tokens[j] != ";":
                body.append(tokens[j])
                j += 1
            if j >= len(tokens) or not body:
                raise ValueError("illegal operation")
            name = body[0]
            if NUMBER_RE.match(name):
                raise ValueError("illegal operation")
            expanded = []
            for t in body[1:]:
                if NUMBER_RE.match(t):
                    expanded.append(t)
                else:
                    up = t.upper()
                    if up in words:
                        expanded.extend(words[up])
                    else:
                        expanded.append(t)
            words[name.upper()] = expanded
            i = j + 1
            continue
        _execute(token, stack, words)
        i += 1
    return stack
