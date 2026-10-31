class StackUnderflowError(Exception):
    pass


def _is_number(token):
    try:
        int(token)
        return True
    except ValueError:
        return False


def _pop(stack, count):
    if len(stack) < count:
        raise StackUnderflowError("Insufficient number of items in stack")
    return [stack.pop() for _ in range(count)]


def _divide(a, b):
    if b == 0:
        raise ZeroDivisionError("divide by zero")
    quotient = abs(a) // abs(b)
    return quotient if (a >= 0) == (b >= 0) else -quotient


def _apply_builtin(token, stack):
    if token == "+":
        a, b = _pop(stack, 2)
        stack.append(b + a)
    elif token == "-":
        a, b = _pop(stack, 2)
        stack.append(b - a)
    elif token == "*":
        a, b = _pop(stack, 2)
        stack.append(b * a)
    elif token == "/":
        a, b = _pop(stack, 2)
        stack.append(_divide(b, a))
    elif token == "dup":
        (a,) = _pop(stack, 1)
        stack.extend([a, a])
    elif token == "drop":
        _pop(stack, 1)
    elif token == "swap":
        a, b = _pop(stack, 2)
        stack.extend([a, b])
    elif token == "over":
        a, b = _pop(stack, 2)
        stack.extend([b, a, b])


BUILTINS = {"+", "-", "*", "/", "dup", "drop", "swap", "over"}


def _compile(tokens, words):
    """Expand user-defined words in a definition body at definition time."""
    compiled = []
    for token in tokens:
        if token in words:
            compiled.extend(words[token])
        else:
            compiled.append(token)
    return compiled


def evaluate(input_data):
    stack = []
    words = {}

    for line in input_data:
        tokens = line.lower().split()
        i = 0
        while i < len(tokens):
            token = tokens[i]
            if token == ":":
                i += 1
                if i >= len(tokens):
                    raise ValueError("illegal operation")
                name = tokens[i]
                if _is_number(name):
                    raise ValueError("illegal operation")
                i += 1
                body = []
                while i < len(tokens) and tokens[i] != ";":
                    body.append(tokens[i])
                    i += 1
                if i >= len(tokens):
                    raise ValueError("illegal operation")
                words[name] = _compile(body, words)
                i += 1
                continue

            if _is_number(token):
                stack.append(int(token))
            elif token in words:
                for inner in words[token]:
                    if _is_number(inner):
                        stack.append(int(inner))
                    elif inner in BUILTINS:
                        _apply_builtin(inner, stack)
                    else:
                        raise ValueError("undefined operation")
            elif token in BUILTINS:
                _apply_builtin(token, stack)
            else:
                raise ValueError("undefined operation")
            i += 1

    return stack
