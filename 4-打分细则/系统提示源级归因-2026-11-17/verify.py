#!/usr/bin/env python3
"""系统提示源级归因验证器（stdlib only）。

构建模式（私档）：从被 pin 的源文件快照按冻结规则重建 capture system，
与给定 system 逐字节比较，产出 evidence.json + result.json。
公开重放模式：只核封印一致性（节哈希/连接序/源 pin/槽声明/基线）。

CLI：
  python3 verify.py --system SYSTEM --sources DIR --build-evidence EV --output R
  python3 verify.py --evidence EV --output R
"""

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

SCHEMA = "sysprompt-source-attribution-evidence-v1"
BASELINE = "f16b61bc03bc56e8d9c160485524651663b7e627"
SYSTEM_SHA = "8e17c07c2a212f104dea010c0200c45a6b7a27682c91ed4bbc14827da059eb93"
SYSTEM_BYTES = 2593
MODEL = "glm-5.3-flash"
WORKFLOW_NAME = "workflow"
DELEGATES = ["subagent", "subagent_fork"]
BLOCKED_AFTER = "3"

SOURCES = {
    "system-prompt": {
        "path": "/dsh/node_modules/@deepseek-ai/dsh-system-prompt/lib/index.js",
        "sha256": "619c2f5d6291377e85eb2a682476ab5fa96a2c5e03230fbf0ed6c4d06fa704ac",
        "bytes": 19996,
    },
    "headless-patch": {
        "path": "/dsh/node_modules/@deepseek-ai/dsh-headless/cordis.patch.yml",
        "sha256": "dfc81e1e44e1080263ac24c86ff2dec5831676e9c5b76096e6bc7ecf6aa817a3",
        "bytes": 1571,
    },
    "tool-bash": {
        "path": "/dsh/node_modules/@deepseek-ai/dsh-tool-bash/lib/index.js",
        "sha256": "8fb836a65eb633f85aa8b1b079fb306866e597fe8f4987c2205b5c4482df57de",
        "bytes": 29281,
    },
    "tool-fs": {
        "path": "/dsh/node_modules/@deepseek-ai/dsh-tool-fs/lib/index.js",
        "sha256": "f27783bf0d89391ed775b65df47acb6b52adf526f4b9d849a0eeb3937a80d6c1",
        "bytes": 79425,
    },
    "tool-fs-search": {
        "path": "/dsh/node_modules/@deepseek-ai/dsh-tool-fs-search/lib/index.js",
        "sha256": "ef1b8212c8805e1ebc5f5cccf6e7c5dcd873dc0e19ad1e2d4b861c2c7fed15ac",
        "bytes": 55621,
    },
    "tool-jobs": {
        "path": "/dsh/node_modules/@deepseek-ai/dsh-tool-jobs/lib/index.js",
        "sha256": "a457e8f5d5d20f6dd917e75b578fb04452824e13560bf658c57ea654461fe6d8",
        "bytes": 20384,
    },
    "tool-goal": {
        "path": "/dsh/node_modules/@deepseek-ai/dsh-tool-goal/lib/index.js",
        "sha256": "f0504ff77f432c1c7359afbad53117290530eac5ba601eec800e93efbe0186d9",
        "bytes": 15968,
    },
    "tool-workflow": {
        "path": "/dsh/node_modules/@deepseek-ai/dsh-tool-workflow/lib/index.js",
        "sha256": "9d7ccb5238318aae82cbf6ae497f00c2b45e4afa29ed430c7b5c7e7e2cd409e4",
        "bytes": 17100,
    },
    "tool-subagent": {
        "path": "/dsh/node_modules/@deepseek-ai/dsh-tool-subagent/lib/index.js",
        "sha256": "13ae95219c99308fa85f543f66ba54ae0b5beb2940686958ff38df9a16a2a39f",
        "bytes": 28409,
    },
}

# 冻结的 13 节归因表：节号 -> (source key, kind)
SECTION_KINDS = [
    ("system-prompt", "static"),
    ("headless-patch", "template"),
    ("tool-bash", "static"),
    ("tool-fs", "static"),
    ("tool-fs", "concat"),
    ("tool-fs", "static"),
    ("tool-fs-search", "static"),
    ("tool-fs-search", "concat"),
    ("tool-jobs", "static"),
    ("tool-goal", "template"),
    ("tool-workflow", "template"),
    ("tool-subagent", "template"),
    ("tool-subagent", "embedded"),
]

