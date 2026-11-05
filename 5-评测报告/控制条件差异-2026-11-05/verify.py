#!/usr/bin/env python3
"""Read-only recorded-control sensitivity view; no product execution or regrading."""
import argparse
from collections import Counter
import difflib
import hashlib
import types
import json
from pathlib import Path
import sys

FORMAL = '5-评测报告/正式行复核-2026-11-05/verify.py'
FORMAL_SHA = '661c4aa0ac48d5a80231ab05a3943a49f332d624c848e744f0d7c2ce24ef7480'
HERE = '5-评测报告/控制条件差异-2026-11-05/'
VIEW = HERE + 'controls.json'


def require(ok, message):
    if not ok:
        raise ValueError(message)


def load_formal(root):
    root = Path(root).resolve()
    path = (root / FORMAL).resolve()
    require(path.is_relative_to(root) and path.is_file(), 'formal dependency escapes root or is missing')
    # Check bytes BEFORE executing the one explicitly reviewed public dependency.
    code = path.read_bytes()
    require(hashlib.sha256(code).hexdigest() == FORMAL_SHA, 'reviewed formal dependency SHA mismatch')
    module = types.ModuleType('_reviewed_formal_controls')
    module.__file__ = str(path)
    # Execute exactly the checked bytes, without import-loader bytecode writes.
    exec(compile(code, str(path), 'exec'), module.__dict__)
    return module


def cell(value, sources, state='recorded', meaning='recorded public value only'):
    require(state in ('recorded', 'unknown', 'not_directly_comparable'), 'invalid control state')
    require(isinstance(sources, list) and bool(sources), 'control has no source')
    require(state != 'unknown' or value is None, 'unknown must preserve null')
    return {'state': state, 'value': value, 'sources': sources, 'meaning': meaning}


def compare(left, right):
    if left['state'] == 'unknown' or right['state'] == 'unknown':
        return 'unknown'
    if left['state'] == 'not_directly_comparable' or right['state'] == 'not_directly_comparable' or left.get('representation') != right.get('representation'):
        return 'not_directly_comparable'
    # Canonical JSON retains boolean/number distinctions, including nested values.
    values = [json.dumps(side['value'], sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(',', ':')) for side in (left, right)]
    return 'same_recorded_value' if values[0] == values[1] else 'different_recorded_value'


def task_diff(store, left, right):
    lp, rp = left['public_task']['sources'][0]['path'], right['public_task']['sources'][0]['path']
    for path in (lp, rp):
        store.check_hash(path)
    lb, rb = store.path(lp).read_bytes(), store.path(rp).read_bytes()
    # Split byte lines with endings retained; no universal-newline translation.
    ll, rl = ([line.decode('utf-8') for line in data.splitlines(keepends=True)] for data in (lb, rb))
    ranges = [{'operation': op, 'left_lines_1_based_half_open': [a + 1, b + 1],
               'right_lines_1_based_half_open': [c + 1, d + 1], 'left_text': ll[a:b], 'right_text': rl[c:d]}
              for op, a, b, c, d in difflib.SequenceMatcher(None, ll, rl, autojunk=False).get_opcodes() if op != 'equal']
    kinds_equal = left['public_task']['representation'] == right['public_task']['representation']
    return {'left_source': store.anchor(lp), 'right_source': store.anchor(rp),
            'comparison_domain': 'public UTF-8 TASK byte lines with line endings retained, not private raw or system/tool/request messages',
            'line_ending_policy': 'read_bytes().splitlines(keepends=True); LF and CRLF are different; no newline normalization',
            'representation_kinds_equal': kinds_equal, 'public_bytes_equal': lb == rb,
            'status': ('same_recorded_value' if lb == rb else 'different_recorded_value') if kinds_equal else 'not_directly_comparable',
            'changed_line_ranges': ranges, 'semantic_equivalence_proven': False}


def display_A_home(diff):
    """Transform only A line-3 display, AFTER raw byte comparison/range checks."""
    for part in diff['changed_line_ranges']:
        for side in ('left', 'right'):
            if part[side + '_lines_1_based_half_open'] != [3, 4]:
                continue
            require(len(part[side + '_text']) == 1, 'A line-3 display is not a single line')
            line = part[side + '_text'][0]
            before, marker, tail = line.partition('/Users/')
            username, slash, rest = tail.partition('/')
            require(bool(marker and username and slash), 'A line-3 home display prefix missing')
            part[side + '_text'] = [before + '[HOME]/' + rest]
            part['text_representation'] = 'display_not_original_bytes'
    diff['not_original_bytes'] = True
    diff['display_transform'] = {'scope': 'A pair changed line 3 display only',
                                 'operation': 'replace local home prefix with [HOME]',
                                 'comparison_uses': 'original source bytes before display transformation',
                                 'source_sha_and_line_ranges_unchanged': True}
    return diff


