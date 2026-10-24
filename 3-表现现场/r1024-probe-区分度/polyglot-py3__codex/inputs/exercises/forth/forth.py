class StackUnderflowError(Exception):
    pass


def evaluate(input_data):
    tokens = " ".join(input_data).lower().split()
    stack = []
    words = {}

    def require(count):
        if len(stack) < count:
            raise StackUnderflowError("Insufficient number of items in stack")

    def apply(operation):
        if operation == "+":
            require(2)
            right = stack.pop()
            left = stack.pop()
            stack.append(left + right)
        elif operation == "-":
            require(2)
            right = stack.pop()
            left = stack.pop()
            stack.append(left - right)
        elif operation == "*":
            require(2)
            right = stack.pop()
            left = stack.pop()
            stack.append(left * right)
        elif operation == "/":
            require(2)
            right = stack.pop()
            left = stack.pop()
            if right == 0:
                raise ZeroDivisionError("divide by zero")
            quotient = abs(left) // abs(right)
            stack.append(-quotient if (left < 0) != (right < 0) else quotient)
        elif operation == "dup":
            require(1)
            stack.append(stack[-1])
        elif operation == "drop":
            require(1)
            stack.pop()
        elif operation == "swap":
            require(2)
            stack[-2], stack[-1] = stack[-1], stack[-2]
        elif operation == "over":
            require(2)
            stack.append(stack[-2])
        else:
            raise ValueError("undefined operation")

    def compile_token(token):
        try:
            return [int(token)]
        except ValueError:
            pass
        if token in words:
            return list(words[token])
        if token in {"+", "-", "*", "/", "dup", "drop", "swap", "over"}:
            return [token]
        return [token]

    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token == ":":
            index += 1
            if index >= len(tokens):
                raise ValueError("illegal operation")
            name = tokens[index]
            try:
                int(name)
            except ValueError:
                pass
            else:
                raise ValueError("illegal operation")

            index += 1
            body = []
            while index < len(tokens) and tokens[index] != ";":
                body.extend(compile_token(tokens[index]))
                index += 1
            if index >= len(tokens):
                raise ValueError("illegal operation")
            words[name] = body
        else:
            try:
                stack.append(int(token))
            except ValueError:
                if token in words:
                    for operation in words[token]:
                        if isinstance(operation, int):
                            stack.append(operation)
                        else:
                            apply(operation)
                else:
                    apply(token)
        index += 1

    return stack