SECTION_SLOTS = {
    2: ["{{model}}"],
    5: ["edit-registered"],
    8: ["read-registered"],
    10: ["blockedAfter"],
    11: ["${toolName}"],
    12: ["delegates"],
}

LIMITS = [
    "attributes only the current installed build (0.2.2-rc.3) and the headless capture profile assembly",
    "public replay checks sealed consistency only; byte-level rebuild runs against privately archived source snapshots",
    "proprietary source files are quoted only as short evaluation excerpts",
    "system sections are harness assembly, not a causal claim about model behavior or task results",
]


class Invalid(ValueError):
    pass


def require(cond, msg):
    if not cond:
        raise Invalid(msg)


def _pairs(pairs):
    out = {}
    for k, v in pairs:
        if k in out:
            raise Invalid("duplicate key: %s" % k)
        out[k] = v
    return out


def _reject_float(text):
    raise Invalid("non-finite number: %s" % text)


def loads(raw):
    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs, parse_constant=lambda c: (_ for _ in ()).throw(Invalid("non-finite constant: %s" % c)), parse_float=_reject_float)
    except UnicodeDecodeError as exc:
        raise Invalid("evidence is not utf-8") from exc


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _literal_around(text, anchor, quote='"'):
    i = text.find(anchor)
    require(i >= 0, "anchor not found in source: %s" % anchor[:40])
    start = text.rfind(quote, 0, i)
    require(start >= 0, "opening quote not found")
    end = text.find(quote, i)
    require(end > i, "closing quote not found")
    return text[start + 1:end]


def _js_unescape(body):
    return body.replace("\\n", "\n").replace("\\`", "`").replace("\\$", "$").replace("\\\\", "\\")


def rebuild_from_sources(sources_dir):
    """从源快照目录重建 12 个抽取段；返回 (segments, joined_bytes, slot_values)。"""
    d = Path(sources_dir)
    cache = {}

    def src(key):
        if key not in cache:
            p = d / (key + ".src")
            if not p.is_file():
                raise Invalid("source snapshot missing: %s" % p.name)
            blob = p.read_bytes()
            if sha(blob) != SOURCES[key]["sha256"]:
                raise Invalid("source snapshot sha mismatch: %s" % key)
            cache[key] = blob.decode("utf-8")
        return cache[key]

    sp = src("system-prompt")
    hp = src("headless-patch")
    tb = src("tool-bash")
    tf = src("tool-fs")
    tfs = src("tool-fs-search")
    tj = src("tool-jobs")
    tg = src("tool-goal")
    tw = src("tool-workflow")
    ts = src("tool-subagent")

    segments = []
    # 1 identity
    segments.append(_literal_around(sp, "You are an AI agent powered by DeepSeek Harness."))
    # 2 persona prefix（yml 折叠块整行）
    m = re.search(r"^\s*(You are a coding agent powered by the \{\{model\}\} model\.)$", hp, re.M)
    require(m, "persona prefix line not found")
    segments.append(m.group(1).replace("{{model}}", MODEL))
    # 3 bash
    segments.append(_literal_around(tb, "Check the [exit code: N] marker"))
    # 4 read
    segments.append(_literal_around(tf, "Use the read tool — not shell commands like cat"))
    # 5 write/edit concat
    i = tf.find("Read an existing file before overwriting")
    require(i >= 0, "write line anchor missing")
    m = re.search(r"(Read an existing file before overwriting it with write)\" \+ \(.*? : \"([^\"]+)\"\) \+ \"\.\"", tf[i:i + 400])
    require(m, "write concat pattern not matched")
    segments.append(m.group(1) + m.group(2) + ".")
    # 6 edit
    segments.append(_literal_around(tf, "Read a file before editing it unless"))
    # 7 glob
    segments.append(_literal_around(tfs, "Use the glob tool — not shell find"))
    # 8 grep concat
    i = tfs.find("Use the grep tool — not shell grep")
    require(i >= 0, "grep line anchor missing")
    m = re.search(r"(Use the grep tool — not shell grep or rg — to search file contents\.)\" \+ \(.*? : \"([^\"]+)\"\)", tfs[i:i + 420])
    require(m, "grep concat pattern not matched")
    segments.append(m.group(1) + m.group(2))
    # 9 jobs
    segments.append(_literal_around(tj, "Track every background job id"))
    # 10 goal template
    m = re.search(r"(create_goal may infer goal intent[^`]*?at least \$\{blockedAfter\} consecutive goal rounds[^`]*?not blocked\.)`", tg)
    require(m, "goal template not matched")
    segments.append(m.group(1).replace("${blockedAfter}", BLOCKED_AFTER))
    # 11 workflow template
    m = re.search(r"(Use the \$\{toolName\} tool ONLY when the user explicitly asks[^`]*?prefer plain subagent calls\.)`", tw)
    require(m, "workflow template not matched")
    segments.append(m.group(1).replace("${toolName}", WORKFLOW_NAME))
    # 12 subagent template（先槽替换后转义还原）
    m = re.search(r"(Start independent delegations with \$\{visible\.map\(\(name\) => `\\\`\$\{name\}\\\``\)\.join\(\" or \"\)\} together[^`]*?run relevant tests\.)`", ts)
    require(m, "subagent template not matched")
    body = m.group(1)
    joined = " or ".join("`" + n + "`" for n in DELEGATES)
    body = re.sub(r"\$\{visible\.map\(\(name\) => `\\\`\$\{name\}\\\``\)\.join\(\" or \"\)\}", joined, body)
    require("${visible" not in body, "subagent slot substitution failed")
    segments.append(_js_unescape(body))

    joined = "\n\n".join(segments).encode("utf-8")
    slot_values = {
        "{{model}}": MODEL,
        "${toolName}": WORKFLOW_NAME,
        "delegates": DELEGATES,
        "blockedAfter": BLOCKED_AFTER,
    }
    return segments, joined, slot_values


