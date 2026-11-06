#!/usr/bin/env python3
"""Offline observation/mirror checks, not legal or origin authentication."""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import stat

EX = "6105f6d9d3ef66ce3d5c8f529d2882af3d76b706"
TB = "73d6279f91eb773bd51af2e2572a6fa044342e7a"
DAB = "22a0bb5708f36d0ccda1355be1868c07050cc7e2"
EX_RAW = "https://raw.githubusercontent.com/exercism/python/" + EX
TB_RAW = "https://raw.githubusercontent.com/harbor-framework/terminal-bench/" + TB
DAB_RAW = "https://huggingface.co/datasets/adyen/DABstep/raw/" + DAB
MIRRORS = {
    "exercism-MIT.txt": (1065, 21, "e52f804e74f0fbd34e8927962319df346166b8194094309a0aee318693df44df"),
    "terminal-bench-Apache-2.0.txt": (11357, 201, "c71d239df91726fc519c6eb72d318ec65820627232b2f796219e87dcf35d0ab4"),
    "dabstep-NOTICE.txt": (321, 1, "f8a83b510da6dfffb2fab959cb8a48f05dec344e76338cff7cd5da36b50eec22"),
}
# Exact observed facts are trusted constants, not a caller-supplied seal.
# source, start/end UTC clock, URL, HTTP-or-None, exit, bytes, SHA, outcome
CAPTURES = {
    "bird-home": ("bird", "14:42:17", "14:42:18", "https://bird-bench.github.io/", 200, 0, 350031, "9701c60f487025c551f391a0e130434702e7bcfe4385a22a4a1bf9b343cdf03c", "source_body"),
    "dab-card": ("dabstep", "14:42:18", "14:42:19", "https://huggingface.co/datasets/adyen/DABstep/raw/main/README.md", 200, 0, 1306, "f690b8e6951014f6f9fbe0a9dca52e92517b64ffbd624d2aa3bec728c22d6e53", "source_body"),
    "atcoder-terms": ("atcoder", "14:42:19", "14:42:19", "https://atcoder.jp/tos", 200, 0, 16463, "c4ab1c413629bc6c91a3dad454bac4d7ece79407cb47b02904a86fde3157d7b5", "source_body"),
    "exercism-license": ("exercism", "14:42:19", "14:42:20", EX_RAW + "/LICENSE", 200, 0, 1065, MIRRORS["exercism-MIT.txt"][2], "source_body"),
    "terminal-license": ("terminal-bench", "14:42:20", "14:42:20", TB_RAW + "/LICENSE", 200, 0, 11357, MIRRORS["terminal-bench-Apache-2.0.txt"][2], "source_body"),
    "exercism-tree": ("exercism", "14:43:47", "14:43:52", "https://api.github.com/repos/exercism/python/git/trees/eba3ee9349c498b66be7880780225790bf272a4d", None, 35, 0, None, "tls_no_response"),
    "terminal-tree": ("terminal-bench", "14:43:52", "14:43:53", "https://api.github.com/repos/harbor-framework/terminal-bench/git/trees/4a3a3f7e2f593847385a642da961d3e79f64cf9f", 403, 0, 279, "af5589ff3db2feb151e02a29471c2895f03df7a27de9816f4781ceb94b827b23", "api_rate_limit"),
    "terminal-task": ("terminal-bench", "14:43:53", "14:43:53", "https://api.github.com/repos/harbor-framework/terminal-bench/contents/tasks/cargo-flight-dispatch?ref=" + TB, 403, 0, 279, "af5589ff3db2feb151e02a29471c2895f03df7a27de9816f4781ceb94b827b23", "api_rate_limit"),
    "dab-tree": ("dabstep", "14:43:53", "14:43:54", "https://huggingface.co/api/datasets/adyen/DABstep/tree/" + DAB, 200, 0, 479, "d3e080372611a7442330de46c8577255db62055df9e64c518466a7a3c0272c51", "top_level_listing_only"),
    "dab-license": ("dabstep", "14:44:56", "14:44:56", DAB_RAW + "/LICENSE", 200, 0, 321, MIRRORS["dabstep-NOTICE.txt"][2], "source_body"),
    "terminal-notice": ("terminal-bench", "14:44:57", "14:44:57", TB_RAW + "/NOTICE", 404, 0, 14, "d5558cd419c8d46bdc958064cb97f963d1ea793866414c025906ec15033512ed", "exact_root_notice_path_unavailable"),
    "exercism-notice": ("exercism", "14:44:57", "14:44:58", EX_RAW + "/NOTICE", 404, 0, 14, "d5558cd419c8d46bdc958064cb97f963d1ea793866414c025906ec15033512ed", "exact_root_notice_path_unavailable"),
}
# capture, canonical URL, version kind/value, evidence kind, excerpt, summary,
# mirror filename, public-full-body, full-legal-text
FACTS = {
    "bird": ("bird-home", "https://bird-bench.github.io/", "response_metadata_not_immutable_commit", "Last-Modified: Thu, 29 Oct 2026 14:32:10 GMT; news: 2024-04-27", "license_declaration_excerpt", "we now modify the license of our data to CC BY-SA 4.0", "官方新闻声明数据改用CC BY-SA 4.0；这是声明节录，不是完整CC法律正文，也未建立与旧数据库发行的适用绑定。", None, False, False),
    "dabstep": ("dab-license", "https://huggingface.co/datasets/adyen/DABstep", "commit", DAB, "complete_copyright_license_notice_not_cc_legalcode", "", "保存完整上游具名notice原文件；文件虽名为LICENSE，仅有版权/许可声明与CC BY 4.0链接，并非完整CC法律正文。数据集声明不自动覆盖Space或scorer代码。", "dabstep-NOTICE.txt", True, False),
    "exercism": ("exercism-license", "https://github.com/exercism/python", "commit", EX, "complete_mit_license", "", "完整MIT正文保留Copyright (c) 2021 Exercism、通知保留条件与免责。该当前commit不证明本机历史打包来源版本，不覆盖Aider或problem-specifications。", "exercism-MIT.txt", True, True),
    "atcoder": ("atcoder-terms", "https://atcoder.jp/tos", "page_revision_label_not_immutable_commit", "English Terms of Use; revision label: June 29, 2026", "service_terms_excerpt_not_reuse_grant", "All rights (ownership, intellectual property rights, portrait rights, publicity rights and the like)", "当前英文条款称服务素材权利归AtCoder或有关权利人；此短引文和摘要不是本仓题面/测试复用授权，也不构成对历史适用性的法律意见。", None, False, False),
    "terminal-bench": ("terminal-license", "https://github.com/harbor-framework/terminal-bench", "commit", TB, "complete_apache_2_0_license", "", "完整Apache2正文包含副本、修改说明、保留通知及若含NOTICE时的条件；附录版权字段保持模板原文，不替项目填版权人，不证明旧Cargo任务通知全链。", "terminal-bench-Apache-2.0.txt", True, True),
}
BOUNDARIES = {
    "current_observation": "retrieved_documents_not_historical_clearance",
    "historical_material_applicability": {"status": "unknown", "bound_version": None},
    "notice_coverage": {"status": "unknown", "recursive_and_space_complete": False},
    "original_owner_license": {"status": "not_selected", "value": None, "authority": "repository_owner"},
    "new_license_granted": False,
    "legal_compliance_certified": False,
    "all_five_full_terms_public_offline": False,
    "lcb_repo_mit_grants_atcoder_material_rights": False,
    "dataset_license_clears_space_scorer": False,
    "copyright_holder_chain_authenticated": False,
    "historical_scores_gold_n_changed": False,
}


