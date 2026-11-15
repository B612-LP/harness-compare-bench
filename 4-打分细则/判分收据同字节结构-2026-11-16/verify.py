#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""verify.py — 判分收据同字节结构-2026-11-16（schema: receipt-collapse-v1）

裁定 r1109 DSH 判分收据中 bird r2/r3 逐字节相同（含 retrorun 收据、mtime 同秒）
是「结构性重合」还是「复制/覆盖错误」。按冻结预注册 README.md 实现：
  §2 判据：15 槽 schema 键集枚举；结果元组 (earned, possible, reward,
      rule_version, checker_sha256) 分组；同元组同 case rep 对 → collapse /
      diverge-with-same-tuple；不同元组的对收据必不同（违反 exit 2）；
      judging_incident 子键集 + cause/pre_fix_checker_stdout 仅字节长度+SHA256
      逐 rep 登记比较；retrorun 存在性映射+同上比较；mtime 秒级矩阵+同秒组；
      bird r2/r3 workspace 文件集 SHA 聚合复算（预注册记载勘察前提 r2≠r3）。
  §3 分支：B-STRUCTURAL-COINCIDENCE / B-COPY-ANOMALY（4 触发条件，第一条
      同元组+对内 incident 材料 SHA 不同+收据同字节=矛盾 → exit 2 fail-closed）
      / B-INDETERMINATE。
  §5 内容无关纪律：只取键名、SHA、字节数、mtime、计数；不读任何收据值文本，
      不读 workspace 文件内容（仅哈希）。

CLI:
    python3 verify.py --root <repo> --archive-root <launch-r1109 根> [--output PATH]
  --root 与 --archive-root 均必填；--output 独占创建（已存在拒改，exit 2）。
  所有冻结校验失败 exit 2；成功 exit 0。python3 与 python3 -O 的 stdout 逐字节一致。

