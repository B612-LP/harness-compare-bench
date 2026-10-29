#!/usr/bin/env python3
"""Exact AST delta and isolated ek_json checks; no CLI or full suite execution."""
import argparse
import ast
import copy
import datetime as dt
import hashlib
import json
from pathlib import Path


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--before', type=Path, required=True)
    ap.add_argument('--after', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    before, after = ast.parse(a.before.read_text()), ast.parse(a.after.read_text())
    old_defs = {n.name: n for n in before.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    new_defs = {n.name: n for n in after.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    added = sorted(set(new_defs) - set(old_defs))
    changed = sorted(k for k in set(new_defs) & set(old_defs)
                     if ast.dump(old_defs[k], include_attributes=False) != ast.dump(new_defs[k], include_attributes=False))
    expected_changed = ['cmd_mockrun', 'cmd_report', 'cmd_selftest', 'cmd_termination_selftest']
    class Unwrap(ast.NodeTransformer):
        count = 0
        def visit_Call(self, node):
            node = self.generic_visit(node)
            if isinstance(node.func, ast.Name) and node.func.id == 'ek_json':
                assert len(node.args) == 1 and not node.keywords
                self.count += 1
                return node.args[0]
            return node
    normalized = copy.deepcopy(after)
    normalized.body = [n for n in normalized.body if not (isinstance(n, ast.FunctionDef) and n.name == 'ek_json')]
    unwrap = Unwrap()
    normalized = unwrap.visit(normalized)
    ast.fix_missing_locations(normalized)
    exact = ast.dump(before, include_attributes=False) == ast.dump(normalized, include_attributes=False)
    # Compile only the pure display helper; do not import or execute the product module.
    ns = {}
    ast_mod = ast.Module(body=[copy.deepcopy(new_defs['ek_json'])], type_ignores=[])
    ast.fix_missing_locations(ast_mod)
    exec(compile(ast_mod, '<isolated-exact-ek_json>', 'exec'), ns)
    helper = ns['ek_json']
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    evidence = [{'path': 'synthetic/path', 'sha256': 'a' * 64, 'sha256_8': 'a' * 8,
                 'bytes': 105009, 'line': 'synthetic/path · aaaaaaaa · 105009B · ' + now,
                 'extra': {'integer': 42}}, {'line': None, 'bytes': 10}, 'synthetic non-dict']
    original = copy.deepcopy(evidence)
    transformed = helper(evidence)
    strip_line = lambda obj: {k: v for k, v in obj.items() if k != 'line'}
    checks = [
        {'id': 'only-ek-json-function-added', 'pass': added == ['ek_json']},
        {'id': 'only-four-receipt-formatting-functions-changed', 'pass': changed == expected_changed},
        {'id': 'complete-module-ast-identical-after-four-display-unwrappings', 'pass': exact and unwrap.count == 4},
        {'id': 'input-evidence-not-mutated', 'pass': evidence == original},
        {'id': 'structured-bytes-integer-and-all-sha-fields-preserved', 'pass': strip_line(evidence[0]) == strip_line(transformed[0]) and isinstance(transformed[0]['bytes'], int)},
        {'id': 'only-line-byte-unit-display-changed', 'pass': transformed[0]['line'] == evidence[0]['line'].replace('105009B', '105009 bytes') and transformed[1:] == evidence[1:]},
        {'id': 'display-adapter-idempotent', 'pass': helper(transformed) == transformed}]
    result = {'category': 'self_test', 'scope': 'Exact frozen source AST equivalence modulo pure display adapter; no runtime/model/CLI/checker/full-suite execution',
              'generated_at': now, 'live_doc_drift': [], 'before_sha256': sha(a.before), 'after_sha256': sha(a.after),
              'reviewer_script_sha256': sha(Path(__file__)), 'added_functions': added,
              'changed_functions': changed, 'display_wrapper_count': unwrap.count,
              'full_normalized_module_ast_equal': exact, 'checks': checks, 'passed': all(r['pass'] for r in checks)}
    with a.out.open('x') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
        f.write('\n')
    print(json.dumps({'checks': len(checks), 'passed': sum(r['pass'] for r in checks), 'out': str(a.out)}))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
