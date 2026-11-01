class StackUnderflowError(Exception):
    pass


def _is_number(token):
    try:
        int(token)
        return True
    except ValueError:
        return False


def _trunc_div(a, b):
    q = abs(a) // abs(b)
    if (a < 0) != (b < 0):
        q = -q
    return q


def evaluate(input_data):
    words = {}
    stack = []

    tokens = []
    for line in input_data:
        tokens.extend(line.split())

    def execute_token(token):
        low = token.lower()

        if _is_number(token):
            stack.append(int(token))
            return

        if low in words:
            for part in words[low]:
                execute_token(part)
            return

        if low == "+":
            if len(stack) < 2:
                raise StackUnderflowError("Insufficient number of items in stack")
            b = stack.pop()
            a = stack.pop()
            stack.append(a + b)
        elif low == "-":
            if len(stack) < 2:
                raise StackUnderflowError("Insufficient number of items in stack")
            b = stack.pop()
            a = stack.pop()
            stack.append(a - b)
        elif low == "*":
            if len(stack) < 2:
                raise StackUnderflowError("Insufficient number of items in stack")
            b = stack.pop()
            a = stack.pop()
            stack.append(a * b)
        elif low == "/":
            if len(stack) < 2:
                raise StackUnderflowError("Insufficient number of items in stack")
            b = stack.pop()
            a = stack.pop()
            if b == 0:
                raise ZeroDivisionError("divide by zero")
            stack.append(_trunc_div(a, b))
        elif low == "dup":
            if not stack:
                raise StackUnderflowError("Insufficient number of items in stack")
            stack.append(stack[-1])
        elif low == "drop":
            if not stack:
                raise StackUnderflowError("Insufficient number of items in stack")
            stack.pop()
        elif low == "swap":
            if len(stack) < 2:
                raise StackUnderflowError("Insufficient number of items in stack")
            stack[-1], stack[-2] = stack[-2], stack[-1]
        elif low == "over":
            if len(stack) < 2:
                raise StackUnderflowError("Insufficient number of items in stack")
            stack.append(stack[-2])
        else:
            raise ValueError("undefined operation")

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
            definition = []
            while i < len(tokens) and tokens[i] != ";":
                definition.append(tokens[i])
                i += 1
            if i >= len(tokens):
                raise ValueError("illegal operation")
            i += 1
            expanded = []
            for part in definition:
                low = part.lower()
                if low in words:
                    expanded.extend(words[low])
                else:
                    expanded.append(part)
            words[name.lower()] = expanded
        else:
            execute_token(token)
            i += 1

    return stack
