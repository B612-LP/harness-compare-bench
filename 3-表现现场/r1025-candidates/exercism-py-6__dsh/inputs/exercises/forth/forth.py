class StackUnderflowError(Exception):
    pass


UNDERFLOW = "Insufficient number of items in stack"


def _is_number(token):
    try:
        int(token)
    except ValueError:
        return False
    return True


def _pop_many(stack, count):
    if len(stack) < count:
        raise StackUnderflowError(UNDERFLOW)


def _execute(token, stack):
    if _is_number(token):
        stack.append(int(token))
        return

    if token == "+":
        _pop_many(stack, 2)
        right = stack.pop()
        left = stack.pop()
        stack.append(left + right)
    elif token == "-":
        _pop_many(stack, 2)
        right = stack.pop()
        left = stack.pop()
        stack.append(left - right)
    elif token == "*":
        _pop_many(stack, 2)
        right = stack.pop()
        left = stack.pop()
        stack.append(left * right)
    elif token == "/":
        _pop_many(stack, 2)
        right = stack.pop()
        left = stack.pop()
        if right == 0:
            raise ZeroDivisionError("divide by zero")
        quotient = abs(left) // abs(right)
        if (left < 0) != (right < 0):
            quotient = -quotient
        stack.append(quotient)
    elif token == "dup":
        _pop_many(stack, 1)
        stack.append(stack[-1])
    elif token == "drop":
        _pop_many(stack, 1)
        stack.pop()
    elif token == "swap":
        _pop_many(stack, 2)
        stack[-1], stack[-2] = stack[-2], stack[-1]
    elif token == "over":
        _pop_many(stack, 2)
        stack.append(stack[-2])
    else:
        raise ValueError("undefined operation")


def evaluate(input_data):
    tokens = " ".join(input_data).lower().split()
    definitions = {}
    stack = []
    index = 0

    while index < len(tokens):
        token = tokens[index]
        if token == ":":
            index += 1
            if index >= len(tokens):
                raise ValueError("illegal operation")
            name = tokens[index]
            if _is_number(name):
                raise ValueError("illegal operation")
            index += 1
            body = []
            while index < len(tokens) and tokens[index] != ";":
                part = tokens[index]
                if part in definitions:
                    body.extend(definitions[part])
                else:
                    body.append(part)
                index += 1
            if index >= len(tokens):
                raise ValueError("illegal operation")
            definitions[name] = body
            index += 1
            continue

        if token in definitions:
            for part in definitions[token]:
                _execute(part, stack)
        else:
            _execute(token, stack)
        index += 1

    return stack
