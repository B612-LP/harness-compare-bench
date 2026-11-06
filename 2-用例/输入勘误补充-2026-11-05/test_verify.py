#!/usr/bin/env python3
"""New-code-only tests. Run only after source review and explicit execution approval."""
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import types
import unittest
from unittest import mock

# Compile the exact reviewed sibling bytes; do not load repository modules or pyc.
VERIFIER_SHA256 = "97a607d5b3c2ecce708871aa166c8120311e6f7867fc421165749b612e84a0fe"
MODULE_PATH = Path(__file__).resolve().with_name("verify.py")
if MODULE_PATH.is_symlink():
    raise ValueError("linked test dependency")
MODULE_BYTES = MODULE_PATH.read_bytes()
if hashlib.sha256(MODULE_BYTES).hexdigest() != VERIFIER_SHA256:
    raise ValueError("test verifier source SHA mismatch")
V = types.ModuleType("mcc_reviewed_verifier")
V.__file__ = str(MODULE_PATH)
exec(compile(MODULE_BYTES, str(MODULE_PATH), "exec"), V.__dict__)


class DocumentSemantics(unittest.TestCase):
    """No fixture, filesystem, collect_sources, or hash-mocking in these cases."""
    def document(self):
        return copy.deepcopy(V.expected_document())

    def reject(self, mutate):
        document = self.document()
        mutate(document)
        with self.assertRaises(ValueError):
            V.validate_document(document)

    def test_positive_exact_local_labels(self):
        document = self.document()
        V.validate_document(document)
        self.assertEqual([row["mcc"] for row in document["conflicts"]], ["5451", "5812", "5521"])
        self.assertEqual([row["dictionary"]["description"] for row in document["conflicts"]], [
            "Dairy Products Stores", "Eating Places and Restaurants",
            "Car and Truck Dealers (Used Only) - Sales, Service, Repairs, Parts, and Leasing",
        ])
        self.assertEqual(document["q1305"]["gold"]["value"], "0.123217")
        self.assertIs(document["q1305"]["recomputed"], False)

    def test_csv_index_is_not_mcc(self):
        for index, wrong in enumerate(("495", "535", "499")):
            with self.subTest(index=index):
                self.reject(lambda d: d["conflicts"][index].__setitem__("mcc", wrong))

    def test_wrong_primary_code(self):
        self.reject(lambda d: d["conflicts"][0].__setitem__("mcc", "9999"))

    def test_auxiliary_does_not_replace_original(self):
        for index, wrong in enumerate(("5542", "5533", "5511")):
            with self.subTest(index=index):
                self.reject(lambda d: d["conflicts"][index].__setitem__("mcc", wrong))

    def test_wrong_same_code_labels(self):
        for index in range(3):
            with self.subTest(index=index):
                self.reject(lambda d: d["conflicts"][index]["dictionary"].__setitem__(
                    "description", d["conflicts"][index]["manual"]["description"]))

    def test_truncated_5521_label(self):
        self.reject(lambda d: d["conflicts"][2]["dictionary"].__setitem__("description", "Used Only"))

    def test_missing_third_example(self):
        self.reject(lambda d: d["conflicts"].pop())

    def test_duplicate_or_reordered_examples(self):
        self.reject(lambda d: d["conflicts"].append(copy.deepcopy(d["conflicts"][0])))
        self.reject(lambda d: d["conflicts"].reverse())

    def test_auxiliary_label_not_manual_synonym(self):
        self.reject(lambda d: d["conflicts"][1]["auxiliary"].__setitem__(
            "description", "Automotive Parts and Accessories Stores"))

    def test_auxiliary_role_not_replacement(self):
        self.reject(lambda d: d["conflicts"][0]["auxiliary"].__setitem__("role", "replacement"))

    def test_fabricated_historical_priority(self):
        self.reject(lambda d: d["boundaries"].__setitem__("prior_conflict_priority_rule_established", True))
        self.reject(lambda d: d["boundaries"].__setitem__("dictionary_policy", "existing_official_priority"))

    def test_fabricated_gold_correction(self):
        self.reject(lambda d: d["boundaries"].__setitem__("gold_changed", True))
        self.reject(lambda d: d["q1305"].__setitem__("recomputed", True))
        self.reject(lambda d: d["q1305"].__setitem__("correctness", "verified"))
        self.reject(lambda d: d["q1305"]["gold"].__setitem__("value", "0.000000"))

    def test_fabricated_no_effect_or_product_use(self):
        for key, wrong in (("scoring_impact", "none"), ("future_behavior_unchanged", True),
                           ("historical_product_use", "confirmed")):
            with self.subTest(key=key):
                self.reject(lambda d: d["boundaries"].__setitem__(key, wrong))
        self.reject(lambda d: d["q1305"].__setitem__("historical_effect", "none"))

    def test_new_inputs_need_registration(self):
        self.reject(lambda d: d["boundaries"].__setitem__("future_input_requires_registration", False))

    def test_no_new_n_regrading_scope_or_license(self):
        for key, wrong in (("formal_rows_added", 1), ("new_product_runs", 1),
                           ("historical_scores_changed", True), ("old_sources_modified", True),
                           ("q49_scope_changed", True), ("q2697_scope_changed", True),
                           ("new_license_granted", True), ("legal_compliance_certified", True)):
            with self.subTest(key=key):
                self.reject(lambda d: d["boundaries"].__setitem__(key, wrong))
        self.reject(lambda d: d.__setitem__("conflict_class_count", 3))

    def test_boolean_not_integer_and_integer_not_boolean(self):
        self.reject(lambda d: d.__setitem__("conflict_class_count", True))
        self.reject(lambda d: d["conflicts"][0]["manual"].__setitem__("line", True))
        self.reject(lambda d: d["boundaries"].__setitem__("formal_rows_added", False))
        self.reject(lambda d: d["boundaries"].__setitem__("gold_changed", 0))
        self.reject(lambda d: d["q1305"].__setitem__("recomputed", 0))

    def test_reference_identity_and_source_claims(self):
        self.reject(lambda d: d["q1305"].__setitem__("line", 2))
        self.reject(lambda d: d["q1305"]["gold"].__setitem__("pointer", "/gold/1273"))
        self.reject(lambda d: d["conflicts"][0]["dictionary"].__setitem__("path", "../outside"))
        self.reject(lambda d: d["source_sha256"].__setitem__(V.MANUAL, "0" * 64))

    def test_missing_limit_or_added_claim(self):
        self.reject(lambda d: d["limits"].pop())
        self.reject(lambda d: d.__setitem__("historical_errata_was_supplied", True))
        self.reject(lambda d: d.pop("boundaries"))

    def test_new_errata_hash_cannot_admit_wrong_semantics(self):
        document = self.document()
        document["conflicts"][0]["mcc"] = "5542"
        encoded = json.dumps(document, ensure_ascii=False).encode("utf-8")
        self.assertEqual(len(hashlib.sha256(encoded).hexdigest()), 64)
        # No errata-file hash comparison occurs here: this is the pure relationship guard.
        with self.assertRaises(ValueError):
            V.validate_document(V.strict_json(encoded.decode("utf-8")))


