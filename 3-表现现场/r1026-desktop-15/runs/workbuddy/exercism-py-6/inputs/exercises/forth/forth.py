import re


class StackUnderflowError(Exception):
    pass


_NUMBER = re.compile(r"^-?\d+$")


def _trunc_div(a, b):
    """Integer division truncating towards zero (Forth semantics)."""
    quotient = abs(a) // abs(b)
    return quotient if (a >= 0) == (b >= 0) else -quotient


def evaluate(input_data):
    stack = []
    words = {}

    def need(count):
        if len(stack) < count:
            raise StackUnderflowError("Insufficient number of items in stack")

    def binary(operation):
        need(2)
        right = stack.pop()
        left = stack.pop()
        stack.append(operation(left, right))

    def divide(left, right):
        if right == 0:
            raise ZeroDivisionError("divide by zero")
        return _trunc_div(left, right)

    builtins = {
        "+": lambda: binary(lambda a, b: a + b),
        "-": lambda: binary(lambda a, b: a - b),
        "*": lambda: binary(lambda a, b: a * b),
        "/": lambda: binary(divide),
        "dup": lambda: (need(1), stack.append(stack[-1])),
        "drop": lambda: (need(1), stack.pop()),
        "swap": lambda: (need(2), stack.extend([stack.pop(), stack.pop()])),
        "over": lambda: (need(2), stack.append(stack[-2])),
    }

    def run(tokens):
        for token in tokens:
            if _NUMBER.match(token):
                stack.append(int(token))
            elif token in words:
                run(words[token])
            elif token in builtins:
                builtins[token]()
            else:
                raise ValueError("undefined operation")

    for line in input_data:
        tokens = [token.lower() for token in line.split()]
        index = 0
        while index < len(tokens):
            token = tokens[index]
            if token == ":":
                index += 1
                if index >= len(tokens):
                    raise ValueError("illegal operation")
                name = tokens[index]
                index += 1
                body = []
                while index < len(tokens) and tokens[index] != ";":
                    body.append(tokens[index])
                    index += 1
                index += 1  # skip the closing ';'
                if _NUMBER.match(name) or name in (";", ":"):
                    raise ValueError("illegal operation")
                # Expand already-defined words now, so that redefinitions
                # do not retroactively change this definition.
                expanded = []
                for word in body:
                    if word in words:
                        expanded.extend(words[word])
                    else:
                        expanded.append(word)
                words[name] = expanded
            else:
                run([token])
                index += 1

    return stack
