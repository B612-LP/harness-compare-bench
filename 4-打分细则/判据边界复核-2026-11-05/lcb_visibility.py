"""Read-only LCB canonical-input/public-audit visibility facts, not a grader.

Only six pinned public files are read. No old Python source is imported or run.
The pure semantic layer checks structured test/sample records; it does not certify
all historical run packaging, actual reads, training decontamination or isolation.
"""
from pathlib import Path, PurePosixPath
import hashlib
import json
import math

CASE = '2-用例/lcb-recent-hard-4/'
REPORT = '5-评测报告/竞品评测报告-v1.8.md'
SOURCE_SHA256 = {
    CASE + 'truth.json': '8a9ae6deb4d088b011348d5245d18697f5df5b8b65390c7679c6a8d539c90d14',
    CASE + 'inputs/problems.json': '0ce2f9c1eee0039fa9cfc7cd9969d99118d3fba4ac41571c49d9f5289592a673',
    CASE + 'case.json': 'ac6b7b901cb5192285f26dd31db03ce4af55611d163a18fb27f3596018f298df',
    CASE + 'spec.md': '65c1debb503fefe9f4e813be9f414cd859fc75063fa3670c838b250772a174b9',
    CASE + 'instruction.md': '1c39b2fa66982a7d54851e20822cb4064d8254122f2b047634b64fecdbd6045c',
    REPORT: 'd1e303afae28570a916fe088b08ff2d3a6a2a0312b031dd9ad2fbec98dd0a3d5',
}
PROBLEM_COUNTS = (('abc387_f', 3), ('abc388_f', 3), ('abc388_g', 2), ('abc389_g', 3))
INPUT_FIELDS = {
    'problem_id', 'title', 'contest', 'date', 'url', 'statement_zh', 'input_zh',
    'output_zh', 'constraints_zh', 'samples', 'sample_notes_zh', 'n_public', 'n_hidden',
}
OLD_REPORT_ROW = '| lcb-recent-hard-4 | 隐藏测试至少 2/4 | 算法产物；隐藏测试不公开的限制单列 |'


class VerificationError(ValueError):
    """A source, schema or visibility invariant failed."""


def require(condition, message):
    if not condition:
        raise VerificationError(message)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def safe_file(root: Path, relative: str) -> Path:
    """Accept only regular, non-symlink files beneath an existing root."""
    require(type(relative) is str and bool(relative), 'invalid relative path')
    parts = relative.split('/')
    require(not PurePosixPath(relative).is_absolute() and '\\' not in relative
            and all(p not in ('', '.', '..') for p in parts), 'unsafe relative path')
    root = Path(root)
    require(root.is_dir() and not root.is_symlink(), 'invalid or symlink root')
    base = root.resolve(strict=True)
    current = base
    for part in parts:
        current = current / part
        require(not current.is_symlink(), 'symlink source component')
    require(current.is_file(), 'missing source: ' + relative)
    require(current.resolve(strict=True).is_relative_to(base), 'source escaped root')
    return current


def strict_json(data: bytes):
    """Reject duplicate keys and both literal and overflow non-finite numbers."""
    def pairs(items):
        out = {}
        for key, value in items:
            require(key not in out, 'duplicate JSON key: ' + key)
            out[key] = value
        return out

    def number(text):
        result = float(text)
        require(math.isfinite(result), 'non-finite JSON number')
        return result

    def constant(text):
        raise VerificationError('non-finite JSON constant: ' + text)

    try:
        return json.loads(data.decode('utf-8'), object_pairs_hook=pairs,
                          parse_float=number, parse_constant=constant)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise VerificationError('invalid UTF-8 JSON') from exc


def integer(value, expected, label):
    require(type(value) is int and value == expected, 'invalid ' + label)


def record(record_value, fields, label):
    require(type(record_value) is dict and set(record_value) == set(fields),
            'invalid fields: ' + label)
    for key in ('input', 'output'):
        require(type(record_value[key]) is str and bool(record_value[key].strip()),
                'missing test body: ' + label)


