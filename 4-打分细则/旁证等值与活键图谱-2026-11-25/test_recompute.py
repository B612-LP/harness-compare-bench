#!/usr/bin/env python3
"""R4 公开复算器测试：正常件 + 5 个近错夹具（全部必须被拒绝或如实区分）。"""
import copy
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from recompute import Invalid, load_contract, verify  # noqa: E402

CONTRACT = json.loads((HERE / 'sidecar-key-contract.json').read_bytes())


def patch(path, value):
    d = copy.deepcopy(CONTRACT)
    cur = d
    for k in path[:-1]:
        cur = cur[k]
    cur[path[-1]] = value
    return d


def run_case(name, c, expect_ok):
    try:
        verify(load_contract(c))
        ok = True
    except Invalid:
        ok = False
    assert ok == expect_ok, f'{name}: 期望 {"通过" if expect_ok else "拒绝"} 实得 {"通过" if ok else "拒绝"}'
    print(f'{name}: {"OK(通过)" if ok else "OK(拒绝)"}')


# 正常件
run_case('normal', CONTRACT, True)

# NM-A 死文件作等值声明（空洞真理）
run_case('dead-equality-claim',
         patch(['sidecar_verdicts', 'socket/briefing.md', 'masked_equal'], True), False)

# NM-B PA 等值翻 false（输入侧旁证破裂）
run_case('pa-equality-broken',
         patch(['PA_input_side', 'masked_equal_all'], False), False)

# NM-C sha 非 hex
run_case('sha-not-hex',
         patch(['binding', 'files', 'doubao::tb-cargo-plan__r1::session_meta.json', 'sha256'], 'zz' * 32), False)

# NM-D 活键 live 与 nonzero 不一致（死键误标活）
c = copy.deepcopy(CONTRACT)
c['wb_rawusage_key_activity']['prompt_cache_write_tokens']['live'] = True
run_case('dead-key-marked-live', c, False)

# NM-E 死键集漂移（把活键挪进死键语义）
c = copy.deepcopy(CONTRACT)
for k in list(c['wb_rawusage_key_activity']):
    c['wb_rawusage_key_activity'][k]['nonzero'] = 0
run_case('all-keys-dead', c, False)

# NM-F 载体计数和 != 160（漏计静默丢失）
c = copy.deepcopy(CONTRACT)
c['wb_rawusage_key_activity']['credit']['nonzero'] = 159
run_case('carrier-count-broken', c, False)

# NM-G 归一层键漂移（DSH 形 totalTokens 口径混入）
c = copy.deepcopy(CONTRACT)
del c['wb_norm_layer']['requests']
run_case('norm-layer-drift', c, False)

# NM-H 不等值却三 SHA 全同（独审 X3 穿透形态，N8 补）
c = copy.deepcopy(CONTRACT)
c['sidecar_verdicts']['board.md']['masked_sha256'] = ['aa' * 32] * 3
run_case('unequal-but-identical-shas', c, False)

# NM-I 等值却 SHA 互异（列表形态破坏不变式）
c = copy.deepcopy(CONTRACT)
c['sidecar_verdicts']['system/assignment.md']['masked_sha256'] = ['bb' * 32, 'cc' * 32, 'dd' * 32]
run_case('equal-but-divergent-shas', c, False)

print('10/10 OK')
