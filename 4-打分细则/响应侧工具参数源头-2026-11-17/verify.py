#!/usr/bin/env python3
"""Frozen W/L/H single-call study. Standard-library only; never executes tools.

Build: --archive-root <archive-root> --build-evidence <new.json> --output <new.json>
Replay: --evidence <public evidence.json> --output <new.json>
Both modes pin README and all input bytes. Output is exclusive. Replay proves
consistency of the public projection, NOT authenticity of private captures.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import pathlib
import re
import shutil
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
README_SHA = "b4acb26d4ebb41bcb92713650142e0c4578a2569c6c783ae0366086034c6cd0a"
EVIDENCE_SHA = "9bbb97d4253b072ce0b9fda47922018eb1297418a894237729604329e59ca159"
SCHEMA = "tool-argument-origin-evidence-v1"
RESULT_SCHEMA = "tool-argument-origin-result-v1"
REQUEST_PINS = [
 (32937, "765b958d5606bc7a43a0960e30e7106eb3638beb402419e0f1d17f471ee52220"),
 (888, "b51f351d000a5a5ca4013a1326ba14d16842d30e1b8a7c5a3862d9f8b2c95f32"),
 (33319, "229ec58c17bb268a616bf738ad9b6a50dca30696d44de39409c8c2db044311eb"),
 (34179, "bb8a9e7d831a7957b4c820b4436970bff0d95eba010c08891c21c170501f0d45"),
 (34688, "05299e53650d2998354518794d3ce7892294da5b383b106db03a10fe06e4998b"),
 (35214, "e985ea2062e3a89931fd83f6dfca2378894de1c5c540df99e4b39b3b7fb5cab9"),
 (35742, "b97d98afdbaae0d1455bf77bb50e93a0468ac88206287d4e6114d29b67fff4c7"),
 (36272, "2b22591643b18ed2d83ab341c1ae5efda5f3026e6b8287e645c591b8734ce6e1"),
 (36799, "0630603497096e43e7cff1eafa9bb6e93697d611f87e1fb9523f4000739cd904"),
 (37323, "74bc1dc020a24020e8225c70ce61c74521bd66b2f17e63837bd5c366b6d680dd"),
 (37849, "6f5ea74cbebb89111eee370504b87b99aeefafe329954cee360970949d5eb7f7"),
 (38377, "02def2af5fffac7611bc47932bb1fb7b45dc24a0a967e8a56b2cfe15ea5788d9"),
 (38907, "cbe6ce8f9a4a19782523ed087c9834d2493abdb828ab95e6e4ba194ec958ebf1"),
 (39434, "22f0eec03ed4efbe1568d0c0cc19439411d6573c35cec8e570eb68fe40df9016"),
 (39959, "eb2a6159b89e295b57d4cc4634d9aa2bf97c29eec8bc9cd869f250b0c7727b47"),
 (40486, "af4d9df543a15ee60d4abe4d32c18ba02a39910d8e2ee632113821af0a8f3112"),
]
META_PINS = [
 "25819aaaf22d78b2c90a7df7bf760c75b592f4fe5202262f78d727249c00fcc2",
 "a507b690d89ac9c3d5cbcd67c99b1531d59ee3d597a52435f601cd6b1e7c1b3d",
 "74aad02f546add8f632d3da0ae26fe7a0f68f8de590d2a1d7cded68f146a88a3",
 "6cfd8d30314f4627e58b91f38a2a4d8551a53b05e4c67803c35861848c1038c8",
 "46a973d4084e70fd51d316404deb548fc33b6f7fddee7b0c7ced522fe99efff2",
 "f63534ecfa88b7715c94d07ef6d72b0bde1b5e9f8cc290569748e52bc7694ca2",
 "db7091004e550552c146164ce18d1b380dac508509f7fe9aefba8a9b8e654e32",
 "b21e0213892c739ec0c4eea90ba58a2b17f96c99232465569771fcd8c3bd13e5",
 "e9567e6561d8fe197d34b197cb88c0b70c9bc78daf2a7e9125f3b7e66cf193da",
 "a4e3c7029101d302a5ed93f41f77a5b271d2e770b80d92ed875aba4cdc5a04fe",
 "83f167c79346c93411859a737cd29d97580bfa52b6da4755c0144ed7f91c1d77",
 "a66c7f8c471945ef63e7626184764c5b11f0af48548db01c04e7b10a547340ad",
 "458387cfae5d8fb603e482ae0ec76b474ab04fbf8010a5dff03da9b419a07f90",
 "b4ca19ab858032c3f9e5c2205e6c7cee00ef732c0aea67a610415f5a5b550eec",
 "1a65023e2422621f841f71798f42daa69063bcefce31a9d129b5cd50b788bc87",
 "9c8a30255d06c0342d1fd7f97d4932e63a991aab039c487b719c90d9a72ae086",
]
RESPONSE_SHA = "b4db600a4381e7eca1d87cee4e58ce0cbb55ba7c721f7fda66fd6b165091a066"
EVENT_SHA = "e636cae386c2bf88aae9ed61dcd9848d38927b6bbdb59e3effe4ac83155a3efa"
DECODED_SHA = "09fd17125137221a4a6a2c7da3f8b93bf341bb05f95e606dfa4f330965196436"
BRANCHES = {"SOURCE_MISSING_PRESERVED", "COMMAND_LOST_IN_CHAIN",
 "COMMAND_ADDED_IN_CHAIN", "MISSING_NOT_REPRODUCED",
 "SOURCE_INVALID_VALUE_PRESERVED", "ARGUMENT_CHANGED_IN_CHAIN"}
UNKNOWNS = {"UNKNOWN_STREAM", "UNKNOWN_BINDING", "UNKNOWN_SHAPE"}


class Invalid(Exception):
    """Hard input/seal/domain failure, not a scientific UNKNOWN."""


class Unknown(Exception):
    def __init__(self, kind, code):
        super().__init__(kind + ":" + code)
        self.kind, self.code = kind, code


def require(ok, code):
    if not ok:
        raise Invalid(code)


def guard(ok, kind, code):
    if not ok:
        raise Unknown(kind, code)


def integer(v, minimum=0):
    require(type(v) is int and v >= minimum, "INTEGER_DOMAIN")
    return v


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def pairs_no_duplicates(pairs):
    out = {}
    for k, v in pairs:
        require(k not in out, "JSON_DUPLICATE_KEY")
        out[k] = v
    return out


def reject_constant(_):
    raise Invalid("JSON_NONFINITE")


def check_finite(value):
    if isinstance(value, float):
        require(math.isfinite(value), "JSON_NONFINITE")
    elif isinstance(value, dict):
        for x in value.values():
            check_finite(x)
    elif isinstance(value, list):
        for x in value:
            check_finite(x)


def loads(raw):
    try:
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8", errors="strict")
        require(isinstance(raw, str), "JSON_INPUT_TYPE")
        obj = json.loads(raw, object_pairs_hook=pairs_no_duplicates,
                         parse_constant=reject_constant)
        check_finite(obj)
        # Reject unpaired surrogate code points as well as invalid byte UTF-8.
        json.dumps(obj, ensure_ascii=False, allow_nan=False).encode("utf-8")
        return obj
    except Invalid:
        raise
    except (ValueError, TypeError, UnicodeError, RecursionError):
        raise Invalid("JSON_INVALID") from None


def canon(obj):
    check_finite(obj)
    return json.dumps(obj, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def dump(obj):
    return canon(obj) + b"\n"


def json_stream(raw):
    try:
        return loads(raw)
    except Invalid:
        raise Unknown("UNKNOWN_STREAM", "STRICT_JSON") from None


def sse_frames(raw):
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeError:
        raise Unknown("UNKNOWN_STREAM", "UTF8") from None
    if text.startswith("\ufeff"):
        text = text[1:]
    # SSE treats CR, LF and CRLF as line endings; blank line dispatches a frame.
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    data, frames = [], []
    for line_no, line in enumerate(lines, 1):
        if line == "":
            if data:
                frames.append((line_no, "\n".join(data)))
                data = []
            continue
        if line.startswith(":"):
            continue
        field, sep, value = line.partition(":")
        if sep and value.startswith(" "):
            value = value[1:]
        if field == "data":
            data.append(value if sep else "")
        # Standard SSE non-data fields do not alter JSON data.
    guard(not data, "UNKNOWN_STREAM", "UNDISPATCHED_FRAME")
    guard(bool(frames), "UNKNOWN_STREAM", "NO_DATA")
    return frames


def parse_sse(raw):
    calls, finishes = {}, {}
    fragments = []
    done = None
    frames = sse_frames(raw)
    for ordinal, (line_no, text) in enumerate(frames, 1):
        guard(done is None, "UNKNOWN_STREAM", "DATA_AFTER_DONE")
        if text == "[DONE]":
            done = ordinal
            continue
        obj = json_stream(text)
        guard(isinstance(obj, dict), "UNKNOWN_SHAPE", "FRAME_NOT_OBJECT")
        choices = obj.get("choices")
        guard(isinstance(choices, list), "UNKNOWN_SHAPE", "CHOICES")
        choice_indices = set()
        for choice in choices:
            guard(isinstance(choice, dict), "UNKNOWN_SHAPE", "CHOICE")
            ci = choice.get("index")
            guard(type(ci) is int and ci >= 0, "UNKNOWN_SHAPE", "CHOICE_INDEX")
            guard(ci not in choice_indices, "UNKNOWN_SHAPE", "DUPLICATE_CHOICE_INDEX")
            choice_indices.add(ci)
            guard(ci not in finishes, "UNKNOWN_STREAM", "AFTER_FINISH")
            delta = choice.get("delta")
            guard(isinstance(delta, dict), "UNKNOWN_SHAPE", "DELTA")
            guard(set(delta) <= {"role", "content", "reasoning_content", "tool_calls"},
                  "UNKNOWN_SHAPE", "DELTA_FIELDS")
            for k in ("role", "content", "reasoning_content"):
                if k in delta:
                    guard(delta[k] is None or isinstance(delta[k], str),
                          "UNKNOWN_SHAPE", "DELTA_VALUE")
            if "tool_calls" in delta:
                guard(isinstance(delta["tool_calls"], list), "UNKNOWN_SHAPE", "TOOL_CALLS")
                tool_indices = set()
                for tc in delta["tool_calls"]:
                    guard(isinstance(tc, dict), "UNKNOWN_SHAPE", "TOOL_CALL")
                    guard(set(tc) <= {"index", "id", "type", "function"},
                          "UNKNOWN_SHAPE", "TOOL_FIELDS")
                    ti = tc.get("index")
                    guard(type(ti) is int and ti >= 0, "UNKNOWN_SHAPE", "TOOL_INDEX")
                    guard(ti not in tool_indices, "UNKNOWN_SHAPE", "DUPLICATE_TOOL_INDEX")
                    tool_indices.add(ti)
                    key = (ci, ti)
                    c = calls.setdefault(key, {"id": None, "name": "", "raw_args": "",
                                               "choice_index": ci, "tool_index": ti})
                    if "type" in tc:
                        guard(tc["type"] == "function", "UNKNOWN_SHAPE", "TOOL_TYPE")
                    if "id" in tc:
                        ident = tc["id"]
                        guard(isinstance(ident, str), "UNKNOWN_SHAPE", "CALL_ID_TYPE")
                        if ident:
                            guard(c["id"] is None or c["id"] == ident,
                                  "UNKNOWN_STREAM", "CONFLICTING_ID")
                            c["id"] = ident
                    if "function" in tc:
                        fn = tc["function"]
                        guard(isinstance(fn, dict) and set(fn) <= {"name", "arguments"},
                              "UNKNOWN_SHAPE", "FUNCTION")
                        for field, dest in (("name", "name"), ("arguments", "raw_args")):
                            if field in fn:
                                piece = fn[field]
                                guard(isinstance(piece, str), "UNKNOWN_SHAPE", "NONSTRING_PIECE")
                                c[dest] += piece
                                fragments.append({"frame": ordinal, "line": line_no,
                                    "choice_index": ci, "tool_index": ti,
                                    "is_arguments": field == "arguments",
                                    "bytes": len(piece.encode("utf-8")),
                                    "sha256": sha(piece.encode("utf-8"))})
            finish = choice.get("finish_reason")
            if finish is not None:
                guard(isinstance(finish, str), "UNKNOWN_SHAPE", "FINISH_TYPE")
                finishes[ci] = {"frame": ordinal, "tool_calls": finish == "tool_calls"}
    guard(done is not None, "UNKNOWN_STREAM", "NO_DONE")
    targets = [v for v in calls.values() if v["name"] == "bash"]
    guard(len(targets) == 1, "UNKNOWN_BINDING", "TARGET_COUNT")
    c = targets[0]
    finish = finishes.get(c["choice_index"])
    guard(finish is not None and finish["tool_calls"] and finish["frame"] < done,
          "UNKNOWN_STREAM", "TARGET_UNFINISHED")
    guard(bool(c["id"]), "UNKNOWN_BINDING", "TARGET_ID_MISSING")
    guard(sum(v["id"] == c["id"] for v in calls.values()) == 1,
          "UNKNOWN_BINDING", "REUSED_ID")
    c["args"] = json_stream(c["raw_args"])
    guard(isinstance(c["args"], dict), "UNKNOWN_SHAPE", "ARGUMENT_NOT_OBJECT")
    return c, {"frames": len(frames), "done_frame": done,
               "finish_frame": finish["frame"], "fragments": fragments,
               "choice_index": c["choice_index"], "tool_index": c["tool_index"]}


def schema_of(request):
    tools = request.get("tools")
    guard(isinstance(tools, list) and bool(tools), "UNKNOWN_BINDING", "NOT_MAIN")
    matches = [t.get("function") for t in tools if isinstance(t, dict)
               and isinstance(t.get("function"), dict) and t["function"].get("name") == "bash"]
    guard(len(matches) == 1, "UNKNOWN_BINDING", "BASH_SCHEMA_COUNT")
    schema = matches[0].get("parameters")
    guard(isinstance(schema, dict) and schema.get("type") == "object",
          "UNKNOWN_SHAPE", "PARAMETER_SCHEMA")
    props = schema.get("properties")
    guard(isinstance(props, dict) and "command" in props,
          "UNKNOWN_SHAPE", "COMMAND_SCHEMA")
    command = props["command"]
    # Frozen capture has only type:string and a description. Do not silently
    # pretend to implement arbitrary JSON Schema restrictions.
    guard(isinstance(command, dict) and command.get("type") == "string"
          and set(command) <= {"type", "description"},
          "UNKNOWN_SHAPE", "UNSUPPORTED_COMMAND_SCHEMA")
    guard(isinstance(schema.get("required"), list) and "command" in schema["required"],
          "UNKNOWN_SHAPE", "COMMAND_NOT_REQUIRED")
    return schema


def has_nested_command(value, depth=0):
    if isinstance(value, dict):
        return (depth > 0 and "command" in value) or any(
            has_nested_command(v, depth + 1) for v in value.values())
    if isinstance(value, list):
        return any(has_nested_command(v, depth + 1) for v in value)
    return False


def layer(args, raw_args, schema):
    guard(isinstance(args, dict), "UNKNOWN_SHAPE", "ARGUMENT_NOT_OBJECT")
    # Unknown keys are conservatively unsupported, rather than guessing aliases
    # after inspecting the outcome. No alias/synonym expansion is performed.
    guard(set(args) <= set(schema["properties"]) and not has_nested_command(args),
          "UNKNOWN_SHAPE", "ARGUMENT_FIELDS")
    encoded = canon(args)
    present = "command" in args
    string = present and isinstance(args["command"], str)
    return {"canonical_sha256": sha(encoded), "canonical_bytes": len(encoded),
            "raw_sha256": sha(raw_args.encode("utf-8")),
            "raw_bytes": len(raw_args.encode("utf-8")),
            "command_present": present, "command_string": string,
            "command_schema_valid": string}


def call_from_history(requests, ident):
    for seq, body in requests:
        msgs = body.get("messages")
        guard(isinstance(msgs, list), "UNKNOWN_SHAPE", "MESSAGES")
        if not body.get("tools"):
            continue
        matches = []
        for mi, m in enumerate(msgs):
            guard(isinstance(m, dict), "UNKNOWN_SHAPE", "MESSAGE")
            if m.get("role") == "assistant":
                tcs = m.get("tool_calls", [])
                guard(isinstance(tcs, list), "UNKNOWN_SHAPE", "HISTORY_TOOL_CALLS")
                for ti, tc in enumerate(tcs):
                    guard(isinstance(tc, dict), "UNKNOWN_SHAPE", "HISTORY_TOOL_CALL")
                    if tc.get("id") == ident:
                        matches.append((mi, ti, tc))
        if matches:
            guard(len(matches) == 1, "UNKNOWN_BINDING", "HISTORY_TARGET_COUNT")
            mi, ti, tc = matches[0]
            fn = tc.get("function")
            guard(tc.get("type") == "function" and isinstance(fn, dict)
                  and fn.get("name") == "bash", "UNKNOWN_BINDING", "HISTORY_NAME")
            raw = fn.get("arguments")
            guard(isinstance(raw, str), "UNKNOWN_SHAPE", "HISTORY_ARGUMENT_CARRIER")
            args = json_stream(raw)
            guard(isinstance(args, dict), "UNKNOWN_SHAPE", "HISTORY_ARGUMENT_OBJECT")
            results = [(i, m) for i, m in enumerate(msgs)
                       if m.get("role") == "tool" and m.get("tool_call_id") == ident]
            guard(len(results) == 1 and results[0][0] == mi + 1,
                  "UNKNOWN_BINDING", "HISTORY_RESULT")
            guard(isinstance(results[0][1].get("content"), str),
                  "UNKNOWN_SHAPE", "HISTORY_RESULT_CONTENT")
            return args, raw, results[0][1]["content"], {
                "history_request_seq": seq, "history_message_index": mi,
                "history_tool_index": ti, "history_result_index": results[0][0]}
    raise Unknown("UNKNOWN_BINDING", "HISTORY_TARGET_MISSING")


def local_call(events, ident, history_result):
    calls = [(i + 1, e) for i, e in enumerate(events)
             if e.get("type") == "tool/call" and isinstance(e.get("data"), dict)
             and e["data"].get("callId") == ident]
    guard(len(calls) == 1, "UNKNOWN_BINDING", "LOCAL_CALL_COUNT")
    line, call = calls[0]
    data = call["data"]
    guard(data.get("name") == "bash", "UNKNOWN_BINDING", "LOCAL_NAME")
    raw = data.get("arguments")
    guard(isinstance(raw, str), "UNKNOWN_SHAPE", "LOCAL_ARGUMENT_CARRIER")
    args = json_stream(raw)
    guard(isinstance(args, dict), "UNKNOWN_SHAPE", "LOCAL_ARGUMENT_OBJECT")
    results = [(i + 1, e) for i, e in enumerate(events)
               if e.get("type") == "tool/result" and isinstance(e.get("data"), dict)
               and isinstance(e["data"].get("message"), dict)
               and e["data"]["message"].get("toolCallId") == ident]
    guard(len(results) == 1, "UNKNOWN_BINDING", "LOCAL_RESULT_COUNT")
    result_line, result = results[0]
    guard(type(call.get("seq")) is int and type(result.get("seq")) is int
          and result["seq"] > call["seq"] and result_line > line
          and result.get("sourceEventSeqs") == [call["seq"]],
          "UNKNOWN_BINDING", "LOCAL_SOURCE_CHAIN")
    msg = result["data"]["message"]
    content = msg.get("content")
    guard(msg.get("isError") is True and isinstance(content, list)
          and len(content) == 1 and isinstance(content[0], dict)
          and content[0].get("type") == "text" and isinstance(content[0].get("text"), str),
          "UNKNOWN_BINDING", "LOCAL_ERROR_RESULT")
    guard(content[0]["text"] == history_result, "UNKNOWN_BINDING", "RESULT_TEXT_MISMATCH")
    return args, raw, {"local_call_line": line, "local_call_seq": call["seq"],
        "local_result_line": result_line, "local_result_seq": result["seq"],
        "result_text_sha256": sha(history_result.encode("utf-8")),
        "result_text_bytes": len(history_result.encode("utf-8")),
        "source_event_seq_equal": True, "result_text_equal": True,
        "local_result_is_error": True}


def empty_observation():
    return {"unknown": None, "stream": None, "schema_sha256": None,
            "binding": {}, "layers": {"W": None, "L": None, "H": None}}


def observe(response, requests, events):
    out = empty_observation()
    try:
        schema = schema_of(requests[0][1])
        out["schema_sha256"] = sha(canon(schema))
        c, out["stream"] = parse_sse(response)
        out["binding"]["call_id_sha256"] = sha(c["id"].encode("utf-8"))
        initial = requests[0][1].get("messages")
        guard(isinstance(initial, list) and all(isinstance(m, dict) for m in initial),
              "UNKNOWN_SHAPE", "INITIAL_MESSAGES")
        for m in initial:
            previous = m.get("tool_calls", [])
            guard(isinstance(previous, list) and all(isinstance(t, dict) for t in previous),
                  "UNKNOWN_SHAPE", "INITIAL_TOOL_CALLS")
            guard(m.get("tool_call_id") != c["id"]
                  and all(t.get("id") != c["id"] for t in previous),
                  "UNKNOWN_BINDING", "ID_ALREADY_IN_INITIAL_REQUEST")
        out["layers"]["W"] = layer(c["args"], c["raw_args"], schema)
        h, hr, result, facts = call_from_history(requests[1:], c["id"])
        out["binding"].update(facts)
        out["layers"]["H"] = layer(h, hr, schema)
        l, lr, facts = local_call(events, c["id"], result)
        out["binding"].update(facts)
        out["layers"]["L"] = layer(l, lr, schema)
    except Unknown as exc:
        out["unknown"] = {"kind": exc.kind, "code": exc.code}
    return out


def pair_branch(w, h):
    same = w["canonical_sha256"] == h["canonical_sha256"]
    wp, hp = w["command_present"], h["command_present"]
    if not wp and not hp and same:
        return "SOURCE_MISSING_PRESERVED"
    if w["command_schema_valid"] and not hp:
        return "COMMAND_LOST_IN_CHAIN"
    if not wp and hp:
        return "COMMAND_ADDED_IN_CHAIN"
    if w["command_schema_valid"] and h["command_schema_valid"] and same:
        return "MISSING_NOT_REPRODUCED"
    if wp and hp and not w["command_schema_valid"] and not h["command_schema_valid"] and same:
        return "SOURCE_INVALID_VALUE_PRESERVED"
    return "ARGUMENT_CHANGED_IN_CHAIN"


def calculate(observation):
    layers = observation["layers"]
    w, l, h = (layers[k] for k in ("W", "L", "H"))
    unknown = observation["unknown"]
    interval = pair_branch(w, h) if w is not None and h is not None else None
    if unknown:
        classification = unknown["kind"]
    elif any(v is None for v in (w, l, h)):
        classification = "UNKNOWN_BINDING"
    else:
        classification = interval
    equal = lambda a, b: None if a is None or b is None else a["canonical_sha256"] == b["canonical_sha256"]
    wl, lh, wh = equal(w, l), equal(l, h), equal(w, h)
    # W/H equality alone never hides an intermediate L mutation.
    if classification in BRANCHES and wh and not (wl and lh):
        classification = "ARGUMENT_CHANGED_IN_CHAIN"
    return {"classification": classification, "interval_observation": interval,
            "unknown": unknown, "W_L_equal": wl, "L_H_equal": lh, "W_H_equal": wh,
            "three_layers_bound": unknown is None and all(v is not None for v in (w, l, h)),
            "three_layers_equal": unknown is None and wl is True and lh is True and wh is True,
            "source_missing_in_captured_response": None if w is None else not w["command_present"],
            "changed_intervals": [k for k, equal_value in (("W_L", wl), ("L_H", lh))
                                  if equal_value is False] if unknown is None else [],
            "single_call_denominator": 1}


def pinned(path, expected_sha, expected_bytes=None):
    require(path.is_file(), "INPUT_MISSING")
    raw = path.read_bytes()
    require(sha(raw) == expected_sha, "INPUT_PIN_MISMATCH")
    if expected_bytes is not None:
        require(len(raw) == expected_bytes, "INPUT_LENGTH_MISMATCH")
    return raw


def meta_binding(meta, seq, request_raw, response_raw=None):
    guard(type(meta.get("seq")) is int and meta["seq"] == seq,
          "UNKNOWN_BINDING", "META_SEQ")
    guard(meta.get("request_body_sha256") == sha(request_raw)
          and type(meta.get("request_body_bytes")) is int
          and meta["request_body_bytes"] == len(request_raw),
          "UNKNOWN_BINDING", "META_REQUEST")
    if response_raw is not None:
        headers = meta.get("response_headers")
        guard(isinstance(headers, dict), "UNKNOWN_BINDING", "META_HEADERS")
        types = [v for k, v in headers.items() if k.lower() == "content-type"]
        guard(meta.get("response_body_sha256") == sha(response_raw)
              and type(meta.get("response_body_bytes")) is int
              and meta["response_body_bytes"] == len(response_raw)
              and meta.get("upstream_status") == 200
              and meta.get("response_framing") == "rechunked"
              and len(types) == 1 and isinstance(types[0], str)
              and types[0].split(";", 1)[0].lower() == "text/event-stream",
              "UNKNOWN_BINDING", "META_RESPONSE")


def build(archive):
    root = pathlib.Path(archive).resolve()
    requests, sources = [], []
    metas = []
    for seq, (size, digest) in enumerate(REQUEST_PINS, 1):
        raw = pinned(root / "t3-r1/requests" / f"{seq:03d}.request.bin", digest, size)
        body = loads(raw)
        require(isinstance(body, dict), "REQUEST_NOT_OBJECT")
        requests.append((seq, body))
        sources.append({"kind": "request", "seq": seq, "bytes": len(raw), "sha256": sha(raw)})
        mr = pinned(root / "t3-r1/responses" / f"{seq:03d}.response.bin.meta.json", META_PINS[seq - 1])
        m = loads(mr)
        require(isinstance(m, dict), "META_NOT_OBJECT")
        metas.append((seq, m, raw))
        sources.append({"kind": "capture_meta", "seq": seq, "bytes": len(mr), "sha256": sha(mr)})
    response = pinned(root / "t3-r1/responses/001.response.bin", RESPONSE_SHA, 6811)
    sources.append({"kind": "response", "seq": 1, "bytes": len(response), "sha256": sha(response)})
    ep = root / "event-layer-t3-r1/session.v4.jsonl.zstd"
    er = pinned(ep, EVENT_SHA, 35577)
    zstd = shutil.which("zstd")
    require(zstd is not None, "ZSTD_UNAVAILABLE")
    try:
        completed = subprocess.run([zstd, "-d", "-q", "-c", str(ep)],
                                   check=True, capture_output=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        raise Invalid("ZSTD_FAILED") from None
    decoded = completed.stdout
    require(sha(decoded) == DECODED_SHA and len(decoded) == 92523, "DECODED_PIN")
    events = [loads(line) for line in decoded.splitlines()]
    require(len(events) == 91 and all(isinstance(e, dict) for e in events), "EVENT_DOMAIN")
    seqs = [e["seq"] for e in events if "seq" in e]
    require(all(type(v) is int for v in seqs) and seqs == sorted(set(seqs)), "EVENT_SEQ_DOMAIN")
    sources.append({"kind": "event_archive", "seq": 0, "bytes": len(er), "sha256": sha(er)})
    try:
        for seq, m, rr in metas:
            meta_binding(m, seq, rr, response if seq == 1 else None)
        observation = observe(response, requests, events)
    except Unknown as exc:
        observation = empty_observation()
        observation["unknown"] = {"kind": exc.kind, "code": exc.code}
    return {"schema": SCHEMA, "frozen_readme_sha256": README_SHA,
            "sources": sources, "decoded_event_sha256": sha(decoded),
            "decoded_event_bytes": len(decoded), "event_count": len(events),
            "observation": observation}


def digest_field(v):
    require(isinstance(v, str) and re.fullmatch(r"[0-9a-f]{64}", v) is not None, "DIGEST_DOMAIN")


def validate(evidence):
    require(isinstance(evidence, dict) and set(evidence) == {
        "schema", "frozen_readme_sha256", "sources", "decoded_event_sha256",
        "decoded_event_bytes", "event_count", "observation"}, "EVIDENCE_KEYS")
    require(evidence["schema"] == SCHEMA and evidence["frozen_readme_sha256"] == README_SHA,
            "EVIDENCE_SCHEMA")
    require(evidence["decoded_event_sha256"] == DECODED_SHA
            and evidence["decoded_event_bytes"] == 92523 and evidence["event_count"] == 91,
            "EVENT_EVIDENCE_PIN")
    sources = evidence["sources"]
    require(isinstance(sources, list) and len(sources) == 34, "SOURCE_COUNT")
    expected = []
    for seq, (size, digest) in enumerate(REQUEST_PINS, 1):
        expected += [("request", seq, size, digest), ("capture_meta", seq, None, META_PINS[seq - 1])]
    expected += [("response", 1, 6811, RESPONSE_SHA), ("event_archive", 0, 35577, EVENT_SHA)]
    for source, (kind, seq, size, digest) in zip(sources, expected):
        require(isinstance(source, dict) and set(source) == {"kind", "seq", "bytes", "sha256"}, "SOURCE_KEYS")
        integer(source["seq"]); integer(source["bytes"], 1)
        require(source["kind"] == kind and source["seq"] == seq
                and source["sha256"] == digest and (size is None or source["bytes"] == size), "SOURCE_PIN")
    ob = evidence["observation"]
    require(isinstance(ob, dict) and set(ob) == {"unknown", "stream", "schema_sha256", "binding", "layers"},
            "OBSERVATION_KEYS")
    require(ob["unknown"] is None or (isinstance(ob["unknown"], dict)
            and set(ob["unknown"]) == {"kind", "code"} and ob["unknown"]["kind"] in UNKNOWNS
            and isinstance(ob["unknown"]["code"], str)
            and re.fullmatch(r"[A-Z_]+", ob["unknown"]["code"])), "UNKNOWN_DOMAIN")
    if ob["schema_sha256"] is not None:
        digest_field(ob["schema_sha256"])
    require(isinstance(ob["layers"], dict) and set(ob["layers"]) == {"W", "L", "H"}, "LAYER_KEYS")
    for v in ob["layers"].values():
        if v is None:
            continue
        require(isinstance(v, dict) and set(v) == {"canonical_sha256", "canonical_bytes", "raw_sha256",
                "raw_bytes", "command_present", "command_string", "command_schema_valid"}, "LAYER_FIELDS")
        digest_field(v["canonical_sha256"]); digest_field(v["raw_sha256"])
        integer(v["canonical_bytes"], 2); integer(v["raw_bytes"], 2)
        for k in ("command_present", "command_string", "command_schema_valid"):
            require(type(v[k]) is bool, "LAYER_BOOL")
        require(not v["command_string"] or v["command_present"], "COMMAND_STATE")
        require(v["command_schema_valid"] == v["command_string"], "COMMAND_SCHEMA_STATE")
    require(isinstance(ob["binding"], dict), "BINDING_TYPE")
    binding = ob["binding"]
    allowed = {"call_id_sha256", "history_request_seq", "history_message_index", "history_tool_index",
               "history_result_index", "local_call_line", "local_call_seq", "local_result_line", "local_result_seq",
               "result_text_sha256", "result_text_bytes", "source_event_seq_equal", "result_text_equal", "local_result_is_error"}
    require(set(binding) <= allowed, "BINDING_KEYS")
    for k, v in binding.items():
        if k.endswith("sha256"):
            digest_field(v)
        elif k in {"source_event_seq_equal", "result_text_equal", "local_result_is_error"}:
            require(type(v) is bool and v is True, "BINDING_BOOL")
        else:
            integer(v)
    stream = ob["stream"]
    if stream is not None:
        require(isinstance(stream, dict) and set(stream) == {"frames", "done_frame", "finish_frame", "fragments", "choice_index", "tool_index"}, "STREAM_KEYS")
        for k in ("frames", "done_frame", "finish_frame", "choice_index", "tool_index"):
            integer(stream[k])
        require(0 < stream["finish_frame"] < stream["done_frame"] == stream["frames"], "STREAM_COMPLETION")
        require(isinstance(stream["fragments"], list) and bool(stream["fragments"]), "FRAGMENTS")
        last = 0
        for f in stream["fragments"]:
            require(isinstance(f, dict) and set(f) == {"frame", "line", "choice_index", "tool_index", "is_arguments", "bytes", "sha256"}, "FRAGMENT_KEYS")
            for k in ("frame", "line", "choice_index", "tool_index", "bytes"):
                integer(f[k])
            require(last <= f["frame"] < stream["done_frame"] and type(f["is_arguments"]) is bool,
                    "FRAGMENT_ORDER")
            digest_field(f["sha256"]); last = f["frame"]
    if ob["unknown"] is None:
        require(stream is not None and all(ob["layers"].values()) and set(binding) == allowed,
                "COMPLETE_BINDING_REQUIRED")
        require(binding["history_request_seq"] > 1
                and binding["history_result_index"] == binding["history_message_index"] + 1
                and binding["local_call_seq"] < binding["local_result_seq"]
                and binding["local_call_line"] < binding["local_result_line"], "BINDING_ORDER")
    return calculate(ob)


def result(evidence):
    calculated = validate(evidence)
    return {"schema": RESULT_SCHEMA, "frozen_readme_sha256": README_SHA,
            "evidence_sha256": sha(dump(evidence)), "endpoints": calculated,
            "observation": evidence["observation"], "source_count": len(evidence["sources"]),
            "public_replay_authenticates_private_originals": False,
            "new_product_runs": 0}


def exclusive(path, raw):
    with pathlib.Path(path).open("xb") as f:
        f.write(raw)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive-root")
    p.add_argument("--build-evidence")
    p.add_argument("--evidence", default=str(HERE / "evidence.json"))
    p.add_argument("--output", required=True)
    args = p.parse_args(argv)
    try:
        pinned(HERE / "README.md", README_SHA)
        require(bool(args.archive_root) == bool(args.build_evidence), "BUILD_ARGUMENTS")
        outputs = [pathlib.Path(args.output)]
        if args.build_evidence:
            outputs.append(pathlib.Path(args.build_evidence))
        require(len({v.resolve() for v in outputs}) == len(outputs), "OUTPUT_COLLISION")
        require(all(not v.exists() for v in outputs), "OUTPUT_EXISTS")
        if args.archive_root:
            evidence = build(args.archive_root)
        else:
            evidence_raw = pinned(pathlib.Path(args.evidence), EVIDENCE_SHA)
            evidence = loads(evidence_raw)
        raw = dump(evidence)
        require(sha(raw) == EVIDENCE_SHA, "EVIDENCE_SEAL")
        out = dump(result(evidence))
        if args.build_evidence:
            exclusive(args.build_evidence, raw)
        exclusive(args.output, out)
        print(sha(out))
        return 0
    except (Invalid, OSError, ValueError, KeyError, TypeError) as exc:
        # Never interpolate a JSON parser exception/body/path into public logs.
        print("INVALID:" + (str(exc) if isinstance(exc, Invalid) else type(exc).__name__), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
