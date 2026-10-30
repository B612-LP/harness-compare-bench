#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L5 共同执行闸门（joint gate v2）：binding/E 封印核验 + 逐场严格准入。

v2 变更（R4，池 L5-8，唯一语义 diff）：not_executed 目录白名单除 notexecuted.json 外
放行且仅放行名字恰为 registrations 的条目（R3 强制的 pre-run 登记目录，见
5-评测报告/L4独立验收-2026-10-29/realdata-product/gate-falsepositive-bird-registration-sidecar.json），
并把其文件清单（相对路径+sha256+bytes）记入 per_slot 收据 whitelisted_entries；
其余任何 extra 名仍按原样 fail。冻结版 L4 gate 不改，历史行为以 L4 版为准。

一、verify_execution(binding_path, ...)（可 import；返回证据 dict 或 raise GateError）
  - binding 必备键、commit 全哈希、released_for_model_calls 为 bool；
  - **require_release（默认 True）**：released_for_model_calls 为 False 即 raise——
    runner 等真实消费者必须显式带 require_release=True，防止把"核验通过"误当"已放行"；
  - registered_at == E 提交时刻（只读 `git show -s --format=%cI <E>`）；E 时刻 ≤ 核验时刻；
  - 祖先关系用只读 `git merge-base --is-ancestor` 证明：D 祖先于 E、E 祖先于 HEAD
    （时钟序 D≤E 只是必要非充分，两者都查；可经 git_ancestor 注入）；
  - plan/contract 磁盘 sha == binding 记载；D、E 两提交内 blob 与磁盘三方一致；
  - execution-manifest.json 取 E blob：sha == binding.execution_manifest_sha256；
    files 逐项 = 仓库内安全相对路径（非绝对、无 ..、无反斜杠、解析后仍在仓内），
    逐文件 E blob sha == manifest sha 且磁盘 sha == manifest sha（drift fail closed）；
    external_files（绝对路径→sha）逐项实算：存在、非软链、sha 一致；
  - git 读取全部经注入点（git_reader/git_time/git_ancestor），合成测试零 git 写。

二、gate_admission(binding_path, product, ...)（先 verify_execution(release 必须)再逐场）
  R1（CLARIFICATION-L4-1）：全集记账与正式准入是两种判定。每 slot 恰一条记账：
  executed / partial / not_executed；not_executed 只需 notexecuted.json（身份+封印引用+理由
  +停止来源），**不要求也不允许 meta.json/空流/假起止时刻**；accounting_complete 只判
  全集/唯一性/声明真实性；formal_admission 按 R1 真值表：
    executed 或 genuine-timeout 且 field_compliance 且 seal_plan_integrity 且
    source_hash_integrity 且 allowed_actual_configuration 且 evidence_complete 且
    contamination_cleared 且 full_denominator_score_valid
  真实 timeout（timed_out=true + 全套证据 + 冻结全分母收据 + 无污染）可 formal_admission=true；
  基础设施 error/transport-error 恒 false（partial 记账）；能力低分不是拒收理由。
  逐键唯一性：slot_id / run_id / event_id 各自唯一。
  R2（WB）：declared_alias 必须有本批选择证据；actual_gateway=unknown 须附
  route_verification=current_not_observed + r2 历史依据；白名单未知须含影响/下一步/停止条件；
  app 版本与 asar 哈希必填；WB 独立 stratum 不得被借名跨层。
  输出分层：field_compliance / execution_status / evidence_integrity / score / formal_admission
  五层分离 + 汇总 {planned, accounted, executed, partial, not_executed, formal_admitted,
  accounting_complete, all_formal_admitted}（后两者互不混同）。

收据 --out：O_EXCL|O_NOFOLLOW 原子拒写（已存在/软链即拒）；live_doc_drift 恒为 list。
退出码：0=对应判定通过；1=判定未过；2=用法或拒写。

用法：
  python3 gate.py --verify-execution --binding <runtime-binding.json> [--no-require-release]
                  [--plan-dir <dir>] [--out <receipt>]
  python3 gate.py --admission --binding <...> --product dsh [--plan-dir <dir>] [--out <receipt>]
  python3 gate.py --selftest
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path, PurePosixPath

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
# L7-A（2026-10-30）：原默认计划目录常量已拔除——计划目录一律显式传参（CLI 必填 / API None 即拒），不再有隐式批。
# 修前行为（v2，锚定 L5 目录）见 git c8710fb；跨批错位实证=L6 E2 REFUSED（L6 废封纪要）。
SPEC = "l4-execution-gate"
ISO_TZ_TOKEN = (r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?"
                r"(?:Z|[+-]\d{2}:?\d{2})")
FULL_HEX_RE = re.compile(r"^[0-9a-f]{40}$")
# E 必锁的外部文件（镜像 runner 常量；防 external_files={} 真空通过/漏锁 AGENTS.md）
# 未知哨兵值：这些字面值一律视为"未知/不可观察"，不得冒充已知（R2 白名单管理）
UNKNOWN_SENTINELS = {"", "unknown", "unobservable", "unobserved", "not_observed",
                     "not observed", "n/a", "na", "none", "null"}


def is_known_value(v) -> bool:
    """非空且非未知哨兵字符串。"""
    return isinstance(v, str) and v.strip() != "" and v.strip().lower() not in UNKNOWN_SENTINELS


EXTERNAL_REQUIRED = [str(Path.home() / ".dsh" / "profiles" / "bench-cli" / "cordis.patch.yml"),
                     str(Path.home() / ".dsh" / "profiles" / "bench-cli" / "package.json"),
                     str(Path.home() / ".dsh" / "AGENTS.md")]
REQUIRED_BINDING_KEYS = ("design_commit", "preregistration_commit", "execution_seal_commit",
                         "registered_at", "execution_manifest_sha256", "plan_sha256",
                         "contract_sha256", "released_for_model_calls")


class GateError(Exception):
    """verify_execution/准入硬失败（fail-closed）。"""


def now_local() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    return sha256_bytes(p.read_bytes())


def whitelisted_entry_inventory(root: Path) -> list:
    """L5 gate v2 (R4): deterministic file inventory for a whitelisted not_executed entry.

    Sorted relative path + sha256 + bytes for every regular non-symlink file; an empty
    directory yields a single zero-byte entry so the receipt always shows what was there.
    """
    files = sorted(p for p in root.rglob("*") if p.is_file() and not p.is_symlink())
    out = [{"path": str(p.relative_to(root.parent)), "sha256": sha256_file(p),
            "bytes": p.stat().st_size} for p in files]
    if not out:
        out = [{"path": root.name, "sha256": hashlib.sha256(b"").hexdigest(), "bytes": 0}]
    return out


def parse_iso(v: str) -> dt.datetime:
    d = dt.datetime.fromisoformat(v)
    if d.tzinfo is None:
        raise ValueError("naive timestamp: %r" % v)
    return d


def atomic_refuse_write(path: Path, payload: str) -> None:
    """新路径原子拒写：已存在或软链即拒；O_EXCL|O_NOFOLLOW 独占创建。"""
    if path.exists() or path.is_symlink():
        raise GateError("拒绝写入：目标已存在或为软链（%s）" % path)
    if path.parent.is_symlink():
        raise GateError("拒绝写入：父目录为软链（%s）" % path.parent)
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o644)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(payload)


# ---------------------------------------------------------------- 只读 git（可注入）

def default_git_reader(repo: Path, commit: str, path: str) -> bytes:
    proc = subprocess.run(["git", "show", "%s:%s" % (commit, path)],
                          capture_output=True, timeout=60, cwd=str(repo))
    if proc.returncode != 0:
        raise GateError("git show 失败：%s:%s → %s" % (commit, path,
                                                       proc.stderr.decode("utf-8", "replace")[-200:]))
    return proc.stdout


def default_git_time(repo: Path, commit: str) -> str:
    proc = subprocess.run(["git", "show", "-s", "--format=%cI", commit],
                          capture_output=True, text=True, timeout=60, cwd=str(repo))
    if proc.returncode != 0:
        raise GateError("git show -s 失败：%s → %s" % (commit, proc.stderr[-200:]))
    return proc.stdout.strip().splitlines()[0]


def default_git_ancestor(repo: Path, ancestor: str, descendant: str) -> bool:
    proc = subprocess.run(["git", "merge-base", "--is-ancestor", ancestor, descendant],
                          capture_output=True, timeout=60, cwd=str(repo))
    return proc.returncode == 0


def is_safe_repo_rel(rel: str, repo: Path) -> bool:
    """manifest.files 键必须是仓内安全相对路径。"""
    if not rel or rel.startswith("/") or "\\" in rel or "\x00" in rel:
        return False
    parts = PurePosixPath(rel).parts
    if any(x in ("..",) for x in parts) or PurePosixPath(rel).is_absolute():
        return False
    try:
        resolved = (repo / rel).resolve()
        resolved.relative_to(repo.resolve())
    except (ValueError, OSError):
        return False
    return True


# ---------------------------------------------------------------- binding 与 verify_execution

def load_binding(binding_path: Path) -> dict:
    if binding_path.is_symlink() or not binding_path.is_file():
        raise GateError("binding 不存在或为软链：%s" % binding_path)
    b = json.loads(binding_path.read_text(encoding="utf-8"))
    missing = [k for k in REQUIRED_BINDING_KEYS if k not in b]
    if missing:
        raise GateError("binding 缺键：%s" % missing)
    for k in ("design_commit", "preregistration_commit", "execution_seal_commit"):
        if not (isinstance(b[k], str) and FULL_HEX_RE.match(b[k])):
            raise GateError("binding.%s 须为 40 位小写全哈希，实测 %r" % (k, b[k]))
    if not isinstance(b["released_for_model_calls"], bool):
        raise GateError("binding.released_for_model_calls 须为 bool")
    if not (isinstance(b["registered_at"], str) and re.fullmatch(ISO_TZ_TOKEN, b["registered_at"])):
        raise GateError("binding.registered_at 须为 ISO8601+tz，实测 %r" % b["registered_at"])
    for k in ("execution_manifest_sha256", "plan_sha256", "contract_sha256"):
        if not (isinstance(b[k], str) and re.fullmatch(r"[0-9a-f]{64}", b[k])):
            raise GateError("binding.%s 须为 64 位 sha256" % k)
    return b


