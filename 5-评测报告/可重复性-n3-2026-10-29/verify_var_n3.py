#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""verify_var_n3.py — 自动循环 L1 包A 独立验收工具（judge 只读核验）。

职责（预注册《自动循环L1-2026-10-29》包A + judge 任务书）：
  a) 每场所用 checker 文件 SHA 与冻结合同一致
     （freeze.lock.json 封印逐 pin 复核 + config.json case_snapshots 逐场比对
       + score-receipt.checker_sha256 交叉 + 运行目录内 checker.py 副本实哈希）；
  b) meta 时序：registered_at < started_at，且两者均 ≥ 预注册封印锚点；
     r1031 场要求 meta.preregistration_commit = be39fc2（r1030 自检无此字段，按锚点 213013b 记 n/a）；
  c) 从 checker.stdout.json 独立重算加权分（GUARDS 守卫项不计分；分母=全题数；
     权重与口径移植自 3-表现现场/r1030-formal-a1/tools/build_import.py，逐行等价）；
  d) 完整性复核：对会话轨迹独立重扫八类越界模式（移植 r1030 tools/rescan_integrity.py），
     不得出现 truth/solution 访问；benign 命中按 r1030 既有裁定口径单列，不掩盖；
  e) 汇总核验矩阵 JSON（每场×a/b/c/d + 批级聚合：每 rep weighted 总分/headline、
     每产品 spread、逐 case 翻转计数、PREREGISTRATION 包A 锁定判据 gap₀ 评估）。

本工具对批目录**只读**；唯一写出物是 --out 指定的矩阵 JSON（默认落在 judge 目录）。
不对运行目录做任何修正/回填（与 r1030 rescan_integrity.py 的“回填”行为不同：
验收工具无写权限边界之外的职责，发现分歧如实记录）。

自检模式 --profile r1030：对 r1030 十场只读运行，并与已知值
（r1030 README 结果矩阵 + PREREGISTRATION 包A：weighted 444.81/414.07、headline 双 3/5）
逐项比对。注意：official-main-table.json 本身无逐行分值（ranking=null），
known 值的实际载体是 r1030 README 结果矩阵与阶段报告-v4.1。

用法：
  python3 verify_var_n3.py --profile r1030 --out verify-matrix-selftest-r1030.json
  python3 verify_var_n3.py --profile r1031 --out verify-matrix-r1031-n3.json
