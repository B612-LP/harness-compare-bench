#!/usr/bin/env python3
"""只读复核公开文件；不执行 checker 或题解，不访问私档。"""
import ast
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOCK = '4-打分细则/可信冻结-20261031-wb-v2/freeze.lock.json'
CHECKER = '2-用例/lcb-recent-hard-4/checker.py'
TRUTH = '2-用例/lcb-recent-hard-4/truth.json'
INPUT = '2-用例/lcb-recent-hard-4/inputs/problems.json'
RUN_DIR = '3-表现现场/r20261101-doubao-n3/runs/lcb-recent-hard-4'
LOCK_SHA = 'e2f52839c444f9e7430110ddae26e719e0c59a89d57fd432901801bff2bc36d7'
PIN_SHAS = {
    CHECKER: '63845361deb0949eba4193b7a2fff34569d7750d9e1b1b29405b28c0223b8ee9',
    TRUTH: '8a9ae6deb4d088b011348d5245d18697f5df5b8b65390c7679c6a8d539c90d14',
    INPUT: '0ce2f9c1eee0039fa9cfc7cd9969d99118d3fba4ac41571c49d9f5289592a673',
}
RECEIPTS = {
    1: ('completed', 100.0, '6a54a0cf7d97f055e27ceaae8b4f53327041f2e6175f84953f31b4174effb7ad'),
    2: ('completed', 75.0, 'e069eeea8cd5a17d1f005e3460d4e522fcffd2f095ee244e6ee6a7c6cf4218f1'),
    3: ('timeout', 75.0, '30bf14453ca72744a9236c8556f1e1332cc7821bdcb901b80466847c7801e4ca'),
}
ORDER = ['abc387_f', 'abc388_f', 'abc388_g', 'abc389_g']
COUNTS = dict(zip(ORDER, (43, 43, 42, 43)))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_bytes(path):
    return (ROOT / path).read_bytes()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def load_json(path):
    return json.loads(read_bytes(path))


def verify():
    require(digest(read_bytes(LOCK)) == LOCK_SHA, 'lock SHA-256 不匹配')
    lock = load_json(LOCK)
    require(lock.get('rule_version') == 'freeze-20261031-wb-v2', 'lock 版本不匹配')
    for path, expected in PIN_SHAS.items():
        pins = [p for p in lock['pins'] if p.get('path') == path]
        require(len(pins) == 1 and pins[0].get('sha256') == expected, path + ' pin 不唯一或不匹配')
        require(digest(read_bytes(path)) == expected, path + ' 文件哈希不匹配')
    print('OK: lock 和三个指定 pin 的实际字节哈希一致；未检查其他 pin。')

    # 只解析 AST 的顶层字面量，不 import 或运行 checker。
    tree = ast.parse(read_bytes(CHECKER), filename=CHECKER)
    wanted = {'CASE_ID', 'PASS_THRESHOLD', 'TEST_TIMEOUT_S', 'PROBLEM_BUDGET_S',
              'N_PROBLEMS', 'PROBLEM_ORDER', 'EXPECTED_TEST_COUNTS'}
    constants = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            if name in wanted:
                require(name not in constants, 'checker 常量重复: ' + name)
                constants[name] = ast.literal_eval(node.value)
    require(constants == {'CASE_ID': 'lcb-recent-hard-4', 'PASS_THRESHOLD': 2,
                          'TEST_TIMEOUT_S': 10, 'PROBLEM_BUDGET_S': 240,
                          'N_PROBLEMS': 4, 'PROBLEM_ORDER': ORDER,
                          'EXPECTED_TEST_COUNTS': COUNTS}, 'checker 常量不符')
    truth = load_json(TRUTH)
    require(truth['case_id'] == constants['CASE_ID'] and truth['n_problems'] == 4
            and truth['pass_threshold'] == 2 and truth['timeout_s_per_test'] == 10,
            'truth 顶层常量不符')
    data = read_bytes(INPUT)
    require(truth['input_name'] == 'problems.json' and truth['input_sha256'] == digest(data)
            and truth['input_bytes'] == len(data), 'truth 的输入文件绑定不符')
    problems = truth['problems']
    require(list(problems) == ORDER, '题单或顺序不符')
    for pid in ORDER:
        problem = problems[pid]
        tests = problem['tests']
        require(isinstance(tests, list) and len(tests) == COUNTS[pid], pid + ' 测试数不符')
        require(all(isinstance(t.get('input'), str) and isinstance(t.get('output'), str)
                    and t.get('source') in ('public', 'private') for t in tests), pid + ' 测试记录无效')
        require(sum(t['source'] == 'public' for t in tests) == problem['n_public']
                and sum(t['source'] == 'private' for t in tests) == problem['n_private'], pid + ' 标签计数不符')
        serialized = json.dumps(tests, ensure_ascii=False, sort_keys=True).encode('utf-8')
        require(digest(serialized) == problem['tests_sha256'], pid + ' tests_sha256 不符')
    sample = problems['abc389_g']['tests'][3]
    require(sample['input'].strip() == '30 100000039' and sample['source'] == 'private',
            'abc389_g 索引 3 静态记录不符')
    print('OK: 四题顺序、测试列表计数与序列化哈希、输入绑定和索引 3 的静态输入一致。')
    print('    索引 3 为零基第 4 组；source=private 是历史标签，truth 本身公开。')

    for rep, (status, score, ref) in RECEIPTS.items():
        path = f'{RUN_DIR}/run-lcb-recent-hard-4__r{rep}.json'
        run = load_json(path)
        grading = run['grading']
        require(run['case'] == 'lcb-recent-hard-4' and type(run['rep']) is int and run['rep'] == rep
                and run['rule_frozen_ref'] == 'freeze-20261031-wb-v2'
                and run['status'] == status and run['final_adjudication'] == 'valid', f'r{rep} 公开字段不符')
        require(type(grading['weighted']) in (int, float) and grading['weighted'] == score
                and type(grading['reward']) is int and grading['reward'] == 1
                and grading['checker_result_reported'] is True
                and grading['execution_receipt_sha256'] == ref, f'r{rep} 分数或私档回执哈希引用不符')
        print(f'OK: r{rep} 状态 {status}，weighted={score:g}，reward=1；回执引用 {ref}')
    print('边界: 仅核公开字段与内容一致性；未读取或认证私档回执、历史源码或实际运行时字节。')
    print('索引与运行行为的关联以历史回执语义和实际采用锁定内容为条件，非独立运行时证明。')


def main():
    try:
        verify()
    except (OSError, ValueError, KeyError, TypeError, SyntaxError, UnicodeError) as exc:
        print(f'FAIL: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
