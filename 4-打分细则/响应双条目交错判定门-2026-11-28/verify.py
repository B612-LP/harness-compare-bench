#!/usr/bin/env python3
"""verify.py — 响应双条目交错判定门：公开派生复算。

本脚本改编自 2026-11-28 完成的内部非作者独审独立复放（该独审已按全部预注册
点逐项复算通过，结论 GO）。设计完全来自预注册文本加公开生命周期门
`../Responses生命周期与同源副本-2026-11-27/lifecycle.py`，不读取任何内部
收据或作者运行产物。仅标准库，无网络，无子进程；stdout 完全确定（无时间戳），
`python3 -B` 与 `python3 -OB` 输出逐字节相同。

合成域（预注册固定）：
  * 两条合成消息 A/B，各自独立的 7 段生命周期：
    item.added / part.added / delta / delta / text.done / part.done / item.done
  * 序列内部顺序保持；枚举全部 C(14,7)=3432 个保位交错
  * 三阶段事件固定在外围（created, in_progress, completed）
  * 三种索引方案：
      s1 固定索引 + 快照按索引序
      s2 固定索引 + 快照交换序
      s3 首现动态重编号，快照按新号
  * 同一固定门上另跑单域真负对照与近错探针
"""
import hashlib
import importlib.util
import itertools
import json
import os
import sys
from collections import Counter

BASE = os.path.dirname(os.path.abspath(__file__))
LIFECYCLE_REL = os.path.join("..", "Responses生命周期与同源副本-2026-11-27", "lifecycle.py")
LIFECYCLE_PATH = os.path.normpath(os.path.join(BASE, LIFECYCLE_REL))
LIFECYCLE_REPO_REL = "4-打分细则/Responses生命周期与同源副本-2026-11-27/lifecycle.py"
EXPECTED_GATE_SHA256 = "4e170c0948e28a2bab813b82ca6d758bcb6fc2c22b11deb1a7286ddb548aec08"
SEGMENTS = 7  # per prereg: item.added/part.added/delta/delta/text.done/part.done/item.done
TOTAL = 2 * SEGMENTS
DENOMINATOR = 3432  # C(14,7)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def fail(kind, detail):
    print(json.dumps({"status": kind, "detail": detail}, sort_keys=True, ensure_ascii=False))
    sys.exit(2)


# ---------------- synthetic universe (from prereg text only) ----------------

ITEM_IDS = {"A": "msg_aaa", "B": "msg_bbb"}
BASE_DELTAS = {"A": ("AA0", "AA1"), "B": ("BB0", "BB1")}


class Frame(object):
    __slots__ = ("label", "obj")

    def __init__(self, label, obj):
        self.label = label
        self.obj = obj


def phase_frame(name, output):
    label = "response." + name
    resp = {
        "id": "resp_syn_001",
        "model": "synthetic",
        "object": "response",
        "created_at": 1764221700,
        "status": "completed" if name == "completed" else "in_progress",
        "error": None,
        "incomplete_details": None,
        "output": output,
    }
    return Frame(label, {"type": label, "response": resp})


def added_item(key):
    # valid_identity(message) = (id, 'message', role, phase) — all non-empty strings
    return {"id": ITEM_IDS[key], "type": "message", "role": "assistant",
            "status": "in_progress", "phase": "final", "content": []}


def done_item(key, d1=None, d2=None):
    if d1 is None:
        d1, d2 = BASE_DELTAS[key]
    full = d1 + d2
    return {"id": ITEM_IDS[key], "type": "message", "role": "assistant",
            "status": "completed", "phase": "final",
            "content": [{"type": "output_text", "text": full}]}


