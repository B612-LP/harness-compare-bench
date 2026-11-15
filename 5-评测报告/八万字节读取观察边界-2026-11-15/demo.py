"""公开汇总算术与独立合成样例；不读取私档，不回放真实请求。"""

SOURCE_BYTES = 80_000
LINE_COUNT = 945
PREFIX_BYTES = 7
RESULT_BYTES = 86_615
FIRST_PROMPT_TOKENS = 28_793
LAST_PROMPT_TOKENS = 80_034
FIRST_CACHE = 0
LAST_CACHE = 7_552


def summary():
    """仅重算给定摘要，不代表对原始记录的验证。"""
    return {
        "prompt_delta": LAST_PROMPT_TOKENS - FIRST_PROMPT_TOKENS,
        "cache_delta": LAST_CACHE - FIRST_CACHE,
        # 80000/2.5 用精确整数算式表达，再取 0.9；不是请求体核验。
        "old_gate": (SOURCE_BYTES * 2 // 5) * 9 // 10,
        "formula_only_20k": SOURCE_BYTES // 4,
        "prefix_overhead": PREFIX_BYTES * LINE_COUNT,
        "observed_local_overhead": RESULT_BYTES - SOURCE_BYTES,
    }


def make_synthetic_source():
    """生成全新 ASCII 样例，恰为 80000B、945 行、无末尾 LF。"""
    body_bytes = SOURCE_BYTES - (LINE_COUNT - 1)
    base, extra = divmod(body_bytes, LINE_COUNT)
    lines = [b"x" * (base + (i < extra)) for i in range(LINE_COUNT)]
    return b"\n".join(lines)


def add_synthetic_prefixes(source):
    """仅处理本模拟的 LF 分行字节；每行加六位序号和空格。"""
    lines = source.split(b"\n")
    if len(lines) != LINE_COUNT or source.endswith(b"\n"):
        raise ValueError("simulation requires 945 lines and no trailing LF")
    return b"\n".join(f"{i:06d} ".encode("ascii") + line
                      for i, line in enumerate(lines, 1))


def strip_synthetic_prefixes(numbered):
    """校验模拟前缀序号后剥除，非对真实工具格式的复刻。"""
    lines = numbered.split(b"\n")
    if len(lines) != LINE_COUNT or numbered.endswith(b"\n"):
        raise ValueError("simulation requires 945 lines and no trailing LF")
    bodies = []
    for i, line in enumerate(lines, 1):
        expected = f"{i:06d} ".encode("ascii")
        if line[:PREFIX_BYTES] != expected:
            raise ValueError("invalid synthetic line prefix")
        bodies.append(line[PREFIX_BYTES:])
    return b"\n".join(bodies)


def main():
    values = summary()
    synthetic = make_synthetic_source()
    numbered = add_synthetic_prefixes(synthetic)
    print("公开摘要算术（不验证私档）：")
    for name, value in values.items():
        print(f"{name}: {value}")
    print("独立合成（不是历史输入或请求）：")
    print(f"source_bytes: {len(synthetic)}; lines: {len(synthetic.splitlines())}")
    print(f"numbered_bytes: {len(numbered)}; trailing_lf: {synthetic.endswith(bytes([10]))}")
    print(f"synthetic_round_trip: {strip_synthetic_prefixes(numbered) == synthetic}")


if __name__ == "__main__":
    main()
