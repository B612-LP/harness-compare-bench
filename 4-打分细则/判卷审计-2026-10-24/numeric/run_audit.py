#!/usr/bin/env python3
"""Independent red/green regression; no model/network calls, temporary runs outside case bank."""
from __future__ import annotations
import ast
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BIRD = "bird-ca-schools-15"
DAB = "dabstep-payments-10"
ENV = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    receipts, failures = [], []
    frozen = HERE / "frozen"
    manifest = json.loads((frozen / "sha256.json").read_text())
    assert all(sha(frozen / rel) == digest for rel, digest in manifest.items())
    # Freeze contains only allowlisted trusted source/truth, never run configuration or credentials.
    assert {str(p.relative_to(frozen)) for p in frozen.rglob("*") if p.is_file()} == set(manifest) | {"sha256.json"}

    def record(name, ok, **details):
        receipts.append(dict(name=name, pass_=bool(ok), **details))
        if not ok:
            failures.append(name)
        print(("PASS " if ok else "FAIL ") + name)

    official_functions = ("is_numeric_with_commas", "question_scorer", "extract_numeric",
                          "compare_numeric", "compare_strings", "compare_lists")
    def functions(path):
        tree = ast.parse(path.read_text())
        return {node.name: ast.dump(node, include_attributes=False) for node in tree.body
                if isinstance(node, ast.FunctionDef) and node.name in official_functions}
    old_funcs = functions(frozen / DAB / "checker.py")
    new_funcs = functions(ROOT / "2-用例" / DAB / "checker.py")
    record("official_scorer_functions_unchanged", len(old_funcs) == 6 and old_funcs == new_funcs)

    with tempfile.TemporaryDirectory(prefix="numeric-grader-audit-") as tmp:
        temp = Path(tmp).resolve()
        assert not temp.is_relative_to(ROOT), "temporary work must stay outside repository/case bank"
        staged = {}
        for case in (BIRD, DAB):
            dst = temp / "frozen" / case
            dst.mkdir(parents=True)
            for file in ("checker.py", "truth.json"):
                shutil.copyfile(frozen / case / file, dst / file)
            for name in ("inputs", "solution"):
                (dst / name).symlink_to(ROOT / "2-用例" / case / name, target_is_directory=True)
            staged[case] = dst

        def run(name, case, source, answers, *, scoring=None, artifact_dir="", expect_reward=1,
                expected_correct=None, expected_question=None, expected_pass=None):
            run_dir = temp / "runs" / name
            target = run_dir / artifact_dir
            target.mkdir(parents=True)
            (target / "answers.jsonl").write_text(answers, encoding="utf-8")
            checker = (staged[case] if source == "before" else ROOT / "2-用例" / case) / "checker.py"
            command = [sys.executable, str(checker), str(run_dir), "--json"]
            if scoring:
                command += ["--scoring", scoring]
            proc = subprocess.run(command, text=True, capture_output=True, env=ENV, timeout=180)
            try:
                result = json.loads(proc.stdout)
            except ValueError:
                result = {}
            ok = (proc.returncode == (0 if expect_reward else 1)
                  and result.get("reward") == expect_reward)
            if expected_correct is not None:
                ok = ok and result.get("correct") == expected_correct
            if expected_question is not None:
                hits = [item["pass"] for item in result.get("checks", [])
                        if item["id"] == expected_question]
                ok = ok and hits == [expected_pass]
            if source == "after" and case == DAB:
                selected = result.get("strict_contract" if scoring == "strict-contract" else "official_compat", {})
                ok = ok and all(result.get(key) == selected.get(key) for key in
                                ("reward", "weighted", "score_rate", "correct", "checks", "failed"))
            record(name, ok, source=source, command=command, exit_code=proc.returncode,
                   stderr=proc.stderr, result=result)
            return result

        bird_oracle = (ROOT / "2-用例" / BIRD / "solution/answers.jsonl").read_text()
        for source in ("before", "after"):
            run(f"bird_{source}_oracle", BIRD, source, bird_oracle, expected_correct=15)
            for label, suffix in (("not_json", "not-json\n"), ("non_object", "[]\n"),
                                  ("bad_structure", '{"question_id":9999}\n')):
                run(f"bird_{source}_{label}", BIRD, source, bird_oracle + suffix,
                    expect_reward=int(source == "before"), expected_correct=15,
                    expected_question="answers_schema", expected_pass=False)
        run("bird_after_blank_lines", BIRD, "after", bird_oracle + "\n \n", expected_correct=15)

        rows = [json.loads(line) for line in
                (ROOT / "2-用例" / DAB / "solution/answers.jsonl").read_text().splitlines()]
        def answers(patch=None):
            patch = patch or {}
            return "".join(json.dumps(dict(row, answer=patch.get(str(row["task_id"]), row["answer"]))) + "\n"
                           for row in rows)
        for source in ("before", "after"):
            run(f"dab_{source}_oracle", DAB, source, answers(), expected_correct=10)
            run(f"dab_{source}_sign_compat", DAB, source, answers({"1871": "0.94810300000017"}),
                expected_correct=10, expected_question="q1871", expected_pass=True)
            run(f"dab_{source}_aci_compat", DAB, source, answers({"2697": "Z:13.57"}),
                expected_correct=10, expected_question="q2697", expected_pass=True)
        strict_cases = [
            ("sign", {"1871": "0.94810300000017"}, 9, "q1871", False),
            ("aci", {"2697": "Z:13.57"}, 9, "q2697", False),
            ("missing_aci", {"2697": "13.57"}, 9, "q2697", False),
            ("prefix", {"1871": "delta=-0.94810300000017"}, 9, "q1871", False),
            ("nan", {"1871": "NaN"}, 9, "q1871", False),
            ("infinity", {"2697": "E:Infinity"}, 9, "q2697", False),
            ("sign_near", {"1871": "-0.94801300000017"}, 10, "q1871", True),
            ("sign_far", {"1871": "-0.94799300000017"}, 9, "q1871", False),
            ("fee_near", {"2697": "e:13.571"}, 10, "q2697", True),
            ("fee_far", {"2697": "E:13.572"}, 9, "q2697", False),
            ("fee_rounding_shortcut", {"2697": "E:13.6"}, 9, "q2697", False),
            ("trailing_zeros", {"1871": "-0.948103000000170", "2697": "e:13.5700"}, 10, "q1871", True),
        ]
        run("dab_after_strict_oracle", DAB, "after", answers(), scoring="strict-contract", expected_correct=10)
        for name, patch, correct, qid, hit in strict_cases:
            run("dab_strict_" + name, DAB, "after", answers(patch), scoring="strict-contract",
                expected_correct=correct, expected_question=qid, expected_pass=hit)
        triple = {"49": "A. NL", "1871": "0.94810300000017", "2697": "Z:13.57"}
        for source in ("before", "after"):
            run("dab_" + source + "_triple_compat", DAB, source, answers(triple), expected_correct=9)
        run("dab_strict_triple_reject", DAB, "after", answers(triple), scoring="strict-contract",
            expect_reward=0, expected_correct=7)
        # 0.8 remains inclusive; two strict misses are not a whole-run hard veto.
        run("dab_strict_threshold_equal", DAB, "after",
            answers({"1871": "0.94810300000017", "2697": "Z:13.57"}),
            scoring="strict-contract", expected_correct=8)
        for location in ("output", "outputs"):
            result = run("dab_extract_" + location, DAB, "after", answers(),
                         scoring="strict-contract", artifact_dir=location, expected_correct=10)
            record("dab_artifact_path_" + location,
                   Path(result.get("artifact", "")).parent.name == location)
        # Existing root > output > outputs lookup priority is deliberately unchanged.
        priority = temp / "priority"
        (priority / "output").mkdir(parents=True)
        (priority / "outputs").mkdir()
        (priority / "answers.jsonl").write_text(answers())
        (priority / "output/answers.jsonl").write_text("not-json\n")
        (priority / "outputs/answers.jsonl").write_text("not-json\n")
        proc = subprocess.run([sys.executable, str(ROOT / "2-用例" / DAB / "checker.py"),
                               str(priority), "--json"], capture_output=True, text=True, env=ENV, timeout=180)
        result = json.loads(proc.stdout)
        record("dab_root_artifact_precedence", proc.returncode == 0 and
               Path(result["artifact"]).parent == priority, exit_code=proc.returncode, result=result)
        for case in (BIRD, DAB):
            command = [sys.executable, str(ROOT / "2-用例" / case / "checker.py"), "--selftest"]
            proc = subprocess.run(command, capture_output=True, text=True, env=ENV, timeout=180)
            (HERE / (case + ".selftest.stdout.txt")).write_text(proc.stdout + proc.stderr)
            record(case + "_selftest", proc.returncode == 0, command=command,
                   exit_code=proc.returncode, stdout=proc.stdout, stderr=proc.stderr)

    sources = {str(path.relative_to(ROOT)): sha(path)
               for case in (BIRD, DAB) for path in
               (ROOT / "2-用例" / case / "checker.py", ROOT / "2-用例" / case / "truth.json")}
    payload = {"audit_version": "numeric-red-green-v1", "no_model_rerun": True,
               "frozen_sha256": manifest, "current_sha256": sources,
               "passed": len(receipts) - len(failures), "total": len(receipts),
               "failures": failures, "receipts": receipts}
    (HERE / "results.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    print(f"Independent audit: {payload['passed']}/{payload['total']} passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