def item_events(key, n, d1=None, d2=None):
    """The 7 events of one item at output_index n, internal order fixed."""
    if d1 is None:
        d1, d2 = BASE_DELTAS[key]
    ident = ITEM_IDS[key]
    full = d1 + d2

    def ev(label, obj):
        payload = dict(obj)
        payload["type"] = label
        return Frame(label, payload)

    return [
        ev("response.output_item.added", {"output_index": n, "item": added_item(key)}),
        ev("response.content_part.added", {"output_index": n, "item_id": ident,
                                           "content_index": 0,
                                           "part": {"type": "output_text", "text": ""}}),
        ev("response.output_text.delta", {"output_index": n, "item_id": ident,
                                          "content_index": 0, "delta": d1}),
        ev("response.output_text.delta", {"output_index": n, "item_id": ident,
                                          "content_index": 0, "delta": d2}),
        ev("response.output_text.done", {"output_index": n, "item_id": ident,
                                         "content_index": 0, "text": full}),
        ev("response.content_part.done", {"output_index": n, "item_id": ident,
                                          "content_index": 0,
                                          "part": {"type": "output_text", "text": full}}),
        ev("response.output_item.done", {"output_index": n, "item": done_item(key, d1, d2)}),
    ]


def run_gate(gate, frames):
    mig, ext = gate.inspect(frames)
    return tuple(mig), tuple(ext)


def scheme_snapshot(scheme, first):
    if scheme == "s1":          # fixed index, snapshot in index order
        return [done_item("A"), done_item("B")]
    if scheme == "s2":          # fixed index, swapped snapshot order
        return [done_item("B"), done_item("A")]
    second = "B" if first == "A" else "A"   # s3: snapshot by new (appearance) numbers
    return [done_item(first), done_item(second)]


def enumerate_scheme(gate, scheme):
    cells = Counter()
    by_first = {"A": Counter(), "B": Counter()}
    passed = {"A": 0, "B": 0}
    for combo in itertools.combinations(range(TOTAL), SEGMENTS):
        a_pos = list(combo)
        a_set = set(a_pos)
        b_pos = [p for p in range(TOTAL) if p not in a_set]
        first = "A" if a_pos[0] < b_pos[0] else "B"
        second = "B" if first == "A" else "A"
        if scheme == "s3":
            n_map = {first: 0, second: 1}       # consecutive renumber by first appearance
        else:
            n_map = {"A": 0, "B": 1}            # fixed identity-index binding
        events = [None] * TOTAL
        ev_a = item_events("A", n_map["A"])
        ev_b = item_events("B", n_map["B"])
        for k, p in enumerate(a_pos):
            events[p] = ev_a[k]
        for k, p in enumerate(b_pos):
            events[p] = ev_b[k]
        frames = ([phase_frame("created", []), phase_frame("in_progress", [])]
                  + events
                  + [phase_frame("completed", scheme_snapshot(scheme, first))])
        mig, ext = run_gate(gate, frames)
        cells[(mig, ext)] += 1
        by_first[first][(mig, ext)] += 1
        if not mig and not ext:
            passed[first] += 1
    return cells, by_first, passed


# prereg-derived expectations ("预期恰 A 先出现的1716条原门通过；B先出现仅触发
# ITEM_START。快照错序在此之外有单独原因" plus scheme semantics)
EXPECTED = {
    ("s1", "A"): {"(PASS)|(PASS)": 1716},
    ("s1", "B"): {"(ITEM_START)|(PASS)": 1716},
    ("s2", "A"): {"(SNAPSHOT_DISAGREEMENT)|(PASS)": 1716},
    ("s2", "B"): {"(ITEM_START,SNAPSHOT_DISAGREEMENT)|(PASS)": 1716},
    ("s3", "A"): {"(PASS)|(PASS)": 1716},
    ("s3", "B"): {"(PASS)|(PASS)": 1716},
}


def cell_key(mig, ext):
    return ("(" + ",".join(mig) + ")" if mig else "(PASS)",
            "(" + ",".join(ext) + ")" if ext else "(PASS)")


def flat_cell(pair):
    """(migration_tuple, extension_tuple) -> flat 'MIG|EXT' JSON-safe key."""
    mig, ext = pair
    return ("(" + ",".join(mig) + ")" if mig else "(PASS)") + "|" + \
           ("(" + ",".join(ext) + ")" if ext else "(PASS)")


def cells_json(counter):
    out = []
    for (mig, ext), count in sorted(counter.items()):
        out.append({"migration": list(mig), "extension": list(ext), "count": count})
    return out


def canonical(a_deltas=None):
    """Known-pass arrangement: A block then B block, fixed numbering, snapshot in index order."""
    if a_deltas is None:
        a_frames = item_events("A", 0)
        a_done = done_item("A")
    else:
        d1, d2 = a_deltas
        a_frames = item_events("A", 0, d1, d2)
        a_done = done_item("A", d1, d2)
    return ([phase_frame("created", []), phase_frame("in_progress", [])]
            + a_frames + item_events("B", 1)
            + [phase_frame("completed", [a_done, done_item("B")])])


def build_report(gate, gate_sha):
    # ---------- P0 baseline sanity: canonical arrangement must pass ----------
    p0 = run_gate(gate, canonical())

    # ---------- enumeration: 3 schemes x 3432 interleavings ----------
    enumeration = {}
    comparisons = {}
    all_cells_match = True
    for scheme in ("s1", "s2", "s3"):
        cells, by_first, passed = enumerate_scheme(gate, scheme)
        enumeration[scheme] = {
            "denominator": DENOMINATOR,
            "gate_calls": DENOMINATOR,
            "total_pass": passed["A"] + passed["B"],
            "first_appeared_A": sum(by_first["A"].values()),
            "cells": cells_json(cells),
            "by_first": {f: {"pass": passed[f], "cells": cells_json(by_first[f])}
                         for f in ("A", "B")},
        }
        comp = {}
        for f in ("A", "B"):
            actual = {flat_cell(k): v for k, v in by_first[f].items()}
            expected = EXPECTED[(scheme, f)]
            actual_pass = passed[f]
            ok = (actual == expected) and (actual_pass == expected.get("(PASS)|(PASS)", 0))
            comp[f] = {
                "expected_cells": {k: v for k, v in sorted(expected.items())},
                "actual_cells": {k: v for k, v in sorted(actual.items())},
                "expected_pass": expected.get("(PASS)|(PASS)", 0),
                "actual_pass": actual_pass,
                "match": ok,
            }
            all_cells_match = all_cells_match and ok
        comparisons[scheme] = comp

    # ---------- true-negative controls + near-miss probes ----------
    checks = []

    def record(name, kind, expect_mig, expect_ext, frames, note):
        mig, ext = run_gate(gate, frames)
        checks.append({
            "name": name, "kind": kind, "note": note,
            "expected": {"migration": list(expect_mig), "extension": list(expect_ext)},
            "actual": {"migration": list(mig), "extension": list(ext)},
            "rejected": bool(mig),
            "match": (mig, ext) == (expect_mig, expect_ext),
        })

    record("P0-baseline", "probe", (), (),
           canonical(),
           "canonical A-block-then-B-block fixed numbering must pass before any perturbation")

    # N1: swap the item's two non-equal deltas
    f = canonical()
    f[4].obj["delta"], f[5].obj["delta"] = f[5].obj["delta"], f[4].obj["delta"]
    record("N1-non-equal-delta-swap", "negative-control", ("TEXT_DISAGREEMENT",), (), f,
           "A deltas AA1/AA0 vs declared text AA0AA1; B untouched")

    # N2a: transplant exactly one segment bound by identity — donor delta (B identity) into A window
    donor = Frame("response.output_text.delta",
                  {"type": "response.output_text.delta", "output_index": 1,
                   "item_id": "msg_bbb", "content_index": 0, "delta": "BB0"})
    record("N2a-transplant-donor-segment", "negative-control",
           ("ITEM_NOT_OPEN_OR_WRONG_ID",), (),
           canonical()[:5] + [donor] + canonical()[5:],
           "B-identity delta inserted after A's first delta; index 1 not open under A-only "
           "ledger. The gate short-circuits this frame and does not admit it into A's text "
           "ledger, so no TEXT_DISAGREEMENT/TEXT_KEY_COVERAGE follow — expectation scoped to "
           "this construction (the internal audit separately recorded that an author-side "
           "variant relabeling a real A delta yields the additional text labels; same gate "
           "mechanism, different construction)")

    # N2b: transplant one of the item's own segments (text.done moved before both deltas)
    f3 = canonical()
    seg = f3[6]
    del f3[6]
    f3.insert(4, seg)
    record("N2b-transplant-own-text-done", "negative-control",
           ("TEXT_AFTER_DONE_OR_DUPLICATE",), (), f3,
           "text.done arrives before deltas; text value still agrees — narrow near-miss")

    # N3: reverse the same-width snapshot whose entries satisfy local order
    record("N3-same-width-snapshot-reversal", "negative-control",
           ("SNAPSHOT_DISAGREEMENT",), (), canonical()[:-1]
           + [phase_frame("completed", [done_item("B"), done_item("A")])],
           "canonical baseline, completed output reversed; width preserved (2)")

    # P-equal: specificity boundary — swapping two EQUAL deltas must NOT be flagged
    f5 = canonical(a_deltas=("XX", "XX"))
    f5[4].obj["delta"], f5[5].obj["delta"] = f5[5].obj["delta"], f5[4].obj["delta"]
    record("P-equal-delta-swap", "probe", (), (), f5,
           "equal-delta swap is a no-op; true negative N1 must not generalize to equal deltas")

    # P1: minimal B-first near-miss — a valid position-preserving interleaving whose ONLY
    # difference from canonical is that B.added precedes A.added (internal orders preserved).
    f6 = ([phase_frame("created", []), phase_frame("in_progress", [])]
          + [item_events("B", 1)[0]]      # B.added (n=1) first
          + [item_events("A", 0)[0]]      # then A.added (n=0)
          + item_events("A", 0)[1:]       # A's remaining six segments, order preserved
          + item_events("B", 1)[1:]       # B's remaining six segments, order preserved
          + [phase_frame("completed", [done_item("A"), done_item("B")])])
    record("P1-minimal-B-first-added-order", "probe", ("ITEM_START",), (), f6,
           "valid interleaving: only the two output_item.added inverted; both internal "
           "orders preserved (member of the 1716 B-first set)")

    # P1b: naive in-place swap of the two added frames inside canonical — detaches A's
    # part/delta/done segments from A.added, so it VIOLATES A's internal order and is NOT
    # one of the 3432; documented near-miss showing why the B-first claim is scoped to
    # position-preserving interleavings only.
    f6b = canonical()
    f6b[2], f6b[9] = f6b[9], f6b[2]
    mig_b, ext_b = run_gate(gate, f6b)
    checks.append({
        "name": "P1b-in-place-added-swap-breaks-internal-order", "kind": "probe",
        "note": "NOT a position-preserving interleaving (A segments precede A.added). "
                "Naive 'swap the added events' yields more than ITEM_START: observed "
                "labels recorded verbatim; prereg B-first claim does not apply here.",
        "expected": {"rejected_only": True},
        "actual": {"migration": list(mig_b), "extension": list(ext_b)},
        "rejected": bool(mig_b),
        "match": bool(mig_b),
    })

    # P3: scheme-3 semantics — B-first renumbered to 0, A to 1, snapshot by new numbers
    f7 = ([phase_frame("created", []), phase_frame("in_progress", [])]
          + item_events("B", 0) + item_events("A", 1)
          + [phase_frame("completed", [done_item("B"), done_item("A")])])
    p3 = run_gate(gate, f7)
    checks.append({
        "name": "P3-s3-full-B-first-renumber", "kind": "probe",
        "note": "first-appearance renumber: msg_bbb->0, msg_aaa->1; passes but identity-index and "
                "final order changed vs s1 (different semantics, not pure equivalence)",
        "expected": {"migration": [], "extension": []},
        "actual": {"migration": list(p3[0]), "extension": list(p3[1])},
        "match": p3 == ((), ()),
        "index_remap": {"msg_bbb": 0, "msg_aaa": 1},
    })

    return {
        "status": "OK",
        "page": "响应双条目交错判定门-2026-11-28 公开派生复算",
        "derivation_note": "adapted from the independent non-author audit replay that passed "
                           "all prereg points on 2026-11-28; no internal receipts or author "
                           "run artifacts are read",
        "gate": {"repo_path": LIFECYCLE_REPO_REL, "sha256": gate_sha,
                 "pin_match": gate_sha == EXPECTED_GATE_SHA256},
        "construction": {
            "item_ids": ITEM_IDS,
            "deltas": BASE_DELTAS,
            "segments_per_item": SEGMENTS,
            "segment_order": ["output_item.added", "content_part.added", "output_text.delta",
                              "output_text.delta", "output_text.done", "content_part.done",
                              "output_item.done"],
            "phases": ["response.created", "response.in_progress", "response.completed"],
            "schemes": {"s1": "fixed index + snapshot in index order",
                        "s2": "fixed index + swapped snapshot order",
                        "s3": "first-appearance dynamic renumber, snapshot by new numbers"},
        },
        "denominators": {"interleavings_per_scheme": DENOMINATOR,
                         "schemes": 3,
                         "enumeration_gate_calls": 3 * DENOMINATOR,
                         "control_and_probe_gate_calls": len(checks)},
        "baseline_probe": {"migration": list(p0[0]), "extension": list(p0[1]),
                           "pass": p0 == ((), ())},
        "enumeration": enumeration,
        "expected_vs_actual": comparisons,
        "controls_and_probes": checks,
        "claims_checked": build_claims(enumeration, comparisons, checks),
        "all_expected_match": (p0 == ((), ())) and all_cells_match
                              and all(c["match"] for c in checks),
        "prereg_expectations_held": all(c["held"] for c in
                                        build_claims(enumeration, comparisons, checks)),
    }


