#!/usr/bin/env python3
"""Codex input-face residual localization (preregistered 2026-11-16).

Localizes the within-group cross-rep residual bytes of the Codex developer/user
message plane (recorded by R3不稳定来源分解) onto JSON key paths, and decides
whether that residual is envelope-metadata drift or message-content drift.
Pure post-hoc algorithmic localization over the same pinned r1109 archive:
no new runs, no network, no model/product calls, no gate or score changes.

Frozen contract (README.md, SHA-pinned below):
- Scope: 5 groups x r1-r3 (15 slots), role in {user, developer} message payloads.
- Hard equality: per group/role/slot canonical payload byte totals must equal
  the R3 result.json message_by_role values (max/min slots via groups[], the
  remaining slot via slots[].message_by_role_bytes); any drift exits 2.
- Alignment: same-role messages aligned by in-stream index k; group/role pairs
  with differing slot counts are registered as count_mismatch; only the common
  aligned prefix is compared and tails are never matched or guessed.
- Classification: all diff offsets on envelope-metadata keys -> metadata_drift;
  any diff offset on a content key -> content_drift. The implementer pinned the
  content-key candidate list after reading the actual payload key surface and
  merged it with prereg section 2; any ambiguous key falls to the content side
  (conservative), per the frozen instruction.
- Content-free discipline: only counts, stream indexes, byte offsets/lengths,
  key paths (structure), byte totals and SHA256 identities are recorded. No
  payload values, no text fragments, no content-derived digests.

stdout is byte-identical under python3 and python3 -O (no asserts are used;
all guards are explicit require() checks that raise Invalid -> exit 2).
"""

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

HERE = '4-打分细则/Codex输入面残差定位-2026-11-16'
R3_PACKAGE = '4-打分细则/R3不稳定来源分解-2026-11-16'
PREREG_SHA256 = '4773ef6eea26af4bd057cceea03dadb608ae2a2bb0e2f879c490ee415fe05088'
CASES = ('bird-ca-schools-15', 'dabstep-payments-10', 'exercism-py-6',
         'lcb-recent-hard-4', 'tb-cargo-plan')
REPS = (1, 2, 3)
ROLES_COMPARED = ('user', 'developer')
PAIR_INDEXES = ((0, 1), (0, 2), (1, 2))
# Three target residuals pinned by the prereg motivation (the R3 max-min record):
TARGET_RESIDUALS = (('lcb-recent-hard-4', 'developer'),
                    ('dabstep-payments-10', 'user'),
                    ('exercism-py-6', 'user'))
R3_SCHEMA = 'r3-decomp-projection-v1'
RESULT_SCHEMA = 'codex-input-residual-localization-v1'


def slot_id(case, rep):
    """R3 slot identifier format: codex__<case>__r<N>."""
    return 'codex__%s__r%d' % (case, rep)

# --- Frozen classification constants (pinned after reading the actual payload
# --- key surface of all 15 slots; merged with prereg section 2). ---------------
# Content-key candidate list (keys that carry message text). Observed surface:
# message payload top-level keys = {content, id, internal_chat_message_metadata_
# passthrough, role, type}; nested keys = content[].{text, type} and internal_
# chat_message_metadata_passthrough.{content_item_kinds, create_time, turn_id}.
CONTENT_KEYS = ('arguments', 'content', 'text')
# Envelope keys the prereg names explicitly (id, call_id, timestamp-class,
# name) plus the observed top-level structural envelope keys role/type.
METADATA_TOP_LEVEL_KEYS = ('call_id', 'id', 'name', 'role', 'type')
# Operationalization of the frozen "时间戳类" (timestamp-class) names; applied
# to top-level keys only (nested timestamps do not qualify; see classify_path).
TIMESTAMP_KEY_RE = re.compile(
    r'(?:_at$|_time$|_times$|_ts$|_date$|timestamp|^time|^date|^ts$|^created|^updated)')