def verify_execution(binding_path, repo: Path = REPO, plan_dir=None,
                     git_reader=None, git_time=None, git_ancestor=None, now=None,
                     require_release=True, required_set=None) -> dict:
    """核验 runtime binding 与 E 封印一致；require_release=True（默认）时未放行即 raise。
    required_set=None（真实路径）时复用 lead execution_seal.validate_manifest 强制必需成员集合
    （防漏封 gate/validator/runner 入口/helper；E 前缺入口被拒=正确）；合成测试注入显式集合。"""
    if plan_dir is None:
        raise GateError("plan_dir 须显式传参（L7-A：不再有隐式默认批目录）")
    binding_path = Path(binding_path)
    repo = Path(repo).resolve()
    plan_dir = Path(plan_dir).resolve()
    git_reader = git_reader or (lambda commit, path: default_git_reader(repo, commit, path))
    git_time = git_time or (lambda commit: default_git_time(repo, commit))
    git_ancestor = git_ancestor or (lambda a, b: default_git_ancestor(repo, a, b))
    now_dt = parse_iso(now) if now else dt.datetime.now().astimezone()
    rel_base = plan_dir.relative_to(repo)
    steps = []

    def step(name, ok, detail=""):
        steps.append({"step": name, "ok": bool(ok), "detail": str(detail)[:300]})
        if not ok:
            raise GateError("verify_execution 失败于 %s：%s" % (name, detail))

    b = load_binding(binding_path)
    step("binding-load", True, str(binding_path))
    step("preregistration-seal-equal",
         b["preregistration_commit"] == b["execution_seal_commit"],
         "prereg=%s seal=%s" % (b["preregistration_commit"][:8], b["execution_seal_commit"][:8]))
    if require_release and not b["released_for_model_calls"]:
        raise GateError("released_for_model_calls=false：E 未放行，拒绝真实消费"
                        "（检查类调用请显式 require_release=False）")
    step("release-gate", True, "released=%s require=%s" % (b["released_for_model_calls"], require_release))

    plan_path = plan_dir / "plan.json"
    contract_path = plan_dir / "contract.json"
    rel_plan = str(rel_base / "plan.json")
    rel_contract = str(rel_base / "contract.json")
    rel_manifest = str(rel_base / "execution-manifest.json")

    # 磁盘 plan/contract == binding 哈希（drift fail closed）
    try:
        disk_plan = sha256_file(plan_path)
        disk_contract = sha256_file(contract_path)
    except OSError as exc:
        raise GateError("plan/contract 磁盘文件缺失（missing-on-disk）：%s" % exc)
    step("plan-disk-sha", disk_plan == b["plan_sha256"],
         "disk=%s binding=%s" % (disk_plan[:8], b["plan_sha256"][:8]))
    step("contract-disk-sha", disk_contract == b["contract_sha256"],
         "disk=%s binding=%s" % (disk_contract[:8], b["contract_sha256"][:8]))

    # D/E 双提交内 plan/contract blob 一致，且与磁盘一致
    for rel, disk_sha, name in ((rel_plan, disk_plan, "plan"), (rel_contract, disk_contract, "contract")):
        d_blob = git_reader(b["design_commit"], rel)
        e_blob = git_reader(b["execution_seal_commit"], rel)
        step("%s-blob-d-e-identical" % name, d_blob == e_blob,
             "D:%s E:%s" % (sha256_bytes(d_blob)[:8], sha256_bytes(e_blob)[:8]))
        step("%s-blob-e-matches-disk" % name, sha256_bytes(e_blob) == disk_sha,
             "E:%s disk:%s" % (sha256_bytes(e_blob)[:8], disk_sha[:8]))

    # registered_at == E 提交时刻（严格等值）；E ≤ 核验时刻；时钟序 D ≤ E
    e_time_raw = git_time(b["execution_seal_commit"])
    e_dt = parse_iso(e_time_raw)
    step("registered-at-equals-E-commit-time", parse_iso(b["registered_at"]) == e_dt,
         "binding=%s git=%s" % (b["registered_at"], e_time_raw))
    step("E-before-verification", e_dt <= now_dt, "E=%s now=%s" % (e_time_raw, now_dt.isoformat()))
    step("D-clock-not-after-E", parse_iso(git_time(b["design_commit"])) <= e_dt,
         "clock-only, ancestry checked separately")

    # 祖先关系（只读 merge-base；时钟序必要非充分）
    step("ancestor-D-of-E", git_ancestor(b["design_commit"], b["execution_seal_commit"]),
         "merge-base --is-ancestor D E")
    step("ancestor-E-of-HEAD", git_ancestor(b["execution_seal_commit"], "HEAD"),
         "merge-base --is-ancestor E HEAD")

    # execution-manifest：E blob → sha 对 binding → files/external_files 逐项核
    rel_prereg = str(rel_base / "PREREGISTRATION.md")
    d_pre = git_reader(b["design_commit"], rel_prereg)
    e_pre = git_reader(b["execution_seal_commit"], rel_prereg)
    step("prereg-blob-d-e-identical", d_pre == e_pre,
         "D:%s E:%s" % (sha256_bytes(d_pre)[:8], sha256_bytes(e_pre)[:8]))

    e_manifest = git_reader(b["execution_seal_commit"], rel_manifest)
    manifest_sha = sha256_bytes(e_manifest)
    step("manifest-sha-matches-binding", manifest_sha == b["execution_manifest_sha256"],
         "E=%s binding=%s" % (manifest_sha[:8], b["execution_manifest_sha256"][:8]))
    manifest = json.loads(e_manifest.decode("utf-8"))
    step("manifest-design-matches-binding",
         manifest.get("design_commit") == b["design_commit"],
         "manifest=%s binding=%s" % (str(manifest.get("design_commit"))[:8], b["design_commit"][:8]))
    files = manifest.get("files")
    ext = manifest.get("external_files") or {}
    if not isinstance(files, dict) or not files:
        raise GateError("execution-manifest.files 缺失或为空（不接受空 dict 浅校验）")
    if not isinstance(ext, dict):
        raise GateError("execution-manifest.external_files 须为 dict")
    # 必需成员集合（防漏封关键代码）：真实路径复用 lead validate_manifest；合成注入集合
    if required_set is None:
        es = load_execution_seal(plan_dir)
        try:
            es.validate_manifest(manifest)
            step("manifest-required-members", True,
                 "validate_manifest（required_files 全覆盖，n=%d）" % len(files))
        except ValueError as exc:
            raise GateError("manifest 违反必需成员/结构（防漏封）：%s" % exc)
    else:
        missing_req = sorted(set(required_set) - set(files))
        step("manifest-required-members", not missing_req,
             "missing=%s" % missing_req[:5])
    drift = []
    for rel, want in sorted(files.items()):
        if not is_safe_repo_rel(rel, repo):
            drift.append({"path": rel, "reason": "unsafe-path"})
            continue
        try:
            e_blob_sha = sha256_bytes(git_reader(b["execution_seal_commit"], rel))
        except GateError:
            drift.append({"path": rel, "reason": "not-in-E-blob"})
            continue
        p = repo / rel
        if not p.is_file():
            drift.append({"path": rel, "reason": "missing-on-disk"})
            continue
        disk = sha256_file(p)
        if e_blob_sha != want or disk != want:
            drift.append({"path": rel, "reason": "sha-mismatch",
                          "want": want[:8], "e": e_blob_sha[:8], "disk": disk[:8]})
    ext_locked = [p for p in EXTERNAL_REQUIRED if p not in ext]
    step("manifest-external-required-locked", not ext_locked,
         "missing-locked=%s" % [p.rsplit("/", 1)[-1] for p in ext_locked])
    ext_drift = []
    for apath, want in sorted(ext.items()):
        p = Path(apath)
        if p.is_symlink() or not p.is_file():
            ext_drift.append({"path": apath, "reason": "missing-or-symlink"})
            continue
        got = sha256_file(p)
        if got != want:
            ext_drift.append({"path": apath, "reason": "sha-mismatch",
                              "want": want[:8], "got": got[:8]})
    step("manifest-files-safe-and-consistent", not drift,
         json.dumps(drift[:5], ensure_ascii=False))
    step("manifest-external-files-consistent", not ext_drift,
         json.dumps(ext_drift[:5], ensure_ascii=False))

    return {"binding": b, "binding_sha256": sha256_file(binding_path),
            "steps": steps, "ok": True,
            "release_check": {"require_release": require_release,
                              "released_for_model_calls": b["released_for_model_calls"],
                              "consumable_for_real_calls": bool(b["released_for_model_calls"] and require_release)},
            "manifest_files": len(files), "manifest_external_files": len(ext),
            "e_commit_time": e_time_raw, "verified_at": now_local(),
            "live_doc_drift": []}


# ---------------------------------------------------------------- 逐场准入

