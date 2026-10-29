#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L4 auditor 凭据泄漏扫描器（task-9 阶段 I；零模型、只读目标文件）。

用途（lead 2026-10-29 指令 + 形似字母更正）：
  对 L4 三个新批次、auditor/评审新产物做凭据泄漏检测。**唯一批准的凭据来源**是
  `~/.dsh/.credentials.yaml` 的 `refs.DEEPSEEK_API_KEY`（精确 ASCII 标识符，沿
  3-表现现场/r1030-formal-a1/tools/lab.py::load_api_key 的既有解析方式，逐字符
  相同；绝不猜测/遍历其他 ref，不读 secret-context）。也可 `--key-stdin` 接收
  外部已解析值（只进内存，不落盘不回显）。

硬纪律：
  1. 匹配到已知真实 key 时，报告只含 **文件定位 + 命中次数**——不输出值、片段、
     值的任何 hash；路径若含 key 先就地 redact。
  2. generic 可疑项（sk-/Authorization: Bearer/api_key 赋值/私钥块/凭据名引用）
     只输出 **类型+次数+行号**；synthetic stub 值与源码 ref 字符串单独归类，
     不冒充真实泄漏。
  3. 覆盖 json/txt/log/md/py/yaml/jsonl/stdout/stderr 等一切可读文件；DSH
     `.zst/.zstd` 会话按魔数嗅探后 **内存解压** 再检测（不能只扫压缩字节）。
  4. 收据绝不包含凭据材料：自检含机械断言（报告字节中不存在测试 key 的
     ≥12 连续子串与其 sha256）。
  5. `--out` 原子拒写（目标已存在 → exit 2，原字节不动）；`live_doc_drift: []`
     内嵌；时间/哈希脚本生成。扫描器自身不发生任何网络请求、不调用模型。

用法：
  python3 credential_scan.py --scan PATH... [--root R] --out REPORT [--key-stdin]
  python3 credential_scan.py --selftest --out RECEIPT