# Conservative tie-break (frozen): any ambiguous key falls to the content side.
# A path qualifies as metadata ONLY if it is a single top-level segment whose
# key is a pinned envelope key or a timestamp-class name. Paths touching any
# content key, paths nested deeper than the payload top level (e.g.
# internal_chat_message_metadata_passthrough.create_time), and any key outside
# the pinned sets are ambiguous under the frozen letter -> content side.
OBSERVED_TOP_LEVEL_KEYS = ('content', 'id', 'internal_chat_message_metadata_passthrough',
                           'role', 'type')
OBSERVED_NESTED_KEYS = ('content[].text', 'content[].type',
                        'internal_chat_message_metadata_passthrough.content_item_kinds',
                        'internal_chat_message_metadata_passthrough.create_time',
                        'internal_chat_message_metadata_passthrough.turn_id')

BRANCH_METADATA_ONLY = 'B-METADATA-ONLY'
BRANCH_CONTENT_DRIFT = 'B-CONTENT-DRIFT'
BRANCH_COUNT_MISMATCH = 'B-COUNT-MISMATCH'

CONTENT_FREE_STATEMENT = ('内容无关纪律：本包只记录槽内条数、流内序位、canonical 字节合计、逐差异字节偏移与长度、'
                          'JSON 键路径（键名与数组下标为结构量）、trace 文件 SHA256 与提交号；'
                          '不记录任何 payload 值、文本片段或内容派生摘要。')

CONSERVATIVE_NOTE = ('分类保守口径（冻结）：预注册 §2 元数据判据字面为「键路径仅触及 payload 顶层非内容键」。'
                     '实测 payload 存在嵌套封装层 internal_chat_message_metadata_passthrough，'
                     '其嵌套键（create_time/turn_id）不在顶层判据与钉定封装键清单内，属歧义键，'
                     '按冻结规则归内容侧。content[].text 等承载文本键在全部 15 槽逐字节稳定，'
                     '零差异触及；本保守分类不改变任何分数，只登记证据。')


class Invalid(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise Invalid(message)


def sha_hex(data):
    return hashlib.sha256(data).hexdigest()


def digest_hex(value):
    require(isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value or '') is not None,
            'invalid SHA256 identity: not 64 lowercase hex chars')
    return value


def canon(value):
    """Canonical payload bytes; identical formula to the v1.1/R3 pipeline."""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'),
                      allow_nan=False).encode('utf-8')


def resolve_head(root):
    """Current HEAD commit, resolved from .git files only (no subprocess)."""
    git = root / '.git'
    if git.is_file():
        text = git.read_text(encoding='utf-8').strip()
        require(text.startswith('gitdir:'), 'unsupported .git indirection')
        git = Path(text.split(':', 1)[1].strip())
        if not git.is_absolute():
            git = (root / git).resolve()
    require(git.is_dir(), 'missing .git directory under --root')
    head = (git / 'HEAD').read_text(encoding='utf-8').strip()
    value = None
    if head.startswith('ref: '):
        ref = head[5:].strip()
        direct = git / ref
        if direct.is_file():
            value = direct.read_text(encoding='utf-8').strip()
        else:
            packed = git / 'packed-refs'
            if packed.is_file():
                for line in packed.read_text(encoding='utf-8').splitlines():
                    if line.endswith(' ' + ref):
                        value = line.split(' ', 1)[0].strip()
                        break
    else:
        value = head
    require(isinstance(value, str) and re.fullmatch('[0-9a-f]{40}', value or '') is not None,
            'cannot resolve current HEAD commit from .git')
    return value


# --- Canonical layout: map every canonical byte of one payload to a key path --

def scalar_bytes(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False).encode('utf-8')