def section_records(segments):
    joined = "\n\n".join(segments).encode("utf-8")
    texts = joined.decode("utf-8").split("\n\n")
    require(len(texts) == len(SECTION_KINDS), "section count mismatch: %d" % len(texts))
    out = []
    for idx, text in enumerate(texts):
        key, kind = SECTION_KINDS[idx]
        rec = {
            "index": idx + 1,
            "sha256": sha(text.encode("utf-8")),
            "bytes": len(text.encode("utf-8")),
            "source": key,
            "kind": kind,
            "slots": SECTION_SLOTS.get(idx + 1, []),
            "text": text,
        }
        out.append(rec)
    return out, joined


def build(system_path, sources_dir):
    segments, joined, slot_values = rebuild_from_sources(sources_dir)
    system = Path(system_path).read_bytes()
    byte_equal = joined == system
    if not byte_equal:
        raise Invalid("rebuilt system does not match given system bytes")
    require(sha(system) == SYSTEM_SHA, "system sha mismatch vs frozen pin")
    records, joined2 = section_records(segments)
    evidence = {
        "schema": SCHEMA,
        "baseline": BASELINE,
        "system": {"sha256": sha(system), "bytes": len(system), "sections": len(records)},
        "sources": SOURCES,
        "sections": records,
        "slot_values": slot_values,
        "rebuild": {"byte_equal": True, "rebuilt_bytes": len(joined), "segments": len(segments)},
        "task_user_content_bytes": 0,
        "limits": LIMITS,
    }
    evidence_bytes = canonical(evidence) + b"\n"
    result = result_for(evidence, evidence_bytes)
    return evidence, evidence_bytes, result


def result_for(evidence, evidence_bytes):
    result = {
        "schema": SCHEMA,
        "baseline": evidence.get("baseline"),
        "verdict": "source_attributed_full",
        "system": evidence.get("system"),
        "attribution": {"sections": len(evidence.get("sections", [])), "unattributed": 0, "source_files": len(evidence.get("sources", {}))},
        "slot_values": evidence.get("slot_values"),
        "task_user_content_bytes": 0,
        "evidence_sha256": sha(evidence_bytes),
        "limits": LIMITS,
    }
    return result


