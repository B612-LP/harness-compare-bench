"""Derived-analysis primitives only: no execution/import of any historical code.
Trace loading/replay needs user-supplied private bytes; released events are not a raw trace.
"""
import ast
import json
import re
from collections import Counter
from hashlib import sha256


def digest(raw):
    return {'bytes': len(raw), 'sha256': sha256(raw).hexdigest()}


def strict_json(text):
    def pairs(items):
        out = {}
        for key, value in items:
            if key in out:
                raise ValueError('duplicate decoded JSON member: ' + key)
            out[key] = value
        return out
    def constant(value):
        raise ValueError('nonfinite JSON constant: ' + value)
    value = json.loads(text, object_pairs_hook=pairs, parse_constant=constant)
    def finite(v):
        if isinstance(v, float) and (v != v or abs(v) == float('inf')):
            raise ValueError('nonfinite JSON number')
        if isinstance(v, dict):
            for k, x in v.items():
                k.encode('utf-8'); finite(x)
        elif isinstance(v, list):
            for x in v: finite(x)
        elif isinstance(v, str):
            v.encode('utf-8')
    finite(value)
    return value


def parse_trace(raw):
    text = raw.decode('utf-8')
    rows, calls, pending, used = [], [], {}, set()
    for line, source in enumerate(text.splitlines(), 1):
        if not source.strip():
            raise ValueError('blank JSONL row')
        row = strict_json(source)
        if not isinstance(row, dict) or row.get('role') not in ('user', 'assistant', 'tool', 'system'):
            raise ValueError('invalid JSONL role/object')
        # Historical exports can begin with assistant; do not invent a missing user prompt.
        if row['role'] != 'tool' and pending:
            raise ValueError('new turn before all tool returns')
        record = {'line': line, 'value': row, 'raw_line': digest(source.encode('utf-8'))}
        rows.append(record)
        if row.get('tool_calls') and row['role'] != 'assistant':
            raise ValueError('only assistant owns calls')
        for call in row.get('tool_calls') or []:
            cid = call['id']
            if not isinstance(cid, str) or not cid or cid in used:
                raise ValueError('duplicate/invalid call id')
            used.add(cid)
            fn = call['function']
            args = strict_json(fn['arguments']) if isinstance(fn['arguments'], str) else fn['arguments']
            if not isinstance(args, dict):
                raise ValueError('arguments must be object')
            entry = {'ordinal': len(calls)+1, 'call_line': line, 'name': fn['name'], 'args': args,
                     'id': cid, 'return_line': None, 'returned': None}
            calls.append(entry); pending[cid] = entry
        if row['role'] == 'tool':
            cid = row.get('tool_call_id')
            if cid not in pending:
                raise ValueError('orphan/duplicate/forward tool return')
            entry = pending.pop(cid)
            if not isinstance(row.get('content'), str):
                raise ValueError('tool content must be string')
            entry.update(return_line=line, returned=row['content'])
    if not rows or pending:
        raise ValueError('empty trace or unmatched calls')
    return {'rows': rows, 'calls': calls,
            'roles': dict(sorted(Counter(x['value']['role'] for x in rows).items())),
            'final_newline': raw.endswith(b'\n')}


def successful_file_ack(path, returned):
    # Exact product text, not substring acceptance of an error quoting a success.
    return returned == 'The file ' + path + ' has been updated successfully.'


def replay_file(trace, path):
    current = None
    versions = []
    for call in trace['calls']:
        if call['name'] not in ('Write', 'Edit') or call['args'].get('file_path') != path:
            continue
        if not successful_file_ack(path, call['returned']):
            raise ValueError('missing/exact-path unsuccessful file ack')
        args = call['args']
        before = None if current is None else digest(current.encode('utf-8'))
        if call['name'] == 'Write':
            if not isinstance(args.get('content'), str):
                raise ValueError('Write content must be string')
            current = args['content']
            count = None
        else:
            old, new = args.get('old_string'), args.get('new_string')
            if current is None or not isinstance(old, str) or not old or not isinstance(new, str):
                raise ValueError('Edit lacks anchored prior Write/nonempty old_string')
            count = current.count(old)
            # str.count is non-overlapping; search all starts to reject overlapping ambiguity.
            starts = [i for i in range(len(current)) if current.startswith(old, i)]
            if len(starts) != 1 or args.get('replace_all', False) is not False:
                raise ValueError('Edit old_string not uniquely matched or replace_all requested')
            current = current[:starts[0]] + new + current[starts[0]+len(old):]
        raw = current.encode('utf-8')
        ast.parse(current)  # Syntax only; never compile/eval/exec/import the implementation.
        versions.append({'operation': call['name'], 'call_line': call['call_line'],
                         'ack_line': call['return_line'], 'before': before,
                         'after': digest(raw), 'old_string_matches': count})
    if current is None:
        raise ValueError('no acknowledged target Write')
    return current.encode('utf-8'), versions


