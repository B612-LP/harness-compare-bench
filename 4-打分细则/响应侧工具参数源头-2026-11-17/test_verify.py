#!/usr/bin/env python3
"""Author counterexamples, not an independent audit or new product runs.

python3 -B test_verify.py --scratch-root <new, disposable output directory>
All generated files stay under that explicit exclusive directory; no cleanup
or deletion is performed. Repeat under -O with a different directory.
"""
import argparse
import copy
import importlib.util
import json
import os
import pathlib
import subprocess
import sys
import unittest

HERE = pathlib.Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("origin_verify", HERE / "verify.py")
V = importlib.util.module_from_spec(spec)
spec.loader.exec_module(V)
SCRATCH = None


def schema():
    return {"type": "object", "properties": {"command": {"type": "string"},
            "description": {"type": "string"}, "workdir": {"type": "string"}},
            "required": ["command", "description"]}


def frame(delta, finish=None, ci=0):
    c = {"index": ci, "delta": delta}
    if finish is not None:
        c["finish_reason"] = finish
    return {"choices": [c]}


def tc(arguments=None, name=None, ident=None, index=0):
    t = {"index": index, "type": "function", "function": {}}
    if arguments is not None:
        t["function"]["arguments"] = arguments
    if name is not None:
        t["function"]["name"] = name
    if ident is not None:
        t["id"] = ident
    return t


def wire(args, ident="synthetic-one", pieces=None, crlf=False):
    raw = args if isinstance(args, str) else json.dumps(args, ensure_ascii=False)
    if pieces is None:
        pieces = [raw]
    fs = [frame({"tool_calls": [tc(p, "bash" if i == 0 else None,
                                           ident if i == 0 else None)]})
          for i, p in enumerate(pieces)]
    fs += [frame({"role": "assistant", "content": ""}, "tool_calls")]
    out = b"".join(b"data: " + V.canon(f) + b"\n\n" for f in fs) + b"data: [DONE]\n\n"
    return out.replace(b"\n", b"\r\n") if crlf else out


def fixture(w, l=None, h=None, raw_w=None, raw_l=None, raw_h=None):
    if l is None:
        l = copy.deepcopy(w)
    if h is None:
        h = copy.deepcopy(w)
    rw = json.dumps(w) if raw_w is None else raw_w
    rl = json.dumps(l) if raw_l is None else raw_l
    rh = json.dumps(h) if raw_h is None else raw_h
    ident = "synthetic-one"
    tool = {"type": "function", "function": {"name": "bash", "parameters": schema()}}
    req1 = {"tools": [tool], "messages": [{"role": "user", "content": "synthetic"}]}
    hist = {"tools": [tool], "messages": req1["messages"] + [
        {"role": "assistant", "tool_calls": [{"id": ident, "type": "function",
            "function": {"name": "bash", "arguments": rh}}]},
        {"role": "tool", "tool_call_id": ident, "content": "synthetic error"}]}
    events = [{"type": "tool/call", "seq": 10,
               "data": {"name": "bash", "callId": ident, "arguments": rl}},
              {"type": "tool/result", "seq": 11, "sourceEventSeqs": [10],
               "data": {"message": {"toolCallId": ident, "isError": True,
                   "content": [{"type": "text", "text": "synthetic error"}]}}}]
    return wire(rw), [(1, req1), (2, {"messages": []}), (3, hist)], events


