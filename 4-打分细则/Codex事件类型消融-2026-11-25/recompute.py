#!/usr/bin/env python3
"""R6 公开复算器：校验 codex-ablation-contract.json 的自洽关系链。只吃本合同，不读原档。"""
import argparse
import json
import sys


class Invalid(Exception):
    pass


HEADER_TYPES = None  # 从合同读


def _hex(s, what):
    if not (isinstance(s, str) and len(s) == 64 and all(c in '0123456789abcdef' for c in s)):
        raise Invalid(f'{what} 非合法 sha256 十六进制: {str(s)[:20]}')


def load_contract(path=None, c=None):
    if c is not None:
        return c
    p = path or 'codex-ablation-contract.json'
    try:
        return json.loads(open(p, encoding='utf-8').read())
    except Exception as e:
        raise Invalid(f'合同读取失败: {e}')


def verify(c):
    if c.get('schema') != 'r1109-codex-type-ablation-v1':
        raise Invalid(f'schema 不符: {c.get("schema")}')

    # 1) 绑定：15 槽、命名、hex
    slots = c.get('binding', {}).get('slots', [])
    if len(slots) != 15:
        raise Invalid(f'绑定槽数 {len(slots)} != 15')
    names = []
    for s in slots:
        sid = s.get('slot', '')
        parts = sid.split('__')
        if len(parts) != 3 or parts[0] != 'codex' or not parts[2] in ('r1', 'r2', 'r3'):
            raise Invalid(f'槽名不合规: {sid}')
        _hex(s.get('sha256', ''), f'{sid}.sha256')
        if not isinstance(s.get('n_lines'), int) or s['n_lines'] <= 0:
            raise Invalid(f'{sid}.n_lines 非法')
        names.append(sid)
    cases = sorted({'__'.join(n.split('__')[:2]) for n in names})
    if len(cases) != 5:
        raise Invalid(f'案例数 {len(cases)} != 5')
    for cse in cases:
        for r in ('r1', 'r2', 'r3'):
            if f'{cse}__{r}' not in names:
                raise Invalid(f'缺槽 {cse}__{r}')

    # 2) 类型并集一致性：face_partition 计数和==union；分解自洽
    union = c.get('type_union', {})
    faces = c.get('face_partition', {}).get('per_case', {})
    total_from_faces = {}
    for case, cats in faces.items():
        for t, v in cats.items():
            for run, n in v['counts'].items():
                total_from_faces[t] = total_from_faces.get(t, 0) + n
    if total_from_faces != union:
        raise Invalid('face_partition 计数与 type_union 不一致')

    top = c.get('top_union', [])
    ri = c.get('response_item_subtypes', [])
    em = c.get('event_msg_subtypes', [])
    if set(top) != {t.split('/')[0] for t in union}:
        raise Invalid('top_union 与 type_union 分解不一致')
    if set(ri) != {t.split('/')[1] for t in union if t.startswith('response_item/')} or len(ri) != 4:
        raise Invalid(f'response_item 子型不符: {ri}')
    if set(em) != {t.split('/')[1] for t in union if t.startswith('event_msg/')}:
        raise Invalid('event_msg 子型与 union 不一致')

    # 3) 面二分：header ⇒ masked_equal；variance ⇒ 不等值；无 other
    hdr = set(c.get('face_partition', {}).get('header_types', []))
    var = set(c.get('face_partition', {}).get('variance_types', []))
    if hdr & var:
        raise Invalid('header/variance 类型重叠')
    for case, cats in faces.items():
        for t, v in cats.items():
            f = v.get('face')
            if f == 'other':
                raise Invalid(f'{case}/{t} 面分类为 other——面二分失败')
            if t in hdr:
                if f != 'header' or not v.get('masked_equal_all_lines'):
                    raise Invalid(f'{case}/{t} 声明 header 但等值不符')
            elif t in var:
                if f != 'variance' or v.get('masked_equal_all_lines'):
                    raise Invalid(f'{case}/{t} 声明 variance 但等值不符')
            else:
                raise Invalid(f'{case}/{t} 不在任一面清单')
        # 三态等值不变式：masked_equal 声明 vs sha 集合
        for t, v in cats.items():
            shs = set(v.get('masked_stream_sha256', {}).values())
            eq = v.get('masked_equal_all_lines')
            if eq and len(shs) != 1:
                raise Invalid(f'{case}/{t} 等值声明与 SHA 集矛盾')
            if (not eq) and len(shs) == 1:
                raise Invalid(f'{case}/{t} 不等值声明与 SHA 集矛盾')

    # 4) 输入侧三行：全等值；developer/env 行跨案例恒 SHA
    rows = c.get('input_rows', {}).get('per_case', {})
    if len(rows) != 5:
        raise Invalid('input_rows 案例数 != 5')
    for case, v in rows.items():
        if v.get('masked_equal') != [True, True, True]:
            raise Invalid(f'{case} 输入三行未全部三-run 等值')
    cc = c.get('input_rows', {}).get('cross_case_constant_rows', {})
    devs = {v['row_shas_r1'][0] for v in rows.values()}
    envs = {v['row_shas_r1'][1] for v in rows.values()}
    if devs != {cc['developer_row_sha_r1']} or envs != {cc['env_context_row_sha_r1']}:
        raise Invalid('developer/env 行跨案例 SHA 不恒一')
    for v in rows.values():
        ac = v.get('assistant_counts', {})
        if not all(isinstance(x, int) and x >= 0 for x in ac.values()):
            raise Invalid('assistant_counts 非法')

    # 5) 常量：单值
    consts = c.get('constants', {})
    for k in ('collaboration_mode.model', 'collaboration_mode.instructions', 'approval_policy', 'sandbox_policy'):
        if len(consts.get(k, [])) != 1:
            raise Invalid(f'常量 {k} 非单值: {consts.get(k)}')
    if consts['collaboration_mode.model'] != ['deepseek-flash']:
        raise Invalid('模型常量非 deepseek-flash')

    # 6) 掩蔽承重探针
    pr = c.get('mask_probes', {})
    if pr.get('no_uuid', {}).get('within_case_row_flipped') != [True, True, True]:
        raise Invalid('no_uuid 探针未翻转')
    if pr.get('no_time_keys', {}).get('within_case_row_flipped') != [True, True, True]:
        raise Invalid('no_time_keys 探针未翻转')
    nc = pr.get('no_cwd', {})
    if not (nc.get('cross_case_env_shas_with_mask') == 1 and nc.get('without_mask') == 5):
        raise Invalid('no_cwd 探针不符（应为 1 vs 5）')

    # 7) 绑定三链 + usage 对表
    bt = c.get('binding_triple', {})
    if not (bt.get('slots_all_equal') is True and bt.get('slots_checked') == 15 and _is_hex64(bt.get('ledger_sha256'))):
        raise Invalid('绑定三链声明不完整或非全等')
    um = c.get('usage_match', {})
    if um.get('slots_total_equal') != um.get('slots_checked') or um.get('slots_checked') != 15:
        raise Invalid('usage 对表未全等')
    if not _is_hex64(um.get('ledger_sha256')):
        raise Invalid('ledger_sha256 非法')
    ns = um.get('per_slot_n', {})
    if len(ns) != 15 or any(not isinstance(x, int) or x <= 0 for x in ns.values()):
        raise Invalid('per_slot_n 非法')

    # 8) 计数合同与近错声明
    if not c.get('count_contract', {}).get('token_count_equals_token_usage_record_per_slot'):
        raise Invalid('计数合同声明失败')
    nm = c.get('near_miss', {})
    if not all(v is True for v in nm.values()):
        raise Invalid(f'近错声明存在非 True: {[k for k, v in nm.items() if v is not True]}')

    return {
        'slots': 15,
        'union_types': len(union),
        'header_types': sorted(hdr),
        'variance_types': sorted(var),
        'input_rows_cases': len(rows),
        'usage_match': f"{um['slots_total_equal']}/{um['slots_checked']}",
        'near_miss_all_true': True,
    }


def _is_hex64(s):
    return isinstance(s, str) and len(s) == 64 and all(ch in '0123456789abcdef' for ch in s)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--contract', default=None)
    args = ap.parse_args()
    c = load_contract(args.contract)
    summary = verify(c)
    print('CONTRACT OK', json.dumps(summary, ensure_ascii=False))


if __name__ == '__main__':
    main()
