class StackUnderflowError(Exception):
    pass


def _to_int(token):
    try:
        return int(token)
    except (TypeError, ValueError):
        return None


def _pop(stack, count=1):
    if len(stack) < count:
        raise StackUnderflowError("Insufficient number of items in stack")


def _div(stack):
    _pop(stack, 2)
    divisor = stack.pop()
    dividend = stack.pop()
    if divisor == 0:
        raise ZeroDivisionError("divide by zero")
    quotient = abs(dividend) // abs(divisor)
    if (dividend < 0) != (divisor < 0):
        quotient = -quotient
    stack.append(quotient)


def _add(stack):
    _pop(stack, 2)
    b = stack.pop()
    a = stack.pop()
    stack.append(a + b)


def _sub(stack):
    _pop(stack, 2)
    b = stack.pop()
    a = stack.pop()
    stack.append(a - b)


def _mul(stack):
    _pop(stack, 2)
    b = stack.pop()
    a = stack.pop()
    stack.append(a * b)


def _dup(stack):
    _pop(stack, 1)
    stack.append(stack[-1])


def _drop(stack):
    _pop(stack, 1)
    stack.pop()


def _swap(stack):
    _pop(stack, 2)
    stack[-2], stack[-1] = stack[-1], stack[-2]


def _over(stack):
    _pop(stack, 2)
    stack.append(stack[-2])


BUILTINS = {
    "+": _add,
    "-": _sub,
    "*": _mul,
    "/": _div,
    "dup": _dup,
    "drop": _drop,
    "swap": _swap,
    "over": _over,
}


def _compile(body, words):
    """Expand a definition body into a flat instruction list.

    Instructions are ("push", int) or ("op", callable). Words are resolved
    at definition time so a later redefinition does not change words already
    defined (and a self reference resolves to the previous definition).
    """
    instructions = []
    for token in body:
        number = _to_int(token)
        if number is not None:
            instructions.append(("push", number))
            continue
        if token in words:
            instructions.extend(words[token])
            continue
        if token in BUILTINS:
            instructions.append(("op", BUILTINS[token]))
            continue
        raise ValueError("undefined operation")
    return instructions


def evaluate(input_data):
    stack = []
    words = {}

    tokens = []
    for line in input_data:
        tokens.extend(line.split())

    i = 0
    while i < len(tokens):
        token = tokens[i].lower()
        i += 1

        if token == ":":
            if i >= len(tokens):
                raise ValueError("illegal operation")
            name = tokens[i].lower()
            i += 1
            if _to_int(name) is not None:
                raise ValueError("illegal operation")
            body = []
            while i < len(tokens) and tokens[i] != ";":
                body.append(tokens[i].lower())
                i += 1
            if i >= len(tokens):
                raise ValueError("illegal operation")
            i += 1  # skip ";"
            words[name] = _compile(body, dict(words))

        elif token == ";":
            raise ValueError("illegal operation")

        else:
            number = _to_int(token)
            if number is not None:
                stack.append(number)
            elif token in words:
                for kind, payload in words[token]:
                    if kind == "push":
                        stack.append(payload)
                    else:
                        payload(stack)
            elif token in BUILTINS:
                BUILTINS[token](stack)
            else:
                raise ValueError("undefined operation")

    return stack