def analyze_visibility(truth: dict, inputs: dict, config: dict) -> dict:
    """Pure structured-data checks; caller independently authenticates source bytes.

    This validates explicit sample/test arrays, not arbitrary prose or encoded
    secrets in arbitrary inputs. Production derive additionally fixes every byte
    of the known canonical input by SHA-256; no generic secrecy claim is made.
    """
    require(type(truth) is dict and type(inputs) is dict and type(config) is dict,
            'documents must be objects')
    require(truth.get('case_id') == inputs.get('case_id') == 'lcb-recent-hard-4',
            'wrong case identity')
    integer(truth.get('n_problems'), 4, 'problem count')
    integer(truth.get('pass_threshold'), 2, 'existing pass threshold')
    require(config == {'inputs': [['inputs', 'inputs']], 'timeout_s': 3000}
            and type(config.get('timeout_s')) is int, 'canonical input configuration changed')
    require(set(inputs) == {'case_id', 'benchmark', 'license', 'note', 'problems'},
            'unexpected canonical input field')
    problems = inputs.get('problems')
    audit = truth.get('problems')
    require(type(problems) is list and len(problems) == 4, 'canonical problem array')
    require(type(audit) is dict and set(audit) == {p for p, _ in PROBLEM_COUNTS},
            'audit problem identities')
    rows = []
    for index, (problem_id, public_count) in enumerate(PROBLEM_COUNTS):
        item = problems[index]
        require(type(item) is dict and set(item) == INPUT_FIELDS, 'canonical problem schema')
        require(item.get('problem_id') == problem_id, 'canonical problem identity/order')
        entry = audit[problem_id]
        require(type(entry) is dict, 'audit problem object')
        for key in ('title', 'contest', 'date', 'url'):
            require(type(item.get(key)) is str and item[key] == entry.get(key),
                    'problem metadata mismatch: ' + key)
        integer(item.get('n_public'), public_count, 'canonical public count')
        integer(item.get('n_hidden'), 40, 'canonical hidden count')
        integer(entry.get('n_public'), public_count, 'audit public count')
        integer(entry.get('n_private'), 40, 'audit private count')
        samples, tests = item.get('samples'), entry.get('tests')
        require(type(samples) is list and len(samples) == public_count, 'sample denominator')
        require(type(tests) is list and len(tests) == public_count + 40, 'test denominator')
        public_tests, private_tests = [], []
        public_indices, private_indices = [], []
        for test_index, test in enumerate(tests):
            record(test, {'input', 'output', 'source'}, 'audit test')
            require(type(test['source']) is str and test['source'] in ('public', 'private'),
                    'unknown source label')
            if test['source'] == 'public':
                public_tests.append({'input': test['input'], 'output': test['output']})
                public_indices.append(test_index)
            else:
                private_tests.append(test)
                private_indices.append(test_index)
        integer(len(public_tests), public_count, 'actual public count')
        integer(len(private_tests), 40, 'actual private count')
        for sample in samples:
            record(sample, {'input', 'output'}, 'canonical sample')
        require(samples == public_tests, 'canonical samples differ from public audit tests')
        tests_digest = sha256(json.dumps(tests, ensure_ascii=False, sort_keys=True).encode('utf-8'))
        require(type(entry.get('tests_sha256')) is str
                and tests_digest == entry['tests_sha256'], 'test-array digest mismatch')
        rows.append({
            'problem_id': problem_id,
            'canonical_public_samples': len(samples),
            'public_audit_source_public': len(public_tests),
            'public_audit_source_private': len(private_tests),
            'public_audit_total': len(tests),
            'private_bodies_present_in_audit': True,
            'tests_sha256': tests_digest,
            'source_pointers': {
                'canonical_samples': '/problems/' + str(index) + '/samples',
                'public_audit_tests': '/problems/' + problem_id + '/tests',
                'source_public_indices': public_indices,
                'source_private_indices': private_indices,
            },
        })
    return {
        'case_id': 'lcb-recent-hard-4',
        'problem_count': 4,
        'canonical_public_samples': sum(r['canonical_public_samples'] for r in rows),
        'public_audit_source_public': sum(r['public_audit_source_public'] for r in rows),
        'public_audit_source_private': sum(r['public_audit_source_private'] for r in rows),
        'public_audit_total': sum(r['public_audit_total'] for r in rows),
        'canonical_input_mapping': [['inputs', 'inputs']],
        'canonical_private_test_records': 0,
        'visibility_interpretation': 'hidden/private is not public-audit confidentiality',
        'historical_score_or_sample_change': False,
        'not_authenticated': {
            'every_historical_run_packaging': 'unknown',
            'historical_products_actual_reads_or_nonreads': 'unknown',
            'training_decontamination': 'unknown',
            'operating_system_isolation': 'unknown',
            'private_raw_evidence_authenticity': 'unknown',
        },
        'scope': 'fixed canonical input schema versus public audit copy; no product outputs or old code executed',
        'problems': rows,
    }


