#!/usr/bin/env python3
"""环21：Codex 环境生成层（input[2]）行级对照。公开档只含行号/字节数/sha/分类，无任何行值。
双模式 fail-closed；--output 必须新文件。stdlib only。"""
import hashlib, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
BASELINE = "7986effb2befe7a08a0d1a3769b6480cdc0ac1ec"
SCHEMA = "codex-envlayer-linelevel-evidence-v1"
README_SHA256 = hashlib.sha256(open(os.path.join(HERE, "README.md"), "rb").read()).hexdigest()
RUNS = [
    ("loop14/capture-codex-r1", "A", "codex"),
    ("loop15/codex-t3-r1", "B", "codex"),
]
REQ1_SHA = {
    "loop14/capture-codex-r1": "6a156cdb57c908fc385076e840ef281ca6f75573b5881af10fbeda73fa08ced9",
    "loop15/codex-t3-r1": "2cf01fa3bb3c8b437926d7cdae9abac17f1e04062dba75ed6189e6c19b26ae7c",
}
ROOT_RE = re.compile(r"<root>(.*?)</root>", re.S)


def die():
    print("input or output failure")
    sys.exit(2)


def _reject(_):
    raise ValueError("non-finite")


def loads(raw):
    try:
        return json.loads(raw.decode("utf-8"), parse_constant=_reject, parse_float=_reject)
    except Exception:
        die()


def no_dup(pairs):
    seen = set()
    for k, _ in pairs:
        if k in seen:
            die()
        seen.add(k)
    return dict(pairs)


def sha_text(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def env_layer(body, rel):
    try:
        inp = body["input"]
        item = inp[2]
    except Exception:
        die()
    if not isinstance(item, dict) or item.get("role") != "user":
        die()
    content = item.get("content")
    if not isinstance(content, list) or len(content) != 1:
        die()
    part = content[0]
    if not isinstance(part, dict) or part.get("type") != "input_text":
        die()
    text = part.get("text")
    if not isinstance(text, str):
        die()
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]  # 尾换行不产生空行叶
    rows = []
    for i, line in enumerate(lines, 1):
        flag = bool(ROOT_RE.search(line))
        rows.append({"line": i, "type": "str", "bytes": len(line.encode("utf-8")),
                     "sha256": sha_text(line), "root_path_like": flag})
    return rows


def build(archive_root):
    data = {}
    for rel, side, kind in RUNS:
        p = os.path.join(archive_root, rel, "requests", "001.request.bin")
        try:
            raw = open(p, "rb").read()
        except Exception:
            die()
        if hashlib.sha256(raw).hexdigest() != REQ1_SHA[rel]:
            die()
        data[rel] = {"side": side, "lines": env_layer(loads(raw), rel)}
    la, lb = data[RUNS[0][0]]["lines"], data[RUNS[1][0]]["lines"]
    if len(la) != len(lb):
        die()
    same = diff = pathlike = 0
    for x, y in zip(la, lb):
        cls = "identical" if (x["sha256"] == y["sha256"] and x["bytes"] == y["bytes"]) else "differs"
        x["classification"] = cls
        y["classification"] = cls
        if cls == "identical":
            same += 1
        else:
            diff += 1
        if x["root_path_like"] or y["root_path_like"]:
            pathlike += 1
    verdict = "env_line_%d_%d_%d_%d" % (same, diff, pathlike, len(la))
    ev = {
        "schema": SCHEMA,
        "baseline_commit": BASELINE,
        "readme_sha256": README_SHA256,
        "runs": {rel: {"side": data[rel]["side"], "req1_sha256": REQ1_SHA[rel], "lines": data[rel]["lines"]} for rel, _, _ in RUNS},
        "line_count": len(la),
    }
    res = {
        "schema": SCHEMA,
        "evidence_sha256": hashlib.sha256(json.dumps(ev, ensure_ascii=False, indent=1).encode() + b"\n").hexdigest(),
        "verdict": verdict,
        "endpoints": {"E1_lines": len(la), "E2_identical": same, "E2_differs": diff,
                      "E5_root_path_like_lines": pathlike,
                      "differs_at_lines": [x["line"] for x, y in zip(la, lb) if x["classification"] == "differs"]},
        "limits": ["line-level only; no line values published", "single task face / single codex version",
                   "root_path_like is a tag-scoped flag, not a field-level parser"],
    }
    return ev, res


def validate_public(ev, readme_sha):
    try:
        if ev.get("schema") != SCHEMA or ev.get("baseline_commit") != BASELINE:
            die()
        if ev.get("readme_sha256") != readme_sha:
            die()
        if set(ev.get("runs", {})) != {r[0] for r in RUNS}:
            die()
        if ev.get("line_count") != FROZEN_LINE_COUNT:
            die()
        for rel, side, _ in RUNS:
            row = ev["runs"][rel]
            if row.get("side") != side or row.get("req1_sha256") != REQ1_SHA[rel]:
                die()
            lines = row.get("lines")
            if not isinstance(lines, list) or len(lines) != FROZEN_LINE_COUNT:
                die()
            frozen = FROZEN_LINES[rel]
            for k, (ln, tp, by, sh, fl, cl) in enumerate(frozen):
                got = lines[k]
                if not isinstance(got, dict):
                    die()
                if (got.get("line"), got.get("type"), got.get("bytes"), got.get("sha256"),
                        got.get("root_path_like"), got.get("classification")) != (ln, tp, by, sh, fl, cl):
                    die()
                if not (isinstance(got.get("sha256"), str) and len(got["sha256"]) == 64
                        and all(c in "0123456789abcdef" for c in got["sha256"])):
                    die()
    except SystemExit:
        raise
    except Exception:
        die()


