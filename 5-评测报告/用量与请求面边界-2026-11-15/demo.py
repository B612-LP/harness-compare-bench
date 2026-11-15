#!/usr/bin/env python3
"""离线数学示意；输入为匿名固定摘要或人工合成，并非历史请求。"""


def old_threshold(size):
    """复现旧分类器的两次向零取整（仅用于非负尺寸）。"""
    if not isinstance(size, int) or isinstance(size, bool) or size < 0:
        raise ValueError("size must be a nonnegative integer")
    return int(int(size / 2.5) * 0.9)


def synthetic_projection(text):
    """演示：只保留长度、前两个字符、末两个字符的人工观测。"""
    return (len(text), text[:2], text[-2:])


def examples():
    # 两个不同的合成字符串在这个人为的投影下不可区分；非真实模型请求。
    full_a = "AA" + "x" * 8 + "ZZ"
    full_b = "AA" + "y" * 8 + "ZZ"
    return full_a, full_b


def main():
    pairs = [(28794, 70733), (28848, 70836)]
    for before, after in pairs:
        print(f"{after} - {before} = {after - before}")
    print(f"旧分类阈值: {old_threshold(65504)}")
    a, b = examples()
    print(f"合成投影相同: {synthetic_projection(a) == synthetic_projection(b)}; 原串不同: {a != b}")
    print("仅算术与合成演示；不验证私档，不重建历史请求。")


if __name__ == "__main__":
    main()