def bash_output(call):
    if call['name'] != 'Bash':
        raise ValueError('not Bash')
    prefix = "Command '" + call['args']['command'] + "' exited with code "
    if not call['returned'].startswith(prefix):
        raise ValueError('Bash response does not bind exact submitted command')
    tail = call['returned'][len(prefix):]
    match = re.match(r'(-?\d+)\. stdout: ', tail)
    if not match:
        raise ValueError('missing structured product exit wrapper')
    return int(match[1]), tail[match.end():]


def unittest_summary(stdout, exit_code):
    matches = list(re.finditer(r'^Ran (\d+) tests? in [^\n]+$', stdout, re.M))
    lines = [x.strip() for x in stdout.splitlines() if x.strip()]
    if len(matches) != 1 or not lines:
        raise ValueError('not one complete unittest summary')
    status = lines[-1]
    if status == 'OK':
        failures = errors = 0
        if exit_code != 0: raise ValueError('OK/exit conflict')
    else:
        failed = re.fullmatch(r'FAILED \((.+)\)', status)
        if not failed or exit_code == 0: raise ValueError('unittest status/exit conflict')
        counts = {}
        for item in failed[1].split(', '):
            key, num = item.split('=')
            if key not in ('failures', 'errors') or key in counts or not num.isdigit():
                raise ValueError('unsupported failed summary')
            counts[key] = int(num)
        failures, errors = counts.get('failures', 0), counts.get('errors', 0)
        if failures+errors == 0: raise ValueError('empty failure count')
    if failures+errors > int(matches[0][1]):
        raise ValueError('failure/error counts exceed traversed tests')
    # Exception details are NOT copied to public candidates.
    return {'tests': int(matches[0][1]), 'failures': failures, 'errors': errors,
            'exit_code': exit_code, 'status': status,
            'failed_test_ids': re.findall(r'^FAIL: (\w+) \(', stdout, re.M)}


def pov_retests(trace, path):
    command = 'cd ' + path.rsplit('/', 1)[0] + ' && python3 -m unittest -q pov_test.py'
    result = []
    for call in trace['calls']:
        if call['name'] == 'Bash' and call['args'].get('command') == command:
            exit_code, stdout = bash_output(call)
            summary = unittest_summary(stdout, exit_code)
            if summary['tests'] != 15:
                raise ValueError('pov observed test count differs from fixed 15')
            result.append({'call_line': call['call_line'], 'return_line': call['return_line'],
                           'command_sha256': sha256(command.encode()).hexdigest(), **summary})
    return result


def terminal_claim(trace):
    # Position + speaker + no calls are required. Earlier local or prospective text is not final.
    last = trace['rows'][-1]
    row = last['value']
    if row['role'] == 'assistant' and not row.get('tool_calls') and isinstance(row.get('content'), str) and row['content'].strip():
        return {'line': last['line'], 'content_sha256': sha256(row['content'].encode()).hexdigest(),
                'observed': True}
    return {'line': None, 'content_sha256': None, 'observed': False}


def runner_origin(source):
    tree = ast.parse(source)
    statements = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            for key, value in zip(node.keys, node.values):
                if isinstance(key, ast.Constant) and key.value == 'complete':
                    statements.append({'key_line': key.lineno, 'value': ast.literal_eval(value)})
    if statements != [{'key_line': 55, 'value': True}]:
        raise ValueError('runner complete source changed')
    run_lines = [n.lineno for n in ast.walk(tree) if isinstance(n, ast.Call)
                 and isinstance(n.func, ast.Attribute) and n.func.attr == 'run'
                 and isinstance(n.func.value, ast.Name) and n.func.value.id == 'suite']
    if run_lines != [53]: raise ValueError('runner test execution position changed')
    return {'owner': 'trusted_runner', 'complete_literal': statements,
            'suite_run_lines': run_lines, 'semantics': 'test traversal completed; not all-success or agent speech'}
