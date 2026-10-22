#!/usr/bin/env python3
"""corpus-squeeze 轻量判卷器 v0.1（2026-10-22）

用法：
    python3 checker.py <run_dir> [--json]
    python3 checker.py --selftest

run_dir 约定（见 spec.md）：
    compressed.bin   必需产物；也接受 run_dir/output/、run_dir/outputs/ 下同名文件
    decompress.py    必需产物；同上
    corpus.txt       可选；存在时核对 SHA-256（输入完整性守卫）
    meta.json        可选；产品/版本/操作人等运行元信息，不参与判分

口径：
    headline 为二值 0/1（BINARY=True：全 PASS=1，任一 FAIL=0）。
    逐项权重用于复核定位与加权参考（partial 口径 = weighted/100*10，单题上限 10）；
    ratio 项在未达标但已压缩时按达标程度给部分 credit（见 ratio 项逻辑）。
    解压器约束为静态扫描：≤8KB、stdlib 白名单 import、源码不含 zlib/lzma/bz2/corpus、
    open() 只允许指向 argv[1]（含直接别名变量）、禁 eval/exec/compile/__import__。
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

CASE_ID = "corpus-squeeze"
CHECKER_VERSION = "0.1"
BINARY = True
ARTIFACT_BIN = "compressed.bin"
ARTIFACT_DEC = "decompress.py"
MAX_DECOMP_BYTES = 8 * 1024        # 8KB = 8192 字节
DECOMP_TIMEOUT_S = 60
THRESHOLD = 0.35                   # 实测校准后写死；须与 truth.json 一致（守卫）

CASE_DIR = Path(__file__).resolve().parent

ITEMS = [
    ("artifacts_exist", "产物存在（compressed.bin + decompress.py）", 10),
    ("input_integrity", "输入完整性（守卫）", 10),
    ("decompress_constraints", "解压器静态约束（≤8KB/stdlib/禁 zlib 系/只读 argv）", 15),
    ("roundtrip", "roundtrip 字节级一致（subprocess，超时 %ds）" % DECOMP_TIMEOUT_S, 40),
    ("ratio", "压缩率 len(bin)/len(corpus) ≤ %.2f" % THRESHOLD, 25),
]

# 解压器允许 import 的标准库白名单（超出即 FAIL；故意不含 os/pathlib/subprocess 等
# 有文件/进程能力的模块，理由见 spec.md §观察项）
ALLOWED_IMPORTS = {
    "sys", "io", "math", "heapq", "collections", "itertools", "functools",
    "struct", "array", "bisect", "string", "types", "typing",
    "argparse", "json", "re", "base64", "binascii", "time",
}
FORBIDDEN_TEXT = re.compile(r"zlib|lzma|bz2", re.IGNORECASE)
FORBIDDEN_TEXT_CORPUS = re.compile(r"corpus", re.IGNORECASE)
DYNAMIC_CALLS = {"eval", "exec", "compile", "__import__"}


class CaseError(Exception):
    """用例自身不一致（truth 漂移等）→ 退出码 2。"""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_truth(case_dir: Path = CASE_DIR) -> dict:
    return json.loads((case_dir / "truth.json").read_text(encoding="utf-8"))


def canonical_input(case_dir: Path = CASE_DIR):
    """读取用例 canonical 语料，并用 truth.json 校验用例自身未被改动/漂移。"""
    truth = load_truth(case_dir)
    path = case_dir / "inputs" / truth["input_name"]
    data = path.read_bytes()
    actual = sha256_bytes(data)
    if actual != truth["input_sha256"]:
        raise CaseError("canonical 语料与 truth 记录不一致：%s\n  truth=%s\n  actual=%s"
                        % (path, truth["input_sha256"], actual))
    if len(data) != truth["input_bytes"]:
        raise CaseError("canonical 语料长度漂移：%d != truth %d" % (len(data), truth["input_bytes"]))
    if abs(float(truth["threshold"]) - THRESHOLD) > 1e-12:
        raise CaseError("truth threshold=%r 与 checker THRESHOLD=%r 不一致" % (truth["threshold"], THRESHOLD))
    return truth, data


def find_file(run_dir: Path, name: str):
    for candidate in (run_dir / name, run_dir / "output" / name, run_dir / "outputs" / name):
        if candidate.is_file():
            return candidate
    return None


def find_input(run_dir: Path, name: str):
    for candidate in (run_dir / name, run_dir / "input" / name, run_dir / "inputs" / name):
        if candidate.is_file():
            return candidate
    return None


# ---------------------------------------------------------------- 静态约束

def collect_imports(tree: ast.AST):
    mods = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                mods.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.level and node.level > 0:
                mods.add("<relative-import>")
            elif node.module:
                mods.add(node.module.split(".")[0])
    return mods


def static_constraints(dec_path: Path):
    """返回 (ok: bool, problems: list[str], info: dict)。"""
    problems = []
    info = {}
    src_bytes = dec_path.read_bytes()
    info["decomp_bytes"] = len(src_bytes)
    info["decomp_sha256"] = sha256_bytes(src_bytes)
    if len(src_bytes) > MAX_DECOMP_BYTES:
        problems.append("源码 %d 字节 > 上限 %d" % (len(src_bytes), MAX_DECOMP_BYTES))
    try:
        text = src_bytes.decode("utf-8")
    except UnicodeDecodeError:
        problems.append("源码不是合法 UTF-8")
        return False, problems, info
    hit = FORBIDDEN_TEXT.search(text)
    if hit:
        problems.append("源码出现禁用字样 %r（禁 zlib/lzma/bz2）" % hit.group(0))
    hit = FORBIDDEN_TEXT_CORPUS.search(text)
    if hit:
        problems.append("源码出现禁用字样 %r（禁止引用语料）" % hit.group(0))
    try:
        tree = ast.parse(text)
    except SyntaxError as exc:
        problems.append("源码无法解析：%s" % exc)
        return False, problems, info

    mods = collect_imports(tree)
    info["imports"] = sorted(mods)
    bad_mods = sorted(m for m in mods if m not in ALLOWED_IMPORTS)
    if bad_mods:
        problems.append("import 超出 stdlib 白名单：%s" % ", ".join(bad_mods))

    # open() 只允许指向 argv[1]（直接字面 sys.argv[1] 或其直接别名变量）
    safe_names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            try:
                value_seg = ast.unparse(node.value)
            except Exception:
                continue
            if value_seg == "sys.argv[1]":
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        safe_names.add(target.id)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            func_name = None
            if isinstance(func, ast.Name):
                func_name = func.id
                if func_name in DYNAMIC_CALLS:
                    problems.append("禁止动态执行调用 %s()" % func_name)
                    continue
            is_open = func_name == "open" or (isinstance(func, ast.Attribute) and func.attr == "open")
            if is_open:
                if not node.args:
                    problems.append("open() 缺少路径参数")
                    continue
                try:
                    seg = ast.unparse(node.args[0])
                except Exception:
                    seg = "<unparseable>"
                if seg != "sys.argv[1]" and seg not in safe_names:
                    problems.append("open() 只允许打开 argv[1]（实际 %s）" % seg)
    return not problems, problems, info


# ---------------------------------------------------------------- roundtrip

def run_roundtrip(dec_path: Path, bin_path: Path, run_dir: Path, expected: bytes):
    cmd = [sys.executable, str(dec_path), str(bin_path)]
    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              stdin=subprocess.DEVNULL, cwd=str(run_dir),
                              timeout=DECOMP_TIMEOUT_S)
    except subprocess.TimeoutExpired:
        return False, "解压超时（>%ds）" % DECOMP_TIMEOUT_S, None
    detail = "exit=%d 输出 %d 字节" % (proc.returncode, len(proc.stdout))
    if proc.returncode != 0:
        tail = proc.stderr.decode("utf-8", "replace").strip().splitlines()
        reason = tail[-1] if tail else "无 stderr"
        return False, "解压器非零退出（%s；stderr: %s）" % (detail, reason[:160]), proc.stdout
    if proc.stdout == expected:
        return True, "输出与 canonical 语料字节一致（%d 字节）" % len(expected), proc.stdout
    return False, "输出与 canonical 语料不一致（%s；期望 %d 字节，得到 %d 字节）" % (
        detail, len(expected), len(proc.stdout)), proc.stdout


# ---------------------------------------------------------------- 判分

def judge(run_dir: Path) -> dict:
    truth, corpus_bytes = canonical_input()
    weights = {item[0]: item[2] for item in ITEMS}
    titles = {item[0]: item[1] for item in ITEMS}
    items = []
    details = {}

    bin_path = find_file(run_dir, ARTIFACT_BIN)
    dec_path = find_file(run_dir, ARTIFACT_DEC)

    # ① 产物存在
    missing = [name for name, path in ((ARTIFACT_BIN, bin_path), (ARTIFACT_DEC, dec_path)) if path is None]
    items.append({"id": "artifacts_exist", "title": titles["artifacts_exist"],
                  "weight": weights["artifacts_exist"],
                  "status": "pass" if not missing else "fail",
                  "credit": weights["artifacts_exist"] if not missing else 0,
                  "detail": "compressed.bin 与 decompress.py 均就位" if not missing
                            else "缺少产物：%s（run_dir=%s）" % (", ".join(missing), run_dir)})

    # ② 输入完整性守卫
    input_path = find_input(run_dir, truth["input_name"])
    if input_path is None:
        integrity = "unverified"
        items.append({"id": "input_integrity", "title": titles["input_integrity"],
                      "weight": weights["input_integrity"], "status": "unknown", "credit": 0,
                      "detail": "运行目录未附输入副本，无法核对（不扣分，但请在运行记录中说明）"})
    else:
        actual_input = input_path.read_bytes()
        if actual_input == corpus_bytes:
            integrity = "verified"
            items.append({"id": "input_integrity", "title": titles["input_integrity"],
                          "weight": weights["input_integrity"], "status": "pass",
                          "credit": weights["input_integrity"],
                          "detail": "输入副本与 canonical 字节一致"})
        else:
            integrity = "mismatch"
            items.append({"id": "input_integrity", "title": titles["input_integrity"],
                          "weight": weights["input_integrity"], "status": "fail", "credit": 0,
                          "detail": "输入被修改：实际使用输入与 canonical 不一致（判 0）"})

    # ③ 解压器静态约束
    constraints_info = {}
    if dec_path is None:
        items.append({"id": "decompress_constraints", "title": titles["decompress_constraints"],
                      "weight": weights["decompress_constraints"], "status": "fail", "credit": 0,
                      "detail": "产物缺失，无法检查"})
    else:
        ok, problems, constraints_info = static_constraints(dec_path)
        items.append({"id": "decompress_constraints", "title": titles["decompress_constraints"],
                      "weight": weights["decompress_constraints"],
                      "status": "pass" if ok else "fail",
                      "credit": weights["decompress_constraints"] if ok else 0,
                      "detail": "全部通过（%d 字节）" % constraints_info.get("decomp_bytes", -1)
                                if ok else "；".join(problems)})

    # ④ roundtrip
    if bin_path is None or dec_path is None:
        items.append({"id": "roundtrip", "title": titles["roundtrip"],
                      "weight": weights["roundtrip"], "status": "fail", "credit": 0,
                      "detail": "产物缺失，无法检查"})
    else:
        ok, reason, _out = run_roundtrip(dec_path, bin_path, run_dir, corpus_bytes)
        items.append({"id": "roundtrip", "title": titles["roundtrip"],
                      "weight": weights["roundtrip"], "status": "pass" if ok else "fail",
                      "credit": weights["roundtrip"] if ok else 0, "detail": reason})

    # ⑤ 压缩率
    if bin_path is None:
        items.append({"id": "ratio", "title": titles["ratio"],
                      "weight": weights["ratio"], "status": "fail", "credit": 0,
                      "detail": "产物缺失，无法检查"})
        ratio = None
    else:
        bin_len = bin_path.stat().st_size
        ratio = bin_len / len(corpus_bytes)
        details["bin_bytes"] = bin_len
        margin = (THRESHOLD - ratio) / THRESHOLD * 100.0
        if ratio <= THRESHOLD + 1e-12:
            items.append({"id": "ratio", "title": titles["ratio"],
                          "weight": weights["ratio"], "status": "pass",
                          "credit": weights["ratio"],
                          "detail": "ratio=%.4f ≤ %.2f（余量 %.1f%%，%d/%d 字节）"
                                    % (ratio, THRESHOLD, margin, bin_len, len(corpus_bytes))})
        else:
            grade = max(0.0, (1.0 - ratio) / (1.0 - THRESHOLD))
            credit = int(round(weights["ratio"] * grade))
            items.append({"id": "ratio", "title": titles["ratio"],
                          "weight": weights["ratio"], "status": "fail", "credit": credit,
                          "detail": "ratio=%.4f > %.2f（超标 %.1f%%；按达标程度记 credit %d/%d）"
                                    % (ratio, THRESHOLD, (ratio / THRESHOLD - 1) * 100.0,
                                       credit, weights["ratio"])})
    if ratio is not None:
        details["ratio"] = round(ratio, 6)
        details["threshold"] = THRESHOLD

    return _result(items, run_dir=run_dir, input_integrity=integrity,
                   bin_path=bin_path, dec_path=dec_path, details=details)


def _result(items, *, run_dir: Path, input_integrity: str, bin_path, dec_path, details=None):
    failed = [item for item in items if item["status"] == "fail"]
    weighted = sum(item.get("credit", 0) for item in items)
    return {
        "case_id": CASE_ID,
        "checker_version": CHECKER_VERSION,
        "binary": BINARY,
        "run_dir": str(run_dir),
        "compressed_bin": str(bin_path) if bin_path else None,
        "decompress_py": str(dec_path) if dec_path else None,
        "items": items,
        "failed": [item["id"] for item in failed],
        "reward": 0 if failed else 1,
        "weighted": weighted,
        "max_weight": sum(item[2] for item in ITEMS),
        "input_integrity": input_integrity,
        "corpus_bytes": load_truth()["input_bytes"],
        **(details or {}),
    }


def render(result: dict) -> str:
    lines = ["[%s] checker v%s  bin=%s dec=%s" % (
        CASE_ID, CHECKER_VERSION, result.get("compressed_bin"), result.get("decompress_py"))]
    for item in result["items"]:
        status = {"pass": "PASS", "fail": "FAIL", "unknown": "UNKNOWN"}[item["status"]]
        lines.append("%-7s %-22s %3d/100  %s" % (status, item["id"], item["weight"], item["detail"]))
    lines.append("REWARD %d (binary)   WEIGHTED %d/%d (partial 口径 %.1f/10)   INPUT %s   RATIO %s"
                 % (result["reward"], result["weighted"], result["max_weight"],
                    result["weighted"] / 10.0, result["input_integrity"],
                    result.get("ratio", "n/a")))
    return "\n".join(lines)


# ---------------------------------------------------------------- selftest

def _write(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(data, bytes):
        path.write_bytes(data)
    else:
        path.write_text(data, encoding="utf-8")


def _run_reference(script: Path, corpus: bytes, workdir: Path):
    """用参考解生成产物，返回 (bin_bytes, dec_bytes)。"""
    src = workdir / "src.bin"
    src.write_bytes(corpus)
    out_dir = workdir / script.stem
    proc = subprocess.run([sys.executable, str(script), str(src), str(out_dir)],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=300)
    if proc.returncode != 0:
        raise SystemExit("selftest 前置失败：参考解 %s 运行出错：%s"
                         % (script.name, proc.stderr.decode("utf-8", "replace")[-300:]))
    return ((out_dir / ARTIFACT_BIN).read_bytes(), (out_dir / ARTIFACT_DEC).read_bytes())


def selftest() -> int:
    truth, corpus_bytes = canonical_input()
    solution_dir = CASE_DIR / "solution"
    fixtures = []
    checks = {}  # name -> (result_check_fn or None)

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        r2_bin, r2_dec = _run_reference(solution_dir / "r2_huffman.py", corpus_bytes, tmp)
        r1_bin, r1_dec = _run_reference(solution_dir / "r1_naive.py", corpus_bytes, tmp)
        variant = bytearray(corpus_bytes)
        pos = int(len(variant) * 0.92)
        variant[pos] ^= 0x01
        variant = bytes(variant)
        var_bin, var_dec = _run_reference(solution_dir / "r2_huffman.py", variant, tmp)
        flipped_bin = bytearray(r2_bin)
        flip_pos = int(len(r2_bin) * 0.6)
        flipped_bin[flip_pos] ^= 0xFF
        flipped_bin = bytes(flipped_bin)

        def golden(decs=None, bins=None, inp=corpus_bytes):
            return {"bin": r2_bin if bins is None else bins,
                    "dec": r2_dec if decs is None else decs,
                    "input": inp}

        def add(name, expect, payload, check=None):
            fixtures.append((name, expect, payload))
            checks[name] = check

        add("golden：R2 参考解产物 + 输入副本", 1, golden())
        add("golden：未附输入副本（未核验不扣分）", 1, golden(inp=None))
        add("空目录（缺产物）", 0, None)
        add("只放 compressed.bin（缺 decompress.py）", 0, {"bin": r2_bin, "dec": None, "input": corpus_bytes})
        add("R1 朴素解产物（ratio 超标，其余应全过）", 0,
            {"bin": r1_bin, "dec": r1_dec, "input": corpus_bytes},
            check=lambda r: r["failed"] == ["ratio"])
        add("compressed.bin 截断（去尾 64 字节）", 0,
            golden(bins=r2_bin[:-64]), check=lambda r: "roundtrip" in r["failed"])
        add("compressed.bin 篡改 1 字节（token 区 flip）", 0,
            golden(bins=flipped_bin), check=lambda r: "roundtrip" in r["failed"])
        add("decompress.py 超 8KB（追加 9000 字节注释）", 0,
            golden(decs=r2_dec + b"# " + b"#" * 9000),
            check=lambda r: r["failed"] == ["decompress_constraints"])
        add("decompress.py 尾部 import zlib（roundtrip 仍过、静态扫描变红）", 0,
            golden(decs=r2_dec + b"\nimport zlib\n"),
            check=lambda r: r["failed"] == ["decompress_constraints"])
        add("decompress.py 尝试 open 其他文件（未调用也拒绝）", 0,
            golden(decs=r2_dec + b"\ndef _probe():\n    return open('notes.txt', 'rb')\n"),
            check=lambda r: r["failed"] == ["decompress_constraints"])
        add("变体语料的压缩产物（roundtrip 不匹配 canonical）", 0,
            {"bin": var_bin, "dec": var_dec, "input": None},
            check=lambda r: "roundtrip" in r["failed"])
        add("附篡改输入副本（输入完整性守卫）", 0,
            golden(inp=variant), check=lambda r: r["failed"] == ["input_integrity"])

        failures = 0
        print("[%s] checker v%s 自测（canonical corpus sha256=%s…，THRESHOLD=%.2f）"
              % (CASE_ID, CHECKER_VERSION, truth["input_sha256"][:12], THRESHOLD))
        for name, expect, payload in fixtures:
            with tempfile.TemporaryDirectory() as run_tmp:
                run_dir = Path(run_tmp)
                if payload is not None:
                    if payload.get("bin") is not None:
                        _write(run_dir / ARTIFACT_BIN, payload["bin"])
                    if payload.get("dec") is not None:
                        _write(run_dir / ARTIFACT_DEC, payload["dec"])
                    if payload.get("input") is not None:
                        _write(run_dir / truth["input_name"], payload["input"])
                result = judge(run_dir)
                ok = result["reward"] == expect
                if ok and checks.get(name) is not None:
                    ok = bool(checks[name](result))
                failures += 0 if ok else 1
                extra = "" if ok else "；failed=%s" % ",".join(result["failed"])
                print("  %s  %s: reward=%d（期望 %d）%s"
                      % ("PASS" if ok else "FAIL", name, result["reward"], expect, extra))
        print("负控制自测：%s" % ("通过" if failures == 0 else "%d 项不符合预期" % failures))
        return 0 if failures == 0 else 1


def main(argv) -> int:
    parser = argparse.ArgumentParser(description="corpus-squeeze 轻量判卷器 v%s" % CHECKER_VERSION)
    parser.add_argument("run_dir", nargs="?", help="运行目录（含 compressed.bin 与 decompress.py，可选 corpus.txt）")
    parser.add_argument("--json", action="store_true", help="只输出 JSON")
    parser.add_argument("--selftest", action="store_true", help="跑负控制/守卫自测")
    args = parser.parse_args(argv)

    if args.selftest:
        return selftest()
    if not args.run_dir:
        parser.error("缺少 run_dir（或使用 --selftest）")
    try:
        result = judge(Path(args.run_dir))
    except CaseError as exc:
        print("ERROR: %s" % exc, file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(result, ensure_ascii=False))
    else:
        print(render(result))
        print("RESULTS_JSON " + json.dumps(result, ensure_ascii=False))
    return 0 if result["reward"] == 1 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