def derive(root):
    f = load_formal(root)
    closure = f.derive(root)
    store = f.Store(root)
    ledger = store.read(f.LEDGER)
    for item in closure['source_inventory']:
        store.expected[item['path']] = item['sha256']
        if item['status'] == 'missing':
            store.missing.add(item['path'])
    formal_ids = {r['event_id'] for r in closure['rows']}
    rows = []
    for old in ledger['all_formal_attempts']:
        event = f.pointer(store.read(old['source']['path']), old['source']['pointer'])
        eid = old['event_id']
        require(event['event_id'] == eid, 'event identity mismatch')
        fields = {}
        for target, original in (('model_label', 'model'), ('route', 'route'), ('tools', 'tools'),
                                 ('product_version', 'product_version'), ('permissions', 'permissions'), ('skills', 'skills'),
                                 ('rule_version', 'rule_version'), ('case_version', 'case_version'),
                                 ('case_sha256', 'case_sha256'), ('checker_sha256', 'checker_sha256'), ('truth_sha256', 'truth_sha256')):
            fact = event['facts'][original]
            refs = f.resolve_fact(store, event, fact)
            fields[target] = cell(fact['value'], refs, 'recorded' if fact['state'] == 'known' else 'unknown')
        model_refs = fields['model_label']['sources']
        require(len(model_refs) == 1 and model_refs[0]['path'].endswith('.json'), 'ambiguous model metadata source')
        mp = model_refs[0]['path']
        meta = store.read(mp)
        # Metadata envelope is checked where supplied, not inferred from its filename.
        for key, expected in (('product', old['product']), ('case', old['case']), ('case_id', old['case']), ('event_id', eid), ('run_id', old['run_id'])):
            if key in meta:
                require(f.same(meta[key], expected), 'metadata envelope mismatch: ' + key)
        fields['backend_model_identity'] = cell(None, model_refs, 'unknown', 'no independent authentication of backend model identity')
        fields['actual_reasoning_budget'] = cell(None, model_refs, 'unknown', 'declared effort/UI label does not measure actual reasoning tokens or budget')
        model = fields['model_label']['value']
        if isinstance(model, dict) and 'reasoning_effort' in model:
            effort, ptr = model['reasoning_effort'], '/model/reasoning_effort'
        elif 'reasoning_effort' in meta:
            effort, ptr = meta['reasoning_effort'], '/reasoning_effort'
        else:
            effort, ptr = None, ''
        effort_ref = store.anchor(mp, ptr)
        if ptr:
            require(f.same(f.pointer(meta, ptr), effort), 'effort source pointer mismatch')
        else:
            effort_ref['absent_field'] = '/reasoning_effort'
        fields['declared_effort'] = cell(effort, [effort_ref], 'recorded' if effort is not None else 'unknown', 'metadata/UI declaration only, not actual reasoning control')
        route = fields['route']['value']
        protocol = route.get('wire_protocol') if isinstance(route, dict) else None
        protocol_refs = [store.anchor(x['path'], x['pointer'] + '/wire_protocol') for x in fields['route']['sources']]
        for source in protocol_refs:
            require(f.same(f.pointer(store.read(source['path']), source['pointer']), protocol), 'protocol source pointer mismatch')
        fields['route_protocol'] = cell(protocol, protocol_refs, 'recorded' if protocol is not None else 'unknown', 'recorded route wire_protocol only; null is unknown, not equality evidence')
        version = fields['product_version']['value']
        if isinstance(version, str) and 'app_build=undisclosed(closed)' in version:
            fields['product_version']['state'] = 'not_directly_comparable'
            fields['product_version']['meaning'] = 'closed app build undisclosed; preserved product label is not a known build'
        # Prefer an available TASK.md; otherwise retain the explicitly public-derived representation.
        prompts = old['prompt_sources']
        require(bool(prompts), 'missing public TASK source')
        preferred = sorted(prompts, key=lambda x: (not x['path'].endswith('/TASK.md'), x['path']))[0]
        refs = [store.anchor(preferred['path'])]
        for p in prompts:
            store.check_hash(p['path'])
            require(store.expected[p['path']] == p['sha256'], 'TASK source pin mismatch')
        representation = 'public_derived' if 'public-derived' in preferred['path'] else 'recorded_public_task'
        fields['public_task'] = cell(preferred['sha256'], refs, meaning='exact bytes of the selected public representation only')
        fields['public_task']['representation'] = representation
        fields['public_task']['all_public_sources'] = [store.anchor(p['path']) for p in prompts]
        rows.append({'event_id': eid, 'run_id': old['run_id'], 'track': old['track'], 'product': old['product'], 'case': old['case'],
                     'formal': eid in formal_ids, 'event_source': store.anchor(old['source']['path'], old['source']['pointer']),
                     'controls': fields, 'recorded_score': old['score']})
    require(len(rows) == len({r['event_id'] for r in rows}) == 30, 'attempt control coverage mismatch')
    require(sum(r['formal'] for r in rows) == 25, 'formal tag coverage mismatch')
    by_id = {r['event_id']: r for r in rows}
    replacements = []
    closed_formal = {row['event_id']: row for row in closure['rows']}
    for edge in closure['replacements']:
        left, right = by_id[edge['parent']], by_id[edge['child']]
        l, r = left['controls'], right['controls']
        replacements.append({'parent': edge['parent'], 'child': edge['child'], 'predecessor_source': edge['source'],
                             'child_registration_source': closed_formal[edge['child']]['registration_source'],
                             'field_comparisons': {k: compare(l[k], r[k]) for k in l}, 'public_task_diff': task_diff(store, l, r)})
    require(len(replacements) == 5, 'replacement comparison coverage mismatch')
    pairs = []
    for case in f.CASES:
        selected = {r['product']: r for r in rows if r['track'] == 'A_same_model' and r['case'] == case}
        left, right = selected['codex'], selected['dsh']
        l, r = left['controls'], right['controls']
        diff = task_diff(store, l, r)
        # A finite, anchored display check, not a generic path/name normalizer.
        expected = [{'operation': 'replace', 'left_lines_1_based_half_open': [n, n + 1], 'right_lines_1_based_half_open': [n, n + 1]} for n in (1, 3)]
        require([{k: part[k] for k in ('operation', 'left_lines_1_based_half_open', 'right_lines_1_based_half_open')} for part in diff['changed_line_ranges']] == expected, 'A finite display changed beyond lines 1/3')
        pairs.append({'case': case, 'left': left['event_id'], 'right': right['event_id'],
                      'field_comparisons': {k: compare(l[k], r[k]) for k in l}, 'public_task_diff': display_A_home(diff),
                      'finite_display': 'Only source TASK lines 1 and 3 differ. Raw comparison removes/normalizes no line; displayed line 3 home is replaced by [HOME], not original bytes or semantic/request equivalence.'})
    db = next(e for e in replacements if by_id[e['child']]['product'] == 'doubao' and by_id[e['child']]['case'] == 'tb-cargo-plan')
    require(all(db['field_comparisons'][k] == 'same_recorded_value' for k in ('case_sha256', 'checker_sha256', 'truth_sha256')), 'DB cargo recorded contract relation changed')
    require(db['field_comparisons']['product_version'] == 'different_recorded_value' and db['public_task_diff']['public_bytes_equal'] is False, 'DB cargo version/TASK distinction lost')
    require(len([e for e in replacements if by_id[e['child']]['product'] == 'workbuddy']) == 3, 'WB replacement count changed')
    return {'schema': 'recorded-control-sensitivity-v1', 'meaning': 'sensitivity of recorded public conditions, not new evaluation or causal attribution',
            'formal_n_per_product_case': 1, 'mixed_track_ranking': False, 'attempt_count': 30, 'formal_count': 25,
            'formal_track_counts': closure['track_counts'], 'formal_summary_unchanged': closure['summary'],
            'formal_generation_counts': dict(sorted(Counter(r['controls']['rule_version']['value'] for r in rows if r['formal']).items())),
            'rows': rows, 'replacement_comparisons': replacements, 'A_finite_TASK_comparisons': pairs,
            'historical_inventory_unchanged': closure['historical_inventory'],
            'grade_identity_limit': '15 formal rows have at least one score receipt without an identity envelope; reviewed assignment is not independent authentication',
            'dependency': {'path': FORMAL, 'sha256': FORMAL_SHA, 'checked_before_execution': True},
            'comparison_states': ['same_recorded_value', 'different_recorded_value', 'unknown', 'not_directly_comparable'],
            'recorded_value_equality': 'canonical JSON with sorted keys, preserved boolean/number types and no nonfinite values; no Python bool-number coercion',
            'limits': ['No backend identity or actual reasoning budget authenticated, including A.',
                       'Same case/checker/truth SHA never implies same TASK, system prompt, tool schema, request, isolation or causal conditions.',
                       'Public-derived TASK differences compare public representations only, not private original prompts.',
                       'No candidate/checker/runner/SQL/product/model/network execution; original scores, n and historical unknowns unchanged.']}