def need(condition, message):
    if not condition:
        raise ValueError(message)


def finite_json(value):
    """Reject non-JSON types and finite-overflow floats, recursively."""
    if type(value) is float:
        need(math.isfinite(value), "nonfinite number")
    elif type(value) is list:
        for item in value:
            finite_json(item)
    elif type(value) is dict:
        for key, item in value.items():
            need(type(key) is str, "nonstring key")
            finite_json(item)
    else:
        need(type(value) in (str, int, bool, type(None)), "non-JSON value")


def same(value, expected):
    """Type-exact comparison: bools cannot stand in for integers."""
    need(type(value) is type(expected), "wrong type")
    if type(expected) is dict:
        need(value.keys() == expected.keys(), "wrong keys")
        for key in expected:
            same(value[key], expected[key])
    elif type(expected) is list:
        need(len(value) == len(expected), "wrong list length")
        for left, right in zip(value, expected):
            same(left, right)
    else:
        need(value == expected, "different observed fact or boundary")


def strict_json(text):
    def pairs(items):
        result = {}
        for key, value in items:
            need(key not in result, "duplicate JSON key")
            result[key] = value
        return result

    def reject_constant(value):
        raise ValueError("nonfinite JSON constant: " + value)

    value = json.loads(text, object_pairs_hook=pairs, parse_constant=reject_constant)
    finite_json(value)
    return value


def keyed(rows, expected_ids):
    need(type(rows) is list, "expected rows list")
    found = {}
    for row in rows:
        need(type(row) is dict and type(row.get("id")) is str, "row identity")
        need(row["id"] not in found, "duplicate row identity")
        found[row["id"]] = row
    need(found.keys() == expected_ids.keys(), "missing or unknown identities")
    return found


