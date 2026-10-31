#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""work-registry-live 账实对账（L9-B，2026-10-30；闭合 L7-O2）。

对 live 台账逐事件三态分类（账实一致性常态化核验）：
- FRESH      source.sha256 == 对盘实算（内容 sha256）
- HISTORICAL 对盘漂移，但内容 sha256 可考于该路径 git 全历史 blob：
             `git log --all --format=%H -- <path>` 逐提交 `git cat-file blob`
             管入 sha256 比对——**禁用 blob sha1 冒比**（blob sha1 与内容 sha256
             是两个哈希体系；L9 补正一钉死的口径，预检假发现即栽在这里）
- UNRESOLVED 漂移且 git 不可考，或源文件缺失

结构核：event_id 唯一；timestamp 全序单调不减；registered_at 须带时区偏移。
退出码：0=全部 FRESH/HISTORICAL（UNRESOLVED 须全部命中 --allowlist）；1=存在未豁免
UNRESOLVED 或结构违规；2=用法错。收据 write-once（--out 目标已存即拒）。

新制度（sidecar 规则，自 L9 起）：correction 类事件登记时 source 必须 FRESH-on-disk
——被更正字节先以 sidecar 副本入盘再登记指向副本，禁指即将被覆盖的活文件
（HISTORICAL 依赖修前字节曾经入 git；从未入 git 的更正前态只能 UNRESOLVED）。

用法：
    python3 ledger_reconcile.py [--registry PATH] [--repo PATH] [--allowlist PATH]
                                [--out REPORT.json] [--selftest]
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]  # 本文件位于 <repo>/4-打分细则/<v3>/，浅 evidence-kit 一层
DEFAULT_REGISTRY = HERE / "work-registry-live.json"
TZ_RE = re.compile(r"(Z|[+-]\d{2}:?\d{2})$")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def historical_verified(repo: Path, rel: str, want: str) -> dict:
    """内容 sha256 考古：want 是否可考于 rel 路径的 git 全历史 blob。"""
    out = subprocess.run(["git", "log", "--all", "--format=%H", "--", rel],
                         cwd=str(repo), capture_output=True, text=True)
    if out.returncode != 0:
        return {"verified": False, "reason": "git log 失败: %s" % out.stderr.strip()[:120]}
    scanned = 0
    for c in out.stdout.split():
        b = subprocess.run(["git", "cat-file", "blob", "%s:%s" % (c, rel)],
                           cwd=str(repo), capture_output=True)
        if b.returncode != 0:
            continue
        scanned += 1
        if sha256_bytes(b.stdout) == want:
            return {"verified": True, "commit": c, "blobs_scanned": scanned}
    return {"verified": False, "reason": "全 %d 提交（命中 %d blob）无此内容 sha256"
                                        % (len(out.stdout.split()), scanned)}


