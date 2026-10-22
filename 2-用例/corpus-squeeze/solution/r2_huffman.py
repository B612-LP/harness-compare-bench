#!/usr/bin/env python3
"""corpus-squeeze 参考解 R2：LZ77 + 自实现 canonical Huffman（stdlib-only 正对照）。

用法：
    python3 r2_huffman.py <corpus.txt> <out_dir>

产物：
    <out_dir>/compressed.bin   CSQ2 格式（贪心 LZ77 + 静态 canonical Huffman，
                               头 8 字节：magic + 原始长度大端；随后位流：
                               384x5bit 字面/长度码长表 + 16x5bit 距离桶码长表 + token 流）
    <out_dir>/decompress.py    独立解压器（仅 import sys；只读 argv[1]；<=8KB）

用途：oracle 正对照 —— checker 判分必须 reward=1；阈值校准以此为锚（见 spec.md）。
"""
import heapq
import sys
from pathlib import Path

MAGIC = b"CSQ2"
MIN_MATCH = 4
MAX_MATCH = 131          # 长度码直接映射（len-4 -> 256..383），超出拆成多个 token
MAX_DIST = 32768
MAX_CHAIN = 48
ALPHA = 384              # 256 字面 + 128 长度码
NBUCKET = 16             # 距离桶：bucket = dist.bit_length()-1
LEN_BITS = 5             # 码长字段位宽（最深 31，204KB 输入实际 <=26）

DECOMPRESSOR_SOURCE = '''#!/usr/bin/env python3
# Standalone decoder for the CSQ2 format (reference R2, stdlib only).
import sys

ALPHA = 384
NBUCKET = 16


def main():
    src = open(sys.argv[1], "rb").read()
    if src[:4] != b"CSQ2":
        sys.exit("bad magic")
    n = int.from_bytes(src[4:8], "big")
    pos = 8
    acc = 0
    cnt = 0
    size = len(src)

    def bits(k):
        nonlocal pos, acc, cnt
        while cnt < k:
            if pos >= size:
                raise ValueError("truncated stream")
            acc |= src[pos] << cnt
            pos += 1
            cnt += 8
        v = acc & ((1 << k) - 1)
        acc >>= k
        cnt -= k
        return v

    def setup(lens):
        m = max(lens) if lens else 0
        if m == 0:
            return None
        bl = [0] * (m + 1)
        for l in lens:
            if l:
                bl[l] += 1
        table = [s for s in range(len(lens)) if lens[s]]
        table.sort(key=lambda s: lens[s])
        first = [0] * (m + 1)
        index = [0] * (m + 1)
        code = 0
        idx = 0
        for l in range(1, m + 1):
            code = (code + bl[l - 1]) << 1
            first[l] = code
            index[l] = idx
            idx += bl[l]
        return (bl, first, index, table, m)

    def decode(t):
        bl, first, index, table, m = t
        code = 0
        f = 0
        idx = 0
        for l in range(1, m + 1):
            code = (code << 1) | bits(1)
            c = bl[l]
            if code - f < c:
                return table[idx + code - f]
            idx += c
            f = (f + c) << 1
        raise ValueError("corrupt code")

    la = setup([bits(5) for _ in range(ALPHA)])
    db = setup([bits(5) for _ in range(NBUCKET)])
    out = bytearray()
    if n:
        while len(out) < n:
            s = decode(la)
            if s < 256:
                out.append(s)
            else:
                length = s - 252
                b = decode(db)
                extra = bits(b) if b else 0
                dist = (1 << b) + extra
                start = len(out) - dist
                if start < 0:
                    raise ValueError("bad distance")
                for k in range(length):
                    out.append(out[start + k])
        if len(out) != n:
            raise ValueError("length mismatch")
    sys.stdout.buffer.write(bytes(out))


main()
'''


def huffman_lengths(freq):
    """freq: dict sym->count（count>0）。返回 dict sym->码长（单符号时码长 1）。"""
    if not freq:
        return {}
    if len(freq) == 1:
        return {next(iter(freq)): 1}
    heap = []
    tick = 0
    for s in sorted(freq):
        heap.append((freq[s], tick, (s,)))
        tick += 1
    heapq.heapify(heap)
    depth = dict.fromkeys(freq, 0)
    while len(heap) > 1:
        f1, _, g1 = heapq.heappop(heap)
        f2, _, g2 = heapq.heappop(heap)
        for s in g1 + g2:
            depth[s] += 1
        heapq.heappush(heap, (f1 + f2, tick, g1 + g2))
        tick += 1
    assert max(depth.values()) <= (1 << LEN_BITS) - 1, "huffman depth overflow"
    return depth


def canonical_codes(lengths):
    """lengths: list 按 symbol 序的码长（0=未用）。返回 list of code（0 处为 None）。"""
    maxl = max(lengths)
    if maxl == 0:
        return [None] * len(lengths)
    bl = [0] * (maxl + 1)
    for l in lengths:
        if l:
            bl[l] += 1
    code = 0
    next_code = [0] * (maxl + 1)
    for l in range(1, maxl + 1):
        code = (code + bl[l - 1]) << 1
        next_code[l] = code
    codes = [None] * len(lengths)
    for s, l in enumerate(lengths):
        if l:
            codes[s] = next_code[l]
            next_code[l] += 1
    return codes