def validate_public(evidence):
    require(isinstance(evidence, dict), "evidence must be an object")
    require(evidence.get("schema") == SCHEMA, "schema mismatch")
    require(evidence.get("baseline") == BASELINE, "baseline mismatch")
    sysrec = evidence.get("system")
    require(isinstance(sysrec, dict) and sysrec.get("sha256") == SYSTEM_SHA, "system sha pin mismatch")
    require(sysrec.get("bytes") == SYSTEM_BYTES, "system bytes pin mismatch")
    sections = evidence.get("sections")
    require(isinstance(sections, list) and len(sections) == len(SECTION_KINDS), "section count mismatch")
    for idx, rec in enumerate(sections):
        require(isinstance(rec, dict), "section record must be object")
        require(rec.get("index") == idx + 1, "section index mismatch at %d" % (idx + 1))
        text = rec.get("text")
        require(isinstance(text, str), "section text must be string")
        digest = sha(text.encode("utf-8"))
        require(rec.get("sha256") == digest, "section sha mismatch at %d" % (idx + 1))
        require(rec.get("bytes") == len(text.encode("utf-8")), "section bytes mismatch at %d" % (idx + 1))
        key, kind = SECTION_KINDS[idx]
        require(rec.get("source") == key, "section source mapping mismatch at %d" % (idx + 1))
        require(rec.get("kind") == kind, "section kind mapping mismatch at %d" % (idx + 1))
        require(rec.get("slots") == SECTION_SLOTS.get(idx + 1, []), "section slots mismatch at %d" % (idx + 1))
    sources = evidence.get("sources")
    require(isinstance(sources, dict) and set(sources.keys()) == set(SOURCES.keys()), "sources table mismatch")
    for k, v in SOURCES.items():
        got = sources[k]
        require(isinstance(got, dict) and got.get("sha256") == v["sha256"] and got.get("bytes") == v["bytes"] and got.get("path") == v["path"], "source pin mismatch: %s" % k)
    joined = "\n\n".join(r["text"] for r in sections).encode("utf-8")
    require(sha(joined) == SYSTEM_SHA, "sections do not join to pinned system sha")
    require(evidence.get("task_user_content_bytes") == 0, "task_user_content_bytes must be 0")
    rebuild = evidence.get("rebuild")
    require(isinstance(rebuild, dict) and rebuild.get("byte_equal") is True, "rebuild.byte_equal must be true")
    require(isinstance(evidence.get("limits"), list) and evidence["limits"] == LIMITS, "limits must match frozen list")


def exclusive(path, raw):
    p = Path(path)
    if p.exists():
        raise Invalid("output path already exists: %s" % p.name)
    if any(part == ".." for part in p.parts):
        raise Invalid("output path must not contain ..")
    if not p.parent.is_dir():
        raise Invalid("output parent directory does not exist: %s" % p.parent)
    with open(p, "xb") as fh:
        fh.write(raw)


def main(argv=None):
    parser = argparse.ArgumentParser(description="system prompt source attribution verifier")
    parser.add_argument("--system")
    parser.add_argument("--sources")
    parser.add_argument("--build-evidence")
    parser.add_argument("--evidence")
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    try:
        if args.evidence:
            require(args.system is None and args.sources is None and args.build_evidence is None, "replay mode takes only --evidence and --output")
            evidence_bytes = Path(args.evidence).read_bytes()
            evidence = loads(evidence_bytes)
            validate_public(evidence)
            result = result_for(evidence, evidence_bytes)
        else:
            require(args.system and args.sources and args.build_evidence, "build mode needs --system, --sources and --build-evidence")
            evidence, evidence_bytes, result = build(args.system, args.sources)
            exclusive(args.build_evidence, evidence_bytes)
        exclusive(args.output, canonical(result) + b"\n")
        if args.evidence:
            print("sysprompt attribution replay OK: sections=%d sources=%d" % (len(evidence.get("sections", [])), len(evidence.get("sources", {}))))
        else:
            print("sysprompt attribution rebuild OK: byte_equal=true sections=%d sources=%d" % (len(evidence.get("sections", [])), len(evidence.get("sources", {}))))
        return 0
    except Invalid as exc:
        print("input or output failure", file=sys.stderr)
        return 2
    except OSError:
        print("input or output failure", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
