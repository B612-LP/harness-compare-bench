class StackUnderflowError(Exception):
    pass


def _is_number(token):
    try:
        int(token)
        return True
    except ValueError:
        return False


def evaluate(input_data):
    stack = []
    # definitions map upper-cased word -> list of tokens (captured at
    # definition time, so later redefinitions don't affect older words)
    definitions = {}

    def forth_div(a, b):
        if b == 0:
            raise ZeroDivisionError("divide by zero")
        # Forth integer division truncates toward zero
        q = abs(a) // abs(b)
        if (a < 0) != (b < 0):
            q = -q
        return q

    def pop():
        if not stack:
            raise StackUnderflowError("Insufficient number of items in stack")
        return stack.pop()

    def binary(op):
        if len(stack) < 2:
            raise StackUnderflowError("Insufficient number of items in stack")
        b = stack.pop()
        a = stack.pop()
        stack.append(op(a, b))

    def do_dup():
        if not stack:
            raise StackUnderflowError("Insufficient number of items in stack")
        stack.append(stack[-1])

    def do_drop():
        if not stack:
            raise StackUnderflowError("Insufficient number of items in stack")
        stack.pop()

    def do_swap():
        if len(stack) < 2:
            raise StackUnderflowError("Insufficient number of items in stack")
        stack[-1], stack[-2] = stack[-2], stack[-1]

    def do_over():
        if len(stack) < 2:
            raise StackUnderflowError("Insufficient number of items in stack")
        stack.append(stack[-2])

    builtins = {
        "+": lambda: binary(lambda a, b: a + b),
        "-": lambda: binary(lambda a, b: a - b),
        "*": lambda: binary(lambda a, b: a * b),
        "/": lambda: binary(forth_div),
        "DUP": do_dup,
        "DROP": do_drop,
        "SWAP": do_swap,
        "OVER": do_over,
    }

    def run_tokens(tokens):
        for raw in tokens:
            token = raw.upper()
            if _is_number(raw):
                stack.append(int(raw))
            elif token in definitions:
                run_tokens(definitions[token])
            elif token in builtins:
                builtins[token]()
            else:
                raise ValueError("undefined operation")

    for line in input_data:
        tokens = line.split()
        if tokens and tokens[0] == ":":
            # definition: : name body... ;
            if len(tokens) < 4 or tokens[-1] != ";":
                raise ValueError("illegal operation")
            name = tokens[1]
            if _is_number(name):
                raise ValueError("illegal operation")

            # Expand user-defined words at definition time (snapshot
            # semantics), before installing the new definition.
            def expand(ts):
                out = []
                for raw in ts:
                    upper = raw.upper()
                    if upper in definitions:
                        out.extend(expand(definitions[upper]))
                    else:
                        out.append(raw)
                return out

            definitions[name.upper()] = expand(tokens[2:-1])
        else:
            run_tokens(tokens)

    return stack