def reconcile(registry: Path, repo: Path, allowlist: dict) -> dict:
    rep = {"registry": str(registry), "repo": str(repo),
           "events": [], "structure_violations": [],
           "counts": {"total": 0, "FRESH": 0, "HISTORICAL": 0,
                      "UNRESOLVED": 0, "waived": 0},
           "all_resolved": False}
    try:
        reg = json.loads(registry.read_text(encoding="utf-8"))
    except Exception as e:
        rep["structure_violations"].append("registry 不可读/非 JSON: %s" % e)
        return rep
    events = reg.get("events", []) if isinstance(reg, dict) else reg
    rep["counts"]["total"] = len(events)

    seen_ids = {}
    prev_ts = None
    for i, ev in enumerate(events):
        eid = ev.get("event_id", "<missing[%d]>" % i)
        # 结构核
        if eid in seen_ids:
            rep["structure_violations"].append(
                "event_id 重复: %s（#%d 与 #%d）" % (eid, seen_ids[eid], i))
        seen_ids[eid] = i
        ts = ev.get("timestamp", "")
        try:
            cur = dt.datetime.fromisoformat(ts)
            if prev_ts is not None and cur < prev_ts:
                rep["structure_violations"].append(
                    "timestamp 回逆: %s（%s < 前一事件）" % (eid, ts))
            prev_ts = cur if prev_ts is None or cur > prev_ts else prev_ts
        except ValueError:
            rep["structure_violations"].append("timestamp 不可解析: %s（%s）" % (eid, ts))
        rat = ev.get("registered_at", "")
        if not (isinstance(rat, str) and rat and TZ_RE.search(rat)):
            rep["structure_violations"].append(
                "registered_at 缺时区偏移: %s（%s）" % (eid, rat))

        # 账实分类
        src = ev.get("source", {})
        rel, want = src.get("path", ""), src.get("sha256", "")
        cls, detail = None, {}
        p = repo / rel if not Path(rel).is_absolute() else Path(rel)
        if p.is_file():
            actual = sha256_bytes(p.read_bytes())
            if actual == want:
                cls = "FRESH"
            else:
                hist = historical_verified(repo, rel, want)
                if hist["verified"]:
                    cls = "HISTORICAL"
                    detail = {"commit": hist["commit"],
                              "actual_sha8": actual[:8]}
                else:
                    cls = "UNRESOLVED"
                    detail = {"actual_sha8": actual[:8],
                              "reason": hist.get("reason", "")}
        else:
            cls = "UNRESOLVED"
            detail = {"reason": "源文件缺失: %s" % rel}
        waived = bool(cls == "UNRESOLVED" and eid in allowlist)
        if waived:
            detail["waive_reason"] = allowlist[eid]
        rep["events"].append({"event_id": eid, "kind": ev.get("kind", ""),
                              "class": cls, "waived": waived,
                              "path": rel, "want_sha8": want[:8], **detail})
        rep["counts"][cls] += 1
        if waived:
            rep["counts"]["waived"] += 1

    unresolved_unwaived = [e["event_id"] for e in rep["events"]
                           if e["class"] == "UNRESOLVED" and not e["waived"]]
    rep["all_resolved"] = bool(not rep["structure_violations"]
                               and not unresolved_unwaived)
    return rep


