class StackUnderflowError(Exception):
    pass


BUILTINS = {"+", "-", "*", "/", "dup", "drop", "swap", "over"}


def _underflow():
    raise StackUnderflowError("Insufficient number of items in stack")


def _execute_builtin(op, stack):
    if op in {"+", "-", "*", "/"}:
        if len(stack) < 2:
            _underflow()
        b = stack.pop()
        a = stack.pop()
        if op == "+":
            stack.append(a + b)
        elif op == "-":
            stack.append(a - b)
        elif op == "*":
            stack.append(a * b)
        elif op == "/":
            if b == 0:
                raise ZeroDivisionError("divide by zero")
            stack.append(int(a / b))
    elif op == "dup":
        if len(stack) < 1:
            _underflow()
        stack.append(stack[-1])
    elif op == "drop":
        if len(stack) < 1:
            _underflow()
        stack.pop()
    elif op == "swap":
        if len(stack) < 2:
            _underflow()
        stack[-1], stack[-2] = stack[-2], stack[-1]
    elif op == "over":
        if len(stack) < 2:
            _underflow()
        stack.append(stack[-2])


def _execute_token(token, stack, words, top_level):
    if isinstance(token, int):
        stack.append(token)
        return

    try:
        stack.append(int(token))
        return
    except (TypeError, ValueError):
        pass

    low = token.lower()

    if top_level and low in words:
        for item in words[low]:
            _execute_token(item, stack, words, False)
        return

    if low in BUILTINS:
        _execute_builtin(low, stack)
        return

    raise ValueError("undefined operation")


def evaluate(input_data):
    tokens = []
    for line in input_data:
        tokens.extend(line.split())

    words = {}
    stack = []
    i = 0

    while i < len(tokens):
        token = tokens[i]

        if token == ":":
            i += 1
            if i >= len(tokens):
                raise ValueError("illegal operation")

            name_token = tokens[i]
            try:
                int(name_token)
                raise ValueError("illegal operation")
            except ValueError:
                pass

            name = name_token.lower()
            i += 1

            body_tokens = []
            while i < len(tokens) and tokens[i] != ";":
                body_tokens.append(tokens[i])
                i += 1

            if i >= len(tokens) or tokens[i] != ";":
                raise ValueError("illegal operation")
            i += 1

            expanded = []
            for body_token in body_tokens:
                try:
                    expanded.append(int(body_token))
                except ValueError:
                    low = body_token.lower()
                    if low in words:
                        expanded.extend(words[low])
                    elif low in BUILTINS:
                        expanded.append(low)
                    else:
                        expanded.append(low)

            words[name] = expanded
        else:
            _execute_token(token, stack, words, True)
            i += 1

    return stack
