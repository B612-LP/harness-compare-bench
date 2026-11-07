#!/usr/bin/env python3
"""tools-redaction-receipt.py v1 (2026-11-08)

敏感现场脱敏收据生成器（老师 2026-11-03 新追问④落地试点）。
对每对（私档原件 → 公开脱敏派生件）生成机械可复核收据：
  原件侧只披露 basename + sha256 + 字节数（不含路径前缀、不含内容）；
  派生件侧披露仓内相对路径 + sha256 + 字节数；
  另记载脱敏范围结构描述（scope）与方法规则 id（method）。
见证签名=机械双跑：--witness 模式用独立实现（shasum -a 256 CLI）复算全部哈希
并逐字节重derive收据 pairs 块比对（机器见证，非真人签名）。

诚实边界：公开派生件是事后编制的摘要，不是历史原件；本收据证明「哪份私档原件、
以何种范围与方法、对应哪份公开派生件（字节层面）」，不认证原件真实性。

输入：
  --manifest  公开清单（basename/derivative/scope/method；不含私档路径）
  --private-map 私档映射（basename→私档绝对路径；私档保存，不入公开仓、不入收据）
用法：
  主跑：python3 tools-redaction-receipt.py <公开仓根> --manifest <m.json> \
        --private-map <p.json> --out <pilot.json> [--receipt <run.json>]
  见证：python3 tools-redaction-receipt.py <公开仓根> --manifest <m.json> \
        --private-map <p.json> --witness <pilot.json> --witness-out <w.json> [--receipt <run.json>]
退出码：0 全过 / 1 有失败 / 2 环境 / 3 收据已存在。
"""
import hashlib
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

TOOL = "tools-redaction-receipt.py"
VERSION = "v1 (2026-11-08)"


def tool_sha256() -> str:
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_shasum(p: Path) -> str:
    out = subprocess.run(["shasum", "-a", "256", str(p)],
                         capture_output=True, text=True, check=True)
    return out.stdout.split()[0]


def fail(msg: str, code: int = 2):
    print(f"FATAL: {msg}", file=sys.stderr)
    sys.exit(code)


def build_pairs(repo: Path, manifest: list, pmap: dict):
    pairs, problems = [], []
    for ent in manifest:
        bn = ent.get("basename", "")
        deriv = ent.get("derivative", "")
        priv = pmap.get(bn)
        if not priv or not Path(priv).is_file():
            problems.append({"basename": bn, "problem": "private original missing"})
            continue
        dpath = repo / deriv
        if not dpath.is_file():
            problems.append({"basename": bn, "problem": "derivative missing"})
            continue
        po, pb = Path(priv), dpath
        pairs.append({
            "basename": bn,
            "original_sha256": sha256_file(po),
            "original_bytes": po.stat().st_size,
            "derivative": deriv,
            "derivative_sha256": sha256_file(pb),
            "derivative_bytes": pb.stat().st_size,
            "scope": ent.get("scope", ""),
            "method": ent.get("method", ""),
        })
    return pairs, problems