仅依赖 Python3 标准库（zstd 解压优先用 zstd CLI，缺失时回退 zstandard 模块）。
"""
import argparse
import datetime as dt
import hashlib
import json
import pathlib
import re
import subprocess
import sys

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
REPO = SCRIPT_DIR.parents[1]
V2 = REPO / '4-打分细则' / '可信冻结-2026-10-29-v2'
FREEZE_LOCK = V2 / 'freeze.lock.json'
PREREG = REPO / '1-评测方案' / '自动循环L1-2026-10-29' / 'PREREGISTRATION.md'
RULE_VERSION = 'freeze-20261029-v2'

# ---- 计分口径（逐行移植自 3-表现现场/r1030-formal-a1/tools/build_import.py，不得改动） ----
CASES = ('bird-ca-schools-15', 'dabstep-payments-10', 'exercism-py-6', 'lcb-recent-hard-4', 'tb-cargo-plan')
TOTALS = dict(zip(CASES, (15, 10, 6, 4, 27)))
GUARDS = {
    'bird-ca-schools-15': {'input_integrity', 'answers_file', 'answers_schema', 'answers_coverage'},
    'dabstep-payments-10': {'answers_format', 'input_integrity'},
    'exercism-py-6': {'input_integrity'},
    'lcb-recent-hard-4': {'input_integrity'},
    'tb-cargo-plan': {'input_integrity', 'code_rerun', 'plan_structure'},
}
# ---- 完整性口径（移植自 r1030 tools/rescan_integrity.py） ----
PATTERNS = ["2-用例", "truth.json", "checker.py", "reference/", "solution/", "../",
            "~/Documents", "harness-compare-bench"]
BENIGN_MARKERS = ('<system-reminder>', 'workspace instructions')  # r1030 已裁定口径：运行时注入的用户级 AGENTS.md 文本

# ---- 预注册锚点 ----
PROFILES = {
    'r1030': {
        'batch': REPO / '3-表现现场' / 'r1030-formal-a1',
        'anchor_commit': '213013b',                       # r1030 README：规则封印提交 Git 213013b
        'anchor_time': '2026-10-29T02:10:00+08:00',       # registration-plan.json created_at（先于全部 started_at）
        'require_commit_field': False,                    # r1030 meta 无 preregistration_commit 字段（该字段自 L1 起）
        'expect_runs': 10,
        'plan_roots': [REPO / '1-评测方案' / '正式批次-2026-10-29'],
    },
    'r1031': {
        'batch': REPO / '3-表现现场' / 'r1031-variance-n3',
        'anchor_commit': 'be39fc2',                       # PREREGISTRATION.md 封印提交
        'anchor_time': '2026-10-29T13:22:00+08:00',
        'require_commit_field': True,
        'expect_runs': 20,
        'plan_roots': [],
    },
}
# ---- 自检已知值（出处：3-表现现场/r1030-formal-a1/README.md 结果矩阵；总分另见 PREREGISTRATION 包A） ----
SELFTEST_EXPECT = {
    'claimed_source': (
        '3-表现现场/r1030-formal-a1/README.md 结果矩阵（headline 双 3/5；weighted 总分 444.81 vs 414.07）；'
        'official-main-table.json 无逐行分值（ranking=null）'),
    'per_case_weighted': {
        'codex': {'bird-ca-schools-15': 93.33, 'dabstep-payments-10': 70.0, 'exercism-py-6': 100.0,
                  'lcb-recent-hard-4': 100.0, 'tb-cargo-plan': 81.48},
        'dsh': {'bird-ca-schools-15': 100.0, 'dabstep-payments-10': 70.0, 'exercism-py-6': 100.0,
                'lcb-recent-hard-4': 100.0, 'tb-cargo-plan': 74.07},
    },
    'weighted_total': {'codex': 444.81, 'dsh': 414.07},
    'headline': {'codex': 3, 'dsh': 3},
}
# ---- 判据参数（lead 裁决 + AMENDMENT-1：主判据 gap₀=0.74=|444.81−444.07| 产物可复现值；
#      原预注册锁定值 30.74 降为敏感性对照；封印文件 be39fc2 不改写。动机=历史值勘误，与 r1031 结果无关） ----
GAP0_MAIN = 0.74
GAP0_SENSITIVITY = 30.74


def sha256_file(p: pathlib.Path) -> str:
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def parse_ts(s):
    if s is None:
        return None
    s = str(s).strip()
    if s.endswith('Z'):
        s = s[:-1] + '+00:00'
    try:
        return dt.datetime.fromisoformat(s)
    except ValueError:
        m = re.match(r'^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})(?::(\d{2}))?(?:\.(\d+))?(Z|[+-]\d{2}:?\d{2})?$', s)
        if not m:
            return None
        Y, Mo, D, H, Mi, S, frac, off = m.groups()
        micro = int((frac or '0').ljust(6, '0')[:6]) if frac else 0
        if off in (None, 'Z'):
            tz = dt.timezone.utc if off == 'Z' else None
        else:
            sign = 1 if off[0] == '+' else -1
            oh, om = int(off[1:3]), int(off[-2:])
            tz = dt.timezone(sign * dt.timedelta(hours=oh, minutes=om))
        base = dt.datetime(int(Y), int(Mo), int(D), int(H), int(Mi), int(S or 0), micro, tz)
        return base if tz else base.replace(tzinfo=dt.timezone.utc)


def jload(p: pathlib.Path):
    try:
        return json.loads(p.read_text(encoding='utf-8'))
    except Exception:
        return None


def load_reg_plan(batch: pathlib.Path, extra_roots=()):
    """批内注册表 → {event_id: registered_at}；支持批根或 <product>/ 子目录；
    r1030 的 plan 在批目录外（1-评测方案/正式批次-2026-10-29/），由 extra_roots 提供。"""
    out = {}
    roots = [batch] + list(extra_roots)
    for root in roots:
        if not root.is_dir():
            continue
        for p in sorted(root.rglob('*registration*.json')):
            d = jload(p)
            if not isinstance(d, dict):
                continue
            for r in d.get('registrations') or []:
                if isinstance(r, dict) and r.get('event_id') and r.get('registered_at'):
                    out[r['event_id']] = r['registered_at']
    return out


def discover_runs(batch: pathlib.Path):
    """泛化发现运行目录：批树下任何含 meta.json 的目录（跳过 staging/preflight/selftest/tools*）。"""
    if not batch.is_dir():
        return []
    skip_names = {'staging', 'preflight', 'selftest'}
    found = []
    for meta_p in sorted(batch.rglob('meta.json')):
        if any(part in skip_names or part.startswith('tools') for part in meta_p.parts):
            continue
        found.append(meta_p.parent)
    return found


def rep_of(meta, run_dir: pathlib.Path, batch_name: str):
    if isinstance(meta.get('rep'), int):
        return meta['rep']
    for key in ('event_id', 'run_id'):
        m = re.search(r'-r(\d+)$', str(meta.get(key) or ''))
        if m:
            return int(m.group(1))
    m = re.search(r'_r(\d+)$', run_dir.name)
    if m:
        return int(m.group(1))
    return 1 if 'r1030' in batch_name else None


def classify_hit(hit):
    """r1030 已裁定口径：命中行为运行时注入的用户级说明文本（<system-reminder> 包裹）→ benign。"""
    blob = hit.get('_blob', '')
    if '<system-reminder>' in blob:
        return 'benign-runtime-injection'
    if 'workspace instructions' in blob:
        return 'benign-runtime-injection'
    return 'strict-violation'


def scan_sessions(run_dir: pathlib.Path):
    """独立重扫会话轨迹（read-only），返回 (res, note)。"""
    sess = run_dir / 'agent-session'
    files = []
    if sess.is_dir():
        files = sorted(sess.iterdir())
    else:  # 泛化回退：运行目录内任何轨迹类文件
        files = [p for p in sorted(run_dir.rglob('*'))
                 if p.is_file() and (p.suffix in ('.jsonl', '.zstd', '.zst')
                                     or p.name.endswith('.jsonl.zstd'))]
    files = [p for p in files if p.is_file() and p.name not in ('checker.stdout.json', 'meta.json',
                                                                'adjudication.json', 'score-receipt.json',
                                                                'integrity-rescan.json')]
    res = {'session_files': [], 'lines_scanned': 0, 'hits': [], 'decompress': 'ok'}
    if not files:
        res['decompress'] = 'no-trajectory-files'
        return res, 'missing'
    zstd_backend = None
    for p in files:
        zst = p.name.endswith('.zstd') or p.name.endswith('.zst')
        res['session_files'].append({'name': p.name, 'bytes': p.stat().st_size, 'zstd': zst})
        if zst:
            text = None
            try:
                pr = subprocess.run(['zstd', '-dc', str(p)], capture_output=True, timeout=120)
                if pr.returncode == 0:
                    text = pr.stdout.decode('utf-8', errors='replace')
                    zstd_backend = 'zstd-cli'
            except (FileNotFoundError, subprocess.TimeoutExpired):
                pass
            if text is None:
                try:
                    import zstandard  # noqa: F401 可选回退
                    dctx = zstandard.ZstdDecompressor()
                    text = dctx.stream_reader(open(p, 'rb')).read().decode('utf-8', errors='replace')
                    zstd_backend = 'zstandard-py'
                except Exception:
                    res['decompress'] = 'failed'
                    continue
        else:
            text = p.read_text(encoding='utf-8', errors='replace')
        for i, line in enumerate(text.splitlines()):
            res['lines_scanned'] += 1
            try:
                ev = json.loads(line)
            except Exception:
                continue
            blob = json.dumps(ev, ensure_ascii=False)
            for pat in PATTERNS:
                if pat in blob:
                    hit = {'file': p.name, 'line': i + 1, 'pattern': pat, 'excerpt': blob[:300], '_blob': blob}
                    hit['class'] = classify_hit(hit)
                    hit.pop('_blob')
                    res['hits'].append(hit)
                    break
            if len(res['hits']) >= 20:
                break
        if len(res['hits']) >= 20:
            break
    if zstd_backend:
        res['decompress'] = zstd_backend
    return res, ('ok' if res['decompress'] != 'failed' else 'cannot-decompress')


def verify_one(run_dir: pathlib.Path, prof: dict, reg_plan: dict, freeze_ok: dict, cfg: dict):
    meta = jload(run_dir / 'meta.json') or {}
    stdout = jload(run_dir / 'checker.stdout.json')
    receipt = jload(run_dir / 'score-receipt.json')
    adj = jload(run_dir / 'adjudication.json')
    row = {
        'run_dir': str(run_dir.relative_to(REPO)),
        'product': meta.get('product'), 'case': meta.get('case'),
        'rep': rep_of(meta, run_dir, prof['batch'].name),
        'event_id': meta.get('event_id') or (adj or {}).get('event_id'),
        'run_id': meta.get('run_id') or (receipt or {}).get('run_id'),
    }
    case = row['case']
    checks = {}

    # ---------- a) checker SHA 与冻结合同一致 ----------
    frozen_sha = (cfg.get('case_snapshots', {}).get(case) or {}).get('checker.py')
    receipt_sha = ((receipt or {}).get('score') or {}).get('checker_sha256')
    copies = []
    for cp in sorted(run_dir.rglob('checker.py')):
        csha = sha256_file(cp)
        copies.append({'path': str(cp.relative_to(REPO)), 'sha256': csha,
                       'match_frozen': (csha == frozen_sha)})
    a_ok = bool(frozen_sha) and (receipt_sha == frozen_sha) \
        and all(c['match_frozen'] for c in copies) \
        and meta.get('rule_version') == RULE_VERSION
    checks['a_checker_sha'] = {
        'status': 'pass' if a_ok else 'fail',
        'frozen_config_sha': frozen_sha, 'receipt_sha': receipt_sha,
        'run_dir_checker_copies': copies,
        'meta_rule_version': meta.get('rule_version'),
        'freeze_lock_pins_ok': freeze_ok.get('ok'),
        'detail': ('receipt+config+副本三方一致' if a_ok else
                   'receipt/config/副本/rule_version 存在不一致，见字段'),
    }

    # ---------- b) meta 时序与预注册锚点 ----------
    reg_src = None
    registered_raw = meta.get('registered_at')
    if registered_raw:
        reg_src = 'meta.registered_at'
    elif row['event_id'] and row['event_id'] in reg_plan:
        registered_raw = reg_plan[row['event_id']]
        reg_src = 'registration-plan'
    started_raw = meta.get('started_at')
    reg_t, start_t = parse_ts(registered_raw), parse_ts(started_raw)
    anchor_t = parse_ts(prof['anchor_time'])
    b_detail = {'registered_at': registered_raw, 'registered_at_source': reg_src,
                'started_at': started_raw,
                'anchor_commit': prof['anchor_commit'], 'anchor_time': prof['anchor_time']}
    if reg_t and start_t:
        b_detail['registered_lt_started'] = reg_t < start_t
        b_detail['registered_ge_anchor'] = reg_t >= anchor_t
        b_detail['started_ge_anchor'] = start_t >= anchor_t
    commit_val = meta.get('preregistration_commit')
    if prof['require_commit_field']:
        commit_ok = isinstance(commit_val, str) and commit_val.startswith(prof['anchor_commit'])
        b_detail['preregistration_commit'] = {'value': commit_val, 'match': commit_ok}
    else:
        commit_ok = None
        b_detail['preregistration_commit'] = {'value': commit_val, 'match': 'n/a（r1030 自检模式：该字段自 L1 起才有）'}
    b_ok = bool(reg_t and start_t and reg_t < start_t
                and reg_t >= anchor_t and start_t >= anchor_t
                and (commit_ok is not False))
    b_ok = b_ok and (commit_ok is not None if prof['require_commit_field'] else True)
    checks['b_meta_timing'] = {'status': 'pass' if b_ok else 'fail', **b_detail}

    # ---------- c) 独立重算加权分（GUARDS 不计分；口径=build_import.py） ----------
    c = {'status': 'fail'}
    if stdout is None:
        c['detail'] = 'checker.stdout.json 缺失或不可解析'
    elif case not in GUARDS:
        c['detail'] = '未知 case，GUARDS/TOTALS 无此题'
    else:
        guards = GUARDS[case]
        all_checks = stdout.get('checks') or []
        scored = [x for x in all_checks if x.get('id') not in guards]
        possible = len(scored)
        earned = sum(1 for x in scored if x.get('pass'))
        weighted = round(100.0 * earned / possible, 2) if possible else None
        c.update({
            'guards_excluded': sorted(guards), 'scored_items': possible,
            'earned': earned, 'expected_denominator': TOTALS[case],
            'weighted_recomputed': weighted,
            'weighted_stdout': stdout.get('weighted'), 'weighted_meta': meta.get('weighted'),
            'reward_stdout': stdout.get('reward'), 'reward_meta': meta.get('reward'),
        })
        denom_ok = possible == TOTALS[case]
        w_ok = (weighted is not None and stdout.get('weighted') is not None
                and abs(weighted - float(stdout['weighted'])) <= 0.011)
        m_ok = (meta.get('weighted') is None or abs(weighted - float(meta['weighted'])) <= 0.011)
        r_ok = (stdout.get('reward') == meta.get('reward'))
        # 收据交叉（存在才核）
        rcp = None
        if receipt:
            s = receipt.get('score') or {}
            rcp = {'present': True, 'earned_match': s.get('earned') == earned,
                   'possible_match': s.get('possible') == possible,
                   'reported_match': abs(float(s.get('reported', -1)) - 100.0 * earned / possible) < 1e-6,
                   'reward_match': s.get('reward') == stdout.get('reward'),
                   'rule_version_match': s.get('rule_version') == RULE_VERSION}
            c['receipt_crosscheck'] = rcp
        # 阈值一致性（checker 自带 threshold 的题才核；cargo 契约无 threshold，记 skipped）
        thr = stdout.get('threshold')
        if thr is not None:
            exp_reward = 1 if (earned / possible) >= float(thr) else 0
            c['threshold_consistency'] = {'threshold': thr, 'expected_reward': exp_reward,
                                          'match': exp_reward == stdout.get('reward')}
        else:
            c['threshold_consistency'] = {'threshold': None, 'note': '该题 checker 契约不含 threshold，reward 以冻结 checker 输出为准'}
        c_ok = denom_ok and w_ok and m_ok and r_ok and (rcp is None or all(rcp[k] for k in
               ('earned_match', 'possible_match', 'reported_match', 'reward_match', 'rule_version_match')))
        c['status'] = 'pass' if c_ok else 'fail'
        c['detail'] = ('分母=全题数，GUARDS 不计分；weighted/双源 reward/收据全部一致'
                       if c_ok else '存在不一致，见上字段')
    checks['c_weighted_recompute'] = c

    # ---------- d) 完整性复核（独立轨迹重扫） ----------
    res, note = scan_sessions(run_dir)
    benign = [h for h in res['hits'] if h['class'] == 'benign-runtime-injection']
    strict = [h for h in res['hits'] if h['class'] == 'strict-violation']
    own = jload(run_dir / 'integrity-rescan.json') or {}
    d = {
        'status': 'pass' if (note == 'ok' and not strict) else 'fail',
        'scan_note': note, 'patterns': PATTERNS,
        'session_files': res['session_files'], 'lines_scanned': res['lines_scanned'],
        'hits_raw': len(res['hits']),
        'hits_benign_runtime_injection': [{k: v for k, v in h.items() if k != 'excerpt'} | {'excerpt': h['excerpt']} for h in benign],
        'violations_strict': [{k: v for k, v in h.items() if k != 'excerpt'} | {'excerpt': h['excerpt']} for h in strict],
        'benign_basis': 'r1030 既有裁定口径：运行时注入的 ~/.dsh/AGENTS.md 文本命中 ~/Documents，非模型访问',
    }
    if note == 'ok':
        d['own_artifacts'] = {
            'integrity_rescan_violations': own.get('violations'),
            'meta_integrity_verdict': meta.get('integrity_verdict') or (meta.get('integrity') or {}).get('violations'),
        }
        d['agreement'] = (own.get('violations') == len(res['hits'])) if own else 'no-own-rescan-file'
    checks['d_integrity'] = d

    # ---------- e) 证据完备性（轻量） + 重算值供聚合 ----------
    row['checks'] = checks
    row['recomputed'] = {'weighted': checks['c_weighted_recompute'].get('weighted_recomputed'),
                         'reward': checks['c_weighted_recompute'].get('reward_stdout')}
    row['evidence_files'] = {
        'meta.json': (run_dir / 'meta.json').is_file(),
        'checker.stdout.json': (run_dir / 'checker.stdout.json').is_file(),
        'score-receipt.json': (run_dir / 'score-receipt.json').is_file(),
        'adjudication.json': (run_dir / 'adjudication.json').is_file(),
        'workspace_TASK_md': (run_dir / 'workspace' / 'TASK.md').is_file(),
        'agent_session_files': len(res['session_files']),
    }
    row['status'] = 'pass' if all(v.get('status') == 'pass' for k, v in checks.items() if k != 'e') else 'fail'
    return row


def aggregate(rows, gap0_main=GAP0_MAIN, gap0_sens=GAP0_SENSITIVITY):
    """批级聚合：每产品×rep weighted 总分/headline、spread、翻转计数、判据评估。

    判据治理（lead 裁决 + AMENDMENT-1）：主判据 gap₀=0.74（=|444.81−444.07|，产物可复现值）；
    原预注册锁定值 30.74 降为敏感性对照；封印文件 be39fc2 不改写。"""
    by_p = {}
    for r in rows:
        by_p.setdefault(r['product'], {}).setdefault(r['rep'], {})[r['case']] = r['recomputed']
    agg = {}
    for p, reps in sorted(by_p.items()):
        agg[p] = {}
        totals, headlines = [], {}
        for rep in sorted(k for k in reps if k is not None):
            cases = reps[rep]
            w = {c: v['weighted'] for c, v in cases.items()}
            total = round(sum(float(x) for x in w.values() if x is not None), 2)
            headline = sum(1 for v in cases.values() if v.get('reward') == 1)
            agg[p][str(rep)] = {'per_case_weighted': w, 'per_case_reward': {c: v['reward'] for c, v in cases.items()},
                                'weighted_total': total, 'headline': headline}
            totals.append(total)
            headlines[rep] = headline
        agg[p]['weighted_spread'] = (round(max(totals) - min(totals), 2) if len(totals) >= 2 else None)
        agg[p]['headline_by_rep'] = {str(k): v for k, v in headlines.items()}
        # 逐 case 翻转计数（reward 序列中相邻不一致的次数）
        flips = {}
        for c in CASES:
            seq = [reps[rep].get(c, {}).get('reward') for rep in sorted(k for k in reps if k is not None)]
            seq = [x for x in seq if x is not None]
            flips[c] = {'reward_seq': seq, 'flips': sum(1 for i in range(1, len(seq)) if seq[i] != seq[i - 1])}
        agg[p]['case_reward_flips'] = flips
        spread = agg[p]['weighted_spread']

        def rule_eval(gap0):
            if spread is None:
                return {'spread': None,
                        'evaluation': 'n=1 per rep（自检/rep1-only）：spread 不适用'}
            if spread >= gap0:
                return {'spread': spread, 'gap0': gap0,
                        'evaluation': 'spread >= gap0 → 「r1030 产品差与重复性方差不可区分」'}
            return {'spread': spread, 'gap0': gap0,
                    'evaluation': (f'spread < gap0 → 报告 gap0/spread = '
                                   f'{round(gap0 / spread, 2) if spread else "n/a（spread=0）"}')}

        main_eval = rule_eval(gap0_main)
        main_eval['role'] = '主判据（AMENDMENT-1：gap₀=0.74，=|444.81−444.07| 产物可复现值）'
        agg[p]['prereg_rule_gap0'] = main_eval
        sens_eval = rule_eval(gap0_sens)
        sens_eval['role'] = f'敏感性对照（原预注册锁定值 gap₀={gap0_sens}，据锚点勘误降级；见锚点勘误披露）'
        agg[p]['sensitivity_gap0'] = sens_eval
    return agg


def selftest_compare(rows, agg):
    cmp = {'claimed_source': SELFTEST_EXPECT['claimed_source'], 'items': []}
    for p in ('codex', 'dsh'):
        for case, want in SELFTEST_EXPECT['per_case_weighted'][p].items():
            got = None
            for r in rows:
                if r['product'] == p and r['case'] == case:
                    got = r['recomputed']['weighted']
            cmp['items'].append({'kind': 'per_case_weighted', 'key': f'{p}/{case}',
                                 'claimed': want, 'recomputed': got,
                                 'match': got is not None and abs(got - want) <= 0.011})
        want_h = SELFTEST_EXPECT['headline'][p]
        got_h = agg.get(p, {}).get('headline_by_rep', {}).get('1')
        cmp['items'].append({'kind': 'headline', 'key': p, 'claimed': want_h, 'recomputed': got_h,
                             'match': got_h == want_h})
        want_t = SELFTEST_EXPECT['weighted_total'][p]
        got_t = agg.get(p, {}).get('1', {}).get('weighted_total')
        cmp['items'].append({'kind': 'weighted_total', 'key': p, 'claimed': want_t, 'recomputed': got_t,
                             'match': got_t is not None and abs(got_t - want_t) <= 0.011})
    cmp['all_match'] = all(i['match'] for i in cmp['items'])
    cmp['mismatch_notes'] = [
        f"{i['key']}: claimed={i['claimed']} recomputed={i['recomputed']}"
        for i in cmp['items'] if not i['match']]
    return cmp


def verify_freeze_lock():
    lock = jload(FREEZE_LOCK)
    out = {'lock_file': str(FREEZE_LOCK.relative_to(REPO)), 'pins_checked': 0, 'pins_ok': 0,
           'mismatches': [], 'ok': False, 'lock_sha256': sha256_file(FREEZE_LOCK)}
    if not lock:
        out['mismatches'].append({'path': str(FREEZE_LOCK), 'error': 'unreadable'})
        return out
    for pin in lock.get('pins', []):
        p = REPO / pin['path']
        out['pins_checked'] += 1
        if not p.is_file():
            out['mismatches'].append({'path': pin['path'], 'error': 'missing'})
            continue
        got = sha256_file(p)
        if got != pin['sha256']:
            out['mismatches'].append({'path': pin['path'], 'expected': pin['sha256'], 'actual': got})
        else:
            out['pins_ok'] += 1
    out['ok'] = not out['mismatches']
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--profile', choices=sorted(PROFILES), default=None)
    ap.add_argument('--batch', type=pathlib.Path, default=None)
    ap.add_argument('--anchor-commit', default=None)
    ap.add_argument('--anchor-time', default=None)
    ap.add_argument('--require-commit-field', dest='require_commit_field', action='store_true', default=None)
    ap.add_argument('--expect-runs', type=int, default=None)
    ap.add_argument('--gap0-main', type=float, default=GAP0_MAIN,
                    help='主判据 gap0（AMENDMENT-1 默认 0.74）')
    ap.add_argument('--gap0-sensitivity', type=float, default=GAP0_SENSITIVITY,
                    help='敏感性对照 gap0（原预注册锁定值，默认 30.74）')
    ap.add_argument('--out', type=pathlib.Path, default=None)
    args = ap.parse_args()

    prof_name = args.profile or 'r1031'
    base = PROFILES[prof_name]
    prof = {
        'batch': args.batch or base['batch'],
        'anchor_commit': args.anchor_commit or base['anchor_commit'],
        'anchor_time': args.anchor_time or base['anchor_time'],
        'require_commit_field': base['require_commit_field'] if args.require_commit_field is None else args.require_commit_field,
        'expect_runs': args.expect_runs if args.expect_runs is not None else base['expect_runs'],
        'plan_roots': base.get('plan_roots', []),
    }
    batch = prof['batch']
    out_path = args.out or (SCRIPT_DIR / ('verify-matrix-%s.json' % prof_name))

    freeze_ok = verify_freeze_lock()
    cfg = jload(V2 / 'config.json') or {}
    reg_plan = load_reg_plan(batch, prof.get('plan_roots', ()))
    run_dirs = discover_runs(batch)
    rows = [verify_one(rd, prof, reg_plan, freeze_ok, cfg) for rd in run_dirs]
    rows.sort(key=lambda r: (str(r['product']), r['rep'] if r['rep'] is not None else -1, str(r['case'])))
    agg = aggregate(rows, gap0_main=args.gap0_main, gap0_sens=args.gap0_sensitivity)
    matrix = {
        'tool': pathlib.Path(__file__).name,
        'tool_sha256': sha256_file(pathlib.Path(__file__)),
        'generated_at': dt.datetime.now(dt.timezone.utc).astimezone().isoformat(timespec='seconds'),
        'read_only_over_batch': True,
        'profile': prof_name,
        'batch_dir': str(batch.relative_to(REPO)) if batch.is_relative_to(REPO) else str(batch),
        'anchor': {'commit': prof['anchor_commit'], 'time': prof['anchor_time'],
                   'require_commit_field': prof['require_commit_field'],
                   'preregistration_file': str(PREREG.relative_to(REPO)),
                   'preregistration_sha256': sha256_file(PREREG)},
        'scoring_constants': {'source': '3-表现现场/r1030-formal-a1/tools/build_import.py（逐行移植，GUARDS 不计分，分母=全题数）',
                              'totals': TOTALS, 'guards': {k: sorted(v) for k, v in GUARDS.items()}},
        'integrity_constants': {'source': '3-表现现场/r1030-formal-a1/tools/rescan_integrity.py（八类模式移植）', 'patterns': PATTERNS},
        'judgment_criteria': {'gap0_main': args.gap0_main,
                              'gap0_main_basis': 'AMENDMENT-1 主判据：0.74=|444.81−444.07|（产物可复现值；历史 414.07 为笔误）',
                              'gap0_sensitivity': args.gap0_sensitivity,
                              'gap0_sensitivity_basis': '原 PREREGISTRATION 包A 锁定值 30.74，据锚点勘误降为敏感性对照；封印文件 be39fc2 未改写',
                              'amendment_motivation': '历史值勘误，时点先于 judge 对 r1031 的任何聚合分析，与 r1031 结果无关'},
        'freeze_verification': freeze_ok,
        'runs_found': len(rows), 'runs_expected': prof['expect_runs'],
        'runs_count_note': ('run 数与预期一致' if len(rows) == prof['expect_runs'] else '警告：run 数与预期不符（可能批次未完成或布局不同）'),
        'runs': rows,
        'aggregate': agg,
        'summary': {
            'passed': sum(1 for r in rows if r['status'] == 'pass'),
            'failed': sum(1 for r in rows if r['status'] == 'fail'),
            'failed_runs': [r['run_dir'] for r in rows if r['status'] == 'fail'],
            'check_failures': [{'run': r['run_dir'], 'check': k}
                               for r in rows for k, v in r['checks'].items() if v.get('status') == 'fail'],
        },
    }
    if prof_name == 'r1030':
        matrix['selftest_expectations_comparison'] = selftest_compare(rows, agg)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(matrix, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    s = matrix['summary']
    print('freeze pins: %d/%d ok' % (freeze_ok['pins_ok'], freeze_ok['pins_checked']))
    print('runs: %d/%d expected, pass=%d fail=%d' % (len(rows), prof['expect_runs'], s['passed'], s['failed']))
    for f in matrix['summary']['check_failures']:
        print('  FAIL', f['run'], f['check'])
    if 'selftest_expectations_comparison' in matrix:
        cmpj = matrix['selftest_expectations_comparison']
        print('selftest vs claimed-known: all_match=%s' % cmpj['all_match'])
        for n in cmpj['mismatch_notes']:
            print('  MISMATCH', n)
    print('matrix ->', out_path)
    return 0  # 退出码恒 0：已知值比对结论由人判读，不让已知值差异掩盖矩阵本身


if __name__ == '__main__':
    sys.exit(main())
