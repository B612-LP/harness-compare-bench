"""forth 参考解：极简 Forth 解释器（数字、四则、栈操作、用户自定义词）。"""


class StackUnderflowError(Exception):
    pass


BUILTIN_NAMES = ("+", "-", "*", "/", "dup", "drop", "swap", "over")


def _as_int(token):
    """是整数就返回 int，否则返回 None（负数带前导 '-' 也算数字）。"""
    try:
        return int(token)
    except (TypeError, ValueError):
        return None


def evaluate(input_data):
    stack = []
    words = {}  # name(lowercase) -> 已编译的 op 列表
    tokens = []
    for line in input_data:
        tokens.extend(str(line).split())

    def need(n):
        if len(stack) < n:
            raise StackUnderflowError("Insufficient number of items in stack")

    def do_builtin(name):
        if name == "dup":
            need(1)
            stack.append(stack[-1])
        elif name == "drop":
            need(1)
            stack.pop()
        elif name == "swap":
            need(2)
            stack[-1], stack[-2] = stack[-2], stack[-1]
        elif name == "over":
            need(2)
            stack.append(stack[-2])
        else:
            need(2)
            right = stack.pop()
            left = stack.pop()
            if name == "+":
                stack.append(left + right)
            elif name == "-":
                stack.append(left - right)
            elif name == "*":
                stack.append(left * right)
            else:  # "/"
                if right == 0:
                    raise ZeroDivisionError("divide by zero")
                quotient = abs(left) // abs(right)
                if (left < 0) != (right < 0):
                    quotient = -quotient
                stack.append(quotient)

    def run(ops):
        for kind, value in ops:
            if kind == "num":
                stack.append(value)
            elif kind == "op":
                do_builtin(value)
            else:  # "word"：定义时未解析的引用，执行时再查
                if value in words:
                    run(words[value])
                elif value in BUILTIN_NAMES:
                    do_builtin(value)
                else:
                    raise ValueError("undefined operation")

    def compile_body(body_tokens):
        ops = []
        for token in body_tokens:
            number = _as_int(token)
            if number is not None:
                ops.append(("num", number))
            elif token in words:
                ops.extend(words[token])  # 快照展开：重定义不影响已定义词
            elif token in BUILTIN_NAMES:
                ops.append(("op", token))
            else:
                ops.append(("word", token))
        return ops

    index = 0
    while index < len(tokens):
        token = tokens[index].lower()
        if token == ":":
            index += 1
            if index >= len(tokens):
                raise ValueError("illegal operation")
            name = tokens[index].lower()
            if _as_int(name) is not None:
                raise ValueError("illegal operation")
            body = []
            index += 1
            while index < len(tokens) and tokens[index] != ";":
                body.append(tokens[index].lower())
                index += 1
            if index >= len(tokens):
                raise ValueError("illegal operation")
            words[name] = compile_body(body)
            index += 1
            continue

        number = _as_int(token)
        if number is not None:
            stack.append(number)
        elif token in words:
            run(words[token])
        elif token in BUILTIN_NAMES:
            do_builtin(token)
        else:
            raise ValueError("undefined operation")
        index += 1

    return stack