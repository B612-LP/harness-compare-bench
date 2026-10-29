#!/usr/bin/env python3
"""Stdlib-only, read-only historical intake; deterministic, fail-closed report builder.
No private-home fallback, model calls, checker execution or historical writes.
"""
import argparse
import copy
import datetime as dt
import hashlib
import json
import re
from urllib.parse import urlsplit
from pathlib import Path

RULE = "freeze-20261029-v3"
BASE = "4-打分细则/可信冻结-2026-10-29-v3"
OUT = "5-评测报告/可信冻结-2026-10-29-v3"
LEDGER = "5-评测报告/运行总账-2026-10-24.json"
CATEGORIES = ("product_run", "self_test", "offline_recompute", "grading_regression", "bare_model_probe", "interface_preflight")
CASES = ("bird-ca-schools-15", "dabstep-payments-10", "exercism-py-6", "lcb-recent-hard-4", "tb-cargo-plan")
PRODUCTS = ("codex", "dsh", "workbuddy", "yuanbao", "doubao")
SCORE_TOTALS = dict(zip(CASES, (15, 10, 6, 4, 27)))
FACTS = ("case_version", "product_version", "model", "route", "tools", "permissions", "skills", "started_at", "finished_at", "evidence_grade", "final_adjudication", "rule_version", "checker_sha256", "truth_sha256", "case_sha256")
GATES = ("rules_frozen", "case_valid", "scoring_reviewable", "evidence_valid", "contamination_free")
SAFE_POLICY = {"first": "first_registered", "replacement": "invalid_only_next_registered_max_1", "repeat": "all_registered_no_best", "retry": "infrastructure_only_max_1", "unknown": "no_zero_no_rescale", "dab2697": "not_capability_attribution", "mixed_group_ranking": False}
HASH = re.compile(r"^[0-9a-f]{64}$")


class Invalid(ValueError):
    pass


def dump(x):
    return json.dumps(x, ensure_ascii=False, indent=2, allow_nan=False) + "\n"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def load(p):
    # Reject duplicate JSON keys, NaN, Infinity: parser must not silently accept ambiguity.
    def pairs(items):
        d = {}
        for k, v in items:
            if k in d:
                raise Invalid("duplicate JSON key: " + k)
            d[k] = v
        return d
    return json.loads(Path(p).read_text(encoding="utf-8"), object_pairs_hook=pairs,
                      parse_constant=lambda s: (_ for _ in ()).throw(Invalid(s)))


def public_path(root, path):
    if not isinstance(path, str) or not path or Path(path).is_absolute() or ".." in Path(path).parts:
        raise Invalid("non-public relative path: " + str(path))
    p = (root / path).resolve()
    if not p.is_relative_to(root.resolve()):
        raise Invalid("path escapes root: " + path)
    return p


def pin(root, path):
    p = public_path(root, path)
    return {"path": path, "sha256": digest(p.read_bytes())}