def canonical_layout(value, path=(), start=0, spans=None):
    """Walk a payload exactly as canon() serializes it.

    Returns (end_offset, entries); entries is a list of (start, end, path)
    covering EVERY canonical byte: leaf value bytes, key-name bytes, and
    container punctuation (attributed to its own path or enclosing container).
    spans accumulates path -> (value_start, value_end): for objects/arrays the
    brace-to-brace subtree span, for leaves the exact scalar bytes (key name
    and colon bytes are excluded from the node span).
    """
    if spans is None:
        spans = {}
    entries = []
    if isinstance(value, dict):
        node_start = start
        entries.append((start, start + 1, path))
        end = start + 1
        items = sorted(value.items())
        for index, (key, child) in enumerate(items):
            require(isinstance(key, str), 'non-string object key in payload')
            key_bytes = json.dumps(key, ensure_ascii=False).encode('utf-8')
            entries.append((end, end + len(key_bytes), path + (key,)))
            end += len(key_bytes)
            entries.append((end, end + 1, path + (key,)))
            end += 1
            end, child_entries = canonical_layout(child, path + (key,), end, spans)
            entries.extend(child_entries)
            if index < len(items) - 1:
                entries.append((end, end + 1, path))
                end += 1
        entries.append((end, end + 1, path))
        end += 1
        spans[path] = (node_start, end)
    elif isinstance(value, list):
        node_start = start
        entries.append((start, start + 1, path))
        end = start + 1
        for index, child in enumerate(value):
            end, child_entries = canonical_layout(child, path + ('[%d]' % index,), end, spans)
            entries.extend(child_entries)
            if index < len(value) - 1:
                entries.append((end, end + 1, path))
                end += 1
        entries.append((end, end + 1, path))
        end += 1
        spans[path] = (node_start, end)
    else:
        require(value is None or isinstance(value, (str, int, float, bool)),
                'unsupported payload leaf type: %s' % type(value).__name__)
        raw = scalar_bytes(value)
        entries.append((start, start + len(raw), path))
        end = start + len(raw)
        spans[path] = (start, end)
    return end, entries


def layout_spans(payload):
    """Canonical bytes plus path -> value-node (start, end) map, self-checked."""
    raw = canon(payload)
    spans = {}
    end, entries = canonical_layout(payload, spans=spans)
    require(end == len(raw), 'canonical layout length mismatch against canon bytes')
    covered = bytearray(len(raw))
    for start, stop, path in entries:
        require(0 <= start <= stop <= len(raw), 'layout span out of range')
        for position in range(start, stop):
            covered[position] = 1
    require(all(covered), 'canonical layout does not cover every byte')
    for path, (node_start, node_stop) in spans.items():
        require(0 <= node_start <= node_stop <= len(raw),
                'node span out of range for path %s' % path_string(path))
    return raw, spans


def path_string(segments):
    out = 'payload'
    for segment in segments:
        if segment.startswith('['):
            out += segment
        else:
            out += '.' + segment
    return out


# --- Frozen classification -----------------------------------------------------

def classify_path(segments):
    """Frozen merged rule. Returns (side, reason); side is 'metadata'|'content'."""
    for segment in segments:
        if segment.startswith('['):
            continue
        if segment in CONTENT_KEYS:
            return 'content', 'path touches a pinned content key: ' + segment
    if len(segments) == 1:
        key = segments[0]
        if key in METADATA_TOP_LEVEL_KEYS:
            return 'metadata', 'top-level pinned envelope key: ' + key
        if TIMESTAMP_KEY_RE.search(key):
            return 'metadata', 'top-level timestamp-class key: ' + key
    return 'content', ('ambiguous under the frozen letter (nested or unknown key); '
                       'conservative content side')


# --- Structural diff (value-level, immune to byte-offset shift artifacts) ------

def structural_diff(left, right, path=(), out=None):
    if out is None:
        out = []
    if isinstance(left, dict) and isinstance(right, dict):
        for key in sorted(set(left) | set(right)):
            if key not in left or key not in right:
                out.append((path + (key,), 'key_set'))
            else:
                structural_diff(left[key], right[key], path + (key,), out)
    elif isinstance(left, list) and isinstance(right, list):
        if len(left) != len(right):
            out.append((path, 'list_length'))
        for index in range(min(len(left), len(right))):
            structural_diff(left[index], right[index], path + ('[%d]' % index,), out)
    elif type(left) is not type(right) and not (
            isinstance(left, (int, float)) and isinstance(right, (int, float))):
        out.append((path, 'type'))
    else:
        require(left is None or isinstance(left, (str, int, float, bool)),
                'unsupported payload node type: %s' % type(left).__name__)
        if left != right:
            out.append((path, 'value'))
    return out