def render_summary(view):
    lines = ['# 控制条件差异：公开记录紧凑视图', '',
             '由同目录 verify.py 的 render_summary() 从固定公开源生成；不是新正式账或新成绩。',
             '完整逐格 path / SHA-256 / JSON pointer 与差异展示见 [controls.json](<controls.json>)；A 第 3 行 home 前缀仅展示替换为 [HOME]，不是原字节。', '',
             '| 尝试 event_id（固定来源身份） | 正式 | 版本披露值 | effort 声明 | route/protocol 声明 |',
             '|---|---|---|---|---|']
    def escape(value):
        return str(value).replace('|', '\\|').replace('\n', ' ')
    for row in view['rows']:
        c = row['controls']
        version = c['product_version']['value']
        if c['product_version']['state'] != 'recorded':
            version = str(version) + '（构建不可直接比较）'
        source = row['event_source']['path']
        identity = '[' + row['event_id'] + '](<../../' + source + '>)'
        lines.append('| ' + ' | '.join([identity, '是' if row['formal'] else '否（作废父场）', escape(version),
                                     escape(c['declared_effort']['value'] if c['declared_effort']['state'] == 'recorded' else '未知'),
                                     escape(c['route_protocol']['value'] if c['route_protocol']['state'] == 'recorded' else '未知')]) + ' |')
    lines += ['', '所有后端模型身份与实际思考预算均为未知；low / 产品标签仅是公开记录声明。',
              '权限、skills、模型标签与 case/checker/truth/TASK 逐字段原值和来源保留在 JSON，不以标签推定隔离或因果相同。', '',
              '| 唯一替代：父 → 子 | case / checker / truth | 版本记录 | TASK 公开表示比较 |', '|---|---|---|---|']
    for edge in view['replacement_comparisons']:
        states = edge['field_comparisons']
        lines.append('| ' + edge['parent'] + ' → ' + edge['child'] + ' | ' +
                     '/'.join(states[k] for k in ('case_sha256', 'checker_sha256', 'truth_sha256')) + ' | ' +
                     states['product_version'] + ' | ' + edge['public_task_diff']['status'] + ' |')
    lines += ['', 'WB 的父场是明确 public-derived 的 TASK 表示，子场是公开 TASK；保留差异文本，但两者不认证原私档提示。', '',
              '## A 五对：有限文本展示（不是语义等价）', '',
              '原字节计算的精确变更范围均为第 1、3 行；比较不删除任何行、不正则或换行归一化（LF/CRLF 不同）。JSON 保留 source SHA 与原行定位，但第 3 行仅展示 home→[HOME] 的派生文本，显式 not_original_bytes / display_transform；不是提示语义归一化。', '',
              '| 用例 | 声明 effort | 协议记录 | TASK |', '|---|---|---|---|']
    indexed = {r['event_id']: r for r in view['rows']}
    for pair in view['A_finite_TASK_comparisons']:
        left, right = (indexed[pair[k]]['controls'] for k in ('left', 'right'))
        effort = escape(left['declared_effort']['value']) + ' / ' + escape(right['declared_effort']['value'])
        protocol = escape(left['route_protocol']['value']) + ' / ' + escape(right['route_protocol']['value'])
        lines.append('| ' + pair['case'] + ' | ' + effort + '（非实际预算） | ' + protocol + ' | 仅第 1、3 行不同；非等价证明 |')
    lines += ['', '相同/不同仅指所列公开记录值；unknown 不因 null == null 转成相同；不同表示域使用 not_directly_comparable。',
              '正式仍 A10/B10/W5，每产品×用例 n=1；历史 5 缺件、40 个 B 观察版本未知、15 个正式成绩无身份信封边界均保留。', '']
    return '\n'.join(lines)


def validate_view(actual, expected, same):
    require(same(actual, expected), 'control view differs from independently rebuilt public sources')


def verify(root):
    expected = derive(root)
    f = load_formal(root)
    store = f.Store(root)
    actual = f.loads(store.path(VIEW).read_text(encoding='utf-8'))
    validate_view(actual, expected, f.same)
    require(store.path(HERE + 'summary.md').read_text(encoding='utf-8') == render_summary(expected), 'compact table differs from rebuilt control view')
    return expected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args()
    try:
        result = verify(args.root)
        print(json.dumps({'ok': True, 'view': result}, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False))
    except (ValueError, KeyError, TypeError, IndexError, OSError, StopIteration) as exc:
        print('FAIL: ' + str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
