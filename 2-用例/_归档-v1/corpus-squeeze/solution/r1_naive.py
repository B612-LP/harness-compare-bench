#!/usr/bin/env python3
"""corpus-squeeze 参考解 R1：朴素 RLE（负对照，预期 ratio 不达标）。

用法：
    python3 r1_naive.py <corpus.txt> <out_dir>

产物：
    <out_dir>/compressed.bin   PackBits 风格 RLE（头 4 字节 magic + 4 字节原始长度）
    <out_dir>/decompress.py    独立解压器（仅依赖标准库，只读 argv 传入的压缩包）

用途：oracle 负对照 —— checker 判分必须 reward=0（ratio 超标），
且失败项应只有 ratio（roundtrip 与静态扫描均应通过）。
"""
import sys
from pathlib import Path

MAGIC = b"CSQ1"

DECOMPRESSOR_SOURCE = '''#!/usr/bin/env python3
# R1 naive reference decompressor (PackBits-style RLE, standalone).
import sys


def main():
    src = open(sys.argv[1], "rb").read()
    if src[:4] != b"CSQ1":
        sys.exit("bad magic")
    n = int.from_bytes(src[4:8], "big")
    out = bytearray()
    i = 8
    L = len(src)
    while len(out) < n:
        if i >= L:
            raise ValueError("truncated stream")
        c = src[i]
        i += 1
        if c < 128:
            k = c + 1
            if i + k > L:
                raise ValueError("truncated literal packet")
            out += src[i:i + k]
            i += k
        else:
            k = c - 125
            if i >= L:
                raise ValueError("truncated repeat packet")
            out += bytes([src[i]]) * k
            i += 1
    if len(out) != n:
        raise ValueError("length mismatch")
    sys.stdout.buffer.write(bytes(out))


main()
'''


def compress(data: bytes) -> bytes:
    n = len(data)
    out = bytearray(MAGIC + n.to_bytes(4, "big"))
    i = 0
    while i < n:
        b = data[i]
        run = 1
        while i + run < n and data[i + run] == b and run < 130:
            run += 1
        if run >= 3:
            out.append(128 + run - 3)
            out.append(b)
            i += run
            continue
        # 字面包：直到遇到 >=3 的连续段或 128 上限
        j = i
        while j < n and j - i < 128:
            nb = data[j]
            r = 1
            while j + r < n and data[j + r] == nb and r < 3:
                r += 1
            if r >= 3:
                break
            j += 1
        packet = data[i:j]
        out.append(len(packet) - 1)
        out += packet
        i = j
    return bytes(out)


def main(argv):
    if len(argv) != 3:
        print("usage: python3 r1_naive.py <corpus.txt> <out_dir>", file=sys.stderr)
        return 2
    src = Path(argv[1])
    out_dir = Path(argv[2])
    out_dir.mkdir(parents=True, exist_ok=True)
    data = src.read_bytes()
    blob = compress(data)
    (out_dir / "compressed.bin").write_bytes(blob)
    (out_dir / "decompress.py").write_text(DECOMPRESSOR_SOURCE, encoding="utf-8")
    print("R1 naive: corpus=%d bytes -> compressed=%d bytes (ratio %.4f)"
          % (len(data), len(blob), len(blob) / len(data)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
