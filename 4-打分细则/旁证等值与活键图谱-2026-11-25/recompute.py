#!/usr/bin/env python3
"""R4 轨迹面格式合同候选 — 旁证等值与活键图谱公开复算器。

只吃钉定统计件 sidecar-key-contract.json（内容无关），做内部一致性校验。
用法同 R3 recompute.py：无参=同目录文件；带参=指定路径；load_contract(c=None) 可注入 dict。
"""
import json
import re
import sys
from pathlib import Path

SCHEMA = 'r1109-sidecar-key-contract-v1'
HEX64 = re.compile(r'^[0-9a-f]{64}$')
DEAD_KEYS = {'cache_creation_input_tokens', 'cache_read_input_tokens',
             'cached_tokens', 'prompt_cache_write_tokens'}


class Invalid(Exception):
    pass


def load_contract(c=None):
    if c is not None:
        if not isinstance(c, dict):
            raise Invalid('contract 必须是 dict')
        return c
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent / 'sidecar-key-contract.json'
    try:
        obj = json.loads(path.read_bytes())
    except (OSError, ValueError) as e:
        raise Invalid(f'无法读取/解析 {path}: {e}')
    if not isinstance(obj, dict):
        raise Invalid('顶层必须是 object')
    return obj


def _need(cond, msg):
    if not cond:
        raise Invalid(msg)


def verify(c):
    _need(c.get('schema') == SCHEMA, f'schema 不符: {c.get("schema")!r}')

    files = c.get('binding', {}).get('files')
    _need(isinstance(files, dict) and len(files) == 18, f'旁证绑定应 18 文件: {len(files) if isinstance(files, dict) else "缺失"}')
    for key, f in files.items():
        _need(HEX64.match(f.get('sha256', '')), f'{key}: sha256 非法')
        _need(isinstance(f.get('bytes'), int) and f['bytes'] >= 0, f'{key}: bytes 非法')
        _need(isinstance(f.get('trace_relative'), str) and f['trace_relative'], f'{key}: trace_relative 缺失')

    verdicts = c.get('sidecar_verdicts')
    _need(isinstance(verdicts, dict) and set(verdicts) == {
        'system/assignment.md', 'socket/briefing.md', 'socket/findings.jsonl',
        'board.md', 'memory/MEMORY.md', 'session_meta.json'}, f'旁证分组不符: {sorted(verdicts) if isinstance(verdicts, dict) else "缺失"}')
    for name, v in verdicts.items():
        _need(v.get('n_runs') == 3, f'{name}: n_runs != 3')
        dead = v.get('dead_file')
        _need(isinstance(dead, bool), f'{name}: dead_file 非布尔')
        if dead:
            _need(v.get('masked_equal') is None, f'{name}: 死文件不得作等值声明（须为 null）')
            _need(all(b == 0 for b in v.get('raw_bytes', [1])), f'{name}: 死文件却有非 0 字节')
        else:
            _need(isinstance(v.get('masked_equal'), bool), f'{name}: 活文件 masked_equal 须为布尔')
            shas = v.get('masked_sha256')
            if isinstance(shas, str) and HEX64.match(shas):
                all_same = True   # 等值情形登记为单 SHA
            elif isinstance(shas, list) and len(shas) == 3 and all(isinstance(x, str) and HEX64.match(x) for x in shas):
                all_same = len(set(shas)) == 1
            else:
                raise Invalid(f'{name}: masked_sha256 形态非法: {shas}')
            eq = v['masked_equal']
            _need(eq == all_same, f'{name}: 三态等值不变式破坏（masked_equal={eq} 但 SHA {"全同" if all_same else "互异"}）')
        _need(isinstance(v.get('raw_bytes'), list) and len(v['raw_bytes']) == 3, f'{name}: raw_bytes 应 3 元素')

    pa = c.get('PA_input_side')
    _need(isinstance(pa, dict) and pa.get('masked_equal_all') is True and pa.get('slots') == 1,
          f'PA 输入侧旁证等值不成立: {pa}')
    _need(verdicts['system/assignment.md']['masked_equal'] is True, 'PA 与 assignment 分组判定矛盾')

    nm = c.get('near_miss')
    _need(isinstance(nm, dict) and all(v is True for v in nm.values()) and len(nm) == 4,
          f'近错应 4/4 True: {nm}')

    act = c.get('wb_rawusage_key_activity')
    _need(isinstance(act, dict) and len(act) == 14, f'rawUsage 应 14 键: {len(act) if isinstance(act, dict) else "缺失"}')
    for k, v in act.items():
        live = v.get('live')
        _need(isinstance(live, bool), f'{k}: live 非布尔')
        _need(live == (v.get('nonzero', 0) > 0), f'{k}: live 与 nonzero 不一致')
        _need(v.get('nonzero', 0) + v.get('zero_or_empty', 0) + v.get('null', 0) == 160,
              f'{k}: 载体计数和 != 160')
    _need(set(k for k, v in act.items() if not v['live']) == DEAD_KEYS,
          f'死键集与登记不符: {sorted(k for k, v in act.items() if not v["live"])}')

    _need(c.get('usage_carriers') == 160, f'载体数 != 160: {c.get("usage_carriers")}')
    norm = c.get('wb_norm_layer')
    _need(isinstance(norm, dict) and set(norm) == {'inputTokens', 'inputTokensDetails',
                                                   'outputTokens', 'outputTokensDetails', 'requests', 'totalTokens'},
          f'归一层键集不符: {sorted(norm) if isinstance(norm, dict) else "缺失"}')
    _need(c.get('wb_inputTokensDetails_form') == {'list': 160}, f'details 形态不符: {c.get("wb_inputTokensDetails_form")}')

    mask = c.get('sidecar_mask_set')
    _need(isinstance(mask, dict) and set(mask) == {'agent_id', 'iso_timestamp', 'slot_path', 'home', 'slot_filename'},
          f'旁证掩蔽集声明不符: {sorted(mask) if isinstance(mask, dict) else "缺失"}')

    return {
        'binding_files': len(files),
        'groups': len(verdicts),
        'dead_groups': sum(1 for v in verdicts.values() if v['dead_file']),
        'live_equal_groups': sum(1 for v in verdicts.values() if v['masked_equal'] is True),
        'live_unequal_groups': sum(1 for v in verdicts.values() if v['masked_equal'] is False),
        'live_keys': sum(1 for v in act.values() if v['live']),
        'dead_keys': sum(1 for v in act.values() if not v['live']),
        'carriers': c['usage_carriers'],
    }


def main():
    try:
        summary = verify(load_contract())
    except Invalid as e:
        print(f'INVALID: {e}', file=sys.stderr)
        sys.exit(1)
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == '__main__':
    main()
