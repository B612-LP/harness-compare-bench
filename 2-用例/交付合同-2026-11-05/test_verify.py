"""Static synthetic tests: no legacy import, candidate execution or SQL execution."""
import ast
from contextlib import contextmanager
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
spec = importlib.util.spec_from_file_location("delivery_contract_verify", HERE / "verify.py")
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)  # Only this package's NEW static verifier, never old checker.


class ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="delivery-contract-test-")
        cls.root = Path(cls.temp.name)
        bindings = json.loads((HERE / "source-bindings.json").read_text(encoding="utf-8"))
        # Clone just frozen bytes into a temporary synthetic workspace. Even
        # legacy .py files are copied as bytes, never imported or executed.
        rels = [str(v.PACK / name) for name in v.PINS]
        rels += [str(v.PACK / "verify.py")]
        rels += [item["path"] for item in bindings["sources"]]
        for rel in rels:
            dest = cls.root / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / rel, dest)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    @contextmanager
    def altered(self, rel, data):
        path = self.root / rel
        before = path.read_bytes()
        path.write_bytes(data)
        try:
            yield
        finally:
            path.write_bytes(before)

    def reject(self, rel, data, prefix):
        with self.altered(rel, data):
            report = v.verify(self.root)
            self.assertFalse(report["pass"])
            self.assertTrue(any(e.startswith(prefix) for e in report["errors"]), report)

    def test_real_sources_pass(self):
        report = v.verify(ROOT)
        self.assertTrue(report["pass"], report)
        self.assertEqual(report["legacy_sources_checked"], 33)
        self.assertFalse(report["sql_checker_candidate_execution"])

    def test_fresh_public_subset_passes_without_private_files(self):
        self.assertTrue(v.verify(self.root)["pass"])

    def test_verifier_read_only(self):
        bindings = json.loads((HERE / "source-bindings.json").read_text(encoding="utf-8"))
        paths = [ROOT / item["path"] for item in bindings["sources"]]
        paths += [HERE / name for name in v.PINS]
        before = [hashlib.sha256(p.read_bytes()).hexdigest() for p in paths]
        v.verify(ROOT)
        self.assertEqual(before, [hashlib.sha256(p.read_bytes()).hexdigest() for p in paths])

    def test_prompt_changed_rejected(self):
        rel = v.PACK / "bird-instruction.md"
        self.reject(rel, (self.root / rel).read_bytes() + b"\nchanged\n", "package_sha256:")

    def test_prompt_and_entry_resealed_rejected(self):
        prompt_rel = v.PACK / "bird-instruction.md"
        data = (self.root / prompt_rel).read_bytes() + b"\nchanged\n"
        entry_rel = v.PACK / "currentpack.json"
        entry = json.loads((self.root / entry_rel).read_text(encoding="utf-8"))
        entry["cases"][0]["agent_instruction_sha256"] = v.digest(data)
        with self.altered(prompt_rel, data):
            self.reject(entry_rel, json.dumps(entry).encode(), "package_sha256:")

    def test_contract_relaxed_rejected(self):
        rel = v.PACK / "contract.json"
        contract = json.loads((self.root / rel).read_text(encoding="utf-8"))
        contract["bird"]["exact_row_keys"].append("verified")
        self.reject(rel, json.dumps(contract).encode(), "package_sha256:")

    def test_cargo_data_immutable_but_application_code_mutable(self):
        contract = json.loads((HERE / "contract.json").read_text(encoding="utf-8"))
        self.assertFalse(contract["cargo"]["data_mutation_allowed"])
        self.assertTrue(contract["cargo"]["application_code_mutation_allowed"])
        self.assertNotIn("input_mutation_allowed", contract["cargo"])
        self.assertEqual(len(contract["cargo"]["immutable_data_paths"]), 4)
        self.assertFalse(contract["bird"]["input_mutation_allowed"])

    def test_cargo_root_json_policy_changed_rejected(self):
        rel = v.PACK / "contract.json"
        contract = json.loads((self.root / rel).read_text(encoding="utf-8"))
        contract["cargo"]["root_json"] = "required-scoring-source"
        self.reject(rel, json.dumps(contract).encode(), "package_sha256:")

    def test_checker_changed_rejected_without_running_it(self):
        rel = Path("2-用例/tb-cargo-plan/checker.py")
        self.reject(rel, b"raise RuntimeError('MUST NOT EXECUTE')\n", "legacy_source_sha256:")

    def test_missing_input_rejected(self):
        rel = Path("2-用例/bird-ca-schools-15/inputs/questions.json")
        path = self.root / rel
        before = path.read_bytes()
        # A temporary fixture missing-file mutation; exact target is known.
        path.unlink()
        try:
            self.assertFalse(v.verify(self.root)["pass"])
        finally:
            path.write_bytes(before)

    def test_source_changed_and_manifest_resealed_rejected(self):
        rel = Path("2-用例/tb-cargo-plan/inputs/app/data/aircraft.json")
        data = b"{}\n"
        manifest_rel = v.PACK / "source-bindings.json"
        manifest = json.loads((self.root / manifest_rel).read_text(encoding="utf-8"))
        for source in manifest["sources"]:
            if source["path"] == str(rel):
                source["sha256"] = v.digest(data)
        with self.altered(rel, data):
            self.reject(manifest_rel, json.dumps(manifest).encode(), "package_sha256:")

    def test_agent_staging_answer_leak_rejected(self):
        rel = v.PACK / "currentpack.json"
        entry = json.loads((self.root / rel).read_text(encoding="utf-8"))
        entry["cases"][0]["staging"].append({"source": "2-用例/bird-ca-schools-15/truth.json", "destination": "inputs/truth.json"})
        self.reject(rel, json.dumps(entry).encode(), "package_sha256:")

    def test_path_traversal_and_absolute_rejected(self):
        for rel in ("../outside", "/outside", "inputs/../../outside"):
            with self.subTest(rel=rel), self.assertRaises(ValueError):
                v.safe_path(self.root, rel)

    def test_symlink_rejected(self):
        link = self.root / "test-link"
        link.symlink_to(HERE / "verify.py")
        try:
            with self.assertRaises(ValueError):
                v.safe_path(self.root, "test-link")
        finally:
            link.unlink()

    def test_no_execution_capabilities_in_verifier(self):
        tree = ast.parse((HERE / "verify.py").read_text(encoding="utf-8"))
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name for alias in node.names)
            if isinstance(node, ast.ImportFrom):
                imports.add(node.module)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                self.assertNotIn(node.func.id, {"exec", "eval", "compile", "__import__"})
        self.assertLessEqual(imports, {"argparse", "hashlib", "json", "pathlib", "re", "sys"})

    def test_cli_normal_and_optimized_identical_and_read_only(self):
        # Execute ONLY the new public static verifier; root fixtures contain
        # an old checker replaced with a trap in other tests, never invoked.
        script = HERE / "verify.py"
        reports = []
        for flags in (["-B"], ["-O", "-B"]):
            proc = subprocess.run([sys.executable] + flags + [str(script), "--root", str(self.root)], capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
            reports.append(json.loads(proc.stdout))
        self.assertEqual(reports[0], reports[1])
        rel = v.PACK / "cargo-instruction.md"
        with self.altered(rel, b"wrong prompt\n"):
            for flags in (["-B"], ["-O", "-B"]):
                proc = subprocess.run([sys.executable] + flags + [str(script), "--root", str(self.root)], capture_output=True, text=True)
                self.assertEqual(proc.returncode, 1, proc.stdout)
                self.assertFalse(json.loads(proc.stdout)["pass"])


class SyntheticBirdFormatTests(unittest.TestCase):
    def rows(self):
        # Deliberately meaningless query strings: not task answers; never run.
        return [{"question_id": qid, "sql": "SELECT 1"} for qid in sorted(v.QIDS)]

    def errors(self, rows):
        return v.bird_delivery_errors("\n".join(json.dumps(row) for row in rows))

    def test_synthetic_two_keys_pass_format_only(self):
        self.assertEqual(self.errors(self.rows()), [])

    def test_extra_key_rejected_even_with_full_coverage(self):
        rows = self.rows()
        rows[0]["verified"] = True
        self.assertTrue(any(e.startswith("exact_row_keys") for e in self.errors(rows)))

    def test_missing_key_rejected(self):
        rows = self.rows()
        del rows[0]["sql"]
        self.assertTrue(self.errors(rows))

    def test_outside_literal_comment_rejected(self):
        rows = self.rows()
        rows[0]["sql"] = "SELECT 1 -- success"
        self.assertTrue(any(e.startswith("sql_comment") for e in self.errors(rows)))

    def test_inside_literal_and_escaped_quote_allowed(self):
        rows = self.rows()
        rows[0]["sql"] = "SELECT 'a''--b'"
        self.assertEqual(self.errors(rows), [])

    def test_inside_literal_does_not_hide_later_comment(self):
        rows = self.rows()
        rows[0]["sql"] = "SELECT 'a''--b' -- outside"
        self.assertTrue(any(e.startswith("sql_comment") for e in self.errors(rows)))

    def test_double_quote_does_not_mask_hyphens(self):
        rows = self.rows()
        rows[0]["sql"] = 'SELECT "--"'
        self.assertTrue(any(e.startswith("sql_comment") for e in self.errors(rows)))

    def test_duplicate_and_missing_id_rejected(self):
        rows = self.rows()
        rows[-1]["question_id"] = rows[0]["question_id"]
        self.assertIn("question_coverage", self.errors(rows))

    def test_16_lines_and_invalid_extra_json_rejected(self):
        text = "\n".join(json.dumps(row) for row in self.rows()) + "\nnot-json"
        self.assertTrue(v.bird_delivery_errors(text))

    def test_bool_rejected_by_canonical_preflight(self):
        rows = self.rows()
        rows[0]["question_id"] = True
        self.assertTrue(self.errors(rows))

    def test_nonfinite_rejected_by_canonical_preflight(self):
        for constant in ("NaN", "Infinity", "-Infinity"):
            with self.subTest(constant=constant):
                rows = self.rows()
                original = "\n".join(json.dumps(row) for row in rows)
                self.assertIn('"question_id": 5', original)
                text = original.replace('"question_id": 5', '"question_id": ' + constant, 1)
                self.assertIn(constant, text)
                self.assertNotEqual(original, text)
                # Prove strict JSON rejection, not merely missing-ID failure.
                self.assertIn("json:1", v.bird_delivery_errors(text))

    def test_duplicate_json_key_rejected_by_canonical_preflight(self):
        text = "\n".join(json.dumps(row) for row in self.rows())
        text = text.replace('"sql": "SELECT 1"', '"sql": "SELECT 1", "sql": "SELECT 2"', 1)
        self.assertTrue(v.bird_delivery_errors(text))

    def test_not_a_scorer(self):
        # A non-SQL string still passes FORMAT ONLY: no correctness claim.
        rows = self.rows()
        rows[0]["sql"] = "this is not executable SQL"
        self.assertEqual(self.errors(rows), [])


if __name__ == "__main__":
    unittest.main()
