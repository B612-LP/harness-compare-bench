"""Offline admission accounting. No product, fixture, collector or old program is run."""
import hashlib
import json
import re
from collections import Counter
from dataclasses import dataclass
from decimal import Decimal
from itertools import combinations
from pathlib import Path

BASELINE = '89e1cf2468b81dd3dad1c00f56f5cd4a7552df10'
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
REPORT = '5-评测报告/'
SOURCES = {
    'rule': ('反馈/2026-11-18-第五轮/验收条款-公开版.md',
             '59cf16d75b35396e12350017f7865b373c2fa2f1b36524514037cbf82a4c9b57'),
    'nov19_design': (REPORT + '产品同对象同窗读取配对-2026-11-19/README.md',
                     '3bd0a7567ba4fab535939db46ccf23af83a1f80ddf830ce210a2e0ef3cd11cf7'),
    'nov19_note': (REPORT + '读取窗口包络复核-2026-11-23/README.md',
                   '472a9af17db3f9f6916ce539a72edd0f2b02b3b0aae53b0f0b299239c6bdd2c0'),
    'nov19': (REPORT + '读取窗口包络复核-2026-11-23/evidence.json',
              '9607349e74a80b3d0c583cfe06f879e1b5463ac38e11b38d9bd34e0e12db919f'),
    'cli_note': (REPORT + '检出率三元组台账-2026-11-20/README.md',
                 '6ff79584661bf25d96771d1fdf853ba58746f3f524d93c0e6082914906ff1a77'),
    'desktop_note': (REPORT + '桌面读取窗与对象键-2026-11-23/README.md',
                     'c0b61e1e19221a771a3b5048ce8d84ead3e8ba03402ae8a8e659536fc1eb427e'),
    'fixture_note': (REPORT + '同对象同窗读取检测校准-2026-11-19/README.md',
                     'd2aeeeb5d465330fb912d2060708803d885e44e5f07e5aa4728c548bf4e3c5af'),
    'fixture': (REPORT + '同对象同窗读取检测校准-2026-11-19/evidence.json',
                '83a8e036c468d2636d183c2dbb316e523d4faa4b2810cf0e3c229ae112a10d4c'),
    'margins': (REPORT + HERE.name + '/archive-axes.json',
                'b8999463135e1157d79285e8bacdde909661ae8483897de363526fb28e99b58d'),
}
AXES = ('C', 'W', 'O', 'T')
PASSED, REFUTED, UNKNOWN = 'pass', 'refuted', 'unknown'
MODES = ('archive_key_relaxed_replacement', 'action_binding_replacement', 'historical_evidence_only')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_inputs():
    inputs = {}
    for name, (path, digest) in SOURCES.items():
        data = (ROOT / path).read_bytes()
        require(hashlib.sha256(data).hexdigest() == digest, f'input SHA-256 mismatch: {path}')
        if path.endswith('.json'):
            inputs[name] = json.loads(data)
    return inputs


@dataclass(frozen=True)
class ProductBlock:
    """A count-weighted combination of facts; not a list of inferred row IDs."""
    n: int
    complete: bool
    available_outer: str
    full_outer: str
    object_relation: str

    def axes(self, archive_proxy=False):
        return dict(C=PASSED if self.complete else REFUTED,
                    W=REFUTED if self.full_outer == 'disjoint' else UNKNOWN,
                    O=(REFUTED if self.object_relation in ('different_key', 'different_assignment') else
                       PASSED if archive_proxy and self.object_relation == 'same_key' else UNKNOWN),
                    T=UNKNOWN)  # Neither earlier detector hits nor earlier truth labels certify the paired actions.


def historical_nine(data):
    runs = data['runs']
    used, blocks, direction = set(), [], 0
    require(len(data['pairs']) == 9, 'unexpected 11-19 cohort size')
    for row in data['pairs']:
        positive, negative = row['positive_arm'], row['negative_arm']
        product = row['product']
        for role, arm in [('pos', positive), ('neg', negative)]:
            if role == 'neg' and arm is None:
                continue
            require(isinstance(arm, str) and arm.startswith(f'{product}-{role}/')
                    and arm in runs and arm not in used, 'missing, misbound or repeated registered arm')
            used.add(arm)
        raw_gap = row['conservative_gap_seconds']
        if negative is None:
            require(raw_gap is None and row['window'] == 'unfired', 'unfired arm has a claimed complete window')
            blocks.append(ProductBlock(1, False, UNKNOWN, UNKNOWN, UNKNOWN))
            continue
        gap = Decimal(raw_gap)
        require(gap.is_finite() and gap > 0 and row['window'] == 'disjoint', 'expected a finite positive gap')
        p, n = runs[positive]['fd_hits'], runs[negative]['fd_hits']
        require(all(type(c) is int and c >= 0 for c in [p['a'], p['b'], n['a'], n['b']]), 'invalid FD hit count')
        direction += p['a'] > 0 and p['b'] == 0 and n['b'] > 0 and n['a'] == 0
        # Challenge targets a and b differ, without implying per-arm key coverage as in the later groups.
        blocks.append(ProductBlock(1, True, 'disjoint', 'disjoint', 'different_assignment'))
    require(used == runs.keys() and len(used) == 17, '11-19 archive arms differ from nominal membership')
    return blocks, direction


