#!/usr/bin/env python3
"""公开证据一致性自检（试行 0.1）。

用法：python3 verify.py --self-test
只核对本目录 evidence.json 的内部一致性与隐私边界（不含会话标识、
不含私档路径），不是隐私检测器，没有原件不能重做身份绑定或流解析。
"""
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
PRIV_PATTERNS = (
    re.compile(r'run-r53-'),          # 私档运行目录名
    re.compile(r'/Users/'),           # 本机路径
    re.compile(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}'),  # 会话/线程 UUID 形状
    re.compile(r'\.response\.bin|\.request\.bin|session\.jsonl'),  # 原件文件名形状
)


def self_test():
    data = json.loads((HERE / 'evidence.json').read_text(encoding='utf-8'))

    text = json.dumps(data, ensure_ascii=False)
    for pat in PRIV_PATTERNS:
        assert not pat.search(text), '隐私边界失守: %s' % pat.pattern

    scope = data['scope']
    assert scope['packets'] == 12 and scope['runs'] == 5
    assert scope['model'] == 'deepseek-flash' and scope['effort'] == 'low'

    chains = data['chains']
    groups = chains['A_grouping']['groups']
    assert sum(len(g) for g in groups) == scope['packets']
    flat = [n for g in groups for n in g]
    assert sorted(flat) == list(range(1, 13)), '分组序号应为 1..12 的划分'
    assert chains['A_grouping']['cross_method_agree'] is True
    assert chains['A_grouping']['top_level_keys_uniform'] == 12

    b = chains['B_metadata']
    assert b['model_deepseek_flash'] == b['effort_low'] == b['framing_rechunked'] == 12

    c = chains['C_stream_gates']
    assert c['envelope_and_item_gates_ok'] == 12
    assert c['response_ids_all_distinct'] == 12
    assert c['run_records_differ'] is True and c['within_run_input_growth'] is True

    h = chains['H_persha']
    assert h['bound'] == h['total'] == 12

    rows = data['g_w_binding']
    assert len(rows) == 5
    msg_local = sum(r['agent_message']['local'] for r in rows)
    msg_wire = sum(r['agent_message']['wire'] for r in rows)
    msg_matched = sum(r['agent_message']['matched'] for r in rows)
    assert (msg_local, msg_wire, msg_matched) == (6, 6, 6), 'agent_message 应为 6/6'

    cmd_local = sum(r['command']['local'] for r in rows)
    cmd_wire = sum(r['command']['wire_calls'] for r in rows)
    cmd_ok = sum(r['command']['adapter_matched'] for r in rows)
    cmd_quote = sum(r['command']['quoting_unprovable'] for r in rows)
    cmd_none = sum(r['command']['no_counterpart'] for r in rows)
    assert (cmd_local, cmd_wire, cmd_ok, cmd_quote, cmd_none) == (7, 7, 5, 2, 0), \
        'command 应为 本地7 / wire7 / 适配5 / quoting不可证2 / 无对应0'
    for r in rows:
        ccmd = r['command']
        assert ccmd['adapter_matched'] + ccmd['quoting_unprovable'] + ccmd['no_counterpart'] == ccmd['local']
        am = r['agent_message']
        assert am['local'] == am['wire'] and 0 <= am['matched'] <= am['local']

    assert len(data['equivalence_not_flipping']) == 3
    assert len(data['negative_gates_synthetic']) == 8
    assert len(data['sample_gaps']) == 3
    assert '不冻结' in ''.join(data['boundaries'])
    print('SELF-TEST OK (%d 分组、%d 包、消息 %d/%d、命令 本地%d/wire%d/适配%d/quoting%d)'
          % (len(groups), scope['packets'], msg_matched, msg_local, cmd_local, cmd_wire, cmd_ok, cmd_quote))
    return 0


def main(argv):
    if '--self-test' in argv:
        return self_test()
    print(__doc__)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
