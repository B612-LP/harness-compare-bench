#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L4 双归档离线反事实投影（offline_recompute）。

对同一场的母本原始证据，在两个独立沙箱副本上分别重放 legacy（r1030 时代归档语义，
含 r1030#1「runner 流被 rmtree 连带删除」缺陷的如实复现）与 current（L4 全量留存）两种
后处理，产出 projections/legacy 与 projections/current。母本 write-once 不动。

边界（预注册 §2B）：这只识别「记录留存/可判定性/usage 投影/分数记录」的归档测量差异，
不声称恢复历史 runner 的因果贡献；本投影为 equivalent_simulation（等价模拟），
非历史 pipeline 原样调用——适配 diff 全量披露于各投影 ADAPTATION.json。
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
LEGACY_SOURCES = [
    {"role": "legacy archive implementation (defective r1030#1 as-published)",
     "path": "3-表现现场/r1030-formal-a1/tools/lab.py"},
    {"role": "legacy rescan correction record",
     "path": "3-表现现场/r1030-formal-a1/tools/rescan_integrity.py"},
]


def sha_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def git_commit_of(path: str) -> str | None:
    """受审程序内只读 git：取历史源文件当前提交（禁止任何写操作）。"""
    try:
        r = subprocess.run(["git", "log", "-1", "--format=%H", "--", path],
                           cwd=str(REPO), capture_output=True, text=True, timeout=30)
        return r.stdout.strip() or None
    except Exception:
        return None


def source_anchors() -> list[dict]:
    out = []
    for s in LEGACY_SOURCES:
        p = REPO / s["path"]
        out.append({**s, "sha256": sha_file(p) if p.exists() else None,
                    "commit": git_commit_of(s["path"])})
    return out


def legacy_meta(meta: dict, adaptation_diff: list[str]) -> dict:
    """r1030 时代 meta 字段语义：无 registered_at/preregistration/usage per_call/stdout_bytes。"""
    legacy = {k: meta[k] for k in ("batch", "rule_version", "product", "case", "form",
                                   "workspace", "model", "reasoning_effort",
                                   "product_version", "route", "tools", "permissions",
                                   "skills", "web_search", "soft_constraints",
                                   "prompt_sha256", "isolation", "inputs",
                                   "status", "exit_code", "started_at", "finished_at",
                                   "duration_s", "reward", "weighted", "failed", "judge",
                                   "integrity", "integrity_verdict", "run_id") if k in meta}
    legacy["usage"] = {"requests": 0, "input_tokens": 0, "output_tokens": 0,
                       "note": ("legacy semantics: runner-side usage extraction absent as standalone "
                                "per_call; r1030 codex aggregate zeros are extraction-layer coercions "
                                "(int(u.get(...) or 0) merges absent/null/0; note 'absent fields stay 0'), "
                                "whereas r1031 dsh mapped cacheWriteTokens only when the key existed "
                                "(no key -> field not written; total None when valueless) — "
                                "historical 'creation=0 across 20 runs' must be reported per product/field-source "
                                "layer, not as a uniform SDK default")}
    legacy["run_id"] = meta.get("run_id")  # 保留 L4 槽位身份，仅字段语义作旧
    adaptation_diff += [
        "legacy projection keeps L4 slot/run/event identity (historical ids would collide with r1030 sealed rows)",
        "legacy integrity field carried over from master rescan instead of the historical vacuous scan+post-hoc fix",
        "checker/judge output identical bytes (same frozen checker invocation contract)",
    ]
    return legacy


def project_legacy(master: Path, sandbox: Path, adaptation_diff: list[str]) -> None:
    """复现 r1030#1：日志写进证据目录并被 rmtree 连带删除 → legacy 投影无 stdout/stderr。"""
    for name in ("workspace", "config-snapshot"):
        if (master / name).exists():
            shutil.copytree(master / name, sandbox / name)
    for f in ("meta.json", "checker.stdout", "score-receipt.json", "prompt.txt"):
        if (master / f).exists():
            shutil.copy2(master / f, sandbox / f)
    m = json.loads((master / "meta.json").read_text(encoding="utf-8"))
    (sandbox / "meta.json").write_text(
        (json.dumps(legacy_meta(m, adaptation_diff), ensure_ascii=False, indent=2) + "\n"),
        encoding="utf-8")
    adaptation_diff.append(
        "r1030#1 defect reproduced in sandbox copy only: agent.jsonl/agent.stderr.txt absent from legacy "
        "projection (historically lost by archive rmtree); master stream files remain untouched")


def project_current(master: Path, sandbox: Path) -> None:
    ignore = shutil.ignore_patterns("projections")
    shutil.copytree(master, sandbox, ignore=ignore, dirs_exist_ok=True)
    for name, final in (("stdout.raw", "agent.jsonl"), ("stderr.raw", "agent.stderr.txt")):
        src = master / name
        if src.exists():
            shutil.copy2(src, sandbox / final)
            for side in (".sha256", ".bytes"):
                if (master / (name + side)).exists():
                    shutil.copy2(master / (name + side), sandbox / (final + side))


def project_run(ev: Path) -> dict:
    anchors = source_anchors()
    master_before = {str(p.relative_to(ev)): sha_file(p) for p in sorted(ev.rglob("*")) if p.is_file()}
    for kind in ("legacy", "current"):
        with tempfile.TemporaryDirectory() as td:
            sandbox = Path(td) / kind
            sandbox.mkdir()
            diff: list[str] = []
            if kind == "legacy":
                project_legacy(ev, sandbox, diff)
            else:
                project_current(ev, sandbox)
            manifest = {
                "projection": kind, "equivalent_simulation": True,
                "master_evidence_dir": str(ev),
                "master_input_mapping": {"meta.json": "identity", "workspace/": "identity",
                                         "config-snapshot/": "identity",
                                         "prompt.txt": "identity",
                                         "checker.stdout": "identity",
                                         "score-receipt.json": "identity",
                                         "agent.jsonl": "identity (current projection); absent in legacy (r1030#1)",
                                         "agent.stderr.txt": "identity (current projection); absent in legacy",
                                         "agent-session/": "usage extraction source"},
                "historical_sources": anchors,
                "adaptation_diff": diff,
                "live_doc_drift": [],
                "note": "离线反事实投影：只识别归档测量语义差异，不声称历史 runner 因果贡献；"
                        "母本 write-once 未被触碰",
            }
            (sandbox / "ADAPTATION.json").write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            dst = ev / "projections" / kind
            if dst.exists():
                shutil.rmtree(dst)  # 投影可重复再生（母本只读）；母本文件不受影响
            shutil.move(str(sandbox), str(dst))
    master_after = {str(p.relative_to(ev)): sha_file(p) for p in sorted(ev.rglob("*")) if p.is_file()}
    untouched = all(master_after.get(k) == v for k, v in master_before.items())
    return {"projections": ["legacy", "current"], "master_untouched": untouched}


def main(argv=None) -> int:
    runs = Path(__file__).resolve().parents[1] / "runs"
    slots = argv
    targets = ([runs / s["slot_id"] for s in slots] if slots
               else sorted(p for p in runs.iterdir() if p.is_dir()))
    results = {}
    for ev in targets:
        if not (ev / "meta.json").exists():
            continue
        r = project_run(ev)
        results[ev.name] = r
        print(json.dumps(r, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