隐私：本文件不含绝对主机路径；结果不含收据值文本（仅长度/摘要 SHA）。
"""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone

SCHEMA = "receipt-collapse-v1"
PACKAGE_TITLE = "判分收据同字节结构-2026-11-16"

# 冻结预注册页相对路径（§4：不改本页；开工先验其 SHA）
PREREG_REL = os.path.join("4-打分细则", "判分收据同字节结构-2026-11-16", "README.md")

# prereg §2：观测面仅 r1109 DSH 15 槽（5 case × 3 rep）
EXPECTED_SLOT_COUNT = 15

TUPLE_FIELDS = ("earned", "possible", "reward", "rule_version", "checker_sha256")
MAIN_RECEIPT = "score-receipt.json"
RETRO_RECEIPT = "score-receipt.retrorun-benchprivate.json"
FAMILIES = ("main", "retrorun")
FAMILY_FILENAME = {"main": MAIN_RECEIPT, "retrorun": RETRO_RECEIPT}
INCIDENT_KEY = "judging_incident"
PER_RUN_LABEL_FIELDS = ("rep", "run_id")  # nested-schema 逐运行身份字段
WORKSPACE_DIRNAME = "workspace"
RUNS_SUBPATH = os.path.join("dsh", "runs")
SLOT_RE = re.compile(r"^dsh__(.+)__r(\d+)$")
UTC8 = timezone(timedelta(hours=8))

# workspace 聚合公式（内容无关；登记于 result，等值/互异判定与公式选择无关）
WORKSPACE_FORMULA = ('sha256 of UTF-8 "\\n".join(sorted("{relpath}\\x00{file_sha256}")); '
                     "empty file set aggregates sha256 of empty bytes")

VERDICT_STRUCTURAL = "B-STRUCTURAL-COINCIDENCE"
VERDICT_COPY_ANOMALY = "B-COPY-ANOMALY"
VERDICT_INDETERMINATE = "B-INDETERMINATE"

# prereg §3 line 19 解释登记（见 result.interpretation_notes）
NOTE_S2_LOCUS = (
    "prereg §3 names incident-subkey per-rep material as the divergence locus; "
    "for diverge-with-same-tuple pairs whose schema has no judging_incident key, "
    "the per-rep material fields are rep/run_id (prereg §2 line 10: run-unique "
    "material evidence). Either way every differing path is fully attributed by "
    "length+SHA256, content-free."
)


class FrozenViolation(Exception):
    """冻结校验失败 → exit 2（fail-closed）。"""

    exit_code = 2


def fail(msg):
    raise FrozenViolation(msg)


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def canonical_json_bytes(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":")).encode("utf-8")


def leaf_digest(value):
    """内容无关叶摘要：str → UTF-8 字节；其他 → canonical JSON 字节。"""
    if isinstance(value, str):
        raw = value.encode("utf-8")
    else:
        raw = canonical_json_bytes(value)
    return {"type": type(value).__name__, "len": len(raw), "sha256": sha256_bytes(raw)}


def flatten_leaves(obj, prefix=""):
    """递归展开为 {key.path: digest}；dict/list 递归，其余为叶。

    根级键无前导点（rep, run_id, judging_incident.cause, score.earned …）。
    """
    out = {}
    if isinstance(obj, dict):
        for k in sorted(obj.keys()):
            child = str(k) if prefix == "" else prefix + "." + str(k)
            out.update(flatten_leaves(obj[k], child))
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            child = str(i) if prefix == "" else prefix + "." + str(i)
            out.update(flatten_leaves(item, child))
    else:
        out[prefix] = leaf_digest(obj)
    return out


def diff_leaves(doc_a, doc_b):
    """逐 key-path 差异；值仅以 {len, sha256} 登记，不读文本。"""
    fa = flatten_leaves(doc_a)
    fb = flatten_leaves(doc_b)
    paths = sorted(set(fa) | set(fb))
    differing = []
    for p in paths:
        da = fa.get(p)
        db = fb.get(p)
        if da != db:
            differing.append({"path": p, "a": da, "b": db})
    return differing


def is_per_rep_material_path(path):
    """差异路径是否落在逐运行材料字段（incident 子键或 rep/run_id）。"""
    if path in PER_RUN_LABEL_FIELDS:
        return True
    if path.startswith(INCIDENT_KEY + "."):
        return True
    return False


def extract_tuple(doc):
    """结果元组：顶层五键，或 score.* 五键；缺键 → (None, None)。"""
    if all(k in doc for k in TUPLE_FIELDS):
        return {k: doc[k] for k in TUPLE_FIELDS}, "top"
    score = doc.get("score")
    if isinstance(score, dict) and all(k in score for k in TUPLE_FIELDS):
        return {k: score[k] for k in TUPLE_FIELDS}, "score"
    return None, None


def tuple_group_key(t):
    """元组分组的确定性键（比较用），t 已含全部五键。"""
    payload = [t[k] for k in TUPLE_FIELDS]
    return sha256_bytes(canonical_json_bytes(payload))


def incident_material(doc):
    """judging_incident：子键集 + 每子键字节长度+SHA256（str→UTF-8；其他→canonical）。

    返回 (present, subkeys, materials, note)；非 dict 视为 absent 并登记 note。
    """
    inc = doc.get(INCIDENT_KEY)
    if INCIDENT_KEY not in doc:
        return False, [], {}, None
    if not isinstance(inc, dict):
        return False, [], {}, "judging_incident present but not an object; treated as absent"
    subkeys = sorted(inc.keys())
    materials = {}
    for k in subkeys:
        v = inc[k]
        raw = v.encode("utf-8") if isinstance(v, str) else canonical_json_bytes(v)
        materials[k] = {"len": len(raw), "sha256": sha256_bytes(raw)}
    return True, subkeys, materials, None


def parse_slot_name(name):
    m = SLOT_RE.match(name)
    if not m:
        return None, None
    return m.group(1), int(m.group(2))


def mtime_seconds(path):
    return os.stat(path).st_mtime_ns // 1_000_000_000


def mtime_utc8(ts):
    return datetime.fromtimestamp(ts, UTC8).strftime("%Y-%m-%d %H:%M:%S +08:00")


def read_receipt(path):
    """读收据字节 → 结构登记（内容无关）。JSON 解析失败 → exit 2。"""
    with open(path, "rb") as fh:
        raw = fh.read()
    try:
        doc = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        fail("receipt is not valid UTF-8 JSON: %s (%s)" % (os.path.basename(path), exc))
    if not isinstance(doc, dict):
        fail("receipt top level is not a JSON object: %s" % os.path.basename(path))
    return raw, doc


def workspace_aggregate(ws_dir):
    """workspace 文件集聚合：相对路径+文件字节 SHA 的聚合 SHA（不读内容文本）。

    公式见 WORKSPACE_FORMULA；目录不存在 → exists=False。
    """
    if not os.path.isdir(ws_dir):
        return {"exists": False, "file_count": 0, "files": [], "aggregate_sha256": None}
    entries = []
    for dirpath, dirnames, filenames in os.walk(ws_dir):
        dirnames.sort()
        for fn in sorted(filenames):
            full = os.path.join(dirpath, fn)
            if not os.path.isfile(full):
                continue
            rel = os.path.relpath(full, ws_dir).replace(os.sep, "/")
            with open(full, "rb") as fh:
                data = fh.read()
            entries.append({"path": rel, "size_bytes": len(data),
                            "sha256": sha256_bytes(data)})
    entries.sort(key=lambda e: e["path"])
    joined = "\n".join("%s\x00%s" % (e["path"], e["sha256"]) for e in entries)
    agg = sha256_bytes(joined.encode("utf-8"))
    return {"exists": True, "file_count": len(entries), "files": entries,
            "aggregate_sha256": agg}


def check_pair_frozen(tuple_a, tuple_b, bytes_equal, materials_a, materials_b,
                      incidents_present_a, incidents_present_b):
    """冻结矛盾守卫（对 prereg §2 line 11 与 §3 触发条件一的 fail-closed 实现）。

    返回分类字符串；矛盾 → FrozenViolation(exit 2)。
    - tuple 缺失（任一侧未提取到五键）→ "unclassified-missing-tuple"
    - 元组不同 + 字节相同 → 矛盾（V2）exit 2
    - 元组相同 + 字节相同 + 对内 incident 材料不同（或单侧缺失）→ 矛盾（V1）exit 2
    - 元组相同 + 字节相同 → "collapse"
    - 元组相同 + 字节不同 → "diverge-with-same-tuple"
    - 元组不同 + 字节不同 → "cross-tuple-different"
    """
    if tuple_a is None or tuple_b is None:
        return "unclassified-missing-tuple"
    same_tuple = tuple_group_key(tuple_a) == tuple_group_key(tuple_b)
    if same_tuple:
        if bytes_equal:
            materials_equal = (incidents_present_a == incidents_present_b) and \
                (materials_a == materials_b)
            if not materials_equal:
                fail("FROZEN VIOLATION V1: same result tuple + identical receipt "
                     "bytes but in-pair judging_incident material digests differ "
                     "(contradiction; prereg §3 first B-COPY-ANOMALY trigger)")
            return "collapse"
        return "diverge-with-same-tuple"
    if bytes_equal:
        fail("FROZEN VIOLATION V2: different result tuples but identical receipt "
             "bytes (prereg §2: 不同元组的对收据必不同)")
    return "cross-tuple-different"


def collect_protected_strings(obj, protected, allowed, prefix=""):
    """登记所有非元组字段的字符串叶值为隐私保护对象（含 judging_incident 子键）。

    元组字段值（earned/possible/reward/rule_version/checker_sha256）按预注册
    §2 原样入 result，属允许集合；case/slot/文件名等标识符亦允许。
    """
    if isinstance(obj, dict):
        for k, v in obj.items():
            child = str(k) if prefix == "" else prefix + "." + str(k)
            collect_protected_strings(v, protected, allowed, child)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            child = str(i) if prefix == "" else prefix + "." + str(i)
            collect_protected_strings(v, protected, allowed, child)
    elif isinstance(obj, str):
        leaf = prefix.rsplit(".", 1)[-1]
        if leaf in TUPLE_FIELDS:
            return
        if obj in allowed:
            return
        protected.add(obj)


def build_receipt_record(path, family, protected_values, allowed_strings):
    raw, doc = read_receipt(path)
    top_keys = sorted(doc.keys())
    t, t_source = extract_tuple(doc)
    inc_present, inc_subkeys, inc_materials, inc_note = incident_material(doc)
    collect_protected_strings(doc, protected_values, allowed_strings)
    rec = {
        "family": family,
        "size_bytes": len(raw),
        "sha256": sha256_bytes(raw),
        "mtime_epoch": mtime_seconds(path),
        "top_key_set": top_keys,
        "tuple": t,
        "tuple_source": t_source,
        "tuple_group_key": tuple_group_key(t) if t is not None else None,
        "incident": {
            "present": inc_present,
            "subkeys": inc_subkeys,
            "materials": inc_materials,
            "note": inc_note,
        },
    }
    rec["mtime_utc8"] = mtime_utc8(rec["mtime_epoch"])
    return rec


def mtime_matrix_and_groups(receipts):
    matrix = {}
    group_map = {}
    for slot in sorted(receipts):
        matrix[slot] = {}
        for family in FAMILIES:
            rec = receipts[slot].get(family)
            if rec is None:
                continue
            ts = rec["mtime_epoch"]
            matrix[slot][family] = {"epoch": ts, "utc8": mtime_utc8(ts)}
            group_map.setdefault(ts, []).append("%s/%s" % (slot, family))
    groups = []
    for ts in sorted(group_map):
        members = sorted(group_map[ts])
        if len(members) >= 2:
            groups.append({"epoch": ts, "utc8": mtime_utc8(ts), "members": members})
    return matrix, groups


def mtime_order_violations(slot_info, receipts):
    """同 case 同 family 内 rep 序 mtime 必须非递减（r3 早于 r2 ⇒ 触发条件三）。"""
    violations = []
    cases = {}
    for slot in sorted(slot_info):
        case, rep = slot_info[slot]
        cases.setdefault(case, {})[rep] = slot
    for case in sorted(cases):
        reps = sorted(cases[case])
        for family in FAMILIES:
            ts = []
            for rep in reps:
                rec = receipts[cases[case][rep]].get(family)
                ts.append(None if rec is None else rec["mtime_epoch"])
            for i in range(len(ts)):
                for j in range(i + 1, len(ts)):
                    if ts[i] is not None and ts[j] is not None and ts[i] > ts[j]:
                        violations.append({
                            "case": case, "family": family,
                            "earlier_rep_slot": cases[case][reps[i]],
                            "later_rep_slot": cases[case][reps[j]],
                            "mtime_earlier_rep": ts[i], "mtime_later_rep": ts[j],
                            "detail": "rep with smaller index has LATER mtime "
                                      "(prereg §3 trigger: r3 早于 r2 写入类矛盾)",
                        })
    return violations


def evaluate_branch(same_case_pairs, cross_case_pairs, order_violations,
                    classification_complete):
    """§3 三分支字面实现。t1（V1 矛盾）已在 check_pair_frozen 内 fail-closed。"""
    triggers = {
        "t1_same_tuple_same_bytes_incident_material_diff_exit2": False,
        "t2_collapse_pattern_inconsistent_with_tuple_grouping": False,
        "t3_mtime_contradicts_batch_semantics": bool(order_violations),
        "t4_retrorun_has_per_run_material_but_collapse_unexplained": False,
    }
    t2_reasons = []
    for p in cross_case_pairs:
        if p["bytes_equal"]:
            triggers["t2_collapse_pattern_inconsistent_with_tuple_grouping"] = True
            t2_reasons.append("cross-case bytes-equal pair: %s vs %s (%s)"
                              % (p["slot_a"], p["slot_b"], p["family"]))
    collapse_pairs = [p for p in same_case_pairs if p["classification"] == "collapse"]
    diverge_pairs = [p for p in same_case_pairs
                     if p["classification"] == "diverge-with-same-tuple"]
    retrorun_divergent = [p for p in same_case_pairs
                          if p["family"] == "retrorun"
                          and p["classification"] == "diverge-with-same-tuple"]
    retrorun_collapse_unexplained = [p for p in collapse_pairs
                                     if p["family"] == "retrorun"
                                     and not p["explanation_complete"]]
    if retrorun_divergent and retrorun_collapse_unexplained:
        triggers["t4_retrorun_has_per_run_material_but_collapse_unexplained"] = True

    # 空集 ⇒ 全称条件按字面为真（无该类对即无待解释项）。
    s1 = all(p["explanation_complete"] for p in collapse_pairs)
    s2 = all(
        p.get("differing_paths") and
        all(is_per_rep_material_path(d["path"]) for d in p["differing_paths"])
        for p in diverge_pairs)
    s2_notes = []
    for p in diverge_pairs:
        if not p.get("differing_paths"):
            s2_notes.append("divergence not located in parsed leaves: %s vs %s (%s)"
                            % (p["slot_a"], p["slot_b"], p["family"]))
        elif any(not is_per_rep_material_path(d["path"]) for d in p["differing_paths"]):
            s2_notes.append("divergence extends beyond per-rep material fields: "
                            "%s vs %s (%s) paths=%s"
                            % (p["slot_a"], p["slot_b"], p["family"],
                               sorted(d["path"] for d in p["differing_paths"])))
    s3 = not triggers["t3_mtime_contradicts_batch_semantics"]

    fired = [k for k, v in triggers.items() if v and k !=
             "t1_same_tuple_same_bytes_incident_material_diff_exit2"]
    if fired:
        verdict = VERDICT_COPY_ANOMALY
        rationale = ["fired: " + ", ".join(fired)] + t2_reasons
    elif s1 and s2 and s3 and classification_complete:
        verdict = VERDICT_STRUCTURAL
        rationale = [
            "all collapse pairs explained by equal result tuple + identical "
            "in-pair incident material (lengths/SHA256) [s1]",
            "all diverge-with-same-tuple pairs have located divergence in per-rep "
            "material fields [s2]",
            "no mtime order contradiction within case/family rep sequences [s3]",
            "all same-case rep pairs classified (no missing-tuple probes) [complete]",
        ]
    else:
        verdict = VERDICT_INDETERMINATE
        rationale = []
        if not collapse_pairs:
            rationale.append("no collapse pairs observed")
        if collapse_pairs and not s1:
            rationale.append("some collapse pair lacks complete material explanation")
        if diverge_pairs and not s2:
            rationale.extend(s2_notes or ["divergence not fully located"])
        if not s3:
            rationale.append("mtime order contradiction present")
        if not classification_complete:
            rationale.append("some same-case pairs could not be classified "
                             "(result tuple missing)")
    return {
        "verdict": verdict,
        "rationale": rationale,
        "triggers": triggers,
        "t2_reasons": t2_reasons,
        "structural_conditions": {"s1_collapse_pairs_fully_explained": s1,
                                  "s2_divergence_located_to_per_rep_material": s2,
                                  "s3_mtime_batch_consistent": s3,
                                  "classification_complete": classification_complete},
        "counts": {"collapse_pairs": len(collapse_pairs),
                   "diverge_same_tuple_pairs": len(diverge_pairs),
                   "cross_tuple_different_pairs": len(
                       [p for p in same_case_pairs
                        if p["classification"] == "cross-tuple-different"]),
                   "unclassified_missing_tuple_pairs": len(
                       [p for p in same_case_pairs
                        if p["classification"] == "unclassified-missing-tuple"]),
                   "cross_case_bytes_equal_pairs": len(cross_case_pairs)},
    }


def privacy_audit(result_obj, protected_values):
    text = json.dumps(result_obj, sort_keys=True, ensure_ascii=False)
    for v in sorted(protected_values):
        if len(v) >= 8 and v in text:
            fail("PRIVACY AUDIT FAILURE: receipt value text leaked into result "
                 "(prefix=%r)" % v[:16])
        head = v[:16]
        if len(v) >= 16 and head in text:
            fail("PRIVACY AUDIT FAILURE: receipt value prefix leaked into result "
                 "(prefix=%r)" % head)


def run_verification(root, archive_root):
    root = os.path.abspath(root)
    archive_root = os.path.abspath(archive_root)
    if not os.path.isdir(root):
        fail("--root is not an existing directory")
    if not os.path.isdir(archive_root):
        fail("--archive-root is not an existing directory")
    runs_dir = os.path.join(archive_root, RUNS_SUBPATH)
    if not os.path.isdir(runs_dir):
        fail("--archive-root must point at launch-r1109 root containing dsh/runs/")

    prereg_path = os.path.join(root, PREREG_REL)
    if not os.path.isfile(prereg_path):
        fail("prereg README not found under --root: %s" % PREREG_REL)
    with open(prereg_path, "rb") as fh:
        prereg_bytes = fh.read()
    prereg_sha = sha256_bytes(prereg_bytes)

    baseline_commit = None
    git_available = False
    try:
        out = subprocess.run(["git", "-C", root, "rev-parse", "HEAD"],
                             capture_output=True, text=True, timeout=30)
        if out.returncode == 0:
            baseline_commit = out.stdout.strip() or None
            git_available = True
    except (OSError, subprocess.SubprocessError):
        pass

    slots = sorted(d for d in os.listdir(runs_dir)
                   if os.path.isdir(os.path.join(runs_dir, d)))
    if not slots:
        fail("no slot directories under dsh/runs/")
    slot_info = {}
    for s in slots:
        case, rep = parse_slot_name(s)
        if case is None:
            fail("slot directory does not match dsh__<case>__r<N>: %s" % s)
        slot_info[s] = (case, rep)
    if len(slots) != EXPECTED_SLOT_COUNT:
        fail("observation surface mismatch: prereg §2 fixes 15 slots (r1109 DSH), "
             "found %d" % len(slots))

    protected_values = set()
    allowed_strings = set(slots) | {s[0] for s in slot_info.values()} | \
        {MAIN_RECEIPT, RETRO_RECEIPT, WORKSPACE_DIRNAME}
    # workspace 相对路径属观测面结构（§2 文件集聚合需登记 path+SHA），
    # 其路径标识符（全路径、后缀、分量、基名）加入允许集合，避免与收据内
    # 文件名类短值发生标识符碰撞误报；审计仍拦截任何长于标识符的值文本。
    workspace = {}
    for slot in slots:
        workspace[slot] = workspace_aggregate(os.path.join(runs_dir, slot,
                                                           WORKSPACE_DIRNAME))
        for f in workspace[slot]["files"]:
            rel = f["path"]
            parts = rel.split("/")
            for i in range(len(parts)):
                suffix = "/".join(parts[i:])
                allowed_strings.add(suffix)
                allowed_strings.add(parts[i])
            base = parts[-1]
            stem = base.rsplit(".", 1)[0]
            if stem:
                allowed_strings.add(stem)
    receipts = {}
    for slot in slots:
        receipts[slot] = {}
        for family in FAMILIES:
            path = os.path.join(runs_dir, slot, FAMILY_FILENAME[family])
            if not os.path.isfile(path):
                if family == "main":
                    fail("missing main receipt: %s/score-receipt.json" % slot)
                continue
            receipts[slot][family] = build_receipt_record(path, family,
                                                          protected_values,
                                                          allowed_strings)
    # 解析文档仅用于叶级 diff（比较后即弃，不入 result；内容无关纪律照旧）
    doc_cache = {}

    same_case_pairs = []
    cases = {}
    for slot in sorted(slot_info):
        case, rep = slot_info[slot]
        cases.setdefault(case, {})[rep] = slot
    for case in sorted(cases):
        reps = sorted(cases[case])
        for i in range(len(reps)):
            for j in range(i + 1, len(reps)):
                sa, sb = cases[case][reps[i]], cases[case][reps[j]]
                for family in FAMILIES:
                    if family not in receipts[sa] or family not in receipts[sb]:
                        continue
                    ra, rb = receipts[sa][family], receipts[sb][family]
                    bytes_equal = ra["sha256"] == rb["sha256"]
                    cls = check_pair_frozen(ra["tuple"], rb["tuple"], bytes_equal,
                                            ra["incident"]["materials"],
                                            rb["incident"]["materials"],
                                            ra["incident"]["present"],
                                            rb["incident"]["present"])
                    record = {
                        "case": case, "family": family,
                        "slot_a": sa, "slot_b": sb,
                        "tuple_a": ra["tuple"], "tuple_b": rb["tuple"],
                        "tuple_equal": (ra["tuple_group_key"] is not None and
                                        ra["tuple_group_key"] == rb["tuple_group_key"]),
                        "bytes_equal": bytes_equal,
                        "sha_a": ra["sha256"], "sha_b": rb["sha256"],
                        "size_a": ra["size_bytes"], "size_b": rb["size_bytes"],
                        "classification": cls,
                    }
                    if cls == "diverge-with-same-tuple":
                        for sl in (sa, sb):
                            if (sl, family) not in doc_cache:
                                _, doc = read_receipt(
                                    os.path.join(runs_dir, sl, FAMILY_FILENAME[family]))
                                doc_cache[(sl, family)] = doc
                        differing = diff_leaves(doc_cache[(sa, family)],
                                                doc_cache[(sb, family)])
                        record["differing_paths"] = differing
                        record["divergence_categories"] = sorted(
                            {"per-rep-material" if is_per_rep_material_path(d["path"])
                             else "other" for d in differing}) or \
                            ["raw-bytes-outside-parsed-leaves"]
                    if cls == "collapse":
                        ma, mb = ra["incident"], rb["incident"]
                        both_absent = (not ma["present"]) and (not mb["present"])
                        mats_equal = None if both_absent else \
                            ma["materials"] == mb["materials"]
                        record["incident_both_absent"] = both_absent
                        record["incident_materials_equal"] = mats_equal
                        record["explanation_complete"] = bool(
                            record["tuple_equal"] and
                            (both_absent or mats_equal is True))
                    same_case_pairs.append(record)

    classification_complete = all(
        p["classification"] not in ("unclassified-missing-tuple",)
        for p in same_case_pairs)

    cross_case_pairs = []
    ordered_slots = sorted(receipts)
    for i in range(len(ordered_slots)):
        for j in range(i + 1, len(ordered_slots)):
            sa, sb = ordered_slots[i], ordered_slots[j]
            if slot_info[sa][0] == slot_info[sb][0]:
                continue
            for family in FAMILIES:
                if family not in receipts[sa] or family not in receipts[sb]:
                    continue
                ra, rb = receipts[sa][family], receipts[sb][family]
                if ra["sha256"] != rb["sha256"]:
                    continue
                cls = check_pair_frozen(ra["tuple"], rb["tuple"], True,
                                        ra["incident"]["materials"],
                                        rb["incident"]["materials"],
                                        ra["incident"]["present"],
                                        rb["incident"]["present"])
                cross_case_pairs.append({
                    "slot_a": sa, "slot_b": sb, "family": family,
                    "case_a": slot_info[sa][0], "case_b": slot_info[sb][0],
                    "bytes_equal": True, "classification": cls,
                })

    order_violations = mtime_order_violations(slot_info, receipts)
    branch = evaluate_branch(same_case_pairs, cross_case_pairs, order_violations,
                             classification_complete)

    matrix, same_second_groups = mtime_matrix_and_groups(receipts)

    retrorun_map = {slot: ("retrorun" in receipts[slot]) for slot in slots}
    retrorun_cases = sorted({slot_info[s][0] for s in slots
                             if retrorun_map[s]})
    ws_patterns = {}
    for case in sorted(cases):
        aggs = {rep: workspace[cases[case][rep]]["aggregate_sha256"]
                for rep in sorted(cases[case])}
        vals = set(aggs.values())
        ws_patterns[case] = {
            "slots": {str(r): cases[case][r] for r in sorted(cases[case])},
            "aggregates": {str(r): aggs[r] for r in sorted(cases[case])},
            "all_reps_equal": len(vals) == 1,
            "distinct_count": len(vals),
        }

    bird_cases = [c for c in sorted(cases) if "bird" in c]
    bird_section = None
    if bird_cases:
        bc = bird_cases[0]
        reps = sorted(cases[bc])
        r2 = cases[bc].get(2)
        r3 = cases[bc].get(3)
        if r2 and r3:
            ws_equal = (workspace[r2]["aggregate_sha256"] is not None and
                        workspace[r2]["aggregate_sha256"] ==
                        workspace[r3]["aggregate_sha256"])
            main_equal = ("main" in receipts[r2] and "main" in receipts[r3] and
                          receipts[r2]["main"]["sha256"] == receipts[r3]["main"]["sha256"])
            retro_equal = ("retrorun" in receipts[r2] and "retrorun" in receipts[r3] and
                           receipts[r2]["retrorun"]["sha256"] ==
                           receipts[r3]["retrorun"]["sha256"])
            same_mtime = ("main" in receipts[r2] and "main" in receipts[r3] and
                          receipts[r2]["main"]["mtime_epoch"] ==
                          receipts[r3]["main"]["mtime_epoch"])
            bird_section = {
                "case": bc,
                "slots": {"r1": cases[bc].get(1), "r2": r2, "r3": r3},
                "receipt_main_bytes_identical_r2_r3": main_equal,
                "receipt_retrorun_bytes_identical_r2_r3": retro_equal,
                "receipt_main_mtime_same_second_r2_r3": same_mtime,
                "workspace_aggregate_r2": workspace[r2]["aggregate_sha256"],
                "workspace_aggregate_r3": workspace[r3]["aggregate_sha256"],
                "workspace_content_identical_r2_r3": ws_equal,
                "survey_expectation_from_prereg": {
                    "bird_r2_r3_workspace_distinct": True,
                    "source": "prereg §2 line 15（已勘察 r2≠r3，包内复算）",
                },
                "survey_premise_supported": (ws_equal is False),
            }

    anomalies = []
    if bird_section is not None:
        if bird_section["workspace_content_identical_r2_r3"] is True:
            anomalies.append({
                "id": "workspace-survey-premise-refuted",
                "detail": "prereg §2 line 15 records the surveyed premise "
                          "bird r2/r3 workspace distinct (r2≠r3); recomputation of "
                          "the workspace file-set aggregate finds the two file sets "
                          "content-identical (equal aggregate SHA). The premise is "
                          "refuted by in-package recomputation. This is a survey "
                          "premise error, not a frozen-criteria failure: §2 requires "
                          "the recomputation itself, and §3 branch conditions are "
                          "receipt-level.",
            })
        if bird_section["workspace_content_identical_r2_r3"] is None:
            anomalies.append({
                "id": "workspace-missing",
                "detail": "bird r2/r3 workspace directory missing or empty; "
                          "workspace probe unavailable",
            })
    for p in same_case_pairs:
        if p["classification"] == "diverge-with-same-tuple" and \
                p.get("divergence_categories") and \
                "raw-bytes-outside-parsed-leaves" in p["divergence_categories"]:
            anomalies.append({
                "id": "byte-diff-outside-json",
                "detail": "%s vs %s (%s): receipts differ in raw bytes but parsed "
                          "leaves identical (formatting-level difference)"
                          % (p["slot_a"], p["slot_b"], p["family"]),
            })
    if not any("bird" in c for c in cases):
        anomalies.append({"id": "bird-case-absent",
                          "detail": "no case name containing 'bird'; §1 target pair "
                                    "not present in archive"})

    key_set_groups = {}
    for slot in slots:
        for family in receipts[slot]:
            ks = json.dumps(receipts[slot][family]["top_key_set"],
                            ensure_ascii=False)
            key_set_groups.setdefault(ks, []).append("%s/%s" % (slot, family))

    incident_table = {}
    for slot in slots:
        for family in receipts[slot]:
            rec = receipts[slot][family]
            if rec["incident"]["present"]:
                incident_table.setdefault(family, {})[slot] = {
                    "subkeys": rec["incident"]["subkeys"],
                    "materials": rec["incident"]["materials"],
                }
    cross_family_material = []
    for slot in slots:
        if "main" in receipts[slot] and "retrorun" in receipts[slot] and \
                receipts[slot]["main"]["incident"]["present"] and \
                receipts[slot]["retrorun"]["incident"]["present"]:
            m = receipts[slot]["main"]["incident"]["materials"]
            r = receipts[slot]["retrorun"]["incident"]["materials"]
            per_subkey = {}
            for k in sorted(set(m) | set(r)):
                mk = m.get(k)
                rk = r.get(k)
                per_subkey[k] = "same" if mk == rk else "different"
            cross_family_material.append({"slot": slot, "subkey_comparison": per_subkey})

    result = {
        "schema": SCHEMA,
        "package": PACKAGE_TITLE,
        "prereg": {
            "path": PREREG_REL.replace(os.sep, "/"),
            "sha256": prereg_sha,
            "size_bytes": len(prereg_bytes),
        },
        "baseline_commit": baseline_commit,
        "git_available": git_available,
        "inputs": {
            "root_provided": True,
            "archive_root_provided": True,
            "archive_layout": "dsh/runs/<slot>/score-receipt.json (+ retrorun file "
                              "where present, workspace/)",
            "paths_redacted": "absolute CLI paths intentionally omitted from result",
        },
        "observation_surface": {
            "expected_slot_count": EXPECTED_SLOT_COUNT,
            "slot_count": len(slots),
            "slots": slots,
            "cases": {c: {"rep_count": len(cases[c]),
                          "slots": [cases[c][r] for r in sorted(cases[c])]}
                      for c in sorted(cases)},
        },
        "tuple_fields": list(TUPLE_FIELDS),
        "key_set_groups": {ks: sorted(v) for ks, v in sorted(key_set_groups.items())},
        "receipts": {slot: {f: receipts[slot][f] for f in sorted(receipts[slot])
                            } for slot in slots},
        "retrorun_existence_map": retrorun_map,
        "retrorun_cases": retrorun_cases,
        "pairs": {
            "same_case": same_case_pairs,
            "cross_case_bytes_equal": cross_case_pairs,
        },
        "incident_material_table": {f: {s: incident_table[f][s]
                                        for s in sorted(incident_table[f])}
                                    for f in sorted(incident_table)},
        "cross_family_incident_material_comparison": cross_family_material,
        "mtime_matrix": matrix,
        "mtime_same_second_groups": same_second_groups,
        "mtime_order_violations": order_violations,
        "workspace": {
            slot: {k: v for k, v in workspace[slot].items()} for slot in slots
        },
        "workspace_formula": WORKSPACE_FORMULA,
        "workspace_case_patterns": ws_patterns,
        "bird_r2_r3": bird_section,
        "branch": branch,
        "anomalies": anomalies,
        "interpretation_notes": [NOTE_S2_LOCUS],
        "score_impact": "none — read-only structural verification; no score/gate "
                        "modification suggested or performed (prereg §5)",
        "content_free_declaration": "verification reads key names, SHA256 digests, "
                                    "byte lengths, mtime seconds and counts only; "
                                    "receipt value text and workspace file contents "
                                    "are never emitted or stored",
        "privacy_audit": "passed",
    }

    privacy_audit(result, protected_values)
    return result, prereg_sha


def render_summary(result):
    b = result["branch"]
    lines = []
    lines.append("== %s (%s) ==" % (result["package"], result["schema"]))
    lines.append("prereg %s sha256=%s size=%dB"
                 % (result["prereg"]["path"], result["prereg"]["sha256"],
                    result["prereg"]["size_bytes"]))
    lines.append("baseline_commit=%s (git_available=%s)"
                 % (result["baseline_commit"], result["git_available"]))
    surf = result["observation_surface"]
    lines.append("slots=%d/%d (prereg surface), cases=%d"
                 % (surf["slot_count"], surf["expected_slot_count"], len(surf["cases"])))
    lines.append("key-set groups: %d distinct" % len(result["key_set_groups"]))
    for ks, members in sorted(result["key_set_groups"].items()):
        lines.append("  keys=%s -> %d receipts" % (ks, len(members)))
    cts = b["counts"]
    lines.append("pairs: collapse=%d diverge-with-same-tuple=%d "
                 "cross-tuple-different=%d unclassified=%d cross-case-bytes-equal=%d"
                 % (cts["collapse_pairs"], cts["diverge_same_tuple_pairs"],
                    cts["cross_tuple_different_pairs"],
                    cts["unclassified_missing_tuple_pairs"],
                    cts["cross_case_bytes_equal_pairs"]))
    for p in result["pairs"]["same_case"]:
        if p["classification"] == "collapse":
            lines.append("  COLLAPSE %s: %s vs %s family=%s sha=%s… size=%dB "
                         "incident_materials_equal=%s explanation_complete=%s"
                         % (p["case"], p["slot_a"], p["slot_b"], p["family"],
                            p["sha_a"][:12], p["size_a"],
                            p.get("incident_materials_equal"),
                            p.get("explanation_complete")))
        elif p["classification"] == "diverge-with-same-tuple":
            paths = sorted(d["path"] for d in p.get("differing_paths", []))
            lines.append("  DIVERGE-SAME-TUPLE %s: %s vs %s family=%s sha %s… vs %s… "
                         "paths=%s cats=%s"
                         % (p["case"], p["slot_a"], p["slot_b"], p["family"],
                            p["sha_a"][:12], p["sha_b"][:12], paths,
                            p.get("divergence_categories")))
    retrorun_slots = [s for s in sorted(result["retrorun_existence_map"])
                      if result["retrorun_existence_map"][s]]
    lines.append("retrorun slots: %s" % (", ".join(retrorun_slots) or "(none)"))
    lines.append("mtime same-second groups: %d" % len(result["mtime_same_second_groups"]))
    for g in result["mtime_same_second_groups"]:
        lines.append("  %s (%d members): %s" % (g["utc8"], len(g["members"]),
                                                ", ".join(g["members"])))
    lines.append("mtime order violations: %d" % len(result["mtime_order_violations"]))
    bird = result["bird_r2_r3"]
    if bird:
        lines.append("bird r2/r3: main_bytes_identical=%s retrorun_bytes_identical=%s "
                     "mtime_same_second=%s"
                     % (bird["receipt_main_bytes_identical_r2_r3"],
                        bird["receipt_retrorun_bytes_identical_r2_r3"],
                        bird["receipt_main_mtime_same_second_r2_r3"]))
        lines.append("bird r2/r3 workspace: aggregate r2=%s r3=%s content_identical=%s"
                     % (bird["workspace_aggregate_r2"][:16] if
                        bird["workspace_aggregate_r2"] else None,
                        bird["workspace_aggregate_r3"][:16] if
                        bird["workspace_aggregate_r3"] else None,
                        bird["workspace_content_identical_r2_r3"]))
        if bird["workspace_content_identical_r2_r3"] is True:
            lines.append("  NOTE: surveyed premise (prereg §2: 已勘察 r2≠r3) is "
                         "REFUTED by recomputation — workspace file sets are "
                         "content-identical; registered as anomaly "
                         "workspace-survey-premise-refuted")
    sc = b["structural_conditions"]
    lines.append("structural conditions: s1=%s s2=%s s3=%s complete=%s"
                 % (sc["s1_collapse_pairs_fully_explained"],
                    sc["s2_divergence_located_to_per_rep_material"],
                    sc["s3_mtime_batch_consistent"], sc["classification_complete"]))
    fired = [k for k, v in b["triggers"].items() if v]
    lines.append("copy-anomaly triggers fired: %s" % (fired or "none"))
    lines.append("BRANCH VERDICT: %s" % b["verdict"])
    for r in b["rationale"]:
        lines.append("  - %s" % r)
    if result["anomalies"]:
        lines.append("anomalies: %d" % len(result["anomalies"]))
        for a in result["anomalies"]:
            lines.append("  - %s" % a["id"])
    lines.append("content-free: %s" % result["content_free_declaration"])
    return "\n".join(lines) + "\n"


def write_output_exclusive(path, payload):
    if os.path.lexists(path):
        fail("--output already exists; refusing to modify (exclusive create): %s"
             % os.path.basename(path))
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(payload)
            fh.flush()
            os.fsync(fh.fileno())
    except OSError:
        fail("--output write failed")
    with open(path, "rb") as fh:
        written = fh.read()
    if written != payload:
        fail("--output readback mismatch after write")


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="判分收据同字节结构-2026-11-16 收据结构裁定（receipt-collapse-v1）")
    parser.add_argument("--root", required=True,
                        help="公开仓库根（含 4-打分细则/<pkg>/README.md 预注册页）")
    parser.add_argument("--archive-root", required=True, dest="archive_root",
                        help="launch-r1109 归档根（其下 dsh/runs/<slot>/）")
    parser.add_argument("--output", default=None,
                        help="result.json 输出路径；独占创建，已存在则拒改 exit 2")
    args = parser.parse_args(argv)
    try:
        result, _ = run_verification(args.root, args.archive_root)
    except FrozenViolation as exc:
        sys.stderr.write("FAIL(exit=2): %s\n" % exc)
        return 2
    summary = render_summary(result)
    sys.stdout.write(summary)
    if args.output:
        payload = (json.dumps(result, sort_keys=True, ensure_ascii=False,
                              indent=2) + "\n").encode("utf-8")
        try:
            write_output_exclusive(args.output, payload)
        except FrozenViolation as exc:
            sys.stdout.flush()
            sys.stderr.write("FAIL(exit=2): %s\n" % exc)
            return 2
        sys.stdout.write("result written: %s (%d bytes)\n"
                         % (os.path.basename(args.output), len(payload)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
