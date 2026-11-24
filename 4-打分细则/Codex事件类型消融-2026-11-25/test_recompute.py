#!/usr/bin/env python3
"""R6 公开复算器测试：正常合同 + 六类篡改夹具全部拒绝。"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from recompute import Invalid, load_contract, verify

HERE = Path(__file__).resolve().parent
CONTRACT = json.loads((HERE / 'codex-ablation-contract.json').read_text())


def patched(fn):
    c = json.loads(json.dumps(CONTRACT))
    fn(c)
    return c


REJECTED = 0


def expect_invalid(name, c):
    global REJECTED
    try:
        verify(c)
    except Invalid as e:
        REJECTED += 1
        print(f'  OK {name}: 拒绝（{str(e)[:60]}…）')
        return
    raise SystemExit(f'夹具 {name} 未被拒绝')


# 正常
s = verify(CONTRACT)
print('normal OK', json.dumps(s, ensure_ascii=False)[:120])

# NM-A 绑定 sha 非 hex
expect_invalid('sha 非 hex', patched(lambda c: c['binding']['slots'][0].__setitem__('sha256', 'zz')))
# NM-B 槽缺失
expect_invalid('槽缺失', patched(lambda c: c['binding']['slots'].pop()))
# NM-C 面分类矛盾：header 类型声明但等值翻 false
def nm_c(c):
    for t in c['face_partition']['per_case']['dabstep-payments-10']:
        if t == 'session_meta':
            c['face_partition']['per_case']['dabstep-payments-10'][t]['masked_equal_all_lines'] = False
expect_invalid('header 等值矛盾', patched(nm_c))
# NM-D variance 类型被声明等值
def nm_d(c):
    c['face_partition']['per_case']['dabstep-payments-10']['token_usage_record']['masked_equal_all_lines'] = True
    # SHA 集也要一致否则先撞三态不变式；这里只看 face 声明矛盾时三个 sha 相同需同步
    shas = c['face_partition']['per_case']['dabstep-payments-10']['token_usage_record']['masked_stream_sha256']
    for k in shas:
        shas[k] = list(shas.values())[0]
expect_invalid('variance 等值矛盾', patched(nm_d))
# NM-E usage 对表破坏
expect_invalid('usage 对表破坏', patched(lambda c: c['usage_match'].__setitem__('slots_total_equal', 14)))
# NM-F 输入三行破坏
def nm_f(c):
    c['input_rows']['per_case']['tb-cargo-plan']['masked_equal'] = [True, False, True]
expect_invalid('输入行等值破坏', patched(nm_f))
# NM-G 常量多值
expect_invalid('常量多值', patched(lambda c: c['constants'].__setitem__('collaboration_mode.model', ['deepseek-flash', 'other'])))
# NM-H 近错声明假
expect_invalid('近错声明假', patched(lambda c: c['near_miss'].__setitem__('QE2_binding_mismatch_rejected', False)))
# NM-I union 与 face 计数不一致
expect_invalid('union 计数不一致', patched(lambda c: c['type_union'].__setitem__('session_meta', 999)))

expect_invalid('绑定三链破坏', patched(lambda c: c['binding_triple'].__setitem__('slots_all_equal', False)))

print(f'全部夹具拒绝通过：{REJECTED} 项')
