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
    words = {}

    def pop():
        if not stack:
            raise StackUnderflowError("Insufficient number of items in stack")
        return stack.pop()

    def run(tokens):
        for token in tokens:
            t = token.upper()
            if _is_number(token):
                stack.append(int(token))
            elif t in words:
                run(words[t])
            elif t == "+":
                b, a = pop(), pop()
                stack.append(a + b)
            elif t == "-":
                b, a = pop(), pop()
                stack.append(a - b)
            elif t == "*":
                b, a = pop(), pop()
                stack.append(a * b)
            elif t == "/":
                b, a = pop(), pop()
                if b == 0:
                    raise ZeroDivisionError("divide by zero")
                stack.append(int(a / b))
            elif t == "DUP":
                a = pop()
                stack.append(a)
                stack.append(a)
            elif t == "DROP":
                pop()
            elif t == "SWAP":
                b, a = pop(), pop()
                stack.append(b)
                stack.append(a)
            elif t == "OVER":
                b = pop()
                if not stack:
                    raise StackUnderflowError(
                        "Insufficient number of items in stack"
                    )
                a = stack[-1]
                stack.append(b)
                stack.append(a)
            else:
                raise ValueError("undefined operation")

    for line in input_data:
        tokens = line.split()
        if tokens and tokens[0] == ":":
            name = tokens[1].upper()
            if _is_number(tokens[1]):
                raise ValueError("illegal operation")
            definition = tokens[2:-1]
            # Expand at definition time so later redefinitions do not
            # change the meaning of previously defined words.
            expanded = []
            for token in definition:
                if _is_number(token):
                    expanded.append(token)
                elif token.upper() in words:
                    expanded.extend(words[token.upper()])
                else:
                    expanded.append(token)
            words[name] = expanded
        else:
            run(tokens)

    return stack