def offset_record(spans_map, path, slots):
    """Per-slot byte offset/length of the node at path; None where absent."""
    record = {}
    for slot in slots:
        span = spans_map[slot].get(path)
        record[slot] = None if span is None else {'offset': span[0], 'length': span[1] - span[0]}
    return record


def compare_role_across_slots(payloads_per_slot, slot_names):
    """One group/role record: counts, alignment, per-k diff entries, classification.

    payloads_per_slot: three lists (parallel to slot_names) of message payloads
    in stream order. Content-free output: counts, indexes, byte offsets and
    lengths, key paths only. Count-mismatch pairs keep only the common aligned
    prefix in the comparison; tails are registered, never matched.
    """
    require(len(payloads_per_slot) == len(slot_names) == 3, 'comparison expects three slots')
    counts = {slot_names[i]: len(payloads_per_slot[i]) for i in range(3)}
    count_mismatch = len(set(counts.values())) != 1
    aligned = min(counts.values())
    layouts = {}
    for i, slot in enumerate(slot_names):
        layouts[slot] = [layout_spans(payloads_per_slot[i][k]) for k in range(aligned)]
    identical_ks = []
    differing_ks = []
    diffs = []
    paths_metadata = {}
    paths_content = {}
    for k in range(aligned):
        pair_entries = []
        for i, j in PAIR_INDEXES:
            slot_a, slot_b = slot_names[i], slot_names[j]
            left = payloads_per_slot[i][k]
            right = payloads_per_slot[j][k]
            entries = structural_diff(left, right)
            require((canon(left) == canon(right)) == (not entries),
                    'canonical-byte equality disagrees with structural diff at k=%d' % k)
            if not entries:
                continue
            spans_map = {slot_a: layouts[slot_a][k][1], slot_b: layouts[slot_b][k][1]}
            translated = []
            for path, kind in entries:
                side, reason = classify_path(tuple(path))
                translated.append({
                    'path': path_string(path),
                    'segments': list(path),
                    'kind': kind,
                    'side': side,
                    'side_reason': reason,
                    'byte_offsets': offset_record(spans_map, path, (slot_a, slot_b)),
                })
                bucket = paths_metadata if side == 'metadata' else paths_content
                bucket.setdefault(path_string(path), reason)
            pair_entries.append({
                'slots': [slot_a, slot_b],
                'byte_lengths': {slot_a: len(layouts[slot_a][k][0]),
                                 slot_b: len(layouts[slot_b][k][0])},
                'entries': translated,
            })
        if pair_entries:
            differing_ks.append(k)
            diffs.append({'k': k, 'slot_pairs': pair_entries})
        else:
            identical_ks.append(k)
    if not differing_ks:
        classification = 'identical'
    elif not paths_content:
        classification = 'metadata_drift'
    else:
        classification = 'content_drift'
    record = {
        'slot_names': list(slot_names),
        'counts': counts,
        'count_mismatch': count_mismatch,
        'aligned_ks': aligned,
        'identical_ks': identical_ks,
        'differing_ks': differing_ks,
        'excluded_tails': {},
        'paths_metadata': paths_metadata,
        'paths_content': paths_content,
        'classification': classification,
        'diffs': diffs,
    }
    if count_mismatch:
        for i, slot in enumerate(slot_names):
            total = counts[slot]
            if total > aligned:
                record['excluded_tails'][slot] = {
                    'registered_range': [aligned, total - 1],
                    'registered_count': total - aligned,
                }
    return record


def select_branch(target_statuses, content_anywhere):
    """Frozen branch order (pinned): see README section 3 and the package notes.

    target_statuses: for each of the three target residuals, one of
    'localized_metadata', 'localized_content', 'blocked'.
    """
    localized = [s for s in target_statuses if s != 'blocked']
    blocked_count = len(target_statuses) - len(localized)
    if len(localized) == 3 and all(s == 'localized_metadata' for s in localized) \
            and not content_anywhere:
        return BRANCH_METADATA_ONLY
    if blocked_count == len(target_statuses):
        return BRANCH_COUNT_MISMATCH
    if content_anywhere or 'localized_content' in localized:
        return BRANCH_CONTENT_DRIFT
    return BRANCH_COUNT_MISMATCH