def load_runner_validator():
    vrm = REPO / "1-评测方案" / "工具链" / "runner-schema-v2" / "validate_runner_meta.py"
    spec = importlib.util.spec_from_file_location("l4_vrm", vrm)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_execution_seal(plan_dir: Path = None):
    """只读导入 lead 的 execution_seal（required_files/validate_manifest；无模型调用）。

    L5 v2：随 plan_dir 取各批自己的 seal 脚本（required_files 与该批 runtime roots
    对应），使同一 gate 可复判历史批次（L4 复判传 plan_dir=L4 目录，用 L4 seal 检查
    L4 manifest，成员集才可比）。"""
    if plan_dir is None:
        raise GateError("plan_dir 须显式传参（L7-A：不再有隐式默认批目录）")
    p = Path(plan_dir) / "execution_seal.py"
    spec = importlib.util.spec_from_file_location("l4_execution_seal", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _nonempty_route(d) -> bool:
    """实际路由证据：dict 且存在非空字符串值（空 dict/空串不作事实）。"""
    return isinstance(d, dict) and any(isinstance(v, str) and v.strip() for v in d.values())


def _read_json(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def gate_admission(binding_path: Path, product: str, repo: Path = REPO, plan_dir=None,
                   git_reader=None, git_time=None, git_ancestor=None, required_set=None) -> dict:
    """真实批次逐场准入。先 verify_execution（release 必须）再逐场；fail-closed。"""
    vm = load_runner_validator()
    binding = load_binding(Path(binding_path))
    if not binding["released_for_model_calls"]:
        raise GateError("准入判定要求 released_for_model_calls=true（当前 %r）"
                        % binding["released_for_model_calls"])
    verify_execution(binding_path, repo=repo, plan_dir=plan_dir, git_reader=git_reader,
                     git_time=git_time, git_ancestor=git_ancestor, require_release=True,
                     required_set=required_set)
    seal_dt = parse_iso(binding["registered_at"])
    plan = _read_json(Path(plan_dir) / "plan.json")
    contract = _read_json(Path(plan_dir) / "contract.json")

    slots = [s for s in plan["product_slots"] if s.get("product") == product]
    if not slots:
        raise GateError("plan 中无 product=%s 的 slot" % product)
    # 逐键唯一（slot_id/run_id/event_id 各自独立唯一）
    for key in ("slot_id", "run_id", "event_id"):
        vals = [s[key] for s in slots]
        dupes = sorted({v for v in vals if vals.count(v) > 1})
        if dupes:
            raise GateError("plan %s 重复：%s" % (key, dupes))
    strata_cfg = contract["strata"]
    required_evidence = contract.get("admission", {}).get("required_original_evidence",
                                                          ["prompt", "stdout", "stderr", "session", "checker", "workspace"])

    per_slot = []
    summary = {"planned": len(slots), "accounted": 0, "executed": 0, "partial": 0,
               "not_executed": 0, "formal_admitted": 0}
    for slot in sorted(slots, key=lambda s: s["order"]):
        rec = {"slot_id": slot["slot_id"], "order": slot["order"], "case": slot["case"],
               "evidence_dir": slot["evidence_dir"], "accounting": None,
               "field_compliance": False, "execution_status": "not_executed",
               "genuine_timeout": False, "evidence_integrity": False,
               "seal_plan_integrity": False, "source_hash_integrity": False,
               "allowed_actual_configuration": False, "evidence_complete": False,
               "contamination_cleared": False, "full_denominator_score_valid": False,
               "score": None, "formal_admission": False, "fails": []}
        fails = rec["fails"]
        ev = repo / slot["evidence_dir"]
        meta_p = ev / "meta.json"
        ne_p = ev / "notexecuted.json"

        # ---------- not_executed 分支（R1）：不要求 meta，也禁止虚造 ----------
        if not meta_p.is_file():
            if ne_p.is_file():
                try:
                    ne = _read_json(ne_p)
                    ok_id = (ne.get("slot_id") == slot["slot_id"] and ne.get("run_id") == slot["run_id"]
                             and ne.get("event_id") == slot["event_id"])
                    if not ok_id:
                        fails.append("notexecuted.json 身份与 plan 不一致")
                    if ne.get("preregistration_commit") != binding["preregistration_commit"]:
                        fails.append("notexecuted.json 缺正确封印引用")
                    if not vm.nonempty(ne.get("reason")) or not vm.nonempty(ne.get("stop_source")):
                        fails.append("not_executed 须非空 reason 与 stop_source")
                except Exception as exc:
                    fails.append("notexecuted.json 不可解析：%s" % exc)
                extra = [p.name for p in ev.iterdir() if p.name not in ("notexecuted.json",)]
                # L5 gate v2 (R4, pool L5-8): R3-style pre-run registrations/ is required
                # evidence, not fabrication; whitelist exactly this name and record its
                # inventory in the per-slot receipt. Any other extra name still fails.
                bad_extra = [n for n in extra if n != "registrations"]
                if bad_extra:
                    fails.append("not_executed 目录含其他文件（疑似虚造证据/空流）：%s" % bad_extra[:5])
                if "registrations" in extra:
                    rec["whitelisted_entries"] = whitelisted_entry_inventory(ev / "registrations")
                rec["record_valid"] = bool(
                    ok_id and ne.get("preregistration_commit") == binding["preregistration_commit"]
                    and vm.nonempty(ne.get("reason")) and vm.nonempty(ne.get("stop_source"))
                    and not bad_extra)
                rec["accounting"] = "not_executed"
                rec["execution_status"] = "not_executed"
                rec["score"] = None
                summary["not_executed"] += 1
            else:
                fails.append("无 meta.json 且无 notexecuted.json（缺记账，非 skip）")
                rec["accounting"] = None
                rec["execution_status"] = "unaccounted"
                rec["record_valid"] = False
            per_slot.append(rec)
            continue

        # ---------- 已执行分支 ----------
        summary["accounted"] += 1
        meta = _read_json(meta_p)
        if ne_p.is_file():
            fails.append("meta 与 notexecuted 并存（一 slot 只允许一条记账）")
            rec["record_valid"] = False
        else:
            rec["record_valid"] = True

        res = vm.validate_meta(meta, seal_at=seal_dt)
        cls = vm.classify(res, allow_unsealed=False)
        rec["field_compliance"] = (cls == "pass")
        if cls != "pass":
            fails.append("classify=%s issues=%s" % (cls, res["issues"][:4]))

        # 身份对齐 + 时序 + 封印锚（严格等值）
        if meta.get("slot_id") != slot["slot_id"]:
            fails.append("slot_id 不匹配：%r" % meta.get("slot_id"))
        if meta.get("run_id") != slot["run_id"]:
            fails.append("run_id 不匹配：%r" % meta.get("run_id"))
        if meta.get("event_id") != slot["event_id"]:
            fails.append("event_id 不匹配：%r" % meta.get("event_id"))
        if meta.get("case") != slot["case"] or meta.get("rep") != slot["rep"]:
            fails.append("case/rep 与 plan 不一致")
        if meta.get("product") != product:
            fails.append("meta.product 与门内 product 不一致：%r" % meta.get("product"))
        if meta.get("rule_version") != contract.get("rule_version"):
            fails.append("rule_version 与 contract 不一致：%r" % meta.get("rule_version"))
        if meta.get("order") != slot["order"]:
            fails.append("order 与 plan 不一致：%r" % meta.get("order"))
        if meta.get("registered_at") != binding["registered_at"]:
            fails.append("registered_at 与 binding 非严格等值：%r" % meta.get("registered_at"))
        if meta.get("preregistration_commit") != binding["preregistration_commit"]:
            fails.append("preregistration_commit 与 binding 不一致")
        try:
            if parse_iso(meta["registered_at"]) >= parse_iso(meta["started_at"]):
                fails.append("registered_at >= started_at")
        except Exception as exc:
            fails.append("时序不可判：%s" % exc)
        rec["seal_plan_integrity"] = not any(f.startswith(("registered_at", "preregistration_commit",
                                                            "时序不可判", "registered_at >=")) for f in fails)
        # attempts：whole_execution_restarts=0
        attempts = meta.get("attempts")
        if not isinstance(attempts, list) or len(attempts) != 1:
            fails.append("attempts 须为单元素（whole_execution_restarts=0），实测 %s"
                         % (len(attempts) if isinstance(attempts, list) else type(attempts).__name__))

        status = meta.get("status")
        rec["execution_status"] = status if status in ("ok", "timeout", "error", "transport-error") \
            else "unknown-status"
        if status == "ok" and meta.get("exit_code") != 0 \
                and slot["stratum"] != "wb_gateway_delivery":
            fails.append("status=ok 但 exit_code=%r≠0（CLI 须真实 0；WB 走原生终态证据，不虚造 0）"
                         % (meta.get("exit_code"),))
        # selection/actual 语义
        if status == "ok" or status == "timeout":
            if not (isinstance(meta.get("selection"), dict)
                    and meta["selection"].get("slot_id") == slot["slot_id"]):
                fails.append("status=%s 但 selection 非 plan slot 实义" % status)
        else:
            if not (meta.get("selection") is None and vm.nonempty(meta.get("diagnostic"))):
                fails.append("status≠ok/timeout 须 selection=null + 非空 diagnostic")

        # 路由/模型实际证据 + strata 归属（R2 分支）
        stratum = slot["stratum"]
        scfg = strata_cfg.get(stratum) or {}
        route = meta.get("route")
        cfg_ok = True
        if not _nonempty_route(route):
            cfg_ok = False
            fails.append("route 非空实际证据缺失（空 dict 不作事实）")
        else:
            if stratum == "cli_current_sentinel":
                if scfg and route.get("host") != scfg.get("route_host"):
                    cfg_ok = False
                    fails.append("route.host=%r ≠ contract %r" % (route.get("host"), scfg.get("route_host")))
                if scfg and (meta.get("model") != scfg.get("model")
                             or meta.get("reasoning_effort") != scfg.get("effort")):
                    cfg_ok = False
                    fails.append("model/effort 与 strata 不一致")
            elif stratum == "wb_gateway_delivery":
                alias_ev = route.get("alias_evidence")
                alias_p = (ev / str(alias_ev)) if vm.nonempty(alias_ev) and (ev / str(alias_ev)).exists() \
                    else (repo / str(alias_ev) if vm.nonempty(alias_ev) else None)
                if route.get("declared_alias") != scfg.get("declared_model_alias") \
                        or alias_p is None or not alias_p.exists():
                    cfg_ok = False
                    fails.append("WB declared_alias 缺本批选择证据（指向原始记录）")
                gw = route.get("actual_gateway", "unknown")
                gw_unknown = (not isinstance(gw, str)) or gw.strip() == "" \
                    or gw.strip().lower() in UNKNOWN_SENTINELS
                managed = meta.get("managed_unknowns") or []
                managed_items = " | ".join(str(u.get("item", "")) for u in managed
                                           if isinstance(u, dict))
                if gw_unknown:
                    if route.get("route_verification") != "current_not_observed" \
                            or not vm.nonempty(route.get("r2_history_ref")):
                        cfg_ok = False
                        fails.append("actual_gateway=unknown 须 route_verification=current_not_observed"
                                     " + r2 历史依据")
                    # unknown 必须进白名单管理（含影响/下一步/停止条件三元组）
                    if not any(isinstance(u, dict) and vm.nonempty(u.get("impact"))
                               and vm.nonempty(u.get("next_step")) and vm.nonempty(u.get("stop_condition"))
                               and "gateway" in str(u.get("item", "")) for u in managed):
                        cfg_ok = False
                        fails.append("actual_gateway=unknown 但 managed_unknowns 未覆盖 gateway 项"
                                     "（含影响/下一步/停止条件）")
                else:
                    if route.get("route_verification") != "observed" \
                            or not vm.nonempty(route.get("observation_method")):
                        cfg_ok = False
                        fails.append("actual_gateway 实测须 route_verification=observed + 非空观察方法")
                if (not is_known_value(meta.get("reasoning_effort"))) \
                        and not any(isinstance(u, dict) and "effort" in str(u.get("item", ""))
                                    and vm.nonempty(u.get("impact")) and vm.nonempty(u.get("next_step"))
                                    and vm.nonempty(u.get("stop_condition")) for u in managed):
                    cfg_ok = False
                    fails.append("WB effort 缺失/未知哨兵（%r）且 managed_unknowns 未覆盖 effort 项"
                                 % meta.get("reasoning_effort"))
                if not (isinstance(meta.get("product_version"), str) and meta.get("product_version").strip()):
                    cfg_ok = False
                    fails.append("WB 本批 app 版本未知（不可豁免）")
                if not (isinstance(meta.get("app_asar_sha256"), str)
                        and re.fullmatch(r"[0-9a-f]{64}", meta.get("app_asar_sha256") or "")):
                    cfg_ok = False
                    fails.append("WB 本批 app.asar 哈希缺失")
            # 白名单未知管理（R2）：effort 档位/网关上游等不阻断，但须列影响/下一步/停止条件
            unk_list = meta.get("managed_unknowns")
            if unk_list not in (None, []) and not isinstance(unk_list, list):
                cfg_ok = False
                fails.append("managed_unknowns 须为 list（list-of-item dict），实测 %s"
                             % type(unk_list).__name__)
            else:
                for unk in (unk_list or []):
                    if not isinstance(unk, dict):
                        cfg_ok = False
                        fails.append("managed_unknowns 条目须为 dict（item/impact/next_step/"
                                     "stop_condition），实测 %s" % type(unk).__name__)
                        break
                    if not (vm.nonempty(unk.get("item")) and vm.nonempty(unk.get("impact"))
                            and vm.nonempty(unk.get("next_step")) and vm.nonempty(unk.get("stop_condition"))):
                        cfg_ok = False
                        fails.append("managed_unknowns 条目缺影响/下一步/停止条件")
        if meta.get("stratum") not in (None, stratum):
            cfg_ok = False
            fails.append("meta.stratum 与 plan 不符（禁止跨层借名）")
        iso = meta.get("isolation")
        if not (isinstance(iso, dict) and iso.get("ok") is True):
            cfg_ok = False
            fails.append("isolation.ok 非真（空/缺不做事实）")
        if status in ("ok", "timeout"):
            iv = meta.get("inputs_verification")
            if not (isinstance(iv, dict) and iv.get("ok") is True):
                cfg_ok = False
                fails.append("inputs_verification.ok 非真（派发前输入子集未对 contract 机械比对）")
        rec["allowed_actual_configuration"] = cfg_ok

        # 原始证据 + canonical 实算（原始流不冒称；full 另列字段独立核）
        src_ok = True
        # 文件名约定：默认固定名；meta.evidence_paths 可按角色覆盖（相对 evidence_dir，禁出目录）
        evp = meta.get("evidence_paths") or {}
        if not isinstance(evp, dict):
            fails.append("evidence_paths 须为 dict")
            src_ok = False
            evp = {}
        for role, relp in evp.items():
            if role not in ("prompt", "stdout", "stderr", "session", "workspace") \
                    or not isinstance(relp, str) or not relp or relp.startswith("/") \
                    or ".." in PurePosixPath(relp).parts or "\\" in relp:
                fails.append("evidence_paths.%s 非法（%r）" % (role, relp))
                src_ok = False
                evp = {}
                break

        def evp_path(role, default):
            rel = evp.get(role)
            return (ev / rel) if rel else (ev / default)
        ev_files = {"prompt": evp_path("prompt", "prompt.txt"), "stdout": evp_path("stdout", "agent.jsonl"),
                    "stderr": evp_path("stderr", "agent.stderr.txt"), "session": evp_path("session", "agent-session"),
                    "workspace": evp_path("workspace", "workspace")}
        if status in ("ok", "timeout", "error", "transport-error"):
            if ev_files["prompt"].is_file():
                if meta.get("prompt_sha256") not in (None, sha256_file(ev_files["prompt"])):
                    src_ok = False
                    fails.append("prompt_sha256 与原始文件实算不符")
            else:
                src_ok = False
                fails.append("prompt 原始文件缺失")
        if status in ("ok", "timeout"):
            for role, path in (("stdout", ev_files["stdout"]), ("stderr", ev_files["stderr"])):
                if not path.is_file():
                    src_ok = False
                    fails.append("原始 %s 缺失" % role)
                    continue
                got, nb = sha256_file(path), path.stat().st_size
                if meta.get("%s_sha256" % role) not in (None, got):
                    src_ok = False
                    fails.append("canonical %s_sha256 与原始文件实算不符" % role)
                if meta.get("%s_bytes" % role) not in (None, nb):
                    src_ok = False
                    fails.append("canonical %s_bytes 与原始文件不符" % role)
                if role == "stdout" and nb == 0:
                    src_ok = False
                    fails.append("canonical stdout 为空文件（无原生 trace 原物；SHA(empty)+clean "
                                 "不作为执行证据）")
            sess = ev_files["session"]
            if not (sess.is_dir() and any(sess.iterdir())):
                src_ok = False
                fails.append("会话轨迹缺失")
            if not ev_files["workspace"].is_dir():
                src_ok = False
                fails.append("workspace 归档缺失")
            full = meta.get("archived_stdout") or {}
            if full.get("full_file"):
                fp = ev / full["full_file"]
                if not fp.is_file() or not full.get("full_sha256") \
                        or sha256_file(fp) != full["full_sha256"]:
                    src_ok = False
                    fails.append("full 重建流与另列字段不符")
        rec["source_hash_integrity"] = src_ok

        # R1 evidence_complete：required_original_evidence 逐项在盘
        have = {"prompt": ev_files["prompt"].is_file(), "stdout": ev_files["stdout"].is_file(),
                "stderr": ev_files["stderr"].is_file(),
                "session": ev_files["session"].is_dir() and any(ev_files["session"].iterdir()),
                "workspace": ev_files["workspace"].is_dir(), "checker": (ev / "checker.stdout").is_file()}
        missing_ev = [k for k in required_evidence if not have.get(k, False)]
        rec["evidence_complete"] = (not missing_ev)
        if missing_ev and status in ("ok", "timeout"):
            fails.append("required_original_evidence 缺：%s" % missing_ev)

        # 判卷：冻结 checker 哈希 + 全分母 + 8dp（score tier）
        snap = contract["case_snapshots"].get(slot["case"])
        score_ok = False
        receipt_p = ev / "score-receipt.json"
        if snap is None:
            fails.append("contract 无该 case 快照")
        elif receipt_p.is_file():
            rec["score_receipt_sha256"] = sha256_file(receipt_p)
            want_chk = snap["checker.py"]
            score_problems = []
            judge = meta.get("judge") or {}
            if judge.get("checker_sha256") != want_chk:
                score_problems.append("judge.checker_sha256 缺失或与 contract 不一致")
            try:
                rc = _read_json(receipt_p)
                score_obj = rc.get("score") or {}
                if score_obj.get("checker_sha256") != want_chk:
                    score_problems.append("score-receipt.checker_sha256 缺失或与 contract 不一致")
                # raw checker.stdout 解析（兼容 dict 或 JSON 字符串；'7/10' 自由文本拒绝）
                raw_doc = None
                raw_p = ev / "checker.stdout"
                if raw_p.is_file():
                    try:
                        raw_doc = json.loads(raw_p.read_text(encoding="utf-8"))
                        if isinstance(raw_doc, str):
                            raw_doc = json.loads(raw_doc)
                    except Exception:
                        score_problems.append("checker.stdout 非可解析 JSON（自由文本不接受）")
                else:
                    score_problems.append("原始 checker.stdout 缺失")
                if isinstance(raw_doc, dict):
                    try:
                        emb = rc.get("raw_checker_output")
                        if isinstance(emb, str):
                            emb = json.loads(emb)
                        if json.dumps(raw_doc, sort_keys=True) != json.dumps(emb or {}, sort_keys=True):
                            score_problems.append("raw checker.stdout 与 receipt.raw_checker_output 不一致")
                    except Exception:
                        score_problems.append("receipt.raw_checker_output 不可解析")
                elif raw_doc is not None:
                    score_problems.append("checker.stdout 须为 JSON object")
                # 计数/guard 重算（必要条件；raw weighted 的 2dp 精度不作等值门——L2 D2）
                checks = raw_doc.get("checks") if isinstance(raw_doc, dict) else None
                guards = judge.get("guards_used")
                if not isinstance(checks, list) or not checks:
                    score_problems.append("raw checker checks 缺失（无法计数重算）")
                elif not isinstance(guards, list):
                    score_problems.append("meta.judge.guards_used 缺失（无法按 guard 重算 earned/possible）")
                else:
                    gset = set(guards)
                    scored = [c for c in checks if isinstance(c, dict) and c.get("id") not in gset]
                    earned_raw = sum(1 for c in scored if c.get("pass") is True)
                    possible_raw = len(scored)
                    denom = contract["denominators"].get(slot["case"])
                    if possible_raw != denom:
                        score_problems.append("raw 计分项数 %d ≠ contract 分母 %r" % (possible_raw, denom))
                    if judge.get("correct") != earned_raw or judge.get("n_tasks") != possible_raw:
                        score_problems.append("meta.judge 计数 %r/%r ≠ raw 重算 %d/%d"
                                              % (judge.get("correct"), judge.get("n_tasks"),
                                                 earned_raw, possible_raw))
                    exp8 = round(100.0 * earned_raw / possible_raw, 8) if possible_raw else None
                    rep = score_obj.get("reported")
                    if exp8 is None or rep is None or float(rep) != exp8:
                        score_problems.append("score.reported ≠ 按原始计数重算 8dp")
                    if exp8 is not None and meta.get("weighted") != exp8:
                        score_problems.append("meta.weighted ≠ 按原始计数重算 8dp")
                    # raw weighted 仅作信息性交叉（2dp 源允许）
                    raw_w = raw_doc.get("weighted") if isinstance(raw_doc, dict) else None
                    rec["score"] = {"reported": rep, "denominator": contract["denominators"].get(slot["case"]),
                                    "earned_recomputed": earned_raw, "possible_recomputed": possible_raw,
                                    "raw_weighted_cross_check": {"raw": raw_w, "exp8": exp8,
                                                                 "within_2dp_rounding": (
                                                                     abs(float(raw_w) - float(exp8)) <= 0.005
                                                                     if isinstance(raw_w, (int, float)) and exp8 is not None
                                                                     else None)}}
                fails.extend(score_problems)
                score_ok = (not score_problems)
            except Exception as exc:
                fails.append("score-receipt 不可解析：%s" % exc)
        else:
            fails.append("score-receipt.json 缺失（全分母收据是准入必要证据）")
        rec["full_denominator_score_valid"] = score_ok

        # 污染裁定
        verd = meta.get("integrity_verdict")
        rec["contamination_cleared"] = verd in ("clean", "benign-reviewed")
        if verd == "violation":
            fails.append("integrity_verdict=violation（污染，不准入、不删槽）")
        rec["evidence_integrity"] = rec["contamination_cleared"] and src_ok

        # R1 formal 真值表
        duration_real = isinstance(meta.get("duration_s"), (int, float)) and \
            float(meta["duration_s"]) >= float(slot["timeout_s"])
        outcome_timeout = (isinstance(attempts, list) and attempts
                           and isinstance(attempts[0], dict)
                           and attempts[0].get("outcome") == "timeout")
        # 停止证据=原物核验，不只信 outcome/stop_source 字符串：
        #   cli 层：termination-receipt.json 原物存在 + sha 与 meta.termination_receipt 绑定一致
        #           + doc.verified_stop is True + 时点字段；WB 层只认 native_stop 信封（防借 CLI 收据穿透）
        stop_verified = False
        if status in ("ok", "timeout"):
            # 同一"停止后判卷"判据：所有已执行 CLI 正式候选须已确认组闭包
            bind = meta.get("termination_receipt") or {}
            if stratum != "wb_gateway_delivery" and isinstance(bind, dict) \
                    and bind.get("file") and bind.get("sha256"):
                tp = ev / str(bind["file"])
                if tp.is_symlink() or not tp.is_file():
                    fails.append("termination receipt 原物缺失/软链：%r" % bind.get("file"))
                elif sha256_file(tp) != bind.get("sha256"):
                    fails.append("termination receipt sha 与 meta 绑定不符")
                else:
                    try:
                        doc = _read_json(tp)
                        if "verified_stop" in bind and \
                                bool(bind.get("verified_stop")) != bool(doc.get("verified_stop")):
                            fails.append("termination 双说矛盾：meta binding 与 doc 的 verified_stop 不一致")
                        if doc.get("slot_id") not in (None, meta.get("slot_id"), slot["slot_id"]):
                            fails.append("termination receipt slot_id 与本场不符（疑似挪用他场收据）:%r"
                                         % doc.get("slot_id"))
                        a0 = attempts[0] if (isinstance(attempts, list) and attempts
                                             and isinstance(attempts[0], dict)) else {}
                        if not (isinstance(doc.get("pgid"), int) and doc.get("pgid", 0) > 0):
                            fails.append("termination receipt 缺启动时 pgid（组级确认依据）")
                        elif a0.get("pgid") is not None and doc.get("pgid") != a0.get("pgid"):
                            fails.append("receipt pgid %r \u2260 attempt 实际 pgid %r"
                                         % (doc.get("pgid"), a0.get("pgid")))
                        if a0.get("pid") is not None and doc.get("pid") not in (None, a0.get("pid")):
                            fails.append("receipt pid \u2260 attempt 实际 pid")
                        try:
                            if doc.get("at") and parse_iso(doc["at"]) < parse_iso(meta["started_at"]):
                                fails.append("receipt 时点早于本场 started_at（时序起点不符）")
                        except Exception:
                            fails.append("receipt 时点不可解析")
                        if doc.get("verified_stop") is not True:
                            fails.append("termination receipt verified_stop\u2260true（未验证停止不得 formal）")
                        elif doc.get("group_confirmed_gone") is not True:
                            fails.append("termination receipt 未经组级确认消失（group_confirmed_gone\u2260true）")
                        elif not vm.nonempty(doc.get("at")) or not vm.nonempty(doc.get("ack_at")):
                            fails.append("termination receipt 缺发出/确认时点")
                        # normal_exit 合法以探针为证（signal=None）；需信号的场景须合法 signal
                        probe_gone = doc.get("probe") == "verified_gone"
                        if doc.get("signal") is None and not (probe_gone and doc.get("phase") == "normal_exit"):
                            fails.append("signal 缺失且非 normal_exit 组不存在探针证明")
                        if doc.get("signal") is not None and doc.get("signal") not in ("SIGTERM", "SIGKILL"):
                            fails.append("termination receipt signal 非法：%r" % doc.get("signal"))
                        if status == "timeout":
                            if not (isinstance(attempts, list) and attempts
                                    and isinstance(attempts[0], dict)
                                    and attempts[0].get("outcome") == "timeout"):
                                fails.append("attempts[0].outcome\u2260timeout 与停止证据不一致")
                        # 两状态统一：无任何收据类 fail 即组闭包已确认
                        stop_verified = not any(f.startswith("termination") or "双说矛盾" in f
                                                or "slot_id 与本场" in f or "pgid" in f
                                                or "pid \u2260" in f or "时序起点" in f
                                                or "时点不可解析" in f for f in fails)
                    except Exception as exc:
                        fails.append("termination receipt 不可解析：%s" % exc)
            elif stratum != "wb_gateway_delivery":
                fails.append("已执行 formal 候选缺 termination receipt 原物绑定（组闭包未证）")
            if status == "timeout" and stratum != "wb_gateway_delivery" and not stop_verified:
                # timeout 的 genuine 约束（duration/outcome/verified）在 executed_or_timeout 处统一评估
                pass
        if status == "ok" and stratum == "wb_gateway_delivery":
            nt = meta.get("native_terminal") or {}
            if not (isinstance(nt, dict) and nt.get("file") and nt.get("sha256")):
                fails.append("WB completed 缺原生终态证据绑定 meta.native_terminal"
                             "（无 OS exit_code，须 DB/trace 终态原物可核，不虚造 0）")
            else:
                ntp = ev / str(nt["file"])
                if ntp.is_symlink() or not ntp.is_file():
                    fails.append("WB 原生终态原物缺失/软链：%r" % nt.get("file"))
                elif sha256_file(ntp) != nt.get("sha256"):
                    fails.append("WB 原生终态 sha 与绑定不符")
                else:
                    try:
                        ndoc = _read_json(ntp)
                        if ndoc.get("slot_id") not in (None, meta.get("slot_id"), slot["slot_id"]):
                            fails.append("WB 原生终态 slot_id 与本场不符")
                        if ndoc.get("terminal") is not True or ndoc.get("state") != "completed":
                            fails.append("WB 原生终态非 completed（terminal/state=%r/%r，活动态/错误态不得 formal）" % (ndoc.get("terminal"), ndoc.get("state")))
                        elif not vm.nonempty(ndoc.get("verified_at")):
                            fails.append("WB 原生终态缺 verified_at")
                    except Exception as exc:
                        fails.append("WB 原生终态不可解析：%s" % exc)
        if status == "timeout" and stratum == "wb_gateway_delivery":
            stop_verified = False
            bind = meta.get("native_stop") or {}
            if isinstance(bind, dict) and bind.get("file") and bind.get("sha256"):
                np_ = ev / str(bind["file"])
                if np_.is_symlink() or not np_.is_file() or sha256_file(np_) != bind.get("sha256"):
                    fails.append("WB native stop 原物缺失/sha 不符")
                else:
                    ndoc = _read_json(np_)
                    if "verified_stop" in bind and \
                            bool(bind.get("verified_stop")) != bool(ndoc.get("verified_stop")):
                        fails.append("WB native_stop 双说矛盾：binding 与 doc 不一致")
                    if ndoc.get("slot_id") not in (None, meta.get("slot_id"), slot["slot_id"]):
                        fails.append("WB native stop slot_id 与本场不符")
                    if ndoc.get("verified_stop") is True:
                        checks = ndoc.get("checks") or {}
                        need = {"db_terminal", "trace_stable", "no_scoped_processes"}
                        if not (isinstance(checks, dict) and need.issubset(checks)
                                and all(checks[k] is True for k in need)):
                            fails.append("WB native stop verified=true 但 checks 三项"
                                         "（db_terminal/trace_stable/no_scoped_processes）未全为 true")
                        else:
                            stop_verified = True
                    else:
                        fails.append("WB native stop verified_stop\u2260true（未验证停止不得 formal）")
            else:
                fails.append("WB timeout 须 native_stop 原物信封（CLI receipt 不接受）")
            if not (isinstance(attempts, list) and attempts and isinstance(attempts[0], dict)
                    and attempts[0].get("outcome") == "timeout"):
                fails.append("attempts[0].outcome\u2260timeout 与停止证据不一致")
            bind = meta.get("termination_receipt") or {}
            if stratum != "wb_gateway_delivery" and isinstance(bind, dict) \
                    and bind.get("file") and bind.get("sha256"):
                tp = ev / str(bind["file"])
                if tp.is_symlink() or not tp.is_file():
                    fails.append("termination receipt 原物缺失/软链：%r" % bind.get("file"))
                elif sha256_file(tp) != bind.get("sha256"):
                    fails.append("termination receipt sha 与 meta 绑定不符")
                else:
                    try:
                        doc = _read_json(tp)
                        if "verified_stop" in bind and \
                                bool(bind.get("verified_stop")) != bool(doc.get("verified_stop")):
                            fails.append("termination 双说矛盾：meta binding 与 doc 的 verified_stop 不一致")
                        if doc.get("slot_id") not in (None, meta.get("slot_id"), slot["slot_id"]):
                            fails.append("termination receipt slot_id 与本场不符（疑似挪用他场收据）:%r"
                                         % doc.get("slot_id"))
                        a0 = attempts[0] if (isinstance(attempts, list) and attempts
                                             and isinstance(attempts[0], dict)) else {}
                        if not (isinstance(doc.get("pgid"), int) and doc.get("pgid", 0) > 0):
                            fails.append("termination receipt 缺启动时 pgid（组级确认依据）")
                        elif a0.get("pgid") is not None and doc.get("pgid") != a0.get("pgid"):
                            fails.append("receipt pgid %r \u2260 attempt 实际 pgid %r"
                                         % (doc.get("pgid"), a0.get("pgid")))
                        if a0.get("pid") is not None and doc.get("pid") not in (None, a0.get("pid")):
                            fails.append("receipt pid \u2260 attempt 实际 pid")
                        try:
                            if doc.get("at") and parse_iso(doc["at"]) < parse_iso(meta["started_at"]):
                                fails.append("receipt 时点早于本场 started_at（时序起点不符）")
                        except Exception:
                            fails.append("receipt 时点不可解析")
                        if doc.get("verified_stop") is not True:
                            fails.append("termination receipt verified_stop\u2260true（未验证停止不得 formal）")
                        elif not (isinstance(doc.get("pgid"), int) and doc.get("pgid", 0) > 0):
                            fails.append("termination receipt 缺启动时 pgid（组级确认依据）")
                        elif doc.get("group_confirmed_gone") is not True:
                            fails.append("termination receipt 未经组级确认消失（group_confirmed_gone\u2260true；"
                                         "父 CLI 退出不等于组受控退出）")
                        elif not vm.nonempty(doc.get("at")) or not vm.nonempty(doc.get("ack_at")):
                            fails.append("termination receipt 缺发出/确认时点")
                        elif doc.get("signal") not in ("SIGTERM", "SIGKILL"):
                            fails.append("termination receipt signal 非法：%r" % doc.get("signal"))
                        else:
                            stop_verified = True
                    except Exception as exc:
                        fails.append("termination receipt 不可解析：%s" % exc)
            elif stratum == "wb_gateway_delivery":
                nb = meta.get("native_stop") or {}
                if isinstance(nb, dict) and nb.get("file") and nb.get("sha256"):
                    np_ = ev / str(nb["file"])
                    if np_.is_symlink() or not np_.is_file() or sha256_file(np_) != nb.get("sha256"):
                        fails.append("WB native stop 原物缺失/sha 不符")
                    else:
                        ndoc = _read_json(np_)
                        if "verified_stop" in nb and \
                                bool(nb.get("verified_stop")) != bool(ndoc.get("verified_stop")):
                            fails.append("WB native_stop 双说矛盾：binding 与 doc 不一致")
                        if ndoc.get("slot_id") not in (None, meta.get("slot_id"), slot["slot_id"]):
                            fails.append("WB native stop slot_id 与本场不符")
                        if ndoc.get("verified_stop") is True:
                            checks = ndoc.get("checks") or {}
                            need = {"db_terminal", "trace_stable", "no_scoped_processes"}
                            if not (isinstance(checks, dict) and need.issubset(checks)
                                    and all(checks[k] is True for k in need)):
                                fails.append("WB native stop verified=true 但 checks 三项"
                                             "（db_terminal/trace_stable/no_scoped_processes）"
                                             "未全为 true")
                            else:
                                stop_verified = True
                        else:
                            fails.append("WB native stop verified_stop\u2260true（未验证停止不得 formal）")
                else:
                    fails.append("WB timeout 须 native_stop 原物信封（CLI receipt 不接受）")
            else:
                fails.append("timeout 缺 termination receipt 原物绑定（outcome/stop_source 字符串不足）")
            if not outcome_timeout:
                fails.append("attempts[0].outcome\u2260timeout 与停止证据不一致")
        timeout_stop = bool(status == "timeout" and meta.get("timed_out") is True
                            and duration_real and outcome_timeout and stop_verified)
        executed_or_timeout = status == "ok" or (
            status == "timeout" and meta.get("timed_out") is True
            and rec["evidence_complete"] and score_ok
            and timeout_stop)
        if status == "timeout" and meta.get("timed_out") is True and not timeout_stop:
            fails.append("timeout 停止证据不完整（duration≥时限=%s + outcome=timeout=%s + 已验证 receipt 原物=%s）"
                         % (duration_real, outcome_timeout, stop_verified))
        rec["genuine_timeout"] = bool(status == "timeout" and executed_or_timeout)
        rec["formal_admission"] = bool(
            executed_or_timeout and rec["field_compliance"] and rec["seal_plan_integrity"]
            and rec["source_hash_integrity"] and rec["allowed_actual_configuration"]
            and rec["evidence_complete"] and rec["contamination_cleared"]
            and rec["full_denominator_score_valid"] and not fails)
        rec.setdefault("record_valid", False)
        if rec["formal_admission"]:
            summary["formal_admitted"] += 1
        # R1：executed=执行完成且证据/判卷完备（污染仍算 executed，formal 另判）；否则 partial
        complete_run = status == "ok" or (status == "timeout" and executed_or_timeout)
        complete_run = bool(complete_run and rec["evidence_complete"] and score_ok)
        if complete_run:
            rec["accounting"] = "executed"
            summary["executed"] += 1
        else:
            rec["accounting"] = "partial"
            summary["partial"] += 1
            if status in ("error", "transport-error"):
                fails.append("infrastructure 失败：完整记账，formal_admission=false，不按能力失败记零")
            elif status == "ok" and not (rec["evidence_complete"] and score_ok):
                fails.append("status=ok 但证据/判卷不完备：partial 记账（unknown 不折满）")
        per_slot.append(rec)

    summary["all_formal_admitted"] = summary["formal_admitted"] == summary["planned"]
    # 结构化判定：每 planned slot 恰一条记账且该记账本身有效（不靠 fails 关键词筛选）
    summary["accounting_complete"] = bool(
        len(per_slot) == summary["planned"]
        and all(r.get("accounting") in ("executed", "partial", "not_executed") for r in per_slot)
        and all(r.get("record_valid") is True for r in per_slot))
    return {"binding": binding, "product": product, "plan_id": plan["plan_id"],
            "per_slot": per_slot, "summary": summary,
            "tiers_note": "field_compliance/execution_status/evidence_integrity/score/formal_admission 五层分离；"
                          "accounting_complete 与 all_formal_admitted 互不混同（R1）",
            "all_admitted": summary["all_formal_admitted"],
            "at": now_local(), "live_doc_drift": []}


# ---------------------------------------------------------------- 合成自测（注入 git，零 git 写）

def _write(p: Path, s: str):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(s, encoding="utf-8")


def sha_file_generic(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else "0" * 64


def _fake_git_env(tmp: Path, plan_dir: Path, D: str, E: str, e_time: str,
                  d_time: str, ext_file: Path):
    """构造注入用 plan/contract/manifest/binding + 假 git 三件套。返回 (binding_path, readers)。"""
    rel_base = plan_dir.relative_to(tmp)
    plan = _read_json(plan_dir / "plan.json")
    contract = _read_json(plan_dir / "contract.json")
    (plan_dir / "PREREGISTRATION.md").write_bytes(b"PREREG")
    ext_map = {str(ext_file): sha256_file(ext_file)}
    for locked in EXTERNAL_REQUIRED:
        lp = Path(locked)
        ext_map[locked] = sha_file_generic(lp)
    manifest = {"schema_version": 1, "design_commit": D, "generated_at": d_time,
                "files": {str(rel_base / "plan.json"): sha256_file(plan_dir / "plan.json"),
                          str(rel_base / "contract.json"): sha256_file(plan_dir / "contract.json"),
                          str(rel_base / "PREREGISTRATION.md"): hashlib.sha256(b"PREREG").hexdigest()},
                "external_files": ext_map,
                "live_doc_drift": []}
    e_time_dt = parse_iso(e_time)
    b = {"schema_version": 1, "design_commit": D, "preregistration_commit": E,
         "execution_seal_commit": E, "registered_at": e_time,
         "execution_manifest_sha256": sha256_bytes(json.dumps(manifest).encode()),
         "plan_sha256": sha256_file(plan_dir / "plan.json"),
         "contract_sha256": sha256_file(plan_dir / "contract.json"),
         "released_for_model_calls": False, "generated_at": e_time, "live_doc_drift": []}
    binding_path = tmp / "runtime-binding.json"
    _write(binding_path, json.dumps(b))
    manifest_bytes = json.dumps(manifest).encode()
    blobs = {D: {str(rel_base / n): (plan_dir / n).read_bytes()
                 for n in ("plan.json", "contract.json")},
             E: None}
    blobs[D][str(rel_base / "PREREGISTRATION.md")] = b"PREREG"
    blobs[D][str(rel_base / "execution-manifest.json")] = manifest_bytes
    blobs[E] = dict(blobs[D])
    gr = lambda commit, path: blobs[commit][path]
    gt = lambda commit: e_time if commit == E else d_time
    ga = lambda a, c: True
    return binding_path, gr, gt, ga, b


def selftest() -> int:
    results = []

    def check(name, ok, detail=""):
        results.append({"case": name, "pass": bool(ok), "detail": str(detail)[:260]})

    D, E = "d" * 40, "e" * 40
    d_time, e_time = "2026-10-29T19:00:00+08:00", "2026-10-29T20:00:00+08:00"
    now = "2026-10-29T20:30:00+08:00"
    CASE = "dabstep-payments-10"
    contract = {"strata": {"cli_current_sentinel": {"products": ["dsh"], "model": "deepseek-flash",
                                                    "effort": "low", "route_host": "api.deepseek.com",
                                                    "ranking": False},
                           "wb_gateway_delivery": {"products": ["workbuddy"],
                                                   "declared_model_alias": "deepseek-v4.1-flash",
                                                   "gateway": "www.workbuddy.cn", "ranking": False}},
                "case_snapshots": {CASE: {"checker.py": "c" * 64}},
                "denominators": {CASE: 10},
                "admission": {"required_original_evidence": ["prompt", "stdout", "stderr",
                                                             "session", "checker", "workspace"]}}

    def mk_plan(tmp, slots):
        return {"plan_id": "l4-20261029", "product_slots": slots}

    def slot(i, case=CASE, status_hint="ok"):
        sid = "l4-cli-dsh-c%s-r%d" % (status_hint, i)
        return {"slot_id": sid, "run_id": sid, "event_id": "event:" + sid, "kind": "product_run",
                "product": "dsh", "case": case, "rep": i, "stratum": "cli_current_sentinel",
                "order": i, "evidence_dir": "runs/" + sid, "timeout_s": 1800}

    def mk_meta(s, status="ok", judge=(7, 10), timed_out=None, verdict="clean",
                route=None, registered=None):
        reg = registered or e_time
        started = "2026-10-29T20:05:00+08:00"
        earned, total = judge
        m = {"batch": "l4-20261029", "rule_version": "l4-20261029-batch-v1",
             "preregistration_commit": E, "registered_at": reg, "rep": s["rep"],
             "product": "dsh", "case": s["case"], "form": "cli", "run_id": s["run_id"],
             "event_id": s["event_id"], "slot_id": s["slot_id"], "order": s["order"],
             "selection": {"slot_id": s["slot_id"]} if status in ("ok", "timeout") else None,
             "diagnostic": None if status in ("ok", "timeout") else "upstream 502 on first stream",
             "workspace": "/tmp/ws", "model": "deepseek-flash", "reasoning_effort": "low",
             "product_version": "dsh-headless 0.2.0-rc.2",
             "route": route or {"host": "api.deepseek.com", "provider_id": "deepseek",
                                "wire_protocol": "dsh-headless --json"},
             "tools": ["read", "write"], "permissions": "workspace-write", "skills": "off",
             "web_search": "off", "soft_constraints": ["offline"],
             "prompt_sha256": "a" * 64, "isolation": {"ok": True, "mode": "fresh-workspace"},
             "inputs": ["TASK.md"], "status": status,
             "exit_code": 0 if status == "ok" else None,
             "created_at": "2026-10-29T20:04:00+08:00", "started_at": started,
             "finished_at": "2026-10-29T20:35:00+08:00", "duration_s": 1800.0,
             "attempts": [{"n": 1}], "transport_retries": 0,
             "stdout_bytes": 100, "stdout_sha256": "b" * 64,
             "stderr_bytes": 10, "stderr_sha256": "9" * 64,
             "usage": {"total": {"input": 1}}, "reward": None,
             "weighted": round(earned / total * 100, 8),
             "failed": [], "judge": {"correct": earned, "n_tasks": total,
                                     "checker_sha256": "c" * 64, "exit_code": 0},
             "integrity": {"scanned": True}, "integrity_verdict": verdict,
             "archived_stdout": {"full_file": "agent.jsonl.full",
                                 "full_sha256": "f" * 64}}
        if timed_out is not None:
            m["timed_out"] = timed_out
        return m

    def mk_run_files(ev: Path, meta):
        ev.mkdir(parents=True, exist_ok=True)
        raw = b"x" * 100
        (ev / "agent.jsonl").write_bytes(raw)
        (ev / "agent.stderr.txt").write_bytes(b"e" * 10)
        (ev / "prompt.txt").write_bytes(b"p")
        (ev / "agent.jsonl.full").write_bytes(b"f")
        (ev / "checker.stdout").write_text("7/10")
        (ev / "agent-session").mkdir(exist_ok=True)
        (ev / "agent-session" / "s.jsonl").write_text("{}")
        (ev / "workspace").mkdir(exist_ok=True)
        (ev / "workspace" / "out.txt").write_text("w")
        meta["stdout_sha256"] = hashlib.sha256(raw).hexdigest()
        meta["stderr_sha256"] = hashlib.sha256(b"e" * 10).hexdigest()
        meta["prompt_sha256"] = hashlib.sha256(b"p").hexdigest()
        meta["archived_stdout"]["full_sha256"] = hashlib.sha256(b"f").hexdigest()
        (ev / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
        (ev / "score-receipt.json").write_text(json.dumps(
            {"score": {"reported": meta["weighted"], "possible": meta["judge"]["n_tasks"]}}),
            encoding="utf-8")

    # ===== verify_execution 电池 =====
    RS = {"plans/l4/plan.json", "plans/l4/contract.json"}
    with tempfile.TemporaryDirectory(prefix="l4gate-v-") as td:
        tmp = Path(td)
        plan_dir = tmp / "plans" / "l4"
        plan_dir.mkdir(parents=True)
        slots = [slot(1)]
        _write(plan_dir / "plan.json", json.dumps(mk_plan(tmp, slots)))
        _write(plan_dir / "contract.json", json.dumps(contract))
        ext = tmp / "driver.sh"
        ext.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        bp, gr, gt, ga, b = _fake_git_env(tmp, plan_dir, D, E, e_time, d_time, ext)

        try:
            v = verify_execution(bp, repo=tmp, plan_dir=plan_dir, git_reader=gr, git_time=gt,
                                 git_ancestor=ga, now=now, require_release=False, required_set=RS)
            check("verify-positive-full", v["ok"] and v["manifest_files"] == 3
                  and v["manifest_external_files"] == 4, json.dumps(v["steps"])[:200])
        except GateError as exc:
            check("verify-positive-full", False, str(exc)[:200])
        try:
            verify_execution(bp, repo=tmp, plan_dir=plan_dir, git_reader=gr, git_time=gt,
                             git_ancestor=ga, now=now, require_release=True, required_set=RS)
            check("verify-release-gate-raises", False, "未 raise")
        except GateError as exc:
            check("verify-release-gate-raises", "未放行" in str(exc), str(exc)[:160])
        # 缺键
        bad = tmp / "b-missing.json"
        _write(bad, json.dumps({"design_commit": D}))
        try:
            verify_execution(bad, repo=tmp, plan_dir=plan_dir, git_reader=gr, git_time=gt,
                             git_ancestor=ga, now=now, require_release=False, required_set=RS)
            check("binding-missing-keys-raises", False, "未 raise")
        except GateError as exc:
            check("binding-missing-keys-raises", "缺键" in str(exc), str(exc)[:140])
        # registered_at ≠ E 时刻
        b2 = dict(b, registered_at="2026-10-29T10:00:00+08:00")
        p2 = tmp / "b2.json"
        _write(p2, json.dumps(b2))
        try:
            verify_execution(p2, repo=tmp, plan_dir=plan_dir, git_reader=gr, git_time=gt,
                             git_ancestor=ga, now=now, require_release=False, required_set=RS)
            check("registered-at-mismatch-raises", False, "未 raise")
        except GateError as exc:
            check("registered-at-mismatch-raises", "registered-at-equals-E" in str(exc), str(exc)[:180])
        # D/E blob 不一致
        relp = lambda n: str(plan_dir.relative_to(tmp) / n)
        mbytes = json.dumps({"schema_version": 1, "design_commit": D, "generated_at": d_time,
                             "files": {relp("plan.json"): sha256_file(plan_dir / "plan.json"),
                                       relp("contract.json"): sha256_file(plan_dir / "contract.json")},
                             "external_files": {str(ext): sha256_file(ext)},
                             "live_doc_drift": []}).encode()
        blobs2 = {D: {relp(n): ((plan_dir / n).read_bytes() if n in ("plan.json", "contract.json")
                                else gr(D, relp(n)))
                      for n in ("plan.json", "contract.json", "PREREGISTRATION.md",
                                "execution-manifest.json")}, E: None}
        blobs2[D][relp("execution-manifest.json")] = mbytes
        blobs2[E] = dict(blobs2[D])
        blobs2[E][relp("plan.json")] = blobs2[D][relp("plan.json")] + b" "
        gr2 = lambda c, p: blobs2[c][p]
        try:
            verify_execution(bp, repo=tmp, plan_dir=plan_dir, git_reader=gr2, git_time=gt,
                             git_ancestor=ga, now=now, require_release=False, required_set=RS)
            check("d-e-blob-drift-raises", False, "未 raise")
        except GateError as exc:
            check("d-e-blob-drift-raises", "blob-d-e-identical" in str(exc), str(exc)[:180])
        # 祖先关系假（时钟序正常也不行）
        try:
            verify_execution(bp, repo=tmp, plan_dir=plan_dir, git_reader=gr, git_time=gt,
                             git_ancestor=lambda a, c: False, now=now, require_release=False, required_set=RS)
            check("ancestor-false-raises", False, "未 raise")
        except GateError as exc:
            check("ancestor-false-raises", "ancestor-D-of-E" in str(exc), str(exc)[:180])
        # external_files 漂移
        ext.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
        try:
            verify_execution(bp, repo=tmp, plan_dir=plan_dir, git_reader=gr, git_time=gt,
                             git_ancestor=ga, now=now, require_release=False, required_set=RS)
            check("external-file-drift-raises", False, "未 raise")
        except GateError as exc:
            check("external-file-drift-raises", "external-files" in str(exc), str(exc)[:180])
        ext.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        # 磁盘文件缺失（manifest 有但盘上没有）
        (plan_dir / "contract.json").rename(tmp / "contract.bak")
        try:
            verify_execution(bp, repo=tmp, plan_dir=plan_dir, git_reader=gr, git_time=gt,
                             git_ancestor=ga, now=now, require_release=False, required_set=RS)
            check("manifest-file-missing-raises", False, "未 raise")
        except GateError as exc:
            check("manifest-file-missing-raises",
                  "missing-on-disk" in str(exc) or "contract-disk-sha" in str(exc), str(exc)[:180])
        (tmp / "contract.bak").rename(plan_dir / "contract.json")
        # manifest 不安全路径
        m3 = json.loads(gr(E, str(plan_dir.relative_to(tmp) / "execution-manifest.json")))
        m3b = dict(m3, files=dict(m3["files"], **{"../evil.txt": "0" * 64}))
        blobs3 = {D: {relp(n): gr(D, relp(n)) for n in ("plan.json", "contract.json",
                                                        "PREREGISTRATION.md", "execution-manifest.json")},
                  E: None}
        blobs3[D][relp("execution-manifest.json")] = json.dumps(m3b).encode()
        blobs3[E] = dict(blobs3[D])
        gr3 = lambda c, p: blobs3[c][p]
        b3 = dict(b, execution_manifest_sha256=sha256_bytes(json.dumps(m3b).encode()))
        p3 = tmp / "b3.json"
        _write(p3, json.dumps(b3))
        try:
            verify_execution(p3, repo=tmp, plan_dir=plan_dir, git_reader=gr3, git_time=gt,
                             git_ancestor=ga, now=now, require_release=False, required_set=RS)
            check("unsafe-manifest-path-raises", False, "未 raise")
        except GateError as exc:
            check("unsafe-manifest-path-raises", "unsafe-path" in str(exc), str(exc)[:180])
        # external_files={} 真空 → 必锁三件缺失
        m_e = json.loads(gr(E, relp("execution-manifest.json")))
        m_e2 = dict(m_e, external_files={})
        blobs_e = {D: {relp(n): gr(D, relp(n)) for n in ("plan.json", "contract.json",
                                                        "PREREGISTRATION.md", "execution-manifest.json")}, E: None}
        blobs_e[D][relp("execution-manifest.json")] = json.dumps(m_e2).encode()
        blobs_e[E] = dict(blobs_e[D])
        b_e = dict(b, execution_manifest_sha256=sha256_bytes(json.dumps(m_e2).encode()))
        p_e = tmp / "b-ext-empty.json"
        _write(p_e, json.dumps(b_e))
        try:
            verify_execution(p_e, repo=tmp, plan_dir=plan_dir, git_reader=lambda c, p: blobs_e[c][p],
                             git_time=gt, git_ancestor=ga, now=now, require_release=False, required_set=RS)
            check("external-empty-locked-missing-raises", False, "未 raise")
        except GateError as exc:
            check("external-empty-locked-missing-raises", "required-locked" in str(exc), str(exc)[:180])
        # preregistration_commit != execution_seal_commit
        b_ps = dict(b, preregistration_commit=D)
        p_ps = tmp / "b-prereg-ne-seal.json"
        _write(p_ps, json.dumps(b_ps))
        try:
            verify_execution(p_ps, repo=tmp, plan_dir=plan_dir, git_reader=gr, git_time=gt,
                             git_ancestor=ga, now=now, require_release=False, required_set=RS)
            check("prereg-ne-seal-raises", False, "未 raise")
        except GateError as exc:
            check("prereg-ne-seal-raises", "preregistration-seal-equal" in str(exc), str(exc)[:180])
        # manifest.design_commit != binding.design_commit
        m_d = dict(m_e, design_commit="a" * 40)
        blobs_d2 = {D: {relp(n): gr(D, relp(n)) for n in ("plan.json", "contract.json",
                                                         "PREREGISTRATION.md", "execution-manifest.json")}, E: None}
        blobs_d2[D][relp("execution-manifest.json")] = json.dumps(m_d).encode()
        blobs_d2[E] = dict(blobs_d2[D])
        b_d = dict(b, execution_manifest_sha256=sha256_bytes(json.dumps(m_d).encode()))
        p_d = tmp / "b-design-mismatch.json"
        _write(p_d, json.dumps(b_d))
        try:
            verify_execution(p_d, repo=tmp, plan_dir=plan_dir, git_reader=lambda c, p: blobs_d2[c][p],
                             git_time=gt, git_ancestor=ga, now=now, require_release=False, required_set=RS)
            check("manifest-design-mismatch-raises", False, "未 raise")
        except GateError as exc:
            check("manifest-design-mismatch-raises", "manifest-design-matches-binding" in str(exc), str(exc)[:180])
        # manifest 漏封必需成员（runner 入口/helper 未进 manifest）
        try:
            verify_execution(bp, repo=tmp, plan_dir=plan_dir, git_reader=gr, git_time=gt,
                             git_ancestor=ga, now=now, require_release=False,
                             required_set=RS | {"plans/l4/runner-helper.py"})
            check("manifest-missing-required-member-raises", False, "未 raise")
        except GateError as exc:
            check("manifest-missing-required-member-raises",
                  "required-members" in str(exc) and "runner-helper" in str(exc), str(exc)[:180])

    # ===== admission 电池 =====
    CASE = "dabstep-payments-10"

    def base_contract():
        return {"rule_version": "l4-20261029-batch-v1",
                "strata": {"cli_current_sentinel": {"products": ["dsh"], "model": "deepseek-flash",
                                                    "effort": "low", "route_host": "api.deepseek.com",
                                                    "ranking": False},
                           "wb_gateway_delivery": {"products": ["workbuddy"],
                                                   "declared_model_alias": "deepseek-v4.1-flash",
                                                   "gateway": "www.workbuddy.cn", "ranking": False}},
                "case_snapshots": {CASE: {"checker.py": "c" * 64}},
                "denominators": {CASE: 10},
                "admission": {"required_original_evidence": ["prompt", "stdout", "stderr",
                                                             "session", "checker", "workspace"]}}

    def mkslot(i, hint, stratum="cli_current_sentinel", case=CASE, product="dsh"):
        sid = "l4-cli-%s-%s-r%d" % (product, hint, i)
        return {"slot_id": sid, "run_id": sid, "event_id": "event:" + sid, "kind": "product_run",
                "product": product, "case": case, "rep": i, "stratum": stratum,
                "order": i, "evidence_dir": "runs/" + sid, "timeout_s": 1800}

    def mkmeta(s, status="ok", judge=(7, 10), verdict="clean", mut=None):
        started = "2026-10-29T20:05:00+08:00"
        earned, total = judge
        m = {"batch": "l4-20261029", "rule_version": "l4-20261029-batch-v1",
             "preregistration_commit": E, "registered_at": e_time, "rep": s["rep"],
             "product": s["product"], "case": s["case"], "form": "cli", "run_id": s["run_id"],
             "event_id": s["event_id"], "slot_id": s["slot_id"], "order": s["order"],
             "stratum": s["stratum"],
             "selection": {"slot_id": s["slot_id"]} if status in ("ok", "timeout") else None,
             "diagnostic": None,
             "workspace": "/tmp/ws", "model": "deepseek-flash", "reasoning_effort": "low",
             "product_version": "dsh-headless 0.2.0-rc.2",
             "route": {"host": "api.deepseek.com", "provider_id": "deepseek-official",
                       "wire_protocol": "anthropic-messages"},
             "tools": ["read"], "permissions": "workspace-write", "skills": "off",
             "web_search": "off", "soft_constraints": ["offline"],
             "prompt_sha256": "a" * 64, "isolation": {"ok": True, "mode": "fresh"},
             "inputs_verification": {"ok": True, "checked": 3},
             "inputs": ["TASK.md"], "status": status,
             "exit_code": 0 if status == "ok" else None,
             "created_at": "2026-10-29T20:04:00+08:00", "started_at": started,
             "finished_at": "2026-10-29T20:35:00+08:00", "duration_s": 1800.0,
             "attempts": [{"n": 1, "outcome": status if status == "timeout" else "completed"}],
             "transport_retries": 0,
             "stdout_bytes": 100, "stdout_sha256": "b" * 64,
             "stderr_bytes": 10, "stderr_sha256": "9" * 64,
             "usage": {"requests": 5, "input_tokens": 1}, "reward": None,
             "weighted": round(earned / total * 100, 8) if status != "timeout" else 40.0,
             "failed": [], "judge": {"correct": earned, "n_tasks": total,
                                     "weighted": round(earned / total * 100, 8),
                                     "guards_used": ["g0"],
                                     "checker_sha256": "c" * 64, "exit_code": 0},
             "integrity": {"scanned": True}, "integrity_verdict": verdict,
             "archived_stdout": {"full_file": "agent.jsonl.full", "full_sha256": "f" * 64}}
        if status == "timeout":
            m["timed_out"] = True
            m["diagnostic"] = {"stop_source": "subprocess timeout signal at plan timeout"}
            m["judge"] = {"correct": earned, "n_tasks": total,
                          "weighted": round(earned / total * 100, 8),
                          "guards_used": ["g0"],
                          "checker_sha256": "c" * 64, "exit_code": 0}
            m["weighted"] = round(earned / total * 100, 8)
        for k, v in (mut or {}).items():
            if v == "__del__":
                m.pop(k, None)
            else:
                m[k] = v
        return m

    def mkrun(ev: Path, meta, raw_weighted=None):
        ev.mkdir(parents=True, exist_ok=True)
        raw = b"x" * 100
        (ev / "agent.jsonl").write_bytes(raw)
        (ev / "agent.stderr.txt").write_bytes(b"e" * 10)
        (ev / "prompt.txt").write_bytes(b"p")
        (ev / "agent.jsonl.full").write_bytes(b"f")
        (ev / "agent-session").mkdir(exist_ok=True)
        (ev / "agent-session" / "s.jsonl").write_text("{}")
        (ev / "workspace").mkdir(exist_ok=True)
        (ev / "workspace" / "out.txt").write_text("w")
        (ev / "alias-proof.jsonl").write_text("{}")
        meta["stdout_sha256"] = hashlib.sha256(raw).hexdigest()
        meta["stderr_sha256"] = hashlib.sha256(b"e" * 10).hexdigest()
        meta["prompt_sha256"] = hashlib.sha256(b"p").hexdigest()
        meta["archived_stdout"]["full_sha256"] = hashlib.sha256(b"f").hexdigest()
        if meta.get("status") == "ok" and "termination_receipt" not in meta:
            term_doc = {"phase": "normal_exit", "probe": "verified_gone", "signal": None,
                        "pgid": 424242, "pid": 424242,
                        "at": "2026-10-29T20:35:00+08:00", "ack_at": "2026-10-29T20:35:00+08:00",
                        "verified_stop": True, "group_confirmed_gone": True,
                        "slot_id": meta["slot_id"]}
            (ev / "termination-receipt.json").write_text(json.dumps(term_doc), encoding="utf-8")
            meta["termination_receipt"] = {"file": "termination-receipt.json",
                                           "sha256": hashlib.sha256(
                                               (ev / "termination-receipt.json").read_bytes()).hexdigest()}
            meta["attempts"][0]["pid"] = 424242
            meta["attempts"][0]["pgid"] = 424242
        if meta.get("status") == "timeout" and "termination_receipt" not in meta:
            term_doc = {"policy": "process-group bounded termination (group-confirmed)",
                        "signal": "SIGTERM", "pgid": 424242, "pid": 424242,
                        "at": "2026-10-29T20:35:00+08:00", "ack_at": "2026-10-29T20:35:01+08:00",
                        "verified_stop": True, "group_confirmed_gone": True,
                        "escalated": False, "returncode": None,
                        "slot_id": meta["slot_id"]}
            (ev / "termination-receipt.json").write_text(json.dumps(term_doc), encoding="utf-8")
            meta["termination_receipt"] = {"file": "termination-receipt.json",
                                           "sha256": hashlib.sha256(
                                               (ev / "termination-receipt.json").read_bytes()).hexdigest()}
            meta["attempts"][0]["pid"] = 424242
            meta["attempts"][0]["pgid"] = 424242
        if "native_terminal" in meta and isinstance(meta["native_terminal"], dict) \
                and meta["native_terminal"].get("file"):
            ntp = meta["native_terminal"]
            ndoc = {"slot_id": meta["slot_id"], "terminal": ntp.get("_terminal", True),
                    "state": ntp.get("_state", "completed"),
                    "verified_at": "2026-10-29T20:35:30+08:00", "live_doc_drift": []}
            (ev / ntp["file"]).write_text(json.dumps(ndoc), encoding="utf-8")
            ntp["sha256"] = hashlib.sha256((ev / ntp["file"]).read_bytes()).hexdigest()
        earned = meta["judge"]["correct"]
        total = meta["judge"]["n_tasks"]
        raw_checks = [{"id": "g0", "pass": True}] + \
            [{"id": "q%d" % i, "pass": i < earned} for i in range(total)]
        raw_doc = {"weighted": round(earned / total * 100, 2), "reward": None,
                   "checks": raw_checks}
        (ev / "checker.stdout").write_text(json.dumps(raw_doc), encoding="utf-8")
        (ev / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
        (ev / "score-receipt.json").write_text(json.dumps(
            {"case": meta["case"], "score": {"reported": meta["weighted"],
                                             "possible": total,
                                             "earned": earned,
                                             "checker_sha256": "c" * 64},
             "raw_checker_output": raw_doc, "live_doc_drift": []}), encoding="utf-8")

    def mknotexec(ev: Path, s, mut=None):
        ev.mkdir(parents=True, exist_ok=True)
        rec = {"slot_id": s["slot_id"], "run_id": s["run_id"], "event_id": s["event_id"],
               "preregistration_commit": E, "reason": "preflight 401", "stop_source": "R4-2",
               "live_doc_drift": []}
        for k, v in (mut or {}).items():
            if v == "__del__":
                rec.pop(k, None)
            else:
                rec[k] = v
        (ev / "notexecuted.json").write_text(json.dumps(rec), encoding="utf-8")

    def build_world(tmp, plan_slots, contract):
        plan_dir = tmp / "plans" / "l4"
        plan_dir.mkdir(parents=True, exist_ok=True)
        _write(plan_dir / "plan.json", json.dumps({"plan_id": "l4-20261029", "product_slots": plan_slots}))
        _write(plan_dir / "contract.json", json.dumps(contract))
        ext = tmp / "driver.sh"
        ext.write_text("ok\n", encoding="utf-8")
        bp, gr, gt, ga, b = _fake_git_env(tmp, plan_dir, D, E, e_time, d_time, ext)
        bp2 = tmp / "binding-released.json"
        _write(bp2, json.dumps(dict(b, released_for_model_calls=True)))
        return plan_dir, bp2, gr, gt, ga

    RS2 = RS  # 同一合成 plan 相对路径集合

    # —— 攻击面1-8（reviewer gate-adversarial-v1 复现集）+ 正例组 ——
    def expect_formal(mut_ok=None, mut_timeout=None, mut_world=None, label="", want_admitted=2,
                      want_slots=None):
        with tempfile.TemporaryDirectory(prefix="l4gate-ax-") as td:
            tmp = Path(td)
            contract = base_contract()
            s1, s2, s3, s4 = mkslot(1, "ok"), mkslot(2, "timeout"), mkslot(3, "infra"), mkslot(4, "ne")
            slots = [s1, s2, s3, s4]
            plan_dir, bp2, gr, gt, ga = build_world(tmp, slots, contract)
            mkrun(tmp / s1["evidence_dir"], mkmeta(s1, "ok", mut=mut_ok))
            mkrun(tmp / s2["evidence_dir"], mkmeta(s2, "timeout", judge=(4, 10), mut=mut_timeout))
            mkrun(tmp / s3["evidence_dir"], mkmeta(s3, "transport-error", mut={"diagnostic": {"class": "502", "stderr_tail": "x"}}))
            mknotexec(tmp / s4["evidence_dir"], s4)
            if mut_world:
                mut_world(tmp, plan_dir, contract)
            rep = gate_admission(bp2, "dsh", repo=tmp, plan_dir=plan_dir,
                                 git_reader=gr, git_time=gt, git_ancestor=ga, required_set=RS)
            s = rep["summary"]
            return rep, s

    # 正例基线：ok + genuine timeout 双准入；infra partial；notexec 完整记账
    rep, s = expect_formal(label="baseline")
    check("admit-baseline-formal=2", s["formal_admitted"] == 2, json.dumps(s))
    check("admit-baseline-genuine-timeout", rep["per_slot"][1]["genuine_timeout"] is True,
          json.dumps(rep["per_slot"][1]["fails"])[:220])
    check("admit-baseline-infra-partial", rep["per_slot"][2]["accounting"] == "partial"
          and rep["per_slot"][2]["formal_admission"] is False,
          json.dumps(rep["per_slot"][2]["fails"])[:180])
    check("admit-baseline-notexec-accounted", rep["per_slot"][3]["accounting"] == "not_executed"
          and rep["per_slot"][3]["score"] is None and rep["per_slot"][3]["formal_admission"] is False,
          json.dumps(rep["per_slot"][3])[:200])
    check("accounting-complete-distinct-from-formal",
          s["accounting_complete"] is True and s["all_formal_admitted"] is False, json.dumps(s))
    # 攻击1：ok + exit_code=9
    rep, s = expect_formal(mut_ok={"exit_code": 9}, want_admitted=1)
    check("atk1-ok-exit9-not-formal", s["formal_admitted"] == 1
          and any("exit_code" in f for f in rep["per_slot"][0]["fails"]),
          json.dumps(s) + str(rep["per_slot"][0]["fails"])[:150])
    # 攻击2：1 秒假 timeout（限 1800）
    rep, s = expect_formal(mut_timeout={"duration_s": 1.0}, want_admitted=1)
    check("atk2-short-timeout-not-formal", s["formal_admitted"] == 1
          and rep["per_slot"][1]["genuine_timeout"] is False
          and any("真实停止证据" in f or "duration" in f for f in rep["per_slot"][1]["fails"]),
          str(rep["per_slot"][1]["fails"])[:200])
    # 攻击3：错 checker SHA（judge 侧）
    rep, s = expect_formal(mut_ok={"judge": {"correct": 7, "n_tasks": 10,
                                             "weighted": 70.0, "checker_sha256": "f" * 64, "exit_code": 0}})
    check("atk3-wrong-checker-sha-not-formal", s["formal_admitted"] == 1
          and any("checker_sha256" in f for f in rep["per_slot"][0]["fails"]),
          str(rep["per_slot"][0]["fails"])[:200])
    # 攻击4a：错 product；4b：错 rule_version；4c：错 order
    rep, s = expect_formal(mut_ok={"product": "codex"})
    check("atk4a-wrong-product-not-formal", s["formal_admitted"] == 1
          and any("meta.product" in f for f in rep["per_slot"][0]["fails"]),
          str(rep["per_slot"][0]["fails"])[:180])
    rep, s = expect_formal(mut_ok={"rule_version": "v9"})
    check("atk4b-wrong-rule-not-formal", s["formal_admitted"] == 1
          and any("rule_version" in f for f in rep["per_slot"][0]["fails"]),
          str(rep["per_slot"][0]["fails"])[:180])
    rep, s = expect_formal(mut_ok={"order": 99})
    check("atk4c-wrong-order-not-formal", s["formal_admitted"] == 1
          and any("order" in f for f in rep["per_slot"][0]["fails"]),
          str(rep["per_slot"][0]["fails"])[:180])
    # 攻击5：raw checker 0/10 而 meta/receipt 声称 70
    def mut_raw_zero(tmp, plan_dir, contract):
        p = tmp / "runs" / "l4-cli-dsh-ok-r1" / "checker.stdout"
        p.write_text(json.dumps({"weighted": 0.0, "reward": None, "checks": []}), encoding="utf-8")
    rep, s = expect_formal(mut_world=mut_raw_zero)
    check("atk5-raw-score-mismatch-not-formal", s["formal_admitted"] == 1
          and rep["per_slot"][0]["full_denominator_score_valid"] is False
          and any("raw checker" in f for f in rep["per_slot"][0]["fails"]),
          str(rep["per_slot"][0]["fails"])[:220])
    # 攻击6：notexec 无 reason/错封印 → accounting_complete 必须 false（结构化，非关键词）
    def mut_ne(tmp, plan_dir, contract):
        p = tmp / "runs" / "l4-cli-dsh-ne-r4" / "notexecuted.json"
        rec = json.loads(p.read_text(encoding="utf-8"))
        rec.pop("reason")
        rec["preregistration_commit"] = "0" * 40
        p.write_text(json.dumps(rec), encoding="utf-8")
    rep, s = expect_formal(mut_world=mut_ne)
    check("atk6-invalid-notexec-breaks-accounting-complete",
          s["accounting_complete"] is False
          and rep["per_slot"][3].get("record_valid") is False,
          json.dumps(s) + json.dumps(rep["per_slot"][3])[:160])
    # 攻击7/8：WB observed 全字段应准入；unknown+managed_unknowns=[] 应拒
    def wb_world(tmp, route_mut, managed, status="ok"):
        contract = base_contract()
        s = mkslot(1, "wb", stratum="wb_gateway_delivery", product="workbuddy")
        plan_dir, bp2, gr, gt, ga = build_world(tmp, [s], contract)
        route = {"declared_alias": "deepseek-v4.1-flash", "alias_evidence": "alias-proof.jsonl",
                 "actual_gateway": "unknown", "route_verification": "current_not_observed",
                 "r2_history_ref": "r2/history.md"}
        route.update(route_mut or {})
        meta = mkmeta(s, status, mut={
            "stratum": "wb_gateway_delivery", "model": "deepseek-v4.1-flash",
            "exit_code": None,
            "native_terminal": {"file": "native-terminal.json"},
            "route": route, "product_version": "WB 3.2.1",
            "app_asar_sha256": "a" * 64,
            "managed_unknowns": [{"item": "gateway upstream weights", "impact": "不能同路由归因",
                                  "next_step": "被动观察", "stop_condition": "不可观察即保持分层"}]})
        if managed == []:
            meta["managed_unknowns"] = []
        mkrun(tmp / s["evidence_dir"], meta)
        return gate_admission(bp2, "workbuddy", repo=tmp, plan_dir=plan_dir,
                              git_reader=gr, git_time=gt, git_ancestor=ga, required_set=RS)
    with tempfile.TemporaryDirectory(prefix="l4gate-wb-") as td:
        tmp = Path(td)
        rep = wb_world(tmp, {"actual_gateway": "gw.example", "route_verification": "observed",
                             "observation_method": "passive dns/proxy log"},
                       managed="keep")
        s = rep["summary"]
        check("atk7-wb-observed-full-fields-admitted",
              s["formal_admitted"] == 1 and not rep["per_slot"][0]["fails"],
              json.dumps(rep["per_slot"][0]["fails"])[:220])
    with tempfile.TemporaryDirectory(prefix="l4gate-wb2-") as td:
        tmp = Path(td)
        rep = wb_world(tmp, {}, managed=[])
        s = rep["summary"]
        check("atk8-wb-unknown-empty-managed-not-formal",
              s["formal_admitted"] == 0
              and any("managed_unknowns" in f or "gateway" in f for f in rep["per_slot"][0]["fails"]),
              json.dumps(rep["per_slot"][0]["fails"])[:220])
    # checker exit1 + 能力低分（合法 JSON）不是基础设施错误，仍可准入（R1：能力低分不是拒收理由）
    rep, s = expect_formal(mut_ok={"weighted": 10.0,
                                   "judge": {"correct": 1, "n_tasks": 10, "weighted": 10.0,
                                             "guards_used": ["g0"],
                                             "checker_sha256": "c" * 64, "exit_code": 1}})
    check("checker-exit1-lowscore-still-admissible", s["formal_admitted"] == 2
          and rep["per_slot"][0]["formal_admission"] is True,
          json.dumps(s) + str(rep["per_slot"][0]["fails"])[:160])
    # cargo 式 27 分母非整百分比正例（raw weighted 2dp；计数重算 8dp 为必要条件）
    with tempfile.TemporaryDirectory(prefix="l4gate-c27-") as td:
        tmp = Path(td)
        contract = base_contract()
        contract["denominators"][CASE] = 27
        sc = mkslot(1, "cargo")
        plan_dir, bp2, gr, gt, ga = build_world(tmp, [sc], contract)
        m = mkmeta(sc, "ok", judge=(19, 27))
        mkrun(tmp / sc["evidence_dir"], m)
        rep = gate_admission(bp2, "dsh", repo=tmp, plan_dir=plan_dir,
                             git_reader=gr, git_time=gt, git_ancestor=ga, required_set=RS)
        ps = rep["per_slot"][0]
        check("cargo27-2dp-raw-still-admitted",
              ps["formal_admission"] is True
              and ps["score"]["earned_recomputed"] == 19
              and ps["score"]["raw_weighted_cross_check"]["within_2dp_rounding"] is True,
              json.dumps(ps["fails"])[:200] + json.dumps(ps.get("score"))[:160])
    # 篡改计数负例：raw earned 18 而 meta/receipt 声称 19
    with tempfile.TemporaryDirectory(prefix="l4gate-t19-") as td:
        tmp = Path(td)
        contract = base_contract()
        sc = mkslot(1, "tamper")
        plan_dir, bp2, gr, gt, ga = build_world(tmp, [sc], contract)
        m = mkmeta(sc, "ok", judge=(19, 10))
        mkrun(tmp / sc["evidence_dir"], m)
        p = tmp / sc["evidence_dir"] / "checker.stdout"
        doc = json.loads(p.read_text(encoding="utf-8"))
        doc["checks"] = [{"id": "g0", "pass": True}] + \
            [{"id": "q%d" % i, "pass": i < 18} for i in range(10)]
        p.write_text(json.dumps(doc), encoding="utf-8")
        rep = gate_admission(bp2, "dsh", repo=tmp, plan_dir=plan_dir,
                             git_reader=gr, git_time=gt, git_ancestor=ga, required_set=RS)
        ps = rep["per_slot"][0]
        check("tampered-raw-counts-not-formal",
              ps["formal_admission"] is False
              and any("raw 重算" in f or "计数" in f for f in ps["fails"]),
              json.dumps(ps["fails"])[:220])
    # 伪造 timeout（有 outcome/stop_source 但无 receipt 原物）不得穿透
    rep, s = expect_formal(mut_timeout={"termination_receipt": None})
    check("atk9-forged-timeout-without-receipt-not-formal",
          s["formal_admitted"] == 1 and rep["per_slot"][1]["genuine_timeout"] is False
          and any("receipt 原物" in f or "停止证据不完整" in f for f in rep["per_slot"][1]["fails"]),
          str(rep["per_slot"][1]["fails"])[:220])
    # receipt sha 绑定被篡改
    def mut_term_sha(tmp, plan_dir, contract):
        evd = tmp / "runs" / "l4-cli-dsh-timeout-r2"
        (evd / "termination-receipt.json").write_text('{"tampered": true}', encoding="utf-8")
    rep, s = expect_formal(mut_world=mut_term_sha)
    check("atk10-termination-sha-tamper-not-formal",
          s["formal_admitted"] == 1
          and any("sha 与 meta 绑定不符" in f for f in rep["per_slot"][1]["fails"]),
          str(rep["per_slot"][1]["fails"])[:200])
    # WB timeout 借 CLI receipt → 拒（须 native_stop 信封）
    with tempfile.TemporaryDirectory(prefix="l4gate-wbt-") as td:
        tmp = Path(td)
        contract = base_contract()
        s = mkslot(1, "wb", stratum="wb_gateway_delivery", product="workbuddy")
        plan_dir, bp2, gr, gt, ga = build_world(tmp, [s], contract)
        m = mkmeta(s, "timeout", judge=(4, 10), mut={
            "stratum": "wb_gateway_delivery", "model": "deepseek-v4.1-flash",
            "product_version": "WB 3.2.1", "app_asar_sha256": "a" * 64,
            "route": {"declared_alias": "deepseek-v4.1-flash", "alias_evidence": "alias-proof.jsonl",
                      "actual_gateway": "unknown", "route_verification": "current_not_observed",
                      "r2_history_ref": "r2/history.md"},
            "managed_unknowns": [{"item": "gateway upstream", "impact": "i",
                                  "next_step": "n", "stop_condition": "s"}]})
        mkrun(tmp / s["evidence_dir"], m)  # mkrun 会写 CLI 风格 receipt（须被 WB 层拒绝）
        rep = gate_admission(bp2, "workbuddy", repo=tmp, plan_dir=plan_dir,
                             git_reader=gr, git_time=gt, git_ancestor=ga, required_set=RS)
        ps = rep["per_slot"][0]
        check("atk11-wb-timeout-cli-receipt-not-accepted",
              ps["formal_admission"] is False
              and any("native_stop" in f for f in ps["fails"]),
              json.dumps(ps["fails"])[:220])
    # atk12：receipt 缺组级确认（父退即 verified 的旧假象）
    def mut_term_nogroup(tmp, plan_dir, contract):
        evd = tmp / "runs" / "l4-cli-dsh-timeout-r2"
        doc = json.loads((evd / "termination-receipt.json").read_text(encoding="utf-8"))
        doc["group_confirmed_gone"] = False
        raw = json.dumps(doc).encode("utf-8")
        (evd / "termination-receipt.json").write_bytes(raw)  # 连绑定 sha 一并伪造（测组级字段门本身）
        meta = json.loads((evd / "meta.json").read_text(encoding="utf-8"))
        meta["termination_receipt"]["sha256"] = hashlib.sha256(raw).hexdigest()
        (evd / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    rep, s = expect_formal(mut_world=mut_term_nogroup)
    check("atk12-receipt-without-group-confirm-not-formal",
          s["formal_admitted"] == 1
          and any("组级确认" in f for f in rep["per_slot"][1]["fails"]),
          str(rep["per_slot"][1]["fails"])[:220])
    # atk14：receipt 挪用他场 slot_id（sha 自洽但身份不符）
    def mut_term_swap(tmp, plan_dir, contract):
        evd = tmp / "runs" / "l4-cli-dsh-timeout-r2"
        p = evd / "termination-receipt.json"
        doc = json.loads(p.read_text(encoding="utf-8"))
        doc["slot_id"] = "l4-cli-dsh-ok-r1"
        raw = json.dumps(doc).encode("utf-8")
        p.write_bytes(raw)
        meta = json.loads((evd / "meta.json").read_text(encoding="utf-8"))
        meta["termination_receipt"]["sha256"] = hashlib.sha256(raw).hexdigest()
        (evd / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    rep, s = expect_formal(mut_world=mut_term_swap)
    check("atk14-swapped-slot-receipt-not-formal",
          s["formal_admitted"] == 1
          and any("slot_id" in f for f in rep["per_slot"][1]["fails"]),
          str(rep["per_slot"][1]["fails"])[:200])
    # atk15：receipt pgid 与 attempt 实际不符
    def mut_term_pgid(tmp, plan_dir, contract):
        evd = tmp / "runs" / "l4-cli-dsh-timeout-r2"
        p = evd / "termination-receipt.json"
        doc = json.loads(p.read_text(encoding="utf-8"))
        doc["pgid"] = 999999999
        raw = json.dumps(doc).encode("utf-8")
        p.write_bytes(raw)
        meta = json.loads((evd / "meta.json").read_text(encoding="utf-8"))
        meta["termination_receipt"]["sha256"] = hashlib.sha256(raw).hexdigest()
        (evd / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    rep, s = expect_formal(mut_world=mut_term_pgid)
    check("atk15-pgid-mismatch-not-formal",
          s["formal_admitted"] == 1
          and any("pgid" in f for f in rep["per_slot"][1]["fails"]),
          str(rep["per_slot"][1]["fails"])[:200])
    # atk16：meta binding verified_stop=true 与 doc=false 双说矛盾 → 显式拒
    def mut_term_dual(tmp, plan_dir, contract):
        evd = tmp / "runs" / "l4-cli-dsh-timeout-r2"
        p = evd / "termination-receipt.json"
        doc = json.loads(p.read_text(encoding="utf-8"))
        doc["verified_stop"] = False
        raw = json.dumps(doc).encode("utf-8")
        p.write_bytes(raw)
        meta = json.loads((evd / "meta.json").read_text(encoding="utf-8"))
        meta["termination_receipt"]["sha256"] = hashlib.sha256(raw).hexdigest()
        meta["termination_receipt"]["verified_stop"] = True
        (evd / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    rep, s = expect_formal(mut_world=mut_term_dual)
    check("atk16-binding-doc-bool-contradiction-rejected",
          s["formal_admitted"] == 1
          and any("双说矛盾" in f for f in rep["per_slot"][1]["fails"]),
          str(rep["per_slot"][1]["fails"])[:200])
    # atk13：WB observed + effort 字面 'unknown' + managed=[] → 拒
    def wb_world_effort(tmp, effort, managed, nterminal=None):
        contract = base_contract()
        s = mkslot(1, "wb", stratum="wb_gateway_delivery", product="workbuddy")
        plan_dir, bp2, gr, gt, ga = build_world(tmp, [s], contract)
        nt = {"file": "native-terminal.json"}
        if nterminal:
            nt.update(nterminal)
        mut = {"stratum": "wb_gateway_delivery", "model": "deepseek-v4.1-flash",
               "reasoning_effort": effort, "product_version": "WB 3.2.1",
               "exit_code": None, "native_terminal": nt,
               "app_asar_sha256": "a" * 64,
               "route": {"declared_alias": "deepseek-v4.1-flash",
                         "alias_evidence": "alias-proof.jsonl",
                         "actual_gateway": "gw.example", "route_verification": "observed",
                         "observation_method": "passive log"},
               "managed_unknowns": managed}
        m = mkmeta(s, "ok", mut=mut)
        mkrun(tmp / s["evidence_dir"], m)
        return gate_admission(bp2, "workbuddy", repo=tmp, plan_dir=plan_dir,
                              git_reader=gr, git_time=gt, git_ancestor=ga, required_set=RS)
    with tempfile.TemporaryDirectory(prefix="l4gate-ef1-") as td:
        rep = wb_world_effort(Path(td), "unknown", [])
        check("atk13a-wb-effort-unknown-sentinel-not-formal",
              rep["summary"]["formal_admitted"] == 0
              and any("effort" in f for f in rep["per_slot"][0]["fails"]),
              json.dumps(rep["per_slot"][0]["fails"])[:220])
    with tempfile.TemporaryDirectory(prefix="l4gate-ef2-") as td:
        rep = wb_world_effort(Path(td), "unknown",
                              [{"item": "effort tier unobservable", "impact": "i",
                                "next_step": "n", "stop_condition": "s"}])
        check("atk13b-wb-effort-unknown-managed-admitted",
              rep["summary"]["formal_admitted"] == 1
              and not rep["per_slot"][0]["fails"],
              json.dumps(rep["per_slot"][0]["fails"])[:220])
    with tempfile.TemporaryDirectory(prefix="l4gate-ef3-") as td:
        # gateway 字面 'unobservable' 也归 unknown 分支（须 route_verification=observed 才认）
        rep = wb_world_effort(Path(td), "low", [])
        # low + observed gateway + managed=[] ：gateway 已实测无需 gateway 项；effort 已知 → 应准入
        check("atk13c-wb-observed-known-effort-admitted",
              rep["summary"]["formal_admitted"] == 1,
              json.dumps(rep["per_slot"][0]["fails"])[:220])
    # atk17：WB native verified=true 但 checks 缺项 → 拒
    with tempfile.TemporaryDirectory(prefix="l4gate-wbc-") as td:
        tmp = Path(td)
        contract = base_contract()
        s = mkslot(1, "wb", stratum="wb_gateway_delivery", product="workbuddy")
        plan_dir, bp2, gr, gt, ga = build_world(tmp, [s], contract)
        m = mkmeta(s, "timeout", judge=(4, 10), mut={
            "stratum": "wb_gateway_delivery", "model": "deepseek-v4.1-flash",
            "product_version": "WB 3.2.1", "app_asar_sha256": "a" * 64,
            "route": {"declared_alias": "deepseek-v4.1-flash",
                      "alias_evidence": "alias-proof.jsonl", "actual_gateway": "unknown",
                      "route_verification": "current_not_observed", "r2_history_ref": "r2/h.md"},
            "managed_unknowns": [{"item": "gateway upstream", "impact": "i",
                                  "next_step": "n", "stop_condition": "s"}]})
        mkrun(tmp / s["evidence_dir"], m)  # 先写 CLI 风格 receipt 占位
        evd = tmp / s["evidence_dir"]
        (evd / "termination-receipt.json").unlink()  # 移除 CLI 收据（WB 层不认它）
        ndoc = {"slot_id": s["slot_id"], "verified_stop": True,
                "stop_kind": "wb:conversations:cancel",
                "checks": {"db_terminal": True, "trace_stable": True,
                           "no_scoped_processes": False},
                "verified_at": "2026-10-29T20:36:00+08:00", "live_doc_drift": []}
        (evd / "native-stop.json").write_text(json.dumps(ndoc), encoding="utf-8")
        m["termination_receipt"] = None
        m["native_stop"] = {"file": "native-stop.json",
                            "sha256": hashlib.sha256((evd / "native-stop.json").read_bytes()).hexdigest()}
        (evd / "meta.json").write_text(json.dumps(m), encoding="utf-8")
        rep = gate_admission(bp2, "workbuddy", repo=tmp, plan_dir=plan_dir,
                             git_reader=gr, git_time=gt, git_ancestor=ga, required_set=RS)
        ps = rep["per_slot"][0]
        check("atk17-wb-native-checks-incomplete-not-formal",
              ps["formal_admission"] is False
              and any("checks" in f for f in ps["fails"]),
              json.dumps(ps["fails"])[:220])
    # atk18：ok 槽无组闭包 receipt（正常退出未验证）→ 拒
    rep, s = expect_formal(mut_ok={"termination_receipt": None})
    check("atk18-ok-without-closure-receipt-not-formal",
          s["formal_admitted"] == 1
          and any("组闭包未证" in f for f in rep["per_slot"][0]["fails"]),
          str(rep["per_slot"][0]["fails"])[:220])
    # W13-1：WB completed + exit_code=None + 原生终态 → 全门正例（judge W13 复现集）
    with tempfile.TemporaryDirectory(prefix="l4gate-w13p-") as td:
        rep = wb_world_effort(Path(td), "unknown",
                              [{"item": "effort tier unobservable", "impact": "i",
                                "next_step": "n", "stop_condition": "s"}])
        ps = rep["per_slot"][0]
        check("w13-wb-completed-none-exitcode-admitted",
              ps["formal_admission"] is True and not ps["fails"],
              json.dumps(ps["fails"])[:240])
    # W13-2：活动态（terminal=False）拒
    with tempfile.TemporaryDirectory(prefix="l4gate-w13a-") as td:
        rep = wb_world_effort(Path(td), "low", [], nterminal={"_terminal": False})
        ps = rep["per_slot"][0]
        check("w13-wb-active-state-not-formal",
              ps["formal_admission"] is False
              and any("非 completed" in f or "terminal" in f for f in ps["fails"]),
              json.dumps(ps["fails"])[:220])
    # W13-3：错误态（state=error）拒
    with tempfile.TemporaryDirectory(prefix="l4gate-w13e-") as td:
        rep = wb_world_effort(Path(td), "low", [], nterminal={"_state": "error"})
        ps = rep["per_slot"][0]
        check("w13-wb-error-state-not-formal",
              ps["formal_admission"] is False
              and any("非 completed" in f for f in ps["fails"]),
              json.dumps(ps["fails"])[:220])
    # inputs_verification 缺失 → 不准入
    rep, s = expect_formal(mut_ok={"inputs_verification": {"ok": False}})
    check("inputs-verification-missing-not-formal", s["formal_admitted"] == 1
          and any("inputs_verification" in f for f in rep["per_slot"][0]["fails"]),
          str(rep["per_slot"][0]["fails"])[:180])
    # notexec 虚造空流（保留）
    with tempfile.TemporaryDirectory(prefix="l4gate-n-") as td:
        tmp = Path(td)
        s4 = mkslot(4, "ne")
        plan_dir, bp2, gr, gt, ga = build_world(tmp, [s4], base_contract())
        ev4 = tmp / s4["evidence_dir"]
        mknotexec(ev4, s4)
        (ev4 / "agent.jsonl").write_text("{}")
        rep = gate_admission(bp2, "dsh", repo=tmp, plan_dir=plan_dir,
                             git_reader=gr, git_time=gt, git_ancestor=ga, required_set=RS)
        f4 = rep["per_slot"][0]["fails"]
        check("notexec-fabricated-stream-flagged",
              rep["per_slot"][3 if False else 0].get("record_valid") is False
              and rep["summary"]["accounting_complete"] is False,
              json.dumps(f4)[:200])
    # 缺记账
    with tempfile.TemporaryDirectory(prefix="l4gate-m-") as td:
        tmp = Path(td)
        sx = mkslot(9, "gone")
        plan_dir, bp2, gr, gt, ga = build_world(tmp, [sx], base_contract())
        rep = gate_admission(bp2, "dsh", repo=tmp, plan_dir=plan_dir,
                             git_reader=gr, git_time=gt, git_ancestor=ga, required_set=RS)
        check("missing-accounting-flagged",
              rep["per_slot"][0]["accounting"] is None
              and rep["summary"]["accounting_complete"] is False,
              json.dumps(rep["per_slot"][0]["fails"])[:200])
    # plan run_id 部分重号
    with tempfile.TemporaryDirectory(prefix="l4gate-d-") as td:
        tmp = Path(td)
        sa, sb = mkslot(1, "ok"), dict(mkslot(2, "ok"))
        sb["run_id"] = sa["run_id"]
        plan_dir, bp2, gr, gt, ga = build_world(tmp, [sa, sb], base_contract())
        try:
            gate_admission(bp2, "dsh", repo=tmp, plan_dir=plan_dir,
                           git_reader=gr, git_time=gt, git_ancestor=ga, required_set=RS)
            check("plan-runid-partial-dupe-raises", False, "未 raise")
        except GateError as exc:
            check("plan-runid-partial-dupe-raises", "run_id 重复" in str(exc), str(exc)[:180])
    # admission 先 verify
    with tempfile.TemporaryDirectory(prefix="l4gate-w-") as td:
        tmp = Path(td)
        sa = mkslot(1, "ok")
        plan_dir, bp2, gr, gt, ga = build_world(tmp, [sa], base_contract())
        bad = json.loads(bp2.read_text(encoding="utf-8"))
        bad["execution_manifest_sha256"] = "0" * 64
        bp3 = tmp / "binding-bad.json"
        _write(bp3, json.dumps(bad))
        try:
            gate_admission(bp3, "dsh", repo=tmp, plan_dir=plan_dir,
                           git_reader=gr, git_time=gt, git_ancestor=ga, required_set=RS)
            check("admission-requires-verify-first", False, "未 raise")
        except GateError as exc:
            check("admission-requires-verify-first", "manifest-sha" in str(exc), str(exc)[:180])

    counts = {"total": len(results), "passed": sum(1 for r in results if r["pass"]),
              "failed": sum(1 for r in results if not r["pass"])}
    out = {"kind": "self_test", "tool": "gate.py", "spec": SPEC, "at": now_local(),
           "counts": counts, "cases": results}
    print(json.dumps(out, ensure_ascii=False, indent=2))
    print("GATE_SELFTEST:", "PASS" if counts["failed"] == 0 else "FAIL")
    return 0 if counts["failed"] == 0 else 1


def main(argv) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify-execution", action="store_true")
    ap.add_argument("--admission", action="store_true")
    ap.add_argument("--binding", default=None,
                    help="runtime-binding.json 路径（L7-A：必填，无默认批）")
    ap.add_argument("--product", default="dsh", choices=["dsh", "codex", "workbuddy"])
    ap.add_argument("--plan-dir", default=None,
                    help="计划目录（L7-A：必填，无默认批）")
    ap.add_argument("--no-require-release", dest="require_release", action="store_false", default=True)
    ap.add_argument("--out", default=None)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    if not a.binding or not a.plan_dir:
        ap.error("--binding 与 --plan-dir 均必填（L7-A：不再有隐式默认批目录）")
    try:
        if a.verify_execution:
            report = verify_execution(a.binding, plan_dir=Path(a.plan_dir),
                                      require_release=a.require_release)
            body = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
            print(json.dumps({"ok": True,
                              "consumable_for_real_calls":
                                  report["release_check"]["consumable_for_real_calls"],
                              "manifest_files": report["manifest_files"],
                              "manifest_external_files": report["manifest_external_files"]},
                             ensure_ascii=False))
            kind = "verify-execution"
        elif a.admission:
            report = gate_admission(a.binding, a.product, plan_dir=Path(a.plan_dir))
            body = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
            print(json.dumps({"summary": report["summary"]}, ensure_ascii=False))
            kind = "admission-%s" % a.product
        else:
            ap.print_help()
            return 2
    except GateError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 1
    if a.out:
        try:
            atomic_refuse_write(Path(a.out), body)
            print("RECEIPT:", a.out)
        except GateError as exc:
            print(str(exc), file=sys.stderr)
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