def selftest() -> int:
    results = []

    def check(name, ok, detail=""):
        results.append({"case": name, "pass": bool(ok), "detail": str(detail)[:200]})
        return bool(ok)

    import os
    with tempfile.TemporaryDirectory(prefix="ledger-reconcile-") as td:
        tmp = Path(td)
        repo = tmp / "repo"
        repo.mkdir()
        env_git = ["git", "-C", str(repo),
                   "-c", "user.email=t@t", "-c", "user.name=t"]
        def git(*a):
            return subprocess.run(env_git + list(a), capture_output=True, text=True)
        assert git("init", "-q").returncode == 0
        f = repo / "doc.json"
        f.write_text("v1-bytes", encoding="utf-8")
        assert git("add", "doc.json").returncode == 0
        assert git("commit", "-q", "-m", "v1").returncode == 0
        v1 = sha256_bytes(f.read_bytes())
        f.write_text("v2-bytes", encoding="utf-8")
        assert git("commit", "-qam", "v2").returncode == 0
        v2 = sha256_bytes(f.read_bytes())

        t0 = "2026-10-30T10:00:00+08:00"
        t1 = "2026-10-30T10:01:00+08:00"
        reg = tmp / "registry.json"
        base = {"kind": "offline_recompute", "executor": "t",
                "registered_at": t0, "locator": "t", "description": "t",
                "pin_class": "live_doc"}
        events = [
            dict(base, event_id="work:e-fresh", timestamp=t0,
                 source={"path": "doc.json", "sha256": v2}),
            dict(base, event_id="work:e-hist", timestamp=t0,
                 source={"path": "doc.json", "sha256": v1}),
            dict(base, event_id="work:e-unres", timestamp=t0,
                 source={"path": "doc.json", "sha256": "e" * 64}),
            dict(base, event_id="work:e-missing", timestamp=t1,
                 source={"path": "nope.json", "sha256": "a" * 64}),
        ]
        reg.write_text(json.dumps({"schema_version": 1, "events": events},
                                  ensure_ascii=False), encoding="utf-8")
        r = reconcile(reg, repo, {})
        check("fresh_classified", r["events"][0]["class"] == "FRESH", r["events"][0])
        check("historical_classified",
              r["events"][1]["class"] == "HISTORICAL"
              and r["events"][1].get("commit"), r["events"][1])
        check("unres_classified", r["events"][2]["class"] == "UNRESOLVED")
        check("missing_is_unresolved", r["events"][3]["class"] == "UNRESOLVED")
        check("all_resolved_false_with_unwaived", r["all_resolved"] is False)

        # allowlist 豁免
        allow = {"work:e-unres": "自测豁免", "work:e-missing": "自测豁免"}
        r2 = reconcile(reg, repo, allow)
        check("allowlist_waives", r2["all_resolved"] is True
              and r2["counts"]["waived"] == 2, r2["counts"])

        # 结构负例：重复 id + 时间回逆 + registered_at 缺时区
        bad2 = list(events)
        dup = dict(base, event_id="work:e-fresh", timestamp=t0,
                   source={"path": "doc.json", "sha256": v2})
        notz = dict(base, event_id="work:e-notz", timestamp=t0,
                    registered_at="2026-10-30T10:00:00",
                    source={"path": "doc.json", "sha256": v2})
        bad2.append(dup)
        bad2.append(notz)
        reg2 = tmp / "registry-bad.json"
        reg2.write_text(json.dumps({"events": bad2}, ensure_ascii=False),
                        encoding="utf-8")
        r3 = reconcile(reg2, repo, {})
        joined = " | ".join(r3["structure_violations"])
        check("dup_id_detected", "event_id 重复" in joined, joined[:200])
        check("ts_regress_detected", "timestamp 回逆" in joined, joined[:200])
        check("missing_tz_detected", "时区偏移" in joined, joined[:200])
        check("structure_blocks_resolved", r3["all_resolved"] is False)

    counts = {"total": len(results), "passed": sum(1 for r in results if r["pass"]),
              "failed": sum(1 for r in results if not r["pass"])}
    print(json.dumps({"kind": "self_test", "tool": "ledger_reconcile.py",
                      "at": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
                      "counts": counts, "cases": results},
                     ensure_ascii=False, indent=2))
    print("LEDGER_RECONCILE_SELFTEST:", "PASS" if counts["failed"] == 0 else "FAIL")
    return 0 if counts["failed"] == 0 else 1


def main(argv) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--registry", default=str(DEFAULT_REGISTRY))
    ap.add_argument("--repo", default=str(REPO))
    ap.add_argument("--allowlist", default=None,
                    help="JSON 对象 {event_id: 豁免理由}；UNRESOLVED 命中即豁免")
    ap.add_argument("--out", default=None)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    if not (Path(a.repo) / ".git").is_dir():
        print("--repo 不是 git 仓库根（防 HERE.parents 深度错位，L9 实测教训）: %s"
              % a.repo, file=sys.stderr)
        return 2
    allow = {}
    if a.allowlist:
        try:
            allow = json.loads(Path(a.allowlist).read_text(encoding="utf-8"))
            assert isinstance(allow, dict)
        except Exception as e:
            print("allowlist 不可读/非对象: %s" % e, file=sys.stderr)
            return 2
    rep = reconcile(Path(a.registry), Path(a.repo), allow)
    rep.update({"kind": "ledger_reconcile_report", "at":
                dt.datetime.now().astimezone().isoformat(timespec="seconds")})
    print(json.dumps({"all_resolved": rep["all_resolved"],
                      "counts": rep["counts"],
                      "structure_violations": rep["structure_violations"],
                      "unresolved": [e for e in rep["events"]
                                     if e["class"] == "UNRESOLVED"]},
                     ensure_ascii=False, indent=1))
    if a.out:
        out = Path(a.out)
        if out.exists():
            print("拒绝写入：目标已存在（C-1 同款纪律），原字节不动。", file=sys.stderr)
            return 2
        out.write_text(json.dumps(rep, ensure_ascii=False, indent=2) + "\n",
                       encoding="utf-8")
        print("REPORT:", out)
    return 0 if rep["all_resolved"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