def archive_margins(data):
    require(data['format'] == 'read-pair-archive-margins-v1', 'unsupported margin data')
    out = {}
    for cohort, sizes in [('cli-11-20', {'Codex CLI': 5, 'DSH': 5}),
                          ('desktop-11-20', {'WorkBuddy': 10, '豆包工作': 5})]:
        out[cohort] = {}
        require(data[cohort].keys() == sizes.keys(), 'unexpected stratum')
        for stratum, size in sizes.items():
            row = data[cohort][stratum]
            keys = row['archive_keys']
            available, full = row['available_wall'], row['full_wall']
            require(type(row['complete']) is int and row['complete'] == size
                    and keys.keys() <= {'same', 'different', UNKNOWN}
                    and all(type(n) is int and n > 0 for n in keys.values()) and sum(keys.values()) == size,
                    'unexpected or inconsistent margin totals')
            require(available == 'disjoint' and full in ('disjoint', 'unanchored'),
                    'cannot form joint blocks from non-uniform time margins')
            relations = {'same': 'same_key', 'different': 'different_key', UNKNOWN: UNKNOWN}
            out[cohort][stratum] = [ProductBlock(n, True, available, full, relations[key]) for key, n in keys.items()]
    return out


def scenario(blocks, replaced, mode):
    count = 0
    for b in blocks:
        axes = b.axes(archive_proxy=(mode == MODES[0]))
        if all(state == PASSED or (a in replaced and (mode != MODES[2] or state != REFUTED))
               for a, state in axes.items()):
            count += b.n
    return count


def summarize(blocks):
    def counts_by(field):
        counts = Counter()
        for b in blocks:
            counts[getattr(b, field)] += b.n
        return dict(counts)

    return {
        'registered': sum(b.n for b in blocks),
        'complete': sum(b.n for b in blocks if b.complete),
        'available_outer': counts_by('available_outer'),
        'full_outer': counts_by('full_outer'),
        'object_evidence': counts_by('object_relation'),
        'certified_independent_content_pairs': sum(b.n for b in blocks if b.axes()['T'] == PASSED),
        'admitted': scenario(blocks, (), MODES[2]),
        'upper_ceiling_by_perfected_axes': {
            mode: {'+'.join(axes): scenario(blocks, axes, mode)
                   for n in (1, 2) for axes in combinations(AXES, n)}
            for mode in MODES
        },
    }


@dataclass(frozen=True)
class Anchor:
    scope: str
    pair: str
    positive_arm: str
    negative_arm: str
    target: str
    window: str


@dataclass(frozen=True)
class Fact:
    anchor: Anchor
    axis: str
    state: str


def joint_axes(anchor, facts):
    """Evaluate an exact pair/arms/target/window binding; other anchors cannot fill gaps."""
    states = {axis: set() for axis in AXES}
    for fact in facts:
        if fact.anchor == anchor:
            require(fact.axis in AXES and fact.state in (PASSED, REFUTED, UNKNOWN), 'invalid admission fact')
            states[fact.axis].add(fact.state)
    return {axis: REFUTED if REFUTED in seen else PASSED if PASSED in seen else UNKNOWN
            for axis, seen in states.items()}


def admitted(axes):
    return all(axes.get(axis) == PASSED for axis in AXES)


@dataclass(frozen=True)
class ObjectKey:
    scope: str
    token: object


def same_object(positive, negative, target):
    keys = [key for key in (positive, negative, target) if key is not None]
    if any(a.scope == b.scope and a.token != b.token for a, b in combinations(keys, 2)):
        return REFUTED
    if len(keys) < 3 or len({key.scope for key in keys}) != 1:
        return UNKNOWN
    return PASSED  # Tokens must come from object/lifetime evidence, never a lexical path.


def interval_relation(a, b):
    require(all(type(t) is int for t in (*a, *b)) and a[0] <= a[1] and b[0] <= b[1], 'invalid interval')
    lo, hi = max(a[0], b[0]), min(a[1], b[1])
    return 'disjoint' if lo > hi else 'touch_only' if lo == hi else 'positive_overlap'