def main() -> int:
    args = sys.argv[1:]
    if not args or args[0].startswith("-"):
        fail("用法: tools-redaction-receipt.py <公开仓根> --manifest <m> --private-map <p> "
             "--out <pilot> [--receipt <run>] | --witness <pilot> --witness-out <w> [--receipt <run>]")
    repo = Path(args[0]).resolve()
    if not (repo / ".git").exists():
        fail(f"not a git repo: {repo}")
    manifest_path, pmap_path = None, None
    out_path = receipt_path = None
    witness_target = witness_out = None
    i = 1
    while i < len(args):
        a = args[i]
        if a == "--manifest":
            manifest_path = Path(args[i + 1]); i += 2
        elif a == "--private-map":
            pmap_path = Path(args[i + 1]); i += 2
        elif a == "--out":
            out_path = Path(args[i + 1]); i += 2
        elif a == "--receipt":
            receipt_path = Path(args[i + 1]); i += 2
        elif a == "--witness":
            witness_target = Path(args[i + 1]); i += 2
        elif a == "--witness-out":
            witness_out = Path(args[i + 1]); i += 2
        else:
            fail(f"unknown arg: {a}")
    if manifest_path is None or pmap_path is None:
        fail("--manifest 与 --private-map 必填")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    pmap = json.loads(pmap_path.read_text(encoding="utf-8"))
    now = datetime.now().astimezone().isoformat(timespec="seconds")

    def write_once(p: Path, payload: str) -> bool:
        if p is None:
            return True
        if p.exists():
            print(f"FATAL: receipt exists (write-once): {p}", file=sys.stderr)
            return False
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(payload, encoding="utf-8")
        print(f"receipt: {p}")
        return True

    if witness_target is not None:
        # ---- 见证模式：独立实现（shasum CLI）复算 + 逐字节重 derive ----
        if witness_out is None:
            fail("--witness 模式需要 --witness-out")
        pilot = json.loads(witness_target.read_text(encoding="utf-8"))
        pairs, problems = build_pairs(repo, manifest, pmap)
        # shasum 独立实现复算
        shasum_checks, mismatch = [], False
        for pair, ent in zip(pairs, manifest):
            o = Path(pmap[pair["basename"]])
            d = repo / pair["derivative"]
            o2, d2 = sha256_shasum(o), sha256_shasum(d)
            ok = (o2 == pair["original_sha256"]) and (d2 == pair["derivative_sha256"])
            mismatch = mismatch or not ok
            shasum_checks.append({"basename": pair["basename"], "original_match": o2 == pair["original_sha256"],
                                  "derivative_match": d2 == pair["derivative_sha256"]})
        # 逐字节重 derive pairs 块（除 generated_at 外的确定性重放）
        rebuilt = json.dumps({"pairs": pairs}, ensure_ascii=False, sort_keys=True, indent=1)
        orig = json.dumps({"pairs": pilot.get("pairs", [])}, ensure_ascii=False, sort_keys=True, indent=1)
        replay_match = rebuilt == orig
        target_sha = sha256_file(witness_target)
        result = {"kind": "redaction-receipt-witness", "tool": TOOL, "tool_sha256": tool_sha256(),
                  "generated_at": now, "witness_of": str(witness_target), "witness_target_sha256": target_sha,
                  "verifier_implementation": "shasum -a 256 CLI (independent of hashlib main run)",
                  "shasum_recompute": shasum_checks, "pairs_replay_match": replay_match,
                  "manifest_sha256": sha256_file(manifest_path),
                  "honesty": {"witness": "机器见证（独立实现复算+确定性重放），非真人签名",
                              "note": "本见证不认证私档原件真实性，仅复算收据哈希与重放一致性"},
                  "all_ok": (not problems) and (not mismatch) and replay_match}
        payload = json.dumps(result, ensure_ascii=False, indent=1, sort_keys=True)
        if not write_once(witness_out, payload):
            return 3
        print(payload)
        return 0 if result["all_ok"] else 1

    # ---- 主跑模式 ----
    if out_path is None:
        fail("主跑模式需要 --out")
    if out_path.exists():
        print(f"FATAL: out exists (write-once): {out_path}", file=sys.stderr)
        return 3
    pairs, problems = build_pairs(repo, manifest, pmap)
    result = {"kind": "redaction-receipt", "tool": TOOL, "tool_sha256": tool_sha256(),
              "generated_at": now,
              "manifest_sha256": sha256_file(manifest_path),
              "private_map_basename_set": sorted(pmap.keys()),
              "honesty": {"witness": "见 --witness 模式产出的机器见证收据（独立实现复算），非真人签名",
                          "original_disclosure": "仅 basename+sha256+字节数；不含路径前缀与内容",
                          "derivative_role": "公开脱敏摘要为事后编制派生件，不是历史原件，不替代证据"},
              "pairs": pairs, "problems": problems,
              "all_pairs_ok": (not problems) and all(p["original_sha256"] and p["derivative_sha256"] for p in pairs)}
    # 防泄漏：收据不得包含私档路径（跳过下划线元数据键与非路径值）
    text = json.dumps(result, ensure_ascii=False)
    for bn, priv in pmap.items():
        sp = str(priv)
        if bn.startswith("_") or not sp.startswith("/"):
            continue
        if sp in text or str(Path(sp).parent) in text:
            fail("private path leaked into receipt payload")
    payload = json.dumps(result, ensure_ascii=False, indent=1, sort_keys=True)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(payload, encoding="utf-8")
    print(f"out: {out_path}")
    run = {"kind": "redaction-receipt-run", "mode": "main", "tool_sha256": tool_sha256(),
           "generated_at": now, "out": str(out_path), "out_sha256": sha256_file(out_path),
           "pairs_ok": result["all_pairs_ok"], "problems": problems}
    if not write_once(receipt_path, json.dumps(run, ensure_ascii=False, indent=1, sort_keys=True)):
        return 3
    print(json.dumps(run, ensure_ascii=False))
    return 0 if result["all_pairs_ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
