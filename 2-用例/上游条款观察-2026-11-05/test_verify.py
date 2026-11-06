#!/usr/bin/env python3
"""Only this new verifier is loaded, explicitly at test runtime."""
from __future__ import annotations
import ast
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import types
import unittest
from unittest import mock

PACKAGE = Path(__file__).absolute().parent
SOURCE = PACKAGE / "verify.py"


class ReviewedModule(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v = types.ModuleType("reviewed_upstream")
        cls.v.__file__ = str(SOURCE)
        exec(compile(SOURCE.read_bytes(), str(SOURCE), "exec"), cls.v.__dict__)
        cls.fixture = cls.v.strict_json((PACKAGE / "observations.json").read_text(encoding="utf-8"))

    def document(self):
        return copy.deepcopy(self.fixture)

    def reject(self, document):
        with self.assertRaises(ValueError):
            self.v.validate_document(document)

    def observation(self, document, identity):
        return next(row for row in document["observations"] if row["id"] == identity)

    def capture(self, document, identity):
        return next(row for row in document["captures"] if row["id"] == identity)


class PureRelations(ReviewedModule):
    """No file-hash gate: mutate parsed objects and call the pure contract."""
    def test_valid_five_sources_three_bodies_and_failures(self):
        result = self.v.validate_document(self.document())
        self.assertEqual(result["public_complete_bodies"], 3)
        self.assertEqual([result[k] for k in ("http_200", "http_403", "http_404", "tls_without_http")], [7, 2, 2, 1])
        self.assertIs(result["new_license_granted"], False)

    def test_row_order_is_not_evidence(self):
        doc = self.document()
        doc["observations"].reverse()
        doc["captures"].reverse()
        self.assertEqual(self.v.validate_document(doc)["sources"], 5)

    def test_missing_extra_duplicate_source(self):
        for change in ("missing", "extra", "duplicate"):
            with self.subTest(change=change):
                doc = self.document()
                if change == "missing":
                    doc["observations"].pop()
                else:
                    row = copy.deepcopy(doc["observations"][0])
                    if change == "extra":
                        row["id"] = "sixth-project"
                    doc["observations"].append(row)
                self.reject(doc)

    def test_missing_extra_duplicate_capture(self):
        for change in ("missing", "extra", "duplicate"):
            with self.subTest(change=change):
                doc = self.document()
                if change == "missing":
                    doc["captures"].pop()
                else:
                    row = copy.deepcopy(doc["captures"][0])
                    if change == "extra":
                        row["id"] = "another-request"
                    doc["captures"].append(row)
                self.reject(doc)

    def test_notice_cannot_become_full_cc_legalcode(self):
        for key, value in (("full_legal_text", True), ("evidence_kind", "complete_cc_legalcode")):
            doc = self.document()
            self.observation(doc, "dabstep")[key] = value
            self.reject(doc)

    def test_lcb_mit_cannot_grant_atcoder_rights(self):
        doc = self.document()
        doc["boundaries"]["lcb_repo_mit_grants_atcoder_material_rights"] = True
        self.reject(doc)
        doc = self.document()
        self.observation(doc, "atcoder")["evidence_kind"] = "complete_mit_license"
        self.reject(doc)

    def test_current_commit_does_not_authenticate_history(self):
        doc = self.document()
        doc["boundaries"]["historical_material_applicability"] = {"status": "verified", "bound_version": self.v.EX}
        self.reject(doc)
        doc = self.document()
        self.observation(doc, "exercism")["version"] = "2026-10-22-authenticated"
        self.reject(doc)

    def test_exact_notice_404_not_global_absence(self):
        doc = self.document()
        self.capture(doc, "terminal-notice")["outcome"] = "repository_has_no_notice"
        self.reject(doc)
        doc = self.document()
        doc["boundaries"]["notice_coverage"] = {"status": "verified_absent", "recursive_and_space_complete": True}
        self.reject(doc)

    def test_403_error_body_not_source_content(self):
        for identity in ("terminal-tree", "terminal-task"):
            doc = self.document()
            self.capture(doc, identity)["outcome"] = "source_body"
            self.reject(doc)

    def test_tls35_has_no_http_body(self):
        for key, value in (("http_status", 404), ("http_status", 0), ("bytes", 14), ("curl_exit", 0), ("sha256", "0" * 64)):
            doc = self.document()
            self.capture(doc, "exercism-tree")[key] = value
            self.reject(doc)

    def test_curl_zero_not_relabelled_success(self):
        doc = self.document()
        self.capture(doc, "exercism-notice")["http_status"] = 200
        self.reject(doc)

    def test_fetch_service_error_not_origin_404(self):
        for key, value in (("layer", "origin"), ("source_http_status_known", True), ("count", 5)):
            doc = self.document()
            doc["service_fetch_errors"][key] = value
            self.reject(doc)

    def test_private_hash_not_full_public_html(self):
        for identity in ("bird", "atcoder"):
            for key, value in (("full_body_public", True), ("mirror", "full.html"), ("full_legal_text", True)):
                doc = self.document()
                self.observation(doc, identity)[key] = value
                self.reject(doc)
        doc = self.document()
        doc["boundaries"]["all_five_full_terms_public_offline"] = True
        self.reject(doc)

    def test_original_owner_not_selected_or_granted(self):
        for key, value in (("status", "selected"), ("value", "MIT"), ("authority", "agent")):
            doc = self.document()
            doc["boundaries"]["original_owner_license"][key] = value
            self.reject(doc)
        for key in ("new_license_granted", "legal_compliance_certified", "copyright_holder_chain_authenticated", "dataset_license_clears_space_scorer", "historical_scores_gold_n_changed"):
            doc = self.document()
            doc["boundaries"][key] = True
            self.reject(doc)

    def test_exact_utc_url_hash_and_byte_receipts(self):
        for key, value in (("start_utc", "2026-11-05T22:42:17Z"), ("end_utc", "2026-11-04T14:42:18Z"), ("url", "https://example.invalid/"), ("sha256", "0" * 64), ("bytes", 350032)):
            doc = self.document()
            self.capture(doc, "bird-home")[key] = value
            self.reject(doc)

    def test_version_scope_and_summary_cannot_expand(self):
        for key, value in (("version_kind", "immutable_commit"), ("excerpt", "different wording"), ("summary", "All historical material is legally cleared."), ("capture_id", "terminal-tree")):
            doc = self.document()
            self.observation(doc, "bird")[key] = value
            self.reject(doc)

    def test_strict_types_at_nested_numeric_and_boolean_fields(self):
        for key, value in (("http_status", True), ("http_status", 200.0), ("bytes", True), ("bytes", "350031"), ("curl_exit", False)):
            doc = self.document()
            self.capture(doc, "bird-home")[key] = value
            self.reject(doc)
        for value in (0, "false", None):
            doc = self.document()
            doc["boundaries"]["new_license_granted"] = value
            self.reject(doc)

    def test_unknown_keys_and_null_shapes(self):
        for place in ("root", "observation", "capture", "boundary"):
            doc = self.document()
            target = {"root": doc, "observation": doc["observations"][0], "capture": doc["captures"][0], "boundary": doc["boundaries"]}[place]
            target["extra"] = None
            self.reject(doc)
        for key in ("captures", "observations", "boundaries"):
            doc = self.document()
            doc[key] = None
            self.reject(doc)

    def test_duplicate_json_and_nonfinite_parser(self):
        for text in ('{"a":1,"a":2}', '{"x":{"a":1,"a":2}}', '{"x":NaN}', '{"x":Infinity}', '{"x":-Infinity}', '{"x":1e999}'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                self.v.strict_json(text)
        self.assertEqual(self.v.strict_json('{"x":[1,true,null]}'), {"x": [1, True, None]})

    def test_direct_nonfinite_or_nonjson_injection(self):
        for value in (float("nan"), float("inf"), float("-inf"), {1, 2}, b"bytes"):
            doc = self.document()
            doc["boundaries"]["extra"] = value
            self.reject(doc)
        for value in ([], None, True, 1, "not an object"):
            self.reject(value)


class ContentAndPaths(ReviewedModule):
    def test_three_content_conditions_without_hash(self):
        for name in self.v.MIRRORS:
            self.v.validate_mirror_content(name, (PACKAGE / name).read_bytes().decode("utf-8"))

    def test_removed_copyright_and_author_rejected_before_hash(self):
        for name, original, changed in (("exercism-MIT.txt", "Copyright (c) 2021 Exercism", "Copyright (c) 2021 SomeoneX"), ("dabstep-NOTICE.txt", "Thomas Wolf", "Someone Else")):
            text = (PACKAGE / name).read_bytes().decode("utf-8").replace(original, changed)
            self.assertNotIn(original, text)
            with self.assertRaises(ValueError):
                self.v.validate_mirror_content(name, text)

    def test_apache_template_and_conditions_not_replaced(self):
        name = "terminal-bench-Apache-2.0.txt"
        text = (PACKAGE / name).read_bytes().decode("utf-8")
        for original, changed in (("Copyright [yyyy] [name of copyright owner]", "Copyright 2026 Repository Owner"), ("(d) If the Work includes a \"NOTICE\"", "(d) No NOTICE obligations ever apply")):
            altered = text.replace(original, changed)
            self.assertNotEqual(altered, text)
            with self.assertRaises(ValueError):
                self.v.validate_mirror_content(name, altered)

    def test_crlf_bom_null_and_removed_line_rejected(self):
        name = "exercism-MIT.txt"
        text = (PACKAGE / name).read_bytes().decode("utf-8")
        for altered in (text.replace("\n", "\r\n"), "\ufeff" + text, text + "\x00", "\n".join(text.splitlines()[1:])):
            with self.assertRaises(ValueError):
                self.v.validate_mirror_content(name, altered)

    def populate(self, root):
        for name in ("observations.json",) + tuple(self.v.MIRRORS):
            (root / name).write_bytes((PACKAGE / name).read_bytes())

    def test_valid_readonly_derive_and_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            self.populate(root)
            before = {p.name: p.read_bytes() for p in root.iterdir()}
            result = self.v.derive(root)
            self.assertTrue(result["ok"])
            self.assertEqual(len(result["checked_sha256"]), 4)
            self.assertEqual(before, {p.name: p.read_bytes() for p in root.iterdir()})

    def test_each_mirror_byte_tamper_not_resealed_by_document(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            for name in self.v.MIRRORS:
                with self.subTest(name=name):
                    self.populate(root)
                    raw = (root / name).read_bytes()
                    # Change content not checked by phrase rules, then claim its SHA.
                    altered = raw.replace(b"software", b"softwarE", 1) if name == "exercism-MIT.txt" else raw + b" "
                    self.assertNotEqual(altered, raw)
                    (root / name).write_bytes(altered)
                    doc = self.document()
                    identity = {"exercism-MIT.txt": "exercism-license", "terminal-bench-Apache-2.0.txt": "terminal-license", "dabstep-NOTICE.txt": "dab-license"}[name]
                    self.capture(doc, identity)["sha256"] = hashlib.sha256(altered).hexdigest()
                    (root / "observations.json").write_text(json.dumps(doc), encoding="utf-8")
                    with self.assertRaises(ValueError):
                        self.v.derive(root)

    def test_mirror_pin_checks_beyond_content_phrases(self):
        replacements = {"exercism-MIT.txt": (b"software", b"softwarE"), "terminal-bench-Apache-2.0.txt": (b"Definitions.", b"DefinitionX."), "dabstep-NOTICE.txt": (b"Multi-step", b"Multi-Step")}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            for name, (old, new) in replacements.items():
                self.populate(root)
                raw = (root / name).read_bytes()
                altered = raw.replace(old, new, 1)
                self.assertNotEqual(altered, raw)
                self.assertEqual(len(altered), len(raw))
                self.v.validate_mirror_content(name, altered.decode("utf-8"))
                (root / name).write_bytes(altered)
                with self.assertRaisesRegex(ValueError, "mirror source SHA mismatch"):
                    self.v.derive(root)

    def test_missing_file_oversize_and_nonutf8(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            self.populate(root)
            (root / "observations.json").unlink()
            with self.assertRaises(OSError):
                self.v.derive(root)
            for raw in (b"x" * 262145, b"\xff"):
                (root / "observations.json").write_bytes(raw)
                with self.assertRaises((ValueError, UnicodeError)):
                    self.v.derive(root)

    def test_stat_then_growth_uses_bounded_read(self):
        fake_path = mock.MagicMock()
        fake_path.stat.return_value.st_size = 1
        fake_path.read_bytes.side_effect = AssertionError("unbounded read forbidden")
        stream = fake_path.open.return_value.__enter__.return_value

        def grown_read(limit):
            self.assertEqual(limit, 262145)
            return b"x" * limit

        stream.read.side_effect = grown_read
        with mock.patch.object(self.v, "safe_file", return_value=fake_path):
            with self.assertRaisesRegex(ValueError, "file grew beyond limit"):
                self.v.read_snapshot(PACKAGE)
        fake_path.stat.assert_called_once_with()
        fake_path.open.assert_called_once_with("rb")
        stream.read.assert_called_once_with(262145)
        fake_path.read_bytes.assert_not_called()

    def test_main_recursion_rejected_without_traceback(self):
        with mock.patch.object(self.v.argparse.ArgumentParser, "parse_args", return_value=types.SimpleNamespace(root=PACKAGE)):
            with mock.patch.object(self.v, "derive", side_effect=RecursionError("nested input")):
                with mock.patch("builtins.print") as output:
                    self.assertEqual(self.v.main(), 1)
        output.assert_called_once()
        self.assertEqual(self.v.strict_json(output.call_args[0][0]), {"ok": False, "error": "nested input"})

    def test_filename_traversal_and_absolute_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            self.populate(root)
            for name in ("../observations.json", "/tmp/observations.json", "nested/observations.json", "", "verify.py"):
                with self.assertRaises(ValueError):
                    self.v.safe_file(root, name)
            with self.assertRaises(ValueError):
                self.v.read_snapshot(root / ".." / root.name)

    def test_file_root_and_ancestor_symlinks_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            root = base / "real"
            root.mkdir()
            self.populate(root)
            link = base / "link"
            link.symlink_to(root, target_is_directory=True)
            with self.assertRaises(ValueError):
                self.v.derive(link)
            child = root / "child"
            child.mkdir()
            with self.assertRaises(ValueError):
                self.v.read_snapshot(link / "child")
            (root / "observations.json").unlink()
            (root / "observations.json").symlink_to(PACKAGE / "observations.json")
            with self.assertRaises(ValueError):
                self.v.derive(root)

    def test_source_change_between_snapshots_rejected(self):
        first = {name: (PACKAGE / name).read_bytes() for name in ("observations.json",) + tuple(self.v.MIRRORS)}
        second = dict(first)
        second["observations.json"] += b"\n"
        with mock.patch.object(self.v, "read_snapshot", side_effect=[first, second]):
            with self.assertRaisesRegex(ValueError, "source changed"):
                self.v.derive(PACKAGE)

    def test_production_ast_capabilities(self):
        tree = ast.parse(SOURCE.read_bytes())
        allowed = {"__future__", "argparse", "hashlib", "json", "math", "pathlib", "stat"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                self.assertTrue(all(alias.name in allowed for alias in node.names))
            elif isinstance(node, ast.ImportFrom):
                self.assertIn(node.module, allowed)
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    self.assertNotIn(node.func.id, {"exec", "eval", "compile", "open", "__import__"})
                elif isinstance(node.func, ast.Attribute):
                    self.assertNotIn(node.func.attr, {"write_text", "write_bytes", "unlink", "rename", "replace", "mkdir", "system", "popen"})
        self.assertFalse(any(isinstance(node, ast.Assert) for node in ast.walk(tree)))


if __name__ == "__main__":
    unittest.main()