def revbits(value, width):
    r = 0
    for _ in range(width):
        r = (r << 1) | (value & 1)
        value >>= 1
    return r


def tokenize(data):
    """贪心 LZ77（一步 lazy）。返回 token 列表：
    0..255 = 字面字节；>= 0x1000000 = (len<<16)|dist 的匹配。"""
    n = len(data)
    if n == 0:
        return []
    tokens = []
    head = {}
    prev = [-1] * n
    limit = min(MAX_MATCH, n)  # 单 token 长度上限还受 n-i 约束

    def find_best(i):
        if i + MIN_MATCH > n:
            return 0, -1
        key = int.from_bytes(data[i:i + MIN_MATCH], "little")
        j = head.get(key, -1)
        low = i - MAX_DIST
        best_len = 0
        best_j = -1
        chain = 0
        lim = n - i
        if lim > MAX_MATCH:
            lim = MAX_MATCH
        while j >= 0 and j >= low and chain < MAX_CHAIN:
            if best_len == 0 or (i + best_len < n and data[j + best_len] == data[i + best_len]):
                if data[j:j + MIN_MATCH] == data[i:i + MIN_MATCH]:
                    l = MIN_MATCH
                    while l < lim and data[j + l] == data[i + l]:
                        l += 1
                    if l > best_len:
                        best_len = l
                        best_j = j
                        if l >= lim:
                            break
            j = prev[j]
            chain += 1
        return best_len, best_j

    def insert(k):
        if k + MIN_MATCH <= n:
            key = int.from_bytes(data[k:k + MIN_MATCH], "little")
            prev[k] = head.get(key, -1)
            head[key] = k

    i = 0
    while i < n:
        length, j = find_best(i)
        if length >= MIN_MATCH:
            # 一步 lazy：看 i+1 是否有更长匹配
            if length < n - i:
                length2, _ = find_best(i + 1)
                if length2 > length:
                    tokens.append(data[i])
                    insert(i)
                    i += 1
                    continue
            dist = i - j
            tokens.append(0x1000000 | (length << 16) | dist)
            for k in range(i, i + length):
                insert(k)
            i += length
        else:
            tokens.append(data[i])
            insert(i)
            i += 1
    return tokens


def compress(data: bytes) -> bytes:
    n = len(data)
    tokens = tokenize(data)
    freq_lit = {}
    freq_dist = {}
    for t in tokens:
        if t < 0x1000000:
            freq_lit[t] = freq_lit.get(t, 0) + 1
        else:
            length = (t >> 16) & 0xFF
            dist = t & 0xFFFF
            s = 256 + (length - MIN_MATCH)
            freq_lit[s] = freq_lit.get(s, 0) + 1
            b = dist.bit_length() - 1
            freq_dist[b] = freq_dist.get(b, 0) + 1

    dlit = huffman_lengths(freq_lit)
    ddis = huffman_lengths(freq_dist)
    lens_lit = [dlit.get(s, 0) for s in range(ALPHA)]
    lens_dis = [ddis.get(s, 0) for s in range(NBUCKET)]
    code_lit = canonical_codes(lens_lit)
    code_dis = canonical_codes(lens_dis)
    rev_lit = [revbits(c, lens_lit[s]) if c is not None else 0
               for s, c in enumerate(code_lit)]
    rev_dis = [revbits(c, lens_dis[s]) if c is not None else 0
               for s, c in enumerate(code_dis)]

    out = bytearray(MAGIC + n.to_bytes(4, "big"))
    acc = 0
    nb = 0

    def putbits(v, k):
        nonlocal acc, nb
        acc |= v << nb
        nb += k
        while nb >= 8:
            out.append(acc & 0xFF)
            acc >>= 8
            nb -= 8

    for l in lens_lit:
        putbits(l, LEN_BITS)
    for l in lens_dis:
        putbits(l, LEN_BITS)
    for t in tokens:
        if t < 0x1000000:
            putbits(rev_lit[t], lens_lit[t])
        else:
            length = (t >> 16) & 0xFF
            dist = t & 0xFFFF
            s = 256 + (length - MIN_MATCH)
            putbits(rev_lit[s], lens_lit[s])
            b = dist.bit_length() - 1
            putbits(rev_dis[b], lens_dis[b])
            if b:
                putbits(dist - (1 << b), b)
    if nb:
        out.append(acc & 0xFF)
    return bytes(out)


def main(argv):
    if len(argv) != 3:
        print("usage: python3 r2_huffman.py <corpus.txt> <out_dir>", file=sys.stderr)
        return 2
    src = Path(argv[1])
    out_dir = Path(argv[2])
    out_dir.mkdir(parents=True, exist_ok=True)
    data = src.read_bytes()
    blob = compress(data)
    (out_dir / "compressed.bin").write_bytes(blob)
    (out_dir / "decompress.py").write_text(DECOMPRESSOR_SOURCE, encoding="utf-8")
    print("R2 lz77+huffman: corpus=%d bytes -> compressed=%d bytes (ratio %.4f)"
          % (len(data), len(blob), len(blob) / len(data)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
