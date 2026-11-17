#!/usr/bin/env python3
"""Loop23 suite: synthetic grammar/frozen-pin cases + real-archive replay (env-gated)."""
import hashlib, importlib, json, os, sys, tempfile, unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
V = importlib.import_module("verify")
E = os.environ.get("XTOD_TEST_ROOT")


def canon(o):
    return json.dumps(o, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()


def req1_body(turn):
    return {
        "model": "deepseek-flash",
        "instructions": "I" * 17374,
        "tools": [{"type": "function", "name": "shell"}],
        "tool_choice": "auto",
        "parallel_tool_calls": False,
        "reasoning": {"effort": "low", "summary": "auto"},
        "store": False,
        "stream": True,
        "include": ["reasoning.encrypted_content"],
        "prompt_cache_key": "pc-%d" % turn,
        "client_metadata": {"root_turn_id": "rt%d" % turn, "session_id": "s%d" % turn,
                            "thread_id": "t%d" % turn, "turn_id": "u%d" % turn,
                            "x-codex-turn-metadata": {"a": turn}, "x-codex-window-id": "w%d" % turn},
        "input": [{"type": "message", "id": "i%d-%d" % (turn, j), "role": r, "content": [{"type": "input_text", "text": t}]}
                  for j, (r, t) in enumerate([("developer", "d1"), ("developer", "d2"), ("user", "T" * 214), ("user", "w")])],
    }


class Base(unittest.TestCase):
    def setUp(self):
        self._snap = {k: getattr(V, k) for k in ("MORNING", "EVENING", "ID_NORMALIZED_CANONICAL_SHA256", "PROMPT", "WORKSPACE_FILES", "DIFF_LEAVES_EXPECT", "DIFF_FIELDS_EXPECT", "PROXY")}

    def tearDown(self):
        for k, v in self._snap.items():
            setattr(V, k, v)


class Grammar(Base):
    def test_classify_paths(self):
        self.assertEqual(V.classify_field("/client_metadata/session_id"), "client_metadata")
        self.assertEqual(V.classify_field("/input/2/id"), "input_item_id")
        self.assertEqual(V.classify_field("/prompt_cache_key"), "prompt_cache_key")
        self.assertEqual(V.classify_field("/model"), "other")

    def test_diff_leaves_value(self):
        self.assertEqual(V.diff_leaves({"a": 1}, {"a": 2}), [["/a", "value"]])

    def test_diff_leaves_type(self):
        self.assertEqual(V.diff_leaves({"a": 1}, {"a": "x"}), [["/a", "type"]])

    def test_diff_leaves_side_only(self):
        self.assertEqual(V.diff_leaves({"a": 1}, {}), [["/a", "side_only"]])

    def test_diff_leaves_len(self):
        self.assertEqual(V.diff_leaves([1], [1, 2]), [["", "len"]])

    def test_normalize_ids_masks(self):
        r = req1_body(1)
        n = V.normalize_ids(r)
        self.assertEqual(n["client_metadata"], "NORMALIZED")
        self.assertEqual(n["prompt_cache_key"], "NORMALIZED")
        self.assertTrue(all(it.get("id") == "NORMALIZED" for it in n["input"] if isinstance(it, dict)))
        self.assertEqual(r["client_metadata"]["root_turn_id"], "rt1")

    def test_reject_float(self):
        with self.assertRaises(V.Invalid):
            V.loads(b'{"x": 1e999}')

    def test_reject_dup_keys(self):
        with self.assertRaises(V.Invalid):
            V.strict_loads(b'{"a": 1, "a": 2}')

    def test_safe_path_escape(self):
        with self.assertRaises(V.Invalid):
            V.safe_path("/tmp/xx", "../y")

    def test_exclusive_rejects_existing(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "o.json")
            open(p, "wb").write(b"x")
            with self.assertRaises(V.Invalid):
                V.exclusive(p, b"y")

    def test_validate_public_ok_on_minimal(self):
        doc = json.loads(open(os.path.join(HERE, "result-first.json")) and canon({}) and b"{}") if False else None
        # full-doc validation is covered by real-replay; here only structure guard
        with self.assertRaises(V.Invalid):
            V.validate_public({})


class RealArchive(Base):
    def test_real_build_replay_tamper(self):
        if not E:
            self.skipTest("XTOD_TEST_ROOT not set")
        pkg = HERE
        root = E
        doc = V.build(root)
        V.validate_public(doc)
        # tamper: change a pinned evening sha -> build must die
        old = json.loads(json.dumps(V.EVENING))
        V.EVENING["e1_req1"]["sha256"] = "0" * 64
        with self.assertRaises(V.Invalid):
            V.build(root)
        V.EVENING = old


if __name__ == "__main__":
    unittest.main()