def canonical_input_inventory(root: Path) -> dict:
    """The directory-copy configuration must not silently include extra files.

    This observes this checkout's canonical directory only, never a historical
    product run. Source links, including same-byte links inside the root, fail.
    """
    relative = CASE + 'inputs/problems.json'
    file = safe_file(root, relative)
    entries = list(file.parent.iterdir())
    require(len(entries) == 1 and entries[0].name == 'problems.json',
            'canonical inputs inventory must contain only problems.json')
    require(not entries[0].is_symlink() and entries[0].is_file(),
            'canonical inputs inventory contains symlink or non-file')
    return {
        'directory': CASE + 'inputs',
        'files': [relative],
        'scope': 'this canonical directory and its pinned JSON schema; not historical run packaging',
    }


def derive(root: Path) -> dict:
    """Read six fixed public sources, returning a deterministic JSON-compatible view."""
    sources = {}
    for relative, expected in SOURCE_SHA256.items():
        data = safe_file(root, relative).read_bytes()
        require(sha256(data) == expected, 'source SHA-256 mismatch: ' + relative)
        sources[relative] = data
    inventory = canonical_input_inventory(root)
    truth = strict_json(sources[CASE + 'truth.json'])
    inputs = strict_json(sources[CASE + 'inputs/problems.json'])
    config = strict_json(sources[CASE + 'case.json'])
    raw_input = sources[CASE + 'inputs/problems.json']
    require(truth.get('input_sha256') == sha256(raw_input), 'truth input digest mismatch')
    integer(truth.get('input_bytes'), len(raw_input), 'truth input byte length')
    integer(truth.get('input_bytes'), 7884, 'existing canonical byte length')
    require(OLD_REPORT_ROW in sources[REPORT].decode('utf-8').splitlines(), 'old report evidence row')
    require('171 组测试全文' in sources[CASE + 'spec.md'].decode('utf-8'), 'old spec full-test disclosure')
    require('**隐藏测试**' in sources[CASE + 'instruction.md'].decode('utf-8'), 'instruction hidden-test wording')
    result = analyze_visibility(truth, inputs, config)
    for row in result['problems']:
        row['source_pointers']['canonical_path'] = CASE + 'inputs/problems.json'
        row['source_pointers']['public_audit_path'] = CASE + 'truth.json'
    result['canonical_input_inventory'] = inventory
    result['sources'] = [{'path': path, 'sha256': digest} for path, digest in SOURCE_SHA256.items()]
    result['old_report_evidence'] = {'path': REPORT, 'line': 39, 'text': OLD_REPORT_ROW,
                                     'status': 'historical wording; narrower canonical/audit distinction required'}
    return result