class JSONAndPaths(unittest.TestCase):
    def test_duplicate_json_keys(self):
        for text in ('{"x":1,"x":2}', '{"x":{"a":1,"a":2}}'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                V.strict_json(text)

    def test_nonfinite_and_overflow(self):
        for token in ("NaN", "Infinity", "-Infinity", "1e9999"):
            with self.subTest(token=token), self.assertRaises(ValueError):
                V.strict_json('{"x":' + token + '}')
        with self.assertRaises(ValueError):
            V.validate_document(float("nan"))

    def test_json_type_and_size(self):
        for value in (None, True, 1, [], "object"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                V.validate_document(value)
        with self.assertRaises(ValueError):
            V.strict_json('"' + 'x' * V.MAX_BYTES + '"')
        with self.assertRaises(ValueError):
            V.validate_json({1: "non-string key"})

    def test_path_rejections(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            for relative in ("", "/etc/passwd", "../outside", "a/../b", "a/./b", "a//b", "a\\b", "a\x00b", "."):
                with self.subTest(relative=relative), self.assertRaises(ValueError):
                    V.safe_file(root, relative)

    def test_linked_root_or_ancestor(self):
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory).resolve()
            real = parent / "real"
            real.mkdir()
            (real / "child").mkdir()
            linked = parent / "linked"
            linked.symlink_to(real, target_is_directory=True)
            for root in (linked, linked / "child"):
                with self.subTest(root=root), self.assertRaises(ValueError):
                    V.canonical_root(root)

    def test_linked_parent_or_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            real = root / "real"
            real.mkdir()
            (real / "file").write_bytes(b"same bytes")
            (root / "linked").symlink_to(real, target_is_directory=True)
            (root / "file-link").symlink_to(real / "file")
            for relative in ("linked/file", "file-link"):
                with self.subTest(relative=relative), self.assertRaises(ValueError):
                    V.read_checked(root, relative)

    def test_hardlink_directory_and_oversize(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            (root / "first").write_bytes(b"same bytes")
            os.link(root / "first", root / "second")
            (root / "dir").mkdir()
            (root / "large").write_bytes(b"x" * (V.MAX_BYTES + 1))
            for relative in ("first", "second", "dir", "large"):
                with self.subTest(relative=relative), self.assertRaises(ValueError):
                    V.read_checked(root, relative)


class PinnedSourcesAndStability(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Explicit opt-in root for an approved staging test; final public layout needs no env.
        root = os.environ.get("MCC_TEST_ROOT")
        cls.root = V.canonical_root(Path(root) if root else MODULE_PATH.parents[2])
        cls.raw, cls.identities = V.collect_sources(cls.root)
        cls.document = V.analyze_sources(cls.raw)

    def fixture(self, omit=None):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name).resolve()
        for relative, data in self.raw.items():
            if relative != omit:
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
        target = root / V.ERRATA
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(self.document, ensure_ascii=False), encoding="utf-8")
        return root

    def test_actual_readonly_derivation_and_fixed_sources(self):
        before, identity = V.collect_sources(self.root)
        result = V.derive(self.root)
        after, final_identity = V.collect_sources(self.root)
        self.assertEqual(before, after)
        self.assertEqual(identity, final_identity)
        self.assertEqual(result["q1305"]["line"], 5)
        self.assertEqual(result["q1305"]["gold"]["pointer"], "/gold/1305")
        self.assertEqual(result["conflicts"][2]["dictionary"]["line"], 501)

    def test_packaged_errata_matches_pinned_source_derivation(self):
        package = V.canonical_root(MODULE_PATH.parent)
        encoded, identity = V.read_checked(package, "errata.json")
        document = V.strict_json(encoded.decode("utf-8"))
        V.validate_document(document)
        V.same_typed(document, V.analyze_sources(self.raw))
        after, after_identity = V.read_checked(package, "errata.json")
        self.assertEqual(encoded, after)
        self.assertEqual(identity, after_identity)

    def test_fixture_verify_and_derive_agree_without_subprocess_network(self):
        root = self.fixture()
        with mock.patch.object(subprocess, "Popen", side_effect=RuntimeError("forbidden subprocess")), \
                mock.patch.object(socket, "socket", side_effect=RuntimeError("forbidden socket")):
            self.assertEqual(V.verify(root), V.derive(root))

    def test_every_fixed_source_pin_rejects_one_byte_drift(self):
        for relative in V.SOURCE_SHA256:
            with self.subTest(relative=relative):
                root = self.fixture()
                (root / relative).write_bytes(self.raw[relative] + b"\n")
                with self.assertRaisesRegex(ValueError, "fixed source SHA mismatch"):
                    V.derive(root)

    def test_missing_source(self):
        root = self.fixture(omit=V.MANUAL)
        with self.assertRaises(OSError):
            V.derive(root)

    def test_same_bytes_linked_source(self):
        root = self.fixture(omit=V.MANUAL)
        copy_path = root / "copy"
        copy_path.write_bytes(self.raw[V.MANUAL])
        (root / V.MANUAL).symlink_to(copy_path)
        with self.assertRaises(ValueError):
            V.derive(root)

    def test_source_mutation_during_analysis(self):
        root = self.fixture()
        original = V.analyze_sources

        def changing(raw):
            result = original(raw)
            (root / V.MANUAL).write_bytes(raw[V.MANUAL] + b"\n")
            return result

        with mock.patch.object(V, "analyze_sources", side_effect=changing):
            with self.assertRaisesRegex(ValueError, "source not stable"):
                V.derive(root)

    def test_source_metadata_mutation_even_with_same_bytes(self):
        root = self.fixture()
        original = V.analyze_sources

        def changing(raw):
            result = original(raw)
            path = root / V.MANUAL
            info = path.stat()
            os.utime(path, ns=(info.st_atime_ns, info.st_mtime_ns + 1000000000))
            return result

        with mock.patch.object(V, "analyze_sources", side_effect=changing):
            with self.assertRaisesRegex(ValueError, "source not stable"):
                V.derive(root)

    def test_errata_mutation_during_analysis(self):
        root = self.fixture()
        original = V.analyze_sources

        def changing(raw):
            result = original(raw)
            path = root / V.ERRATA
            path.write_bytes(path.read_bytes() + b"\n")
            return result

        with mock.patch.object(V, "analyze_sources", side_effect=changing):
            with self.assertRaisesRegex(ValueError, "errata not stable"):
                V.verify(root)

    def test_wrong_errata_not_just_pin_failure(self):
        root = self.fixture()
        document = copy.deepcopy(self.document)
        document["conflicts"][2]["dictionary"]["description"] = "New and Used"
        (root / V.ERRATA).write_text(json.dumps(document), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "value mismatch"):
            V.verify(root)

    def test_source_semantics_rejects_wrong_csv_mcc_without_hash_layer(self):
        raw = dict(self.raw)
        raw[V.DICTIONARY] = raw[V.DICTIONARY].replace(
            b"495,5451,Dairy Products Stores", b"495,0495,Dairy Products Stores", 1)
        self.assertNotEqual(raw[V.DICTIONARY], self.raw[V.DICTIONARY])
        with self.assertRaisesRegex(ValueError, "missing relevant dictionary MCC"):
            V.analyze_sources(raw)

    def test_source_semantics_rejects_same_code_wrong_label_even_resealed(self):
        raw = dict(self.raw)
        raw[V.DICTIONARY] = raw[V.DICTIONARY].replace(b"Dairy Products Stores", b"Automated Fuel Dispensers", 1)
        resealed = {name: hashlib.sha256(data).hexdigest() for name, data in raw.items()}
        self.assertNotEqual(resealed[V.DICTIONARY], V.SOURCE_SHA256[V.DICTIONARY])
        # TEST ONLY: grant even the changed source hashes. No production bypass is exposed.
        # The pure source relationship still fails specifically at dictionary.5451.
        with mock.patch.dict(V.SOURCE_SHA256, resealed, clear=True):
            with self.assertRaisesRegex(ValueError, r"dictionary\.5451"):
                V.analyze_sources(raw)

    def test_source_semantics_rejects_manual_rewrite_without_hash_layer(self):
        raw = dict(self.raw)
        raw[V.MANUAL] = raw[V.MANUAL].replace(b"5451 (Automated Fuel Dispensers)", b"5542 (Automated Fuel Dispensers)", 1)
        with self.assertRaisesRegex(ValueError, "manual line 44"):
            V.analyze_sources(raw)

    def test_cli_stdout_only_and_rebuild_not_errata_writer(self):
        root = self.fixture()
        errata_before = (root / V.ERRATA).read_bytes()
        for rebuild in (False, True):
            args = ["--root", str(root)] + (["--rebuild"] if rebuild else [])
            out, err = io.StringIO(), io.StringIO()
            with mock.patch("sys.stdout", out), mock.patch("sys.stderr", err):
                status = V.main(args)
            self.assertEqual(status, 0)
            self.assertEqual(err.getvalue(), "")
            V.validate_document(V.strict_json(out.getvalue()))
        self.assertEqual((root / V.ERRATA).read_bytes(), errata_before)

    def test_cli_failure_nonzero_and_no_json_success(self):
        root = self.fixture()
        (root / V.MANUAL).write_bytes(b"wrong")
        out, err = io.StringIO(), io.StringIO()
        with mock.patch("sys.stdout", out), mock.patch("sys.stderr", err):
            status = V.main(["--root", str(root)])
        self.assertEqual(status, 1)
        self.assertEqual(out.getvalue(), "")
        self.assertIn("fixed source SHA mismatch", err.getvalue())


if __name__ == "__main__":
    unittest.main(verbosity=2)
