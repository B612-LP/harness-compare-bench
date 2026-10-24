class StackUnderflowError(Exception):
    pass


def evaluate(input_data):
    tokens = " ".join(input_data).split()
    stack = []
    definitions = {}

    def require(count):
        if len(stack) < count:
            raise StackUnderflowError("Insufficient number of items in stack")

    def is_number(token):
        try:
            int(token)
        except ValueError:
            return False
        return True

    def execute(word):
        if word in definitions:
            for definition_word in definitions[word]:
                execute(definition_word)
            return

        if is_number(word):
            stack.append(int(word))
            return

        if word == "+":
            require(2)
            right = stack.pop()
            left = stack.pop()
            stack.append(left + right)
        elif word == "-":
            require(2)
            right = stack.pop()
            left = stack.pop()
            stack.append(left - right)
        elif word == "*":
            require(2)
            right = stack.pop()
            left = stack.pop()
            stack.append(left * right)
        elif word == "/":
            require(2)
            divisor = stack.pop()
            dividend = stack.pop()
            if divisor == 0:
                raise ZeroDivisionError("divide by zero")
            quotient = abs(dividend) // abs(divisor)
            stack.append(-quotient if (dividend < 0) != (divisor < 0) else quotient)
        elif word == "dup":
            require(1)
            stack.append(stack[-1])
        elif word == "drop":
            require(1)
            stack.pop()
        elif word == "swap":
            require(2)
            stack[-2], stack[-1] = stack[-1], stack[-2]
        elif word == "over":
            require(2)
            stack.append(stack[-2])
        elif word == ":" or word == ";":
            raise ValueError("illegal operation")
        else:
            raise ValueError("undefined operation")

    index = 0
    while index < len(tokens):
        word = tokens[index].lower()

        if word == ":":
            if index + 1 >= len(tokens):
                raise ValueError("illegal operation")

            name = tokens[index + 1].lower()
            if is_number(name):
                raise ValueError("illegal operation")

            try:
                end = tokens.index(";", index + 2)
            except ValueError:
                raise ValueError("illegal operation")

            body = []
            for raw_body_word in tokens[index + 2 : end]:
                body_word = raw_body_word.lower()
                if body_word in definitions:
                    body.extend(definitions[body_word])
                elif body_word in (":", ";"):
                    raise ValueError("illegal operation")
                else:
                    body.append(body_word)

            definitions[name] = body
            index = end + 1
        elif word == ";":
            raise ValueError("illegal operation")
        else:
            execute(word)
            index += 1

    return stack