class StudyTests(unittest.TestCase):
    def observation(self, *a, **kw):
        return V.observe(*fixture(*a, **kw))

    def classification(self, *a, **kw):
        return V.calculate(self.observation(*a, **kw))["classification"]

    def unknown_stream(self, raw):
        with self.assertRaises(V.Unknown) as e:
            V.parse_sse(raw)
        self.assertEqual(e.exception.kind, "UNKNOWN_STREAM")

    def test_01_fragmented_command_and_name(self):
        fs = [frame({"tool_calls": [tc('{"com', "ba", "x")]}),
              frame({"tool_calls": [tc('mand":"s', "sh")]}),
              frame({"tool_calls": [tc('ynthetic"}')]}), frame({}, "tool_calls")]
        raw = b"".join(b"data: " + V.canon(f) + b"\n\n" for f in fs) + b"data: [DONE]\n\n"
        call, obs = V.parse_sse(raw)
        self.assertEqual(call["args"], {"command": "synthetic"})
        self.assertEqual(obs["done_frame"], 5)
        self.assertEqual(len(obs["fragments"]), 5)

    def test_02_complete_empty_object_is_missing(self):
        self.assertEqual(self.classification({}), "SOURCE_MISSING_PRESERVED")
        ob = self.observation({})
        self.assertFalse(ob["layers"]["W"]["command_present"])
        self.assertTrue(V.calculate(ob)["three_layers_equal"])

    def test_03_valid_command_lost_W_to_L(self):
        a, b = {"command": "synthetic"}, {}
        ob = self.observation(a, l=b, h=b)
        result = V.calculate(ob)
        self.assertEqual(result["classification"], "COMMAND_LOST_IN_CHAIN")
        self.assertEqual(result["changed_intervals"], ["W_L"])

    def test_04_valid_command_lost_L_to_H(self):
        a, b = {"command": "synthetic"}, {}
        result = V.calculate(self.observation(a, l=a, h=b))
        self.assertEqual(result["classification"], "COMMAND_LOST_IN_CHAIN")
        self.assertEqual(result["changed_intervals"], ["L_H"])

    def test_05_added_is_not_lost(self):
        self.assertEqual(self.classification({}, l={"command": "x"}, h={"command": "x"}),
                         "COMMAND_ADDED_IN_CHAIN")

    def test_06_invalid_values_and_legal_empty_string(self):
        for val in (None, 1, False, [], {}):
            with self.subTest(value=val):
                self.assertEqual(self.classification({"command": val}), "SOURCE_INVALID_VALUE_PRESERVED")
        self.assertEqual(self.classification({"command": ""}), "MISSING_NOT_REPRODUCED")

    def test_07_nested_alias_case_and_double_encoding(self):
        for obj in ({"cmd": "x"}, {"Command": "x"}, {"workdir": {"command": "x"}},
                    {"command": "x", "description": [{"command": "x"}]}):
            with self.subTest(obj=obj):
                self.assertEqual(self.classification(obj), "UNKNOWN_SHAPE")
        raw = wire(json.dumps('{"command":"x"}'))
        with self.assertRaises(V.Unknown) as e:
            V.parse_sse(raw)
        self.assertEqual(e.exception.kind, "UNKNOWN_SHAPE")

    def test_08_wrong_local_id(self):
        r, req, ev = fixture({})
        ev[0]["data"]["callId"] = "other"
        result = V.calculate(V.observe(r, req, ev))
        self.assertEqual(result["classification"], "UNKNOWN_BINDING")
        self.assertEqual(result["interval_observation"], "SOURCE_MISSING_PRESERVED")
        self.assertFalse(result["three_layers_bound"])

    def test_09_wrong_history_id_and_result_id(self):
        for field in ("call", "result"):
            r, req, ev = fixture({})
            if field == "call":
                req[-1][1]["messages"][1]["tool_calls"][0]["id"] = "other"
            else:
                req[-1][1]["messages"][2]["tool_call_id"] = "other"
            self.assertEqual(V.calculate(V.observe(r, req, ev))["classification"], "UNKNOWN_BINDING")

    def test_10_wrong_seq_or_meta_response(self):
        raw = b"synthetic"
        m = {"seq": 2, "request_body_sha256": V.sha(raw), "request_body_bytes": len(raw)}
        with self.assertRaises(V.Unknown) as e:
            V.meta_binding(m, 1, raw)
        self.assertEqual(e.exception.kind, "UNKNOWN_BINDING")
        m["seq"] = 1
        V.meta_binding(m, 1, raw)
        m["request_body_bytes"] += 1
        with self.assertRaises(V.Unknown):
            V.meta_binding(m, 1, raw)

    def test_11_no_finish_and_no_done(self):
        raw = wire({})
        a, rest = raw.split(b"\n\n", 1)
        self.unknown_stream(a + b"\n\ndata: [DONE]\n\n")
        self.unknown_stream(raw.replace(b"data: [DONE]\n\n", b""))
        self.unknown_stream(raw[:-3])

    def test_12_stop_is_not_tool_completion(self):
        original = wire({})
        modified = original.replace(b'"finish_reason":"tool_calls"', b'"finish_reason":"stop"')
        self.assertNotEqual(original, modified)
        self.unknown_stream(modified)

    def test_13_truncated_json_and_invalid_utf8(self):
        self.unknown_stream(b'data: {"choices":\n\ndata: [DONE]\n\n')
        self.unknown_stream(wire('{"command":'))
        self.unknown_stream(b"\xff" + wire({}))

    def test_14_duplicate_keys_every_level(self):
        self.unknown_stream(b'data: {"choices":[],"choices":[]}\n\ndata: [DONE]\n\n')
        self.unknown_stream(wire('{"command":"a","command":"b"}'))
        for raw in (b'{"a":1,"a":2}', b'{"nested":{"a":1,"a":2}}'):
            with self.assertRaises(V.Invalid):
                V.loads(raw)

    def test_15_nonfinite_and_overflow(self):
        for v in ("NaN", "Infinity", "-Infinity", "1e999", "-1e999"):
            with self.subTest(v=v):
                with self.assertRaises(V.Invalid):
                    V.loads('{"n":' + v + '}')
                self.unknown_stream(wire('{"command":' + v + '}'))

    def test_16_two_bash_targets(self):
        fs = [frame({"tool_calls": [tc("{}", "bash", "one", 0), tc("{}", "bash", "two", 1)]}),
              frame({}, "tool_calls")]
        raw = b"".join(b"data: " + V.canon(f) + b"\n\n" for f in fs) + b"data: [DONE]\n\n"
        with self.assertRaises(V.Unknown) as e:
            V.parse_sse(raw)
        self.assertEqual(e.exception.kind, "UNKNOWN_BINDING")

    def test_17_key_order_only_not_value_difference(self):
        ob = self.observation({"command": "x", "description": "a"},
            raw_w='{"command":"x","description":"a"}',
            raw_l='{"description":"a","command":"x"}',
            raw_h='{ "description": "a", "command": "x" }')
        r = V.calculate(ob)
        self.assertEqual(r["classification"], "MISSING_NOT_REPRODUCED")
        self.assertTrue(r["three_layers_equal"])
        self.assertNotEqual(ob["layers"]["W"]["raw_sha256"], ob["layers"]["H"]["raw_sha256"])

    def test_18_other_parameter_changed_command_unchanged(self):
        self.assertEqual(self.classification({"command": "x", "description": "a"},
            l={"command": "x", "description": "b"}, h={"command": "x", "description": "b"}),
            "ARGUMENT_CHANGED_IN_CHAIN")

    def test_19_missing_local_never_closes_three_layers(self):
        r, req, ev = fixture({})
        result = V.calculate(V.observe(r, req, []))
        self.assertEqual(result["classification"], "UNKNOWN_BINDING")
        self.assertFalse(result["three_layers_equal"])
        self.assertIsNone(result["W_L_equal"])

    def test_20_changed_body_unchanged_meta_and_pin(self):
        d = SCRATCH / "changed_body"
        d.mkdir()
        p = d / "input.bin"
        p.write_bytes(b"original")
        V.pinned(p, V.sha(b"original"))
        p.write_bytes(b"modified")
        with self.assertRaises(V.Invalid) as e:
            V.pinned(p, V.sha(b"original"))
        self.assertEqual(str(e.exception), "INPUT_PIN_MISMATCH")
        m = {"seq": 1, "request_body_sha256": V.sha(b"q"), "request_body_bytes": 1,
             "response_body_sha256": V.sha(b"original"), "response_body_bytes": 8,
             "upstream_status": 200, "response_framing": "rechunked",
             "response_headers": {"Content-Type": "text/event-stream"}}
        with self.assertRaises(V.Unknown):
            V.meta_binding(m, 1, b"q", b"modified")

    def test_21_crlf_comments_and_multiline_data(self):
        raw = wire({}, crlf=True)
        c, _ = V.parse_sse(b": comment\r\nevent: message\r\n\r\n" + raw)
        self.assertEqual(c["args"], {})
        obj = V.canon(frame({"tool_calls": [tc("{}", "bash", "x")]})).decode()
        point = obj.index('"delta"')
        raw = ("data: " + obj[:point] + "\ndata: " + obj[point:] + "\n\n").encode()
        raw += b"data: " + V.canon(frame({}, "tool_calls")) + b"\n\ndata: [DONE]\n\n"
        self.assertEqual(V.parse_sse(raw)[0]["args"], {})

    def test_22_interleaved_tool_indices(self):
        fs = [frame({"tool_calls": [tc('{"com', "bash", "target", 1), tc("{}", "read", "other", 0)]}),
              frame({"tool_calls": [tc('mand":"x"}', index=1)]}), frame({}, "tool_calls")]
        raw = b"".join(b"data: " + V.canon(f) + b"\n\n" for f in fs) + b"data: [DONE]\n\n"
        c, _ = V.parse_sse(raw)
        self.assertEqual(c["args"], {"command": "x"})
        self.assertEqual(c["tool_index"], 1)

    def test_23_conflicting_id_or_finish(self):
        fs = [frame({"tool_calls": [tc("{", "bash", "one")]}),
              frame({"tool_calls": [tc("}", ident="two")]}), frame({}, "tool_calls")]
        raw = b"".join(b"data: " + V.canon(f) + b"\n\n" for f in fs) + b"data: [DONE]\n\n"
        self.unknown_stream(raw)
        raw = wire({}).replace(b"data: [DONE]", b"data: " + V.canon(frame({}, "tool_calls")) + b"\n\ndata: [DONE]")
        self.unknown_stream(raw)

    def test_24_data_after_done_and_unsupported_delta(self):
        self.unknown_stream(wire({}) + b'data: {"choices":[]}\n\n')
        self.unknown_stream(wire({}) + b'data: [DONE]\n\n')
        raw = b'data: {"choices":[{"index":0,"delta":{"unknown":"x"}}]}\n\ndata: [DONE]\n\n'
        with self.assertRaises(V.Unknown) as e:
            V.parse_sse(raw)
        self.assertEqual(e.exception.kind, "UNKNOWN_SHAPE")

    def test_25_shape_object_only_and_surrogates(self):
        for text in ("[]", "null", '"{}"', "1"):
            with self.assertRaises(V.Unknown) as e:
                V.parse_sse(wire(text))
            self.assertEqual(e.exception.kind, "UNKNOWN_SHAPE")
        with self.assertRaises(V.Invalid):
            V.loads('"\\ud800"')

    def test_26_intermediate_mutation_is_not_hidden_by_WH(self):
        ob = self.observation({}, l={"description": "changed"}, h={})
        result = V.calculate(ob)
        self.assertTrue(result["W_H_equal"])
        self.assertFalse(result["three_layers_equal"])
        self.assertEqual(result["classification"], "ARGUMENT_CHANGED_IN_CHAIN")
        self.assertEqual(result["changed_intervals"], ["W_L", "L_H"])

    def test_27_missing_stream_no_zero_imputation(self):
        r, req, ev = fixture({})
        result = V.calculate(V.observe(r[:-20], req, ev))
        self.assertIn(result["classification"], V.UNKNOWNS)
        self.assertIsNone(result["source_missing_in_captured_response"])

    def test_28_source_event_seq_and_error_text(self):
        for kind in ("seq", "text", "isError"):
            r, req, ev = fixture({})
            if kind == "seq":
                ev[1]["sourceEventSeqs"] = [9]
            elif kind == "text":
                ev[1]["data"]["message"]["content"][0]["text"] = "other"
            else:
                ev[1]["data"]["message"]["isError"] = False
            self.assertEqual(V.calculate(V.observe(r, req, ev))["classification"], "UNKNOWN_BINDING")

    def test_29_unknown_schema_restriction(self):
        r, req, ev = fixture({"command": ""})
        req[0][1]["tools"][0]["function"]["parameters"]["properties"]["command"]["minLength"] = 1
        self.assertEqual(V.calculate(V.observe(r, req, ev))["classification"], "UNKNOWN_SHAPE")

    def test_30_cli_replay_and_fail_closed(self):
        d = SCRATCH / "cli"
        d.mkdir()
        out = d / "result.json"
        cmd = [sys.executable, "-B", str(HERE / "verify.py"), "--output", str(out)]
        r = subprocess.run(cmd, capture_output=True, timeout=15)
        self.assertEqual(r.returncode, 0, r.stderr.decode())
        self.assertEqual(V.sha(out.read_bytes()), r.stdout.decode().strip())
        old = out.read_bytes()
        r = subprocess.run(cmd, capture_output=True, timeout=15)
        self.assertEqual(r.returncode, 2)
        self.assertEqual(out.read_bytes(), old)
        bad = d / "bad-evidence.json"
        bad.write_bytes(b'{"schema":"tampered"}')
        failed = d / "failed.json"
        r = subprocess.run([sys.executable, "-B", str(HERE / "verify.py"), "--evidence", str(bad),
                            "--output", str(failed)], capture_output=True, timeout=15)
        self.assertEqual(r.returncode, 2)
        self.assertFalse(failed.exists())
        r = subprocess.run([sys.executable, "-B", str(HERE / "verify.py")], capture_output=True, timeout=15)
        self.assertNotEqual(r.returncode, 0)
        r = subprocess.run([sys.executable, "-B", str(HERE / "verify.py"), "--archive-root", "unused",
                            "--output", str(failed)], capture_output=True, timeout=15)
        self.assertEqual(r.returncode, 2)
        self.assertFalse(failed.exists())

    def test_31_duplicate_indices_and_bool_index(self):
        choices = [frame({})["choices"][0], frame({})["choices"][0]]
        duplicate_choice = b"data: " + V.canon({"choices": choices}) + b"\n\ndata: [DONE]\n\n"
        duplicate_tool = b"data: " + V.canon(frame({"tool_calls": [tc("{", "bash", "x"), tc("}")]})) + b"\n\ndata: [DONE]\n\n"
        boolean_index = b"data: " + V.canon(frame({"tool_calls": [tc("{}", "bash", "x", True)]})) + b"\n\ndata: [DONE]\n\n"
        for raw in (duplicate_choice, duplicate_tool, boolean_index):
            with self.subTest(raw_sha=V.sha(raw)):
                with self.assertRaises(V.Unknown) as e:
                    V.parse_sse(raw)
                self.assertEqual(e.exception.kind, "UNKNOWN_SHAPE")

    def test_32_preexisting_id_is_not_a_new_response_call(self):
        r, req, ev = fixture({})
        req[0][1]["messages"].append({"role": "assistant", "tool_calls": [
            {"id": "synthetic-one", "type": "function", "function": {"name": "bash", "arguments": "{}"}}]})
        self.assertEqual(V.calculate(V.observe(r, req, ev))["classification"], "UNKNOWN_BINDING")

    def test_33_target_absent_and_nonstring_fragment(self):
        for raw in (wire({}).replace(b'"bash"', b'"read"'),
                    b"data: " + V.canon(frame({"tool_calls": [tc({}, "bash", "x")]})) + b"\n\ndata: [DONE]\n\n"):
            with self.assertRaises(V.Unknown) as e:
                V.parse_sse(raw)
            self.assertIn(e.exception.kind, {"UNKNOWN_BINDING", "UNKNOWN_SHAPE"})

    def test_34_public_evidence_whitespace_is_not_an_unsealed_input(self):
        d = SCRATCH / "evidence_whitespace"
        d.mkdir()
        p = d / "changed.json"
        p.write_bytes((HERE / "evidence.json").read_bytes() + b" ")
        out = d / "result.json"
        r = subprocess.run([sys.executable, "-B", str(HERE / "verify.py"),
                            "--evidence", str(p), "--output", str(out)],
                           capture_output=True, timeout=15)
        self.assertEqual(r.returncode, 2)
        self.assertFalse(out.exists())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--scratch-root", required=True)
    args, rest = parser.parse_known_args()
    SCRATCH = pathlib.Path(args.scratch_root).resolve()
    SCRATCH.mkdir(parents=False, exist_ok=False)
    unittest.main(argv=[sys.argv[0]] + rest)