def load_json_bytes(path, what):
    require(path.is_file(), 'missing %s: %s' % (what, path.as_posix()))
    raw = path.read_bytes()
    try:
        return json.loads(raw.decode('utf-8')), raw
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise Invalid('unreadable %s (%s): %s' % (what, path.as_posix(), exc)) from None


def load_rollout(archive_root, binding):
    """SHA-checked rollout reader; returns {role: [payload,...]} in stream order."""
    relative = binding['archive_relative_path']
    require(isinstance(relative, str) and not relative.startswith('/'),
            'trace binding path must be archive-relative')
    path = archive_root / relative
    require(path.is_file(), 'missing trace file: %s' % relative)
    raw = path.read_bytes()
    actual = sha_hex(raw)
    require(actual == digest_hex(binding['sha256']),
            'trace SHA mismatch for %s: binding=%s actual=%s' % (relative, binding['sha256'], actual))
    messages = {role: [] for role in ROLES_COMPARED}
    for line_no, line in enumerate(raw.decode('utf-8').splitlines(), start=1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            raise Invalid('malformed jsonl line %d in %s: %s' % (line_no, relative, exc)) from None
        require(isinstance(event, dict), 'non-object jsonl line %d in %s' % (line_no, relative))
        if event.get('type') != 'response_item':
            continue
        payload = event.get('payload')
        require(isinstance(payload, dict), 'response_item without payload object at line %d in %s'
                % (line_no, relative))
        if payload.get('type') != 'message':
            continue
        role = payload.get('role')
        if role in messages:
            messages[role].append(payload)
    return messages


def load_r3_reference(root):
    result, _raw = load_json_bytes(root / R3_PACKAGE / 'result.json', 'R3 result.json')
    require(isinstance(result, dict), 'R3 result.json must be an object')
    require(result.get('schema') == R3_SCHEMA, 'unexpected R3 schema: %r' % (result.get('schema'),))
    digest_hex(result.get('prereg_sha256'))
    slots = result.get('slots')
    require(isinstance(slots, list) and len(slots) == len(CASES) * len(REPS),
            'R3 slots[] must list 15 slot records')
    slot_bytes = {}
    bindings = {}
    for entry in slots:
        require(isinstance(entry, dict), 'R3 slot entry must be an object')
        slot = entry.get('slot')
        require(isinstance(slot, str), 'R3 slot entry missing slot id')
        require(slot not in slot_bytes, 'duplicate slot id in R3 slots[]: %s' % slot)
        by_role = entry.get('message_by_role_bytes')
        require(isinstance(by_role, dict), 'slot %s missing message_by_role_bytes' % slot)
        slot_bytes[slot] = by_role
    for entry in result.get('trace_bindings', []):
        require(isinstance(entry, dict), 'trace binding entry must be an object')
        slot = entry.get('slot')
        for field in ('archive_relative_path', 'sha256', 'file'):
            require(isinstance(entry.get(field), str) and entry[field],
                    'trace binding for %s missing %s' % (slot, field))
        digest_hex(entry['sha256'])
        require(slot not in bindings, 'duplicate trace binding for %s' % slot)
        bindings[slot] = entry
    require(set(bindings) == set(slot_bytes) == set(slot_id(c, r) for c in CASES for r in REPS),
            'R3 bindings/slots must cover exactly the 15 preregistered slots')
    groups_raw = result.get('groups')
    require(isinstance(groups_raw, list) and len(groups_raw) == len(CASES),
            'R3 groups[] must list 5 group records')
    groups = {}
    for entry in groups_raw:
        require(isinstance(entry, dict), 'R3 group entry must be an object')
        name = entry.get('group')
        require(name in CASES, 'unexpected R3 group: %r' % (name,))
        require(name not in groups, 'duplicate R3 group: %s' % name)
        require(entry.get('arm') == 'codex', 'R3 group %s arm must be codex' % name)
        max_slot, min_slot = entry.get('max_slot'), entry.get('min_slot')
        require(max_slot in slot_bytes and min_slot in slot_bytes,
                'R3 group %s max/min slot not in slots[]' % name)
        by_max = entry.get('message_by_role_max_slot')
        by_min = entry.get('message_by_role_min_slot')
        require(isinstance(by_max, dict) and isinstance(by_min, dict),
                'R3 group %s missing message_by_role_max_slot/min_slot' % name)
        groups[name] = {'max_slot': max_slot, 'min_slot': min_slot,
                        'by_max': by_max, 'by_min': by_min}
    require(set(groups) == set(CASES), 'R3 groups[] must cover exactly the 5 preregistered groups')
    return {'result': result, 'slot_bytes': slot_bytes, 'bindings': bindings, 'groups': groups}


def hard_equality(reference, observed_sums, slot_names_by_group):
    """Tie observed canonical sums to the R3 record; any drift is fatal (exit 2)."""
    checks = []
    all_ok = True
    for case in CASES:
        group = reference['groups'][case]
        for slot in slot_names_by_group[case]:
            for role in ROLES_COMPARED:
                observed = observed_sums[slot][role]
                per_slot = reference['slot_bytes'][slot].get(role)
                checks.append({'group': case, 'role': role, 'slot': slot,
                               'reference_source': 'slots[].message_by_role_bytes',
                               'observed_bytes': observed, 'reference_bytes': per_slot,
                               'ok': per_slot == observed})
                all_ok = all_ok and per_slot == observed
        for which in ('max_slot', 'min_slot'):
            slot = group[which]
            by_role = group['by_max'] if which == 'max_slot' else group['by_min']
            for role in ROLES_COMPARED:
                observed = observed_sums[slot][role]
                expected = by_role.get(role)
                checks.append({'group': case, 'role': role, 'slot': slot,
                               'reference_source': 'groups[].message_by_role_%s' % which,
                               'observed_bytes': observed, 'reference_bytes': expected,
                               'ok': expected == observed})
                all_ok = all_ok and expected == observed
    require(all_ok, 'hard equality failed: observed canonical sums drifted from the R3 record')
    return {'passed': True, 'checks_total': len(checks), 'checks': checks}


def analyze(root, archive_root):
    """Full package analysis; content-free result dict."""
    root = Path(root)
    archive_root = Path(archive_root)
    require(archive_root.is_dir(), '--archive-root must be an existing directory')
    require((archive_root / 'codex' / 'runs').is_dir(),
            'archive root lacks codex/runs layout')
    readme = root / HERE / 'README.md'
    require(readme.is_file(), 'missing prereg README.md under package directory')
    readme_raw = readme.read_bytes()
    actual_prereg = sha_hex(readme_raw)
    require(actual_prereg == PREREG_SHA256,
            'prereg README SHA mismatch: pinned=%s actual=%s' % (PREREG_SHA256, actual_prereg))
    baseline = resolve_head(root)
    reference = load_r3_reference(root)

    slot_names_by_group = {case: [slot_id(case, rep) for rep in REPS] for case in CASES}
    payloads = {}
    observed_sums = {}
    trace_records = []
    for case in CASES:
        for slot in slot_names_by_group[case]:
            binding = reference['bindings'][slot]
            messages = load_rollout(archive_root, binding)
            observed_sums[slot] = {role: sum(len(canon(m)) for m in messages[role])
                                   for role in ROLES_COMPARED}
            payloads[slot] = messages
            trace_records.append({'slot': slot,
                                  'file': binding['file'],
                                  'archive_relative_path': binding['archive_relative_path'],
                                  'sha256_verified': binding['sha256']})

    hard = hard_equality(reference, observed_sums, slot_names_by_group)

    groups = {}
    content_anywhere = False
    for case in CASES:
        records = {}
        for role in ROLES_COMPARED:
            trio = [payloads[slot][role] for slot in slot_names_by_group[case]]
            record = compare_role_across_slots(trio, slot_names_by_group[case])
            records[role] = record
            if record['classification'] == 'content_drift':
                content_anywhere = True
        groups[case] = records

    targets = []
    target_statuses = []
    for case, role in TARGET_RESIDUALS:
        record = groups[case][role]
        sums = {slot: observed_sums[slot][role] for slot in slot_names_by_group[case]}
        deltas = {}
        slot_list = slot_names_by_group[case]
        for i, j in PAIR_INDEXES:
            deltas['%s|%s' % (slot_list[i], slot_list[j])] = sums[slot_list[j]] - sums[slot_list[i]]
        blocked = record['count_mismatch']
        status = 'blocked' if blocked else (
            'localized_metadata' if record['classification'] == 'metadata_drift'
            else 'localized_content' if record['classification'] == 'content_drift'
            else 'blocked')
        target_statuses.append(status)
        anchors = []
        for diff in record['diffs']:
            for pair in diff['slot_pairs']:
                slot_a, slot_b = pair['slots']
                if pair['byte_lengths'][slot_a] != pair['byte_lengths'][slot_b]:
                    for entry in pair['entries']:
                        offsets = entry['byte_offsets']
                        len_a = (offsets[slot_a] or {}).get('length')
                        len_b = (offsets[slot_b] or {}).get('length')
                        if len_a is not None and len_b is not None and len_a != len_b:
                            anchors.append({'k': diff['k'], 'slots': [slot_a, slot_b],
                                            'path': entry['path'], 'side': entry['side'],
                                            'byte_lengths': {slot_a: len_a, slot_b: len_b}})
        targets.append({
            'group': case, 'role': role,
            'status': status,
            'count_mismatch': blocked,
            'slot_byte_totals': sums,
            'slot_pair_deltas': deltas,
            'classification': record['classification'],
            'aligned_ks': record['aligned_ks'],
            'differing_ks': record['differing_ks'],
            'paths_metadata': sorted(record['paths_metadata']),
            'paths_content': sorted(record['paths_content']),
            'path_side_reasons': dict(sorted(
                list(record['paths_metadata'].items()) + list(record['paths_content'].items()))),
            'sum_delta_anchor_entries': anchors,
        })

    branch = select_branch(target_statuses, content_anywhere)
    classification_counts = {}
    for case in CASES:
        for role in ROLES_COMPARED:
            value = groups[case][role]['classification']
            classification_counts[value] = classification_counts.get(value, 0) + 1

    return {
        'schema': RESULT_SCHEMA,
        'preregistration': {
            'package': HERE,
            'readme_file': 'README.md',
            'sha256': PREREG_SHA256,
            'sha256_verified': True,
        },
        'baseline_commit': baseline,
        'inputs': {
            'archive_root_marker': 'launch-r1109',
            'r3_reference_package': R3_PACKAGE,
            'r3_schema': R3_SCHEMA,
            'r3_prereg_sha256': reference['result'].get('prereg_sha256'),
            'groups': list(CASES),
            'reps': list(REPS),
            'roles_compared': list(ROLES_COMPARED),
            'target_residuals': [list(t) for t in TARGET_RESIDUALS],
        },
        'content_keys_pinned': {
            'content_keys': list(CONTENT_KEYS),
            'metadata_top_level_keys': list(METADATA_TOP_LEVEL_KEYS),
            'timestamp_key_rule': 'top-level keys matching TIMESTAMP_KEY_RE (timestamp-class)',
            'observed_top_level_keys': list(OBSERVED_TOP_LEVEL_KEYS),
            'observed_nested_keys': list(OBSERVED_NESTED_KEYS),
            'rule': ('content side = any path touching a pinned content key at any depth, '
                     'plus every ambiguous key (nested or unknown) per the frozen '
                     'conservative tie-break; metadata side = single top-level segment '
                     'whose key is a pinned envelope key or timestamp-class name'),
        },
        'hard_equality': hard,
        'trace_bindings_verified': trace_records,
        'groups': groups,
        'target_residuals': targets,
        'classification_counts': classification_counts,
        'content_anywhere': content_anywhere,
        'branch': branch,
        'content_free_statement': CONTENT_FREE_STATEMENT,
        'notes': [
            CONSERVATIVE_NOTE,
            ('登记说明：R3 的 max/min 槽位级合计只暴露三处目标残差；本包按预注册 §2 对全部三槽逐 k 比较，'
             '因此同时登记了成对合计相等的组内字节级漂移（例如 tb user r2 槽合计 4026，'
             '而 R3 记录的 max/min 两槽同为 4027）。这是同一冻结档案的事后定位登记，不是新批次。'),
            ('对齐说明：实测 15 槽 message 条数全部为 developer=1、user=2，无 count_mismatch；'
             '该分支仍按冻结口径实现并由合成测试覆盖。'),
        ],
    }


def rep_label(slot):
    """Short 'rN' label for summaries; full slot ids stay in result.json."""
    return 'r' + slot.rsplit('__r', 1)[-1]


def render_summary(result):
    lines = []
    lines.append('Codex 输入面残差定位（预注册 %s）' % result['preregistration']['sha256'][:12])
    lines.append('baseline_commit=%s schema=%s' % (result['baseline_commit'], result['schema']))
    lines.append('硬等校验：%d/%d 通过（15 槽 × user/developer canonical 字节合计 vs R3 记录）'
                 % (result['hard_equality']['checks_total'], result['hard_equality']['checks_total']))
    lines.append('trace：15 个 rollout SHA256 全部与 R3 trace_bindings 一致')
    for case in CASES:
        for role in ROLES_COMPARED:
            record = result['groups'][case][role]
            counts = ','.join('%s=%d' % (rep_label(slot), record['counts'][slot])
                              for slot in record['slot_names'])
            head = '%s %s: 条数[%s] ' % (case, role, counts)
            if record['count_mismatch']:
                head += 'count_mismatch 已登记，尾部不定位; '
            head += 'identical k=%s' % (record['identical_ks'] if record['identical_ks'] else '[]')
            if record['differing_ks']:
                head += ' differing k=%s -> %s' % (record['differing_ks'], record['classification'])
            lines.append(head)
            for path in sorted(set(record['paths_metadata']) | set(record['paths_content'])):
                side = 'metadata' if path in record['paths_metadata'] else 'content'
                lines.append('    %s %s' % (path, side))
    lines.append('目标残差：')
    for target in result['target_residuals']:
        deltas = ','.join('%s:%s=%+d' % (rep_label(pair.split('|')[0]), rep_label(pair.split('|')[1]), delta)
                          for pair, delta in sorted(target['slot_pair_deltas'].items()))
        lines.append('  %s %s: status=%s classification=%s deltas(%s)'
                     % (target['group'], target['role'], target['status'],
                        target['classification'], deltas))
        for path in target['paths_metadata']:
            lines.append('    %s metadata' % path)
        for path in target['paths_content']:
            lines.append('    %s content(保守)' % path)
    lines.append('全局分支：%s' % result['branch'])
    lines.append('分类计数：%s' % json.dumps(result['classification_counts'], sort_keys=True))
    lines.append(result['content_free_statement'])
    return '\n'.join(lines) + '\n'


def dump_result(result):
    return (json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + '\n').encode('utf-8')


def main(argv=None):
    parser = argparse.ArgumentParser(
        description='Codex input-face residual localization (preregistered; content-free)')
    parser.add_argument('--root', default='.', help='public repo root (default: cwd)')
    parser.add_argument('--archive-root', required=True,
                        help='private archive root (launch-r1109), read-only')
    parser.add_argument('--output', default=None,
                        help='write full result.json here; refuses to overwrite (exclusive create)')
    args = parser.parse_args(argv)
    try:
        result = analyze(args.root, args.archive_root)
        summary = render_summary(result)
        if args.output is not None:
            out_path = Path(args.output)
            if out_path.exists():
                sys.stderr.write('--output refuses to overwrite existing file: %s\n'
                                 % out_path.as_posix())
                return 2
            payload = dump_result(result)
            with open(out_path, 'xb') as handle:
                handle.write(payload)
        sys.stdout.write(summary)
        return 0
    except Invalid as exc:
        sys.stderr.write('FAIL-CLOSED (exit 2): %s\n' % exc)
        return 2


if __name__ == '__main__':
    sys.exit(main())