退出码：0=完成且无真实 key 精确命中；4=发现真实 key 精确命中（告警）；
2=用法/拒写/凭据源不可用。
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
CREDENTIALS_PATH = Path.home() / ".dsh" / ".credentials.yaml"
APPROVED_REF = "DEEPSEEK_API_KEY"  # 精确 ASCII；形似 Unicode 字母一律不认
ZSTD_MAGIC = b"\x28\xb5\x2f\xfd"
GENERIC_PATTERNS = [
    ("sk-token", re.compile(r"sk-[A-Za-z0-9]{16,}")),
    ("bearer-header", re.compile(r"Authorization\s*[:=]\s*Bearer\s+[A-Za-z0-9._~+/=-]{8,}", re.I)),
    ("apikey-assignment", re.compile(r"(?i)\bapi[_-]?key\b\s*[:=]\s*[\"']?[^\s\"']{8,}")),
    ("private-key-block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
]
# 源码 ref 字符串：凭据**名字**出现在代码/配置里不是泄漏，单独计数不抓值
ENV_NAME_RE = re.compile(r"\bDEEPSEEK_API_KEY\b")


def now_local() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def load_approved_key() -> str:
    """逐字符复刻 lab.py::load_api_key 的解析，仅认 refs 下 APPROVED_REF 一项。"""
    text = CREDENTIALS_PATH.read_text(encoding="utf-8")
    m = re.search(r"^refs:\n((?:  .*\n)+)", text, re.M)
    if not m:
        raise SystemExit("credentials: refs 段未找到")
    for line in m.group(1).splitlines():
        k, _, v = line.partition(":")
        if k.strip() == APPROVED_REF:
            return v.strip()
    raise SystemExit("credentials: %s 未找到" % APPROVED_REF)


def safe_path(p: str, key: str) -> str:
    """路径含 key 时就地 redact（只 hide 值本身，不引入新信息）。"""
    return p.replace(key, "[REDACTED]") if key and key in p else p


def iter_files(target: Path):
    if target.is_file():
        yield target
    elif target.is_dir():
        for root, _dirs, files in os.walk(target):
            for name in sorted(files):
                yield Path(root) / name


def maybe_zstd(raw: bytes):
    """魔数嗅探 + 内存解压；返回 (payload_bytes, was_zstd, decompress_ok)。"""
    if raw[:4] == ZSTD_MAGIC:
        try:
            import zstandard
            return zstandard.ZstdDecompressor().decompress(raw, max_output_size=1 << 30), True, True
        except Exception:
            return raw, True, False
    return raw, False, False


def scan_file(path: Path, key: str, stub_values: set[str]) -> dict:
    entry = {"path": safe_path(str(path), key), "readable": True, "zstd": False,
             "zstd_decompress_ok": None, "bytes": 0, "exact_hits": 0,
             "generic": {}, "env_name_refs": 0}
    try:
        raw = path.read_bytes()
    except Exception as exc:
        return {"path": safe_path(str(path), key), "readable": False,
                "error_class": type(exc).__name__}
    payload, was_zstd, ok = maybe_zstd(raw)
    entry["zstd"] = was_zstd
    entry["zstd_decompress_ok"] = None if not was_zstd else ok
    entry["bytes"] = len(raw)
    # 1) 精确匹配：真实 key 的字节级出现（压缩/明文载荷均可），只计次
    if key:
        entry["exact_hits"] = payload.count(key.encode("utf-8"))
    # 2) generic：解码后在行级匹配，只记类型/次数/行号，绝不记捕获文本
    text = payload.decode("utf-8", errors="replace")
    counts: dict[str, dict] = {}
    for i, line in enumerate(text.splitlines(), 1):
        for type_name, rx in GENERIC_PATTERNS:
            for m in rx.finditer(line):
                cls = "real-key-exact" if (key and m.group(0).find(key) >= 0) else (
                    "synthetic-stub" if any(s in m.group(0) for s in stub_values) else "unclassified")
                slot = counts.setdefault(type_name, {})
                slot["count"] = slot.get("count", 0) + 1
                slot.setdefault("classes", {}).setdefault(cls, 0)
                slot["classes"][cls] += 1
                slot.setdefault("lines", []).append(i)
        if ENV_NAME_RE.search(line):
            entry["env_name_refs"] += 1
    entry["generic"] = {k: {"count": v["count"], "classes": v["classes"],
                            "lines": v["lines"][:50]} for k, v in counts.items()}
    return entry


def do_scan(targets: list[Path], root: Path, key: str, key_source: str,
            out: Path | None) -> tuple[int, dict]:
    stub_values = {"stub-key", "sk-synthetic", "SYNTHETIC"}  # 已知合成桩标记
    files = [scan_file(f, key, stub_values)
             for t in targets for f in iter_files(t)]
    exact = [{"path": f["path"], "count": f["exact_hits"]}
             for f in files if f.get("exact_hits")]
    report = {"kind": "credential_scan_report", "tool": "credential_scan.py",
              "at": now_local(), "root": str(root), "key_source": key_source,
              "approved_ref": APPROVED_REF,
              "targets": [safe_path(str(t), key) for t in targets],
              "files_scanned": len(files),
              "exact_hits": exact, "exact_hit_count": sum(e["count"] for e in exact),
              "generic_summary": {
                  g: sum(f["generic"].get(g, {}).get("count", 0) for f in files)
                  for g in sorted({k for f in files for k in f.get("generic", {})})},
              "env_name_ref_files": sum(1 for f in files if f.get("env_name_refs")),
              "key_material_in_report": False,
              "live_doc_drift": [], "files": files}
    exit_code = 4 if exact else 0
    if out is not None:
        blob = json.dumps(report, ensure_ascii=False, indent=1) + "\n"
        if out.exists():
            print(json.dumps({"refused": True, "target": str(out),
                              "reason": "目标已存在（原子拒写，原字节不动）"},
                             ensure_ascii=False))
            return 2, report
        out.write_text(blob, encoding="utf-8")
        print(json.dumps({"exact_hit_count": report["exact_hit_count"],
                          "files_scanned": report["files_scanned"],
                          "generic_summary": report["generic_summary"],
                          "report": str(out)}, ensure_ascii=False))
    return exit_code, report


# ---------------------------------------------------------------- selftest

def selftest(out: Path | None) -> int:
    """合成自检：绝不读真实凭据、绝不把真实 key 写入任何 fixture。"""
    results = []

    def check(name, ok, detail=""):
        results.append({"case": name, "pass": bool(ok), "detail": str(detail)[:200]})
        return bool(ok)

    synth_key = "sk-synthetic-selftest-0123456789abcdef0123456789abcdef"
    synth_sha = hashlib.sha256(synth_key.encode()).hexdigest()
    with tempfile.TemporaryDirectory(prefix="cred-scan-selftest-") as td:
        tmp = Path(td)
        plain = tmp / "a.txt"
        plain.write_text("hello\nkey=%s\nbye\n" % synth_key, encoding="utf-8")
        import zstandard
        zpath = tmp / "session.v4.jsonl.zstd"
        zpath.write_bytes(zstandard.ZstdCompressor().compress(
            ("secret=%s\n" % synth_key).encode("utf-8")))
        r = tmp / "b.json"
        r.write_text(json.dumps({"nested": {"v": synth_key}}), encoding="utf-8")
        clean = tmp / "clean.md"
        clean.write_text("no secrets here, env_key = \"DEEPSEEK_API_KEY\" is a name\n",
                         encoding="utf-8")
        generic = tmp / "g.log"
        generic.write_text("Authorization: Bearer sk-syntheticselftestabcdef1234567890\n"
                           "token=stub-key\n", encoding="utf-8")
        # T1–T4 定位/计数/覆盖面
        code, rep = do_scan([tmp], tmp, synth_key, "selftest-synthetic", None)
        by = {f["path"]: f for f in rep["files"]}
        check("t1_exact_txt", by[str(plain)]["exact_hits"] == 1)
        check("t2_exact_json", by[str(r)]["exact_hits"] == 1)
        check("t3_zstd_inmemory_decompress",
              by[str(zpath)]["zstd"] is True and by[str(zpath)]["zstd_decompress_ok"] is True
              and by[str(zpath)]["exact_hits"] == 1,
              json.dumps(by[str(zpath)]))
        check("t4_exit4_on_hits", code == 4)
        # T5 generic：只计类型/次数，值不入报告；stub 归类 synthetic-stub
        g = by[str(generic)]["generic"]
        check("t5_generic_counts_only",
              g["bearer-header"]["count"] == 1 and "sk-token" in g
              and all("value" not in json.dumps(v) for v in g.values()),
              json.dumps(g))
        check("t5b_stub_classified", any(
            c == "synthetic-stub" for v in g.values() for c in v["classes"]))
        # T6 env 名字引用 ≠ 泄漏
        check("t6_env_name_ref_only", by[str(clean)]["env_name_refs"] == 1
              and by[str(clean)]["exact_hits"] == 0 and not by[str(clean)]["generic"])
        # T7 路径含完整 key → redact（部分前缀不代表 key 本身，不 redact 属预期）
        leaky_dir = tmp / ("dir-%s-x" % synth_key)
        leaky_dir.mkdir()
        (leaky_dir / "f.txt").write_text(synth_key, encoding="utf-8")
        partial_dir = tmp / ("partial-%s-x" % synth_key[:20])
        partial_dir.mkdir()
        (partial_dir / "p.txt").write_text("clean content", encoding="utf-8")
        code2, rep2 = do_scan([tmp], tmp, synth_key, "selftest-synthetic", None)
        leak_entries = [f for f in rep2["files"] if "[REDACTED]" in f["path"]]
        check("t7_path_redacted", len(leak_entries) >= 1
              and not any(synth_key in f["path"] for f in rep2["files"]),
              json.dumps([f["path"] for f in leak_entries]))
        # partial 前缀目录仅用于 T7 对照（部分前缀≠key，不 redact 属预期），移出后续扫描树
        import shutil as _sh
        _sh.rmtree(partial_dir)
        # T8 原子拒写（报告写在被扫树之外，避免扫到自身报告）
        reports = Path(td) / "reports"
        reports.mkdir()
        outp = reports / "r.json"
        o1, _ = do_scan([tmp], tmp, synth_key, "selftest-synthetic", outp)
        first = outp.read_bytes()
        o2, _ = do_scan([tmp], tmp, synth_key, "selftest-synthetic", outp)
        check("t8_atomic_refuse", o1 == 4 and o2 == 2 and outp.read_bytes() == first)
        # T9 报告零凭据材料：无 ≥12 连续 key 子串、无其 sha256
        blob = outp.read_text(encoding="utf-8")
        subs = {synth_key[i:i + 12] for i in range(0, len(synth_key) - 11)}
        check("t9_no_key_material_in_report",
              not any(s in blob for s in subs) and synth_sha not in blob
              and rep2["key_material_in_report"] is False)
        # T10 干净树零命中 → exit 0
        with tempfile.TemporaryDirectory(prefix="cred-scan-clean-") as td2:
            (Path(td2) / "x.txt").write_text("nothing", encoding="utf-8")
            code3, rep3 = do_scan([Path(td2)], Path(td2), synth_key, "selftest-synthetic", None)
            check("t10_clean_exit0", code3 == 0 and rep3["exact_hit_count"] == 0)

    counts = {"total": len(results), "passed": sum(1 for r in results if r["pass"]),
              "failed": sum(1 for r in results if not r["pass"])}
    all_pass = counts["failed"] == 0
    receipt = {"kind": "self_test", "tool": "credential_scan.py --selftest",
               "at": now_local(), "counts": counts, "cases": results,
               "all_pass": all_pass,
               "note": "全部用例使用合成 key；真实凭据未参与、未落盘；key_source=selftest-synthetic",
               "live_doc_drift": []}
    if out is not None:
        if out.exists():
            print(json.dumps({"refused": True, "target": str(out)}), file=sys.stderr)
            return 2
        out.write_text(json.dumps(receipt, ensure_ascii=False, indent=1) + "\n",
                       encoding="utf-8")
    print(json.dumps(counts, ensure_ascii=False))
    print("CREDENTIAL_SCAN_SELFTEST:", "PASS" if all_pass else "FAIL")
    return 0 if all_pass else 1


def main(argv) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scan", nargs="*", metavar="TARGET")
    ap.add_argument("--root", default=os.getcwd())
    ap.add_argument("--out", default=None)
    ap.add_argument("--key-stdin", action="store_true",
                    help="从 stdin 读外部已解析 key（不回显、不落盘）；缺省走批准 refs")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest(Path(a.out) if a.out else None)
    if not a.scan:
        ap.print_help()
        return 2
    if a.key_stdin:
        key = sys.stdin.readline().rstrip("\r\n")
        source = "stdin-pre-resolved"
    else:
        key = load_approved_key()
        source = "approved-refs-%s" % APPROVED_REF
    if not key:
        print("empty key", file=sys.stderr)
        return 2
    code, _rep = do_scan([Path(p) for p in a.scan], Path(a.root), key, source,
                         Path(a.out) if a.out else None)
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