def build_claims(enumeration, comparisons, checks):
    def cells_of(scheme, first):
        c = comparisons[scheme][first]["actual_cells"]
        return c

    c1 = (comparisons["s1"]["A"]["actual_pass"] == 1716
          and cells_of("s1", "A") == {"(PASS)|(PASS)": 1716})
    c2 = cells_of("s1", "B") == {"(ITEM_START)|(PASS)": 1716}
    c3 = cells_of("s2", "A") == {"(SNAPSHOT_DISAGREEMENT)|(PASS)": 1716}
    c4 = (enumeration["s3"]["total_pass"] == 3432
          and any(c["name"] == "P3-s3-full-B-first-renumber" and c["match"] for c in checks))
    c5 = all(c["rejected"] for c in checks if c["kind"] == "negative-control")
    return [
        {"claim_id": "C1", "held": c1,
         "claim": "prereg: under fixed numbering exactly the 1716 A-first interleavings pass"},
        {"claim_id": "C2", "held": c2,
         "claim": "prereg: every B-first fixed-numbering interleaving fails with ITEM_START "
                  "and nothing else (migration and extension)"},
        {"claim_id": "C3", "held": c3,
         "claim": "prereg: snapshot misorder is a separate cause — A-first with swapped "
                  "snapshot fails only SNAPSHOT_DISAGREEMENT"},
        {"claim_id": "C4", "held": c4,
         "claim": "prereg: first-appearance dynamic renumber passes all 3432 but is a "
                  "different semantics (index and final order change), not pure equivalence"},
        {"claim_id": "C5", "held": c5,
         "claim": "prereg: true-negative controls (non-equal delta swap / one-segment "
                  "transplant / same-width snapshot reversal) are rejected by the gate"},
    ]


def main():
    if not os.path.exists(LIFECYCLE_PATH):
        fail("BLOCKED", "pinned lifecycle.py not found at repo-relative path: "
                        + LIFECYCLE_REPO_REL + " (run from the public repo checkout)")
    gate_sha = sha256_file(LIFECYCLE_PATH)
    if gate_sha != EXPECTED_GATE_SHA256:
        fail("NOT_ADMITTED", "pinned lifecycle.py sha256 mismatch: got " + gate_sha)
    spec = importlib.util.spec_from_file_location("lifecycle_pinned", LIFECYCLE_PATH)
    if spec is None or spec.loader is None:
        fail("BLOCKED", "importlib could not create spec for pinned lifecycle.py")
    gate = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gate)
    if not hasattr(gate, "inspect"):
        fail("BLOCKED", "pinned module lacks inspect()")
    print(json.dumps(build_report(gate, gate_sha), ensure_ascii=False,
                     sort_keys=True, indent=1))


if __name__ == "__main__":
    main()
