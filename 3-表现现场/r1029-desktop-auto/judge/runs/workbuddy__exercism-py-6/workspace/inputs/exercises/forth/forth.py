class StackUnderflowError(Exception):
    pass


UNDERFLOW_MESSAGE = "Insufficient number of items in stack"


def _is_number(token):
    try:
        int(token)
        return True
    except ValueError:
        return False


def evaluate(input_data):
    stack = []
    words = {}

    def need(count):
        if len(stack) < count:
            raise StackUnderflowError(UNDERFLOW_MESSAGE)

    def divide(a, b):
        if b == 0:
            raise ZeroDivisionError("divide by zero")
        return int(a / b)

    def do_add():
        need(2)
        right = stack.pop()
        left = stack.pop()
        stack.append(left + right)

    def do_sub():
        need(2)
        right = stack.pop()
        left = stack.pop()
        stack.append(left - right)

    def do_mul():
        need(2)
        right = stack.pop()
        left = stack.pop()
        stack.append(left * right)

    def do_div():
        need(2)
        right = stack.pop()
        left = stack.pop()
        stack.append(divide(left, right))

    def do_dup():
        need(1)
        stack.append(stack[-1])

    def do_drop():
        need(1)
        stack.pop()

    def do_swap():
        need(2)
        stack[-1], stack[-2] = stack[-2], stack[-1]

    def do_over():
        need(2)
        stack.append(stack[-2])

    builtins = {
        "+": do_add,
        "-": do_sub,
        "*": do_mul,
        "/": do_div,
        "dup": do_dup,
        "drop": do_drop,
        "swap": do_swap,
        "over": do_over,
    }

    def expand(token):
        """Resolve a token against the words defined so far."""
        lowered = token.lower()
        if lowered in words:
            return list(words[lowered])
        return [lowered]

    def execute(tokens):
        for token in tokens:
            lowered = token.lower()
            if _is_number(lowered):
                stack.append(int(lowered))
            elif lowered in words:
                execute(words[lowered])
            elif lowered in builtins:
                builtins[lowered]()
            else:
                raise ValueError("undefined operation")

    tokens = []
    for line in input_data:
        tokens.extend(line.split())

    index = 0
    total = len(tokens)
    while index < total:
        token = tokens[index]
        if token.lower() == ":":
            end = index + 1
            while end < total and tokens[end].lower() != ";":
                end += 1
            if end >= total or index + 1 >= end:
                raise ValueError("illegal operation")
            name = tokens[index + 1].lower()
            if _is_number(name):
                raise ValueError("illegal operation")
            body = []
            for part in tokens[index + 2:end]:
                body.extend(expand(part))
            words[name] = body
            index = end + 1
        else:
            execute([token])
            index += 1

    return stack