def dump(path, value):
    if os.path.exists(path) or os.path.isdir(os.path.dirname(os.path.abspath(path))) is False:
        die()
    if os.path.realpath(path) == os.path.realpath(HERE):
        die()
    try:
        with open(path, "x") as f:
            f.write(json.dumps(value, ensure_ascii=False, indent=1) + "\n")
    except Exception:
        die()


FROZEN_LINE_COUNT = 7
FROZEN_LINES = {
    "loop14/capture-codex-r1": [[1, "str", 21, "70ed17e44b5b131e925d139dfe9fef505496d8f4e5d43b5fc3f3c55ea6226f37", False, "identical"], [2, "str", 55, "e0c682510549d8f327176737924b15164d9365d553204ee268474cf0603ecce4", False, "differs"], [3, "str", 20, "44cfdfa5ff4d30e1e95e7f2155084b0a41246a8a0642bd9e097f2c1eafd65fc9", False, "identical"], [4, "str", 41, "fb5a99a0c68cfcd43556420648832a1bae9df43b3a8a271379edba47fc5a42d1", False, "identical"], [5, "str", 36, "054958a53307cbe8c168ecfb842a2bd6c0431e2aef40e0352cd56ebae4775baa", False, "identical"], [6, "str", 209, "4c34ff2ab11b72918f732386bdf826818e1083faabda039878a5c00caa19a397", True, "differs"], [7, "str", 22, "bd956c2ad24394e71988845b0683dcd791fb0f8e25470dcd31967c0bafb7250f", False, "identical"]],
    "loop15/codex-t3-r1": [[1, "str", 21, "70ed17e44b5b131e925d139dfe9fef505496d8f4e5d43b5fc3f3c55ea6226f37", False, "identical"], [2, "str", 55, "7b7cddfea4cfee0b7cfa94c66a30a2a582ece608343d654d98b1d3b4540ad6ae", False, "differs"], [3, "str", 20, "44cfdfa5ff4d30e1e95e7f2155084b0a41246a8a0642bd9e097f2c1eafd65fc9", False, "identical"], [4, "str", 41, "fb5a99a0c68cfcd43556420648832a1bae9df43b3a8a271379edba47fc5a42d1", False, "identical"], [5, "str", 36, "054958a53307cbe8c168ecfb842a2bd6c0431e2aef40e0352cd56ebae4775baa", False, "identical"], [6, "str", 209, "6f3c443296df07d4321c19ac2bf9493c0a78c9e05b0bfd0069223d03b946850e", True, "differs"], [7, "str", 22, "bd956c2ad24394e71988845b0683dcd791fb0f8e25470dcd31967c0bafb7250f", False, "identical"]],
}
FROZEN_LINES = {k: [tuple(x) for x in rows] for k, rows in FROZEN_LINES.items()}


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    root = "."
    archive_root = None
    evidence = None
    build_evidence = None
    output = None
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--root":
            root = argv[i + 1]; i += 2
        elif a == "--archive-root":
            archive_root = argv[i + 1]; i += 2
        elif a == "--evidence":
            evidence = argv[i + 1]; i += 2
        elif a == "--build-evidence":
            build_evidence = argv[i + 1]; i += 2
        elif a == "--output":
            output = argv[i + 1]; i += 2
        else:
            die()
    if output is None or os.path.exists(output):
        die()
    if (archive_root is None) == (evidence is None):
        die()
    if build_evidence is not None and evidence is not None:
        die()
    if evidence is not None:
        try:
            ev_raw = open(evidence, "rb").read()
        except Exception:
            die()
        ev = loads_strict(ev_raw)
        validate_public(ev, README_SHA256)
        res = result_for(ev)
    else:
        ev, res = build(archive_root)
        if build_evidence is not None:
            dump(build_evidence, ev)
    dump(output, res)
    print("lines=%d verdict=%s" % (ev.get("line_count", -1), res["verdict"]))
    return 0


def loads_strict(raw):
    try:
        return json.loads(raw.decode("utf-8"), parse_constant=_reject, parse_float=_reject,
                          object_pairs_hook=no_dup)
    except SystemExit:
        raise
    except Exception:
        die()


def result_for(ev):
    la = ev["runs"][RUNS[0][0]]["lines"]
    same = sum(1 for x in la if x["classification"] == "identical")
    diff = sum(1 for x in la if x["classification"] == "differs")
    pl = sum(1 for x in la if x["root_path_like"])
    verdict = "env_line_%d_%d_%d_%d" % (same, diff, pl, len(la))
    return {
        "schema": SCHEMA,
        "evidence_sha256": hashlib.sha256(json.dumps(ev, ensure_ascii=False, indent=1).encode() + b"\n").hexdigest(),
        "verdict": verdict,
        "endpoints": {"E1_lines": len(la), "E2_identical": same, "E2_differs": diff,
                      "E5_root_path_like_lines": pl,
                      "differs_at_lines": [x["line"] for x in la if x["classification"] == "differs"]},
        "limits": ["line-level only; no line values published", "single task face / single codex version",
                   "root_path_like is a tag-scoped flag, not a field-level parser"],
    }


if __name__ == "__main__":
    sys.exit(main())