def validate_document(document):
    """Pure documentary contract; does not read files or consult a hash seal."""
    finite_json(document)
    need(type(document) is dict, "expected document")
    need(set(document) == {"schema", "observation_date", "observations", "captures", "service_fetch_errors", "boundaries"}, "document keys")
    same(document["schema"], "current-upstream-terms-observation-v1")
    same(document["observation_date"], "2026-11-05")
    same(document["boundaries"], BOUNDARIES)
    same(document["service_fetch_errors"], {"count": 3, "reported_http_status": 404, "layer": "fetch_service_not_origin", "source_http_status_known": False})
    captures = keyed(document["captures"], CAPTURES)
    fields = ("source", "start_utc", "end_utc", "url", "http_status", "curl_exit", "bytes", "sha256", "outcome")
    for identity, fact in CAPTURES.items():
        values = list(fact)
        values[1:3] = ["2026-11-05T" + clock + "Z" for clock in values[1:3]]
        expected = dict(zip(fields, values))
        expected["id"] = identity
        same(captures[identity], expected)
    observations = keyed(document["observations"], FACTS)
    fields = ("capture_id", "canonical_url", "version_kind", "version", "evidence_kind", "excerpt", "summary", "mirror", "full_body_public", "full_legal_text")
    for identity, fact in FACTS.items():
        expected = dict(zip(fields, fact))
        expected["id"] = identity
        same(observations[identity], expected)
        event = captures[observations[identity]["capture_id"]]
        need(event["source"] == identity and event["http_status"] == 200, "observation not source success")
    statuses = [row["http_status"] for row in captures.values()]
    same([statuses.count(200), statuses.count(403), statuses.count(404), statuses.count(None)], [7, 2, 2, 1])
    return {"sources": 5, "captures": 12, "http_200": 7, "http_403": 2, "http_404": 2, "tls_without_http": 1, "public_complete_bodies": 3, "all_five_full_terms_public_offline": False, "historical_applicability": "unknown", "notice_coverage": "unknown", "original_owner_license": "not_selected", "new_license_granted": False, "legal_compliance_certified": False}


def validate_mirror_content(name, text):
    """Content conditions independent of byte SHA checks, not a legal parser."""
    need(name in MIRRORS and type(text) is str, "unknown mirror or nontext")
    need("\r" not in text and "\x00" not in text and not text.startswith("\ufeff"), "modified text representation")
    need(len(text.splitlines()) == MIRRORS[name][1], "mirror line count")
    if name == "exercism-MIT.txt":
        for phrase in ("MIT License", "Copyright (c) 2021 Exercism", "The above copyright notice and this permission notice shall be included in all", "THE SOFTWARE IS PROVIDED \"AS IS\"", "SOFTWARE."):
            need(phrase in text, "MIT condition or copyright missing")
    elif name == "terminal-bench-Apache-2.0.txt":
        for phrase in ("Version 2.0, January 2004", "(a) You must give any other recipients", "(b) You must cause any modified files", "(c) You must retain, in the Source form", '(d) If the Work includes a "NOTICE"', "Copyright [yyyy] [name of copyright owner]", "END OF TERMS AND CONDITIONS"):
            need(phrase in text, "Apache condition or template missing")
    else:
        for phrase in ("© 2025", "Alexander David Egg", "Martin Iglesias Goyanes", "Andreu Mora", "Friso H. Kingma", "Thomas Wolf", "Leandro Von Werra", "https://creativecommons.org/licenses/by/4.0/"):
            need(phrase in text, "DAB notice author or link missing")
        need("is licensed under Creative Commons Attribution 4.0 International." in text, "DAB notice classification")


def safe_file(root, name):
    root = Path(root).absolute()
    need(".." not in root.parts, "parent traversal in root")
    for parent in (root,) + tuple(root.parents):
        need(not parent.is_symlink(), "symlink root or ancestor")
    need(root.is_dir(), "missing package directory")
    need(type(name) is str and name in ("observations.json",) + tuple(MIRRORS), "unapproved filename")
    path = root / name
    need(stat.S_ISREG(path.lstat().st_mode), "not a regular nonsymlink file")
    return path


def read_snapshot(root):
    result = {}
    for name in ("observations.json",) + tuple(MIRRORS):
        path = safe_file(root, name)
        need(path.stat().st_size <= 262144, "file size limit")
        with path.open("rb") as stream:
            raw = stream.read(262145)
        need(len(raw) <= 262144, "file grew beyond limit")
        result[name] = raw
    return result


def derive(root):
    before = read_snapshot(root)
    summary = validate_document(strict_json(before["observations.json"].decode("utf-8")))
    for name, (size, lines, digest) in MIRRORS.items():
        raw = before[name]
        validate_mirror_content(name, raw.decode("utf-8"))
        need(len(raw) == size and len(raw.splitlines()) == lines, "mirror byte/line size")
        need(hashlib.sha256(raw).hexdigest() == digest, "mirror source SHA mismatch")
    after = read_snapshot(root)
    need(before == after, "source changed during verification")
    return {"ok": True, "summary": summary, "checked_sha256": {name: hashlib.sha256(raw).hexdigest() for name, raw in before.items()}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).absolute().parent, help="directory containing observations.json and three mirrors")
    args = parser.parse_args()
    try:
        result = derive(args.root)
    except (ValueError, OSError, UnicodeError, RecursionError) as error:
        print(json.dumps({"ok": False, "error": str(error)}, ensure_ascii=False, allow_nan=False))
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
