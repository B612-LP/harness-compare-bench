class StackUnderflowError(Exception):
    pass


def _is_number(token):
    try:
        int(token)
        return True
    except (TypeError, ValueError):
        return False


def _require(stack, count):
    if len(stack) < count:
        raise StackUnderflowError("Insufficient number of items in stack")


def _apply_word(word, stack):
    if _is_number(word):
        stack.append(int(word))
        return

    if word == "+":
        _require(stack, 2)
        b = stack.pop()
        a = stack.pop()
        stack.append(a + b)
    elif word == "-":
        _require(stack, 2)
        b = stack.pop()
        a = stack.pop()
        stack.append(a - b)
    elif word == "*":
        _require(stack, 2)
        b = stack.pop()
        a = stack.pop()
        stack.append(a * b)
    elif word == "/":
        _require(stack, 2)
        b = stack.pop()
        a = stack.pop()
        if b == 0:
            raise ZeroDivisionError("divide by zero")
        stack.append(int(a / b))
    elif word == "dup":
        _require(stack, 1)
        stack.append(stack[-1])
    elif word == "drop":
        _require(stack, 1)
        stack.pop()
    elif word == "swap":
        _require(stack, 2)
        stack[-1], stack[-2] = stack[-2], stack[-1]
    elif word == "over":
        _require(stack, 2)
        stack.append(stack[-2])
    else:
        raise ValueError("undefined operation")


def evaluate(input_data):
    stack = []
    definitions = {}
    in_definition = False
    expecting_name = False
    name = None
    body = []

    for line in input_data:
        for token in line.lower().split():
            if in_definition:
                if expecting_name:
                    if _is_number(token):
                        raise ValueError("illegal operation")
                    name = token
                    expecting_name = False
                elif token == ";":
                    definitions[name] = body
                    in_definition = False
                    name = None
                    body = []
                else:
                    # Compile user-defined words now so later redefinitions
                    # do not change this word's meaning.
                    if token in definitions:
                        body.extend(definitions[token])
                    else:
                        body.append(token)
                continue

            if token == ":":
                in_definition = True
                expecting_name = True
                name = None
                body = []
            elif token in definitions:
                for word in definitions[token]:
                    _apply_word(word, stack)
            else:
                _apply_word(token, stack)

    return stack