def fixture_window(row, p, n, common_clock):
    """Check worker timing and the whole collector lifetime, not just a broad intersection."""
    if common_clock is not True:
        return UNKNOWN, ['unanchored_clock']
    action, sample_at, hold, slop = (row[k] for k in ('planned_action_ns', 'planned_sample_ns',
                                                     'planned_hold_ns', 'phase_tolerance_ns'))
    require(all(type(v) is int for v in (action, sample_at, hold, slop)) and 0 <= slop
            and 0 < action < sample_at < hold, 'invalid fixture timing plan')
    names = ('open_start_ns', 'open_end_ns', 'pre_fstat_ns', 'action_start_ns', 'action_end_ns',
             'post_fstat_ns', 'close_start_ns', 'close_end_ns')
    times = [tuple(arm.get(k) for k in names) for arm in (p, n)]
    if any(type(t) is not int for arm in times for t in arm):
        return UNKNOWN, ['missing_worker_times']
    reasons = []
    for ob, oe, pre, ab, ae, post, cb, ce in times:
        if not (0 <= ob <= oe <= pre <= ab <= ae <= post <= hold <= cb <= ce):
            reasons.append('worker_event_order')
        if not (ob <= slop and action <= ab <= ae <= action + slop and cb <= hold + slop):
            reasons.append('worker_phase')
    if max(x[2] for x in times) > min(x[3] for x in times):
        reasons.append('not_both_open_before_action')
    lo, hi = max(0, *(x[5] for x in times)), min(hold, *(x[6] for x in times))
    if lo >= hi:
        reasons.append('no_positive_common_hold')
    s = row['sample']
    begin, end = s.get('start_ns'), s.get('end_ns')
    span_known = s.get('attempted') is True and type(begin) is int and type(end) is int
    if span_known:
        if not sample_at <= begin <= sample_at + slop:
            reasons.append('sample_phase')
        if not lo <= begin < end <= hi:
            reasons.append('whole_capture_not_contained')
    usable = type(s.get('exit')) is int and s['exit'] == 0 and s.get('stderr_empty') is True and s.get('stdout_empty') is False
    state = REFUTED if reasons else PASSED if span_known and usable else UNKNOWN
    if not span_known:
        reasons.append('missing_capture_span')
    if not usable:
        reasons.append('capture_unusable')
    return state, list(dict.fromkeys(reasons))


def fixture_pair(row, target, common_clock):
    arms = row['arms']
    require(len(arms) == 2 and [a['role'] for a in arms] == ['read', 'open_only'], 'unexpected control arms')
    p, n = arms
    alias = target['alias']
    anchor = Anchor('non-product', row['pair'], 'read', 'open_only', alias, 'registered_phase_at_this_pair_T')
    # The pinned projection attests fstat before/after each action against this target. No raw keys are re-created.
    target_key = ObjectKey(row['pair'], alias) if target['regular'] is True else None
    identity = same_object(*(target_key if a['opened_on_target'] is True and row['target_alias'] == alias else None
                             for a in arms), target_key)
    nbytes, digest = target['bytes'], target['sha256']
    pos = (p['action'] == 'os.read' and type(nbytes) is int and nbytes > 0
           and type(p['bytes']) is int and type(p['final_offset']) is int and p['bytes'] == p['final_offset'] == nbytes
           and isinstance(digest, str) and re.fullmatch(r'[0-9a-f]{64}', digest) and p['sha256'] == digest)
    # The independently instrumented open-only branch (no read/mapping) is the premise; zero offset alone is not.
    neg = (n['action'] == 'no_content_read_marker' and n['bytes'] is None and n['sha256'] is None
           and type(n['final_offset']) is int and n['final_offset'] == 0)
    contents = (PASSED if pos and neg and all(type(a['initial_offset']) is int and a['initial_offset'] == 0 for a in arms)
                else UNKNOWN)
    window, reasons = fixture_window(row, p, n, common_clock)
    states = dict(C=PASSED, W=window, O=identity, T=contents)
    axes = joint_axes(anchor, (Fact(anchor, axis, state) for axis, state in states.items()))
    qualifies = admitted(axes)
    flags = row['sample']['exact_FD_target_matches_read_then_open_only']
    same_visibility = (qualifies and isinstance(flags, list) and len(flags) == 2 and all(f is True for f in flags))
    return {'axes': axes, 'window_notes': reasons, 'admitted': qualifies,
            'observation': 'same_fd_visibility' if same_visibility else UNKNOWN}


def replay_control(data):
    require(data['scope'] == 'one_non_product_regular_fixture' and data['product_runs'] == 0,
            'not the non-product controller projection')
    clock = data['clock'] == 'CLOCK_MONOTONIC' and data['time_unit'] == 'nanoseconds_from_each_pair_T'
    require([row['pair'] for row in data['pairs']] == ['long', 'short'], 'unexpected control labels')
    return {row['pair']: fixture_pair(row, data['target'], clock) for row in data['pairs']}


def run():
    source = read_inputs()
    nov19, direction = historical_nine(source['nov19'])
    older_arms = archive_margins(source['margins'])
    cohorts = {'product-11-19': nov19}
    for cohort, strata in older_arms.items():
        cohorts[cohort] = [b for blocks in strata.values() for b in blocks]
    groups = {cohort: summarize(blocks) for cohort, blocks in cohorts.items()}
    for cohort, strata in older_arms.items():
        groups[cohort]['strata'] = {stratum: summarize(blocks) for stratum, blocks in strata.items()}
    return {
        'baseline': BASELINE,
        'denominator': 'registered nominal pairs; not independent runs or samples',
        'product_groups': groups,
        'product_inventory_sum': summarize([b for blocks in cohorts.values() for b in blocks]),
        'older_11_19_direction_control_only': {'count': direction, 'complete_denominator': groups['product-11-19']['complete']},
        'non_product_control': replay_control(source['fixture']),
    }


if __name__ == '__main__':
    print(json.dumps(run(), ensure_ascii=False, indent=2, sort_keys=True))