def snapshot_case(root, case):
    root = root.resolve()
    directory = public_path(root, "2-用例/" + case)
    fixed = [directory / n for n in ("instruction.md", "spec.md", "case.json", "truth.json", "checker.py", "trusted_runner.py") if (directory / n).is_file()]
    files = fixed + sorted(p for p in (directory / "inputs").rglob("*") if p.is_file())
    tree = {str(p.relative_to(directory)): digest(public_path(root, str(p.relative_to(root))).read_bytes()) for p in files}
    sha = digest(json.dumps(tree, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8"))
    return {"checker.py": tree["checker.py"], "truth.json": tree["truth.json"], "instruction.md": tree["instruction.md"], "manifest_sha256": sha, "case_version": case + "@sha256:" + sha, "files": tree}


def pointer(value, ptr):
    if ptr == "":
        return value
    if not isinstance(ptr, str) or not ptr.startswith("/"):
        raise Invalid("invalid JSON pointer")
    for part in ptr[1:].split("/"):
        part = part.replace("~1", "/").replace("~0", "~")
        value = value[int(part)] if isinstance(value, list) else value[part]
    return value


def leaves(value, prefix=""):
    if isinstance(value, dict) and value:
        for k, v in value.items():
            yield from leaves(v, prefix + "/" + k.replace("~", "~0").replace("/", "~1"))
    elif isinstance(value, list) and value:
        for i, v in enumerate(value):
            yield from leaves(v, prefix + "/" + str(i))
    else:
        yield {"pointer": prefix, "value": value}


def fact(value=None, source=0, ptr="", state=None):
    return {"state": state or ("unknown" if value is None else "known"), "value": value,
            "refs": [] if value is None else [{"source": source, "pointer": ptr}]}


def stamp(value):
    if not isinstance(value, str):
        raise Invalid("timestamp not string")
    t = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if t.tzinfo is None:
        raise Invalid("timestamp must have timezone")
    return t


def audit_source(root, s, source_map):
    if not isinstance(s, dict) or set(s) != {"path", "sha256"} or not HASH.fullmatch(str(s.get("sha256", ""))):
        raise Invalid("malformed source: " + str(s))
    mapped = source_map.get(s["path"], s["path"])
    p = public_path(root, mapped)
    result = dict(s, resolved_path=mapped)
    if not p.is_file():
        result.update(status="external_not_packaged" if s["path"].startswith("bench-automation/") else "missing", actual_sha256=None)
    else:
        actual = digest(p.read_bytes())
        result.update(status="verified" if actual == s["sha256"] else "hash_drift", actual_sha256=actual)
    return result


def validate_fact(f, sources, root, source_map, name):
    if not isinstance(f, dict) or set(f) != {"state", "value", "refs"} or f["state"] not in ("known", "supplemented", "unknown"):
        raise Invalid("bad fact: " + name)
    if f["state"] == "unknown":
        if f["value"] is not None or f["refs"]:
            raise Invalid("unknown must be null, not guessed: " + name)
        return
    if f["value"] is None or not isinstance(f["refs"], list) or not f["refs"]:
        raise Invalid("known fact needs value and refs: " + name)
    for ref in f["refs"]:
        if set(ref) != {"source", "pointer"} or type(ref["source"]) is not int or not 0 <= ref["source"] < len(sources):
            raise Invalid("invalid ref: " + name)
        s = sources[ref["source"]]
        a = audit_source(root, s, source_map)
        if a["status"] != "verified":
            raise Invalid("unreviewable source: " + name)
        try:
            v = pointer(load(public_path(root, a["resolved_path"])), ref["pointer"])
        except (ValueError, KeyError, IndexError, TypeError) as e:
            raise Invalid("unresolvable fact ref: " + name) from e
        if type(v) is not type(f["value"]) or v != f["value"]:
            raise Invalid("ref does not substantiate value: " + name)


def validate_issues(issues):
    if not isinstance(issues, list):
        raise Invalid("issues not list")
    ids = set()
    for i in issues:
        needed = {"id", "knowledge_status", "investigation_status", "confound_status", "impact", "next_step", "stop_condition", "reopen_condition", "refs"}
        if not isinstance(i, dict) or not needed.issubset(i) or set(i) - needed - {"unknown_fields"} or not all(i.get(k) for k in ("id", "impact", "next_step", "stop_condition", "reopen_condition", "refs")):
            raise Invalid("incomplete issue management")
        if i["id"] in ids:
            raise Invalid("duplicate issue ID")
        ids.add(i["id"])
        if i["knowledge_status"] not in ("unknown", "accepted_limitation", "resolved") or i["investigation_status"] not in ("open", "stopped", "closed") or i["confound_status"] not in ("not_excluded", "excluded", "not_applicable"):
            raise Invalid("issue axes conflated")
        if i["knowledge_status"] == "unknown" and i["confound_status"] == "excluded":
            raise Invalid("unknown cannot claim confound excluded")


def validate_event(e, root, source_map):
    keys = {"event_id", "identity", "category", "product", "group", "experiment", "case_id", "facts", "gates", "score", "selection", "sources", "issues", "collected_at", "original_time"}
    if not isinstance(e, dict) or set(e) != keys:
        raise Invalid("event fields mismatch: " + str(set(e) ^ keys))
    if not isinstance(e["event_id"], str) or not e["event_id"] or e["category"] not in CATEGORIES or type(e["experiment"]) is not bool:
        raise Invalid("bad event identity/category")
    if e["group"] not in ("A_same_model", "B_native", "research", "not_applicable"):
        raise Invalid("bad group")
    stamp(e["collected_at"])
    if not e["sources"]:
        raise Invalid("event requires locatable source")
    for s in e["sources"]:
        if audit_source(root, s, source_map)["status"] != "verified":
            raise Invalid("imported source must be packaged and hash-verified")
    validate_fact(e["identity"], e["sources"], root, source_map, "identity")
    ident = e["identity"]["value"]
    if not isinstance(ident, dict) or set(ident) != {"event_id", "run_id", "category", "product", "group", "experiment", "case_id"} or not isinstance(ident["run_id"], str) or not ident["run_id"]:
        raise Invalid("original run identity missing")
    if any(ident[k] != e[k] or type(ident[k]) is not type(e[k]) for k in ident if k != "run_id"):
        raise Invalid("identity does not bind top-level product/group/variant")
    if any(re.search(r"(?:ablation|codex-gpt|[/-]skill|work01)", s["path"], re.I) for s in e["sources"]) and not e["experiment"]:
        raise Invalid("known research source cannot impersonate official product")
    for container in ("facts", "gates"):
        if not isinstance(e[container], dict):
            raise Invalid("facts/gates not object")
        for k, v in e[container].items():
            validate_fact(v, e["sources"], root, source_map, container + "." + k)
    validate_fact(e["score"], e["sources"], root, source_map, "score")
    validate_fact(e["original_time"], e["sources"], root, source_map, "original_time")
    validate_issues(e["issues"])
    unknowns = {container + "." + k for container in ("facts", "gates") for k, v in e[container].items() if v["state"] == "unknown"}
    unknowns.update(k for k in ("score", "original_time") if e[k]["state"] == "unknown")
    covered = set()
    for i in e["issues"]:
        fields = i.get("unknown_fields", [])
        if not isinstance(fields, list) or not all(isinstance(k, str) for k in fields):
            raise Invalid("issue unknown_fields must be string paths")
        covered.update(fields)
    if unknowns - covered:
        raise Invalid("unknown without managed issue: " + ",".join(sorted(unknowns - covered)))
    for issue in e["issues"]:
        for ref in issue["refs"]:
            if set(ref) != {"source", "pointer"} or type(ref["source"]) is not int or not 0 <= ref["source"] < len(e["sources"]):
                raise Invalid("bad issue ref")
            s = e["sources"][ref["source"]]
            try:
                pointer(load(public_path(root, source_map.get(s["path"], s["path"]))), ref["pointer"])
            except (ValueError, KeyError, IndexError, TypeError) as ex:
                raise Invalid("unresolvable issue ref") from ex
    if e["category"] == "product_run":
        if set(e["facts"]) != set(FACTS) or set(e["gates"]) != set(GATES):
            raise Invalid("product event requires complete fact/gate slots (unknown allowed)")
    route = e["facts"].get("route", fact())
    if route["state"] != "unknown":
        rv = route["value"]
        if not isinstance(rv, dict) or set(rv) != {"host", "provider_id", "wire_protocol", "endpoint"} or not isinstance(rv["host"], str) or not rv["host"] or any(rv[k] is not None and not isinstance(rv[k], str) for k in ("provider_id", "wire_protocol", "endpoint")):
            raise Invalid("route must disclose host/provider_id/wire_protocol/endpoint")
        if rv["endpoint"] is not None and (urlsplit(rv["endpoint"]).scheme != "https" or urlsplit(rv["endpoint"]).hostname != rv["host"]):
            raise Invalid("route host contradicts endpoint")
    sc = e["score"]["value"]
    if sc is not None:
        if not isinstance(sc, dict) or set(sc) != {"earned", "possible", "assessed", "reported", "reward", "rule_version", "checker_sha256"}:
            raise Invalid("score schema mismatch")
        if not all(type(sc[k]) in (int, float) for k in ("earned", "possible", "assessed", "reported")) or not 0 <= sc["earned"] <= sc["assessed"] <= sc["possible"] or sc["possible"] <= 0:
            raise Invalid("invalid score denominator")
        expected = round(100 * sc["earned"] / sc["possible"], 8)
        if abs(sc["reported"] - expected) > 0.005:
            raise Invalid("score rescaled against assessed subset")
        if sc["reward"] not in (None, 0, 1) or (sc["assessed"] < sc["possible"] and sc["reward"] is not None):
            raise Invalid("partial assessment cannot invent binary verdict")
        if not sc["rule_version"] or not HASH.fullmatch(str(sc["checker_sha256"])):
            raise Invalid("score missing rule/hash")
    sel = e["selection"]
    sk = {"plan_id", "slot_id", "order", "kind", "parent_id", "reason", "registered_at", "plan_source", "plan_pointer"}
    if sel is not None:
        if not isinstance(sel, dict) or set(sel) != sk or type(sel["order"]) is not int or sel["order"] < 1 or sel["kind"] not in ("first", "replacement", "repeat", "retry"):
            raise Invalid("bad selection registration")
        stamp(sel["registered_at"])
        if type(sel["plan_source"]) is not int or not 0 <= sel["plan_source"] < len(e["sources"]):
            raise Invalid("bad plan source")
        s = e["sources"][sel["plan_source"]]
        registration = pointer(load(public_path(root, source_map.get(s["path"], s["path"]))), sel["plan_pointer"])
        if registration != {"event_id": e["event_id"], **{k: v for k, v in sel.items() if k not in ("plan_source", "plan_pointer")}}:
            raise Invalid("selection differs from source preregistration")
        start = e["facts"].get("started_at", {}).get("value")
        if start is not None and stamp(sel["registered_at"]) >= stamp(start):
            raise Invalid("outcome-based/late registration")


def select_events(events):
    """Validate the entire declared queue; never sort by reward or choose best."""
    ids = [e["event_id"] for e in events]
    if len(ids) != len(set(ids)):
        raise Invalid("duplicate event ID")
    run_ids = [e["raw"]["run_id"] if e.get("historical") else e["identity"]["value"]["run_id"] for e in events]
    if len(run_ids) != len(set(run_ids)):
        raise Invalid("duplicate original run_id under different event IDs")
    queues = {}
    by_id = {e["event_id"]: e for e in events}
    for e in events:
        s = e.get("selection")
        if s:
            key = (s["plan_id"], s["slot_id"])
            queues.setdefault(key, []).append(e)
    for q in queues.values():
        q.sort(key=lambda x: x["selection"]["order"])
        if [e["selection"]["order"] for e in q] != list(range(1, len(q) + 1)):
            raise Invalid("selection queue gap/duplicate order")
        if len({(e["product"], e["group"], e["experiment"], e["case_id"]) for e in q}) != 1:
            raise Invalid("selection queue crosses treatment/product/case")
        retries = 0
        replacements = 0
        for n, e in enumerate(q):
            s = e["selection"]
            if n == 0:
                if s["kind"] != "first" or s["parent_id"] is not None:
                    raise Invalid("queue must start at first")
                continue
            parent = by_id.get(s["parent_id"])
            if parent is not q[n - 1]:
                raise Invalid("retry/replacement must point to preceding registered attempt")
            if s["kind"] == "first":
                raise Invalid("second first")
            if s["kind"] == "retry":
                retries += 1
                if retries > 1 or s["reason"] not in ("transport_error", "startup_error", "tool_infrastructure_error"):
                    raise Invalid("retry result sampling / exceeded cap")
                if parent["facts"].get("final_adjudication", {}).get("value") != "infrastructure_invalid":
                    raise Invalid("retry after score-visible/product result")
            if s["kind"] == "replacement":
                replacements += 1
                if replacements > 1:
                    raise Invalid("replacement cap exceeded; stop rather than sample until success")
                if s["reason"] not in ("contamination", "case_invalid", "evidence_invalid") or parent["facts"].get("final_adjudication", {}).get("value") not in ("invalid", "suspect"):
                    raise Invalid("replacement of valid or unknown attempt")
    return queues


def validate_plan_completeness(events, root, source_map):
    """Every registered attempt in a referenced public plan must be imported, even losers."""
    planned = {}
    actual = {}
    for e in events:
        s = e.get("selection")
        if not s:
            continue
        source = e["sources"][s["plan_source"]]
        ptr = s["plan_pointer"]
        parent = ptr.rsplit("/", 1)[0]
        data = load(public_path(root, source_map.get(source["path"], source["path"])))
        registrations = pointer(data, parent)
        if not isinstance(registrations, list):
            raise Invalid("plan must expose complete registrations array")
        entries = [r for r in registrations if r.get("plan_id") == s["plan_id"]]
        expected = {r["event_id"] for r in entries}
        if len(expected) != len(entries):
            raise Invalid("duplicate ID in preregistered plan")
        key = s["plan_id"]
        if key in planned and planned[key] != expected:
            raise Invalid("plan ID reused with conflicting registrations")
        planned[key] = expected
        actual.setdefault(key, set()).add(e["event_id"])
    if planned != actual:
        raise Invalid("omitted registered attempt / retry outcome sampling")


def reasons(e, config):
    r = []
    if e.get("historical"):
        r.append("historical_not_prospectively_frozen")
        if e["raw"].get("websearch_policy_annotation", {}).get("verdict") == "不纳入":
            r.append("historical_policy_review_excluded_despite_raw_verdict")
    if e["category"] != "product_run":
        r.append("not_product_run")
    if e["experiment"] or e["group"] == "research":
        r.append("research_variant_not_official_product")
    if e["group"] == "A_same_model" and e["product"] not in ("codex", "dsh", "workbuddy"):
        r.append("group_product_mismatch")
    if e["group"] == "B_native" and e["product"] not in ("yuanbao", "doubao"):
        r.append("group_product_mismatch")
    if e["group"] not in ("A_same_model", "B_native"):
        r.append("not_comparison_group")
    if e["case_id"] not in CASES:
        r.append("case_not_frozen")
    for k in FACTS:
        f = e["facts"].get(k, fact())
        if f["state"] == "unknown":
            r.append("unknown:" + k)
    for k in GATES:
        f = e["gates"].get(k, fact())
        if f["state"] == "unknown" or f["value"] is not True or not f["refs"]:
            r.append("gate:" + k)
    if any(s["status"] != "verified" for s in e.get("source_audit", [])):
        r.append("source_unavailable_or_drift")
    if e["score"]["state"] == "unknown":
        r.append("no_reviewable_score")
    elif e["score"]["value"].get("assessed") != e["score"]["value"].get("possible"):
        r.append("score_incomplete_no_rescale")
    if e["selection"] is None:
        r.append("no_prospective_selection_registration")
    elif e["selection"]["kind"] in ("repeat", "retry"):
        r.append("repeat_or_retry_diagnostic_not_primary")
    if e["facts"].get("final_adjudication", {}).get("value") != "valid":
        r.append("final_adjudication_not_valid")
    if e["facts"].get("rule_version", {}).get("value") != RULE:
        r.append("rule_version_not_frozen")
    case_pins = config["case_snapshots"].get(e["case_id"], {})
    if e["facts"].get("case_version", {}).get("value") != case_pins.get("case_version"):
        r.append("case_version_identity_mismatch")
    sel = e["selection"]
    slot_key = e["group"] + "|" + e["product"] + "|" + e["case_id"]
    slot = config["official_slots"].get(slot_key)
    if not slot or not sel or slot != {"plan_id": sel["plan_id"], "slot_id": sel["slot_id"], "plan_sha256": e["sources"][sel["plan_source"]]["sha256"]}:
        r.append("not_canonical_official_slot")
    for field, key in (("checker_sha256", "checker.py"), ("truth_sha256", "truth.json"), ("case_sha256", "manifest_sha256")):
        if e["facts"].get(field, {}).get("value") != case_pins.get(key):
            r.append("version_not_frozen:" + field)
    if e["group"] == "A_same_model" and e["facts"].get("model", {}).get("value") != config["a_model"]:
        r.append("same_model_not_proven")
    route = e["facts"].get("route", {}).get("value")
    if e["group"] == "A_same_model" and (not isinstance(route, dict) or route.get("host") != config["a_route_host"]):
        r.append("official_upstream_route_not_proven")
    for k in ("started_at", "finished_at"):
        try:
            stamp(e["facts"].get(k, {}).get("value"))
        except (ValueError, TypeError):
            r.append("invalid_time:" + k)
    try:
        start = stamp(e["facts"]["started_at"]["value"])
        end = stamp(e["facts"]["finished_at"]["value"])
        if start < stamp(config["effective_at"]) or end < start:
            r.append("not_in_freeze_period_or_time_reversed")
    except (ValueError, TypeError, KeyError):
        pass
    sc = e["score"]["value"]
    if sc and sc.get("possible") != SCORE_TOTALS.get(e["case_id"]):
        r.append("score_denominator_not_full_case_contract")
    if sc and (sc.get("rule_version") != RULE or sc.get("checker_sha256") != case_pins.get("checker.py")):
        r.append("score_receipt_rule_or_checker_mismatch")
    if any(i["confound_status"] == "not_excluded" for i in e["issues"]):
        r.append("confounds_not_excluded")
    return sorted(set(r))


def historical_events(root, config, source_map):
    ledger = load(root / LEDGER)
    if len(ledger["runs"]) != 96:
        raise Invalid("expected frozen 96 historical rows")
    ledger_pin = pin(root, LEDGER)
    result, audits = [], []
    aliases = {"case_version": ("case_version", "task_version"), "product_version": ("product_version", "app_version"), "model": ("model",), "route": ("route",), "tools": ("tools",), "permissions": ("permissions",), "skills": ("skills", "skill_state"), "started_at": ("started_at", "started"), "finished_at": ("ended_at", "finished_at", "finished"), "evidence_grade": (), "final_adjudication": ()}
    for i, raw in enumerate(ledger["runs"]):
        refs = [ledger_pin] + copy.deepcopy(raw.get("sources", []))
        a = [audit_source(root, s, source_map) for s in refs]
        if any(s["status"] == "hash_drift" for s in a):
            raise Invalid("historical source hash drift: " + raw["run_id"])
        fields = {f: fact() for f in FACTS}
        orig = raw.get("original_fields", {})
        for f, names in aliases.items():
            for name in names:
                if name in orig and orig[name] is not None:
                    fields[f] = fact(orig[name], ptr=f"/runs/{i}/original_fields/{name}")
                    break
        for f, name in (("evidence_grade", "evidence_grade"), ("final_adjudication", "adjudication")):
            if raw.get(name) is not None:
                fields[f] = fact(raw[name], ptr=f"/runs/{i}/{name}")
        experiment = "ablation" in raw["batch"] or "work01" in raw["batch"] or raw["role"] == "exploratory-probe"
        group = "research" if experiment or raw["product"] == "bare" else ("B_native" if raw["product"] in ("doubao", "yuanbao") else "A_same_model")
        e = {"event_id": "history:" + raw["run_id"], "identity": fact(), "original_run_identity": fact(raw["run_id"], ptr=f"/runs/{i}/run_id"), "category": "bare_model_probe" if raw["product"] == "bare" else "product_run", "product": raw["product"], "group": group, "experiment": experiment, "case_id": raw["case"], "facts": fields, "gates": {k: fact() for k in GATES}, "score": fact(), "selection": None, "sources": refs, "source_audit": a, "issues": [], "collected_at": config["collected_at"], "original_time": fields["started_at"], "historical": True, "raw": raw, "ledger_pointer": f"/runs/{i}", "raw_score": {"reward": raw.get("raw_reward"), "weighted": raw.get("raw_weighted"), "refs": [{"source": 0, "pointer": f"/runs/{i}/raw_weighted"}]}, "attribution_exclusions": ["DAB2697"] if raw["case"] == "dabstep-payments-10" else []}
        for key, f in fields.items():
            if isinstance(f["value"], str) and (f["value"].strip().lower().startswith("unknown") or "记 unknown" in f["value"]):
                fields[key] = fact()
        if not isinstance(fields["route"]["value"], dict) or set(fields["route"]["value"]) != {"host", "provider_id", "wire_protocol", "endpoint"}:
            fields["route"] = fact()  # endpoint alone remains raw partial evidence, never invented provider/route.
        e["original_time"] = fields["started_at"]
        unknown_paths = ["facts." + k for k, v in fields.items() if v["state"] == "unknown"] + ["gates." + k for k in GATES] + ["identity", "score"]
        if e["original_time"]["state"] == "unknown":
            unknown_paths.append("original_time")
        for key in unknown_paths:
            e["issues"].append({"id": "missing:" + key, "unknown_fields": [key], "knowledge_status": "unknown", "investigation_status": "stopped", "confound_status": "not_excluded", "impact": key + " lacks contemporaneous, independently verifiable freeze evidence; blocks formal admission, not a product failure", "next_step": "request independently dated original receipt; retain limited historical observation until found", "stop_condition": "no original receipt in frozen public intake; do not backfill current configuration", "reopen_condition": "new independently dated original receipt becomes available", "refs": [{"source": 0, "pointer": f"/runs/{i}"}]})
        if raw["case"] == "dabstep-payments-10":
            policy_path = "5-评测报告/未知登记.json"
            policy = load(root / policy_path)
            policy_index = next(n for n, x in enumerate(policy["unknowns"]) if x["id"] == "dab-q2697-adjudicated")
            policy_source = len(e["sources"])
            e["sources"].append(pin(root, policy_path))
            e["source_audit"].append(audit_source(root, e["sources"][-1], source_map))
            e["issues"].append({"id": "DAB2697", "knowledge_status": "accepted_limitation", "investigation_status": "stopped", "confound_status": "not_excluded", "impact": "official-compatible score retained, q2697 must not support capability attribution", "next_step": "await official clarification, corrected task or new independent evidence", "stop_condition": "stop investigation pending new evidence; stopping does not exclude confound", "reopen_condition": "official clarification, corrected task or new independent evidence", "refs": [{"source": policy_source, "pointer": f"/unknowns/{policy_index}"}]})
        # Preserve every original field and every supplied source; no inferred clean, version or timing.
        audits.append({"event_id": e["event_id"], "source": ledger_pin, "ledger_pointer": e["ledger_pointer"], "original_fields": list(leaves(orig)), "all_row_fields": list(raw), "source_audit": a[1:1 + len(raw.get("sources", []))]})
        result.append(e)
    return result, audits


def lock_drifts(root, lock):
    """v3: contract 漂移=硬错误（exit≠0）；live_doc 漂移=报告列表（exit=0，还原+旁挂）。"""
    contract_errors, live_drifts = [], []
    for s in lock["pins"]:
        if not isinstance(s, dict) or not {"path", "sha256"} <= set(s) or set(s) - {"path", "sha256", "pin_class"}:
            raise Invalid("bad pin: " + str(s))
        if s.get("pin_class", "contract") not in ("contract", "live_doc"):
            raise Invalid("bad pin_class: " + str(s["path"]))
        sealed = {"path": s["path"], "sha256": s["sha256"]}
        try:
            drifted = pin(root, s["path"]) != sealed
            actual = digest(public_path(root, s["path"]).read_bytes())
        except OSError:
            drifted, actual = True, None
        if drifted:
            if s.get("pin_class") == "live_doc":
                live_drifts.append({"path": s["path"], "sealed_sha256": s["sha256"], "actual_sha256": actual})
            else:
                contract_errors.append("sealed file drift: " + s["path"])
    return contract_errors, live_drifts


def verify_seal(root):
    lock = load(root / BASE / "freeze.lock.json")
    if set(lock) != {"rule_version", "pins", "trust_boundary"} or lock["rule_version"] != RULE:
        raise Invalid("bad lock")
    contract_errors, live_drifts = lock_drifts(root, lock)
    for e in contract_errors:
        raise Invalid(e)
    c = load(root / BASE / "config.json")
    if set(c) != {"schema_version", "rule_version", "effective_at", "collected_at", "a_model", "a_route_host", "policy", "case_snapshots", "official_slots", "historical_ledger", "work_registry"} or c["schema_version"] != 1 or c["rule_version"] != RULE or c["policy"] != SAFE_POLICY or c["a_route_host"] != "api.deepseek.com" or c["a_model"] != "deepseek-flash":
        raise Invalid("unsafe/unknown config schema or policy")
    stamp(c["effective_at"])
    stamp(c["collected_at"])
    for s in (c["historical_ledger"], c["work_registry"]):
        if pin(root, s["path"]) != s:
            raise Invalid("input source hash drift: " + s["path"])
    if set(c["case_snapshots"]) != set(CASES) or not isinstance(c["official_slots"], dict):
        raise Invalid("missing case manifest or official slots")
    for key, slot in c["official_slots"].items():
        if len(key.split("|")) != 3 or set(slot) != {"plan_id", "slot_id", "plan_sha256"} or not HASH.fullmatch(str(slot["plan_sha256"])):
            raise Invalid("bad canonical official slot")
    for case, files in c["case_snapshots"].items():
        if snapshot_case(root, case) != files:
            raise Invalid("full case manifest drift (not historical version proof): " + case)
    return c, live_drifts


def work_events(root, config, source_map):
    registry = load(root / config["work_registry"]["path"])
    events = []
    for x in registry["events"]:
        if set(x) != {"event_id", "category", "source", "locator", "description"} or x["category"] not in CATEGORIES or x["category"] == "product_run":
            raise Invalid("bad work registry event")
        a = audit_source(root, x["source"], source_map)
        if a["status"] == "hash_drift":
            raise Invalid("work receipt drift")
        raw_time = None
        raw_support = []
        collection = registry["coverage"]["cutoff"]
        if a["status"] == "verified":
            p = public_path(root, a["resolved_path"])
            try:
                receipt = load(p)
                if isinstance(receipt, dict):
                    raw_time = {k: receipt[k] for k in ("started_at", "finished_at", "generated_at", "date") if k in receipt} or None
                    collection = receipt.get("collected_at", collection)
                    for source in receipt.get("raw_sources", []):
                        checked = audit_source(root, source, source_map)
                        if checked["status"] != "verified":
                            raise Invalid("work raw receipt drift")
                        raw_support.append(checked)
            except (UnicodeError, json.JSONDecodeError):
                time_lines = [line for line in p.read_text(encoding="utf-8").splitlines() if "运行时间" in line]
                raw_time = {"verbatim_time_lines": time_lines} if time_lines else None
        events.append({"event_id": x["event_id"], "category": x["category"], "source": x["source"], "source_audit": a, "supporting_source_audit": raw_support, "locator": x["locator"], "description": x["description"], "original_time": raw_time, "collected_at": collection, "timing_note": "raw receipt fields preserved; generated_at/date are not necessarily execution time; no inference from filename"})
    return events, registry["coverage"]


def build(root, imports=(), source_map=None):
    source_map = source_map or {}
    config, live_drifts = verify_seal(root)
    hist, audit = historical_events(root, config, source_map)
    works, coverage = work_events(root, config, source_map)
    new = []
    input_pins = []
    for name in imports:
        rel = str(Path(name))
        d = load(public_path(root, rel))
        if set(d) != {"schema_version", "events"} or d["schema_version"] != 1:
            raise Invalid("bad import envelope")
        input_pins.append(pin(root, rel))
        for e in d["events"]:
            validate_event(e, root, source_map)
            e = copy.deepcopy(e)
            e["source_audit"] = [audit_source(root, s, source_map) for s in e["sources"]]
            e["attribution_exclusions"] = ["DAB2697"] if e["case_id"] == "dabstep-payments-10" else []
            new.append(e)
    select_events(hist + new)
    validate_plan_completeness(new, root, source_map)
    all_ids = [e["event_id"] for e in hist + new + works]
    if len(all_ids) != len(set(all_ids)):
        raise Invalid("duplicate event ID across work ledgers")
    official = {"A_same_model": [], "B_native": []}
    rejected = []
    for e in hist + new:
        rr = reasons(e, config)
        e["admission"] = {"eligible": not rr, "reasons": rr}
        if rr:
            rejected.append({"event_id": e["event_id"], "reasons": rr})
        else:
            official[e["group"]].append(e["event_id"])
    # Archived offline score observations are NEVER relabelled 'current checker' results.
    replay_path = "5-评测报告/复算/2026-10-24/results.json"
    replays = load(root / replay_path)
    replay_source = pin(root, replay_path)
    replay_by_id = {x["run_id"].removeprefix("3-表现现场/"): (i, x) for i, x in enumerate(replays["runs"])}
    later_path = "4-打分细则/判卷回归/replay-all-results.json"
    later = load(root / later_path)
    later_source = pin(root, later_path)
    later_by_id = {x["run_id"]: (i, x) for i, x in enumerate(later["rows"])}
    cells = []
    for product in PRODUCTS:
        for case in CASES:
            candidates = []
            for e in hist:
                if e["product"] != product or e["case_id"] != case or e["experiment"]:
                    continue
                raw = e["raw"]
                rp = replay_by_id.get(raw["run_id"])
                later_rp = later_by_id.get(raw["run_id"])
                score_sources = [s for s in e["source_audit"][1:] if re.search(r"(checker|judge|result)", s["path"], re.I)]
                version_fields = [f for f in leaves(raw.get("original_fields", {})) if re.search(r"(version|sha256)", f["pointer"], re.I)]
                candidates.append({"event_id": e["event_id"], "raw_score": e["raw_score"], "historical_adjudication": raw.get("adjudication"), "historical_integrity": raw.get("integrity_verdict"), "later_policy_annotation": raw.get("websearch_policy_annotation"), "raw_verdict_is_not_current_policy": True, "archived_recompute_2026_10_27": {"source": later_source, "pointer": "/rows/" + str(later_rp[0]), "status": later_rp[1].get("status"), "replay": later_rp[1].get("replay"), "skip_reason": later_rp[1].get("skip_reason"), "provenance_limitation": "archived result only; original script can use private fallback; not a new clean-public replay"} if later_rp else None, "raw_rule_version_fields": version_fields, "score_receipts": score_sources, "sources": e["source_audit"][1:], "archived_recompute": {"reward": rp[1].get("reward"), "weighted": rp[1].get("weighted"), "status": rp[1].get("status"), "checker_version": rp[1].get("checker_version"), "checker_snapshot": replays["versions"].get(case), "source": replay_source, "pointer": "/runs/" + str(rp[0])} if rp else None, "current_recompute": None, "current_recompute_reason": "not_executed_by_archive_builder; see separately identified public replay receipt", "formal_rejection_reasons": e["admission"]["reasons"]})
            cells.append({"group": "B_native" if product in ("yuanbao", "doubao") else "A_same_model", "product": product, "case_id": case, "candidates": candidates, "selection": "none; historical candidates listed in original ledger order, no retroactive best-pick"})
    counts = {c: sum(e["category"] == c for e in hist + new + works) for c in CATEGORIES}
    source_counts = {}
    for e in audit:
        for s in e["source_audit"]:
            source_counts[s["status"]] = source_counts.get(s["status"], 0) + 1
    summary = {"rule_version": RULE, "collected_at": config["collected_at"], "live_doc_drift": live_drifts, "historical_rows": len(hist), "historical_original_sources": sum(len(e["raw"].get("sources", [])) for e in hist), "source_counts": source_counts, "registered_counts_not_all_time_totals": counts, "official_counts": {k: len(v) for k, v in official.items()}, "historical_cells": len(cells), "coverage": coverage, "import_pins": input_pins, "source_map": source_map, "no_cross_group_ranking": True, "current_config_hash_is_not_historical_version": True}
    ledgers = {c: [e for e in hist + new + works if e["category"] == c] for c in CATEGORIES}
    return {"summary.json": summary, "archive.json": {"schema_version": 1, "historical_metadata": {k:v for k,v in load(root / LEDGER).items() if k != "runs"}, "events": hist + new}, "field-source-audit.json": audit, "six-ledgers.json": ledgers, "official-main-table.json": {"rule_version": RULE, "groups": official, "rejected": rejected, "ranking": None}, "historical-25-cells.json": cells, "historical-25-cells.md": render_cells(cells), "unknown-limitations.json": {"policy": "knowledge, investigation and confound axes independent; stopping is not resolution; refs locate source, machine does not adjudicate causal semantics", "events": [{"event_id": e["event_id"], "sources": e["sources"], "issues": e["issues"]} for e in hist + new if e["issues"]]}, "summary.md": render_summary(summary)}


def render_cells(cells):
    lines = ["# 25格有限历史观察（非正式排名）", "", "原分、10-24归档复算、10-27归档复算、本轮新复算严格分开；unknown不是0，也不代表不可复算。候选按原账顺序全列，不选最高分。规则/评分收据完整SHA与全部拒绝理由见同名JSON；当前checker快照不能证明历史版本一致。DAB2697一律不作能力归因。原V/clean仅是raw字段，不是现行裁定：特别r1031已被后续检索复核排除（关联会话有直接检索证据），旧50分留档不回写。10-27复算为既存归档结果，其原脚本可用私有fallback，不冒认本轮公开干净重跑。", ""]
    for group in ("A_same_model", "B_native"):
        lines += ["## " + group, "", "| 产品 / 用例 | 历史候选（唯一ID：原weighted / 10-24归档weighted / 10-27归档weighted / 本轮复算）及后续口径 | 正式准入 |", "|---|---|---|"]
        for cell in cells:
            if cell["group"] != group:
                continue
            parts = []
            for c in cell["candidates"]:
                rp = c["archived_recompute"]
                late = c['archived_recompute_2026_10_27']
                late_score = late.get('replay', {}).get('weighted') if late and late.get('replay') else None
                annotation = c.get('later_policy_annotation') or {}
                policy_note = '；后续口径=' + str(annotation.get('verdict')) if annotation else ''
                parts.append(f"`{c['event_id']}`：{c['raw_score']['weighted']} / {rp['weighted'] if rp and rp['weighted'] is not None else 'unknown'} / {late_score if late_score is not None else 'unknown'} / unknown；raw原{c['historical_adjudication']}/{c['historical_integrity']}{policy_note}")
            lines.append(f"| {cell['product']} / {cell['case_id']} | " + "<br>".join(parts) + " | 拒绝：未前瞻冻结；其他逐项原因见JSON |")
        lines.append("")
    return "\n".join(lines) + "\n"


def render_summary(s):
    return "# 冻结档案收据\n\n" + f"历史原账 {s['historical_rows']} 行，原sources {s['historical_original_sources']} 条；正式 A={s['official_counts']['A_same_model']}，B={s['official_counts']['B_native']}。25格历史全列，不等于新标准正式准入。\n\n" + "六类已登记事件（不是全仓检查项/历史完整总数）：\n\n" + "\n".join(f"- {k}: {v}" for k, v in s["registered_counts_not_all_time_totals"].items()) + "\n\n历史来源状态：" + json.dumps(s["source_counts"], ensure_ascii=False) + "。external_not_packaged仅说明公开包不可得，不声称原件不存在。\n\n历史自测/复算/回归只登记有独立可定位收据的调用事件；脚本存在、断言数、题数不计运行；空类不代表历史从未做过。\n"


def save_outputs(root, outputs, output_dir=OUT):
    out = public_path(root, output_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths = []
    for name, value in outputs.items():
        path = out / name
        path.write_text(value if isinstance(value, str) else dump(value), encoding="utf-8")
        paths.append(pin(root, str(path.relative_to(root))))
    (out / "output-manifest.json").write_text(dump({"rule_version": RULE, "files": paths}), encoding="utf-8")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("action", choices=("build", "verify", "validate-import"))
    p.add_argument("--root", default=".")
    p.add_argument("--imports", action="append", default=[])
    p.add_argument("--source-map")
    p.add_argument("--output-dir", default=OUT)
    a = p.parse_args()
    root = Path(a.root).resolve()
    try:
        sm = load(public_path(root, a.source_map)) if a.source_map else {}
        recipe_path = public_path(root, a.output_dir) / "build-recipe.json"
        if a.action == "verify" and not a.imports and recipe_path.is_file():
            recipe = load(recipe_path)
            for s in recipe["imports"]:
                if pin(root, s["path"]) != s:
                    raise Invalid("import source hash drift")
            a.imports = [s["path"] for s in recipe["imports"]]
            sm = recipe["source_map"]
        expected = build(root, a.imports, sm)
        expected["build-recipe.json"] = {"imports": [pin(root, n) for n in a.imports], "source_map": sm}
        if a.action == "build":
            save_outputs(root, expected, a.output_dir)
        elif a.action == "verify":
            for name, value in expected.items():
                actual = (public_path(root, a.output_dir) / name).read_text(encoding="utf-8")
                if actual != (value if isinstance(value, str) else dump(value)):
                    raise Invalid("generated output drift: " + name)
            manifest = load(public_path(root, a.output_dir) / "output-manifest.json")
            if manifest != {"rule_version": RULE, "files": [pin(root, a.output_dir + "/" + n) for n in expected]}:
                raise Invalid("output manifest drift")
        print(dump({"ok": True, "action": a.action, "summary": expected["summary.json"]}), end="")
    except (Invalid, OSError, ValueError, KeyError, TypeError) as e:
        print(dump({"ok": False, "error": str(e)}), end="")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
