#!/usr/bin/env python3
"""Codex input-face metadata VALUE semantics (preregistered 2026-11-16).

Ring-7 (Codex输入面残差定位) localized all 135 input-face byte diffs of the 15
Codex slots onto exactly three key paths: payload.id,
payload.internal_chat_message_metadata_passthrough.create_time and
...turn_id, with content[].text byte-identical across reps.  This package
reads the VALUES behind those three key paths and decides whether they behave
as per-session build metadata (timestamp / sequence / random id):

- V1: all 45 create_time values parse under one registered time format
      (epoch seconds / epoch millis / ISO -- as actually observed);
- V2: per rep, |create_time - rollout first-event timestamp| <= 120 s
      (per-slot deltas registered; units aligned and the unit decision
      evidence is registered);
- V3: per slot, the turn_id relation over its developer+user messages
      (equal / increasing / all-distinct) plus cross-slot consistency and
      the cross-rep disjointness side-note;
- V4: per (case, role, k) the payload.id all-distinct rate over the three
      reps (expectation: 100%);
- V5: on the stable-slot pairs registered by ring-7 (equal canonical byte
      lengths in result.json diffs[].slot_pairs[]), the three key values stay
      pairwise distinct per rep -- a registrational assertion that drift
      detection works on value differences, not on key paths; it never
      breaks the branch.

Hard equality (both fatal, exit 2):
- key-path hard equality: the freshly re-extracted per-unit diff path sets
  must equal the sets ring-7 registered in its result.json;
- content[].text zero-difference re-verification across reps (values are
  never extracted, published or summarized -- only byte equality).

Branch (frozen README section 3):
- B-METADATA-CONFIRMED: V1 and V2 (>=14/15 slots) and V4 == 100%;
- B-MIXED: only some of the three hold (per-key verdict registered);
- B-REFUTED: none hold; hard-equality failure exits 2 instead (fail-closed).

Release boundary: payload.id / turn_id / create_time raw values, time deltas,
turn_id patterns and id-distinctness booleans are metadata-face and
publishable; content[].text values and message bodies are never read into the
result, never published; the private archive root is referenced only by its
marker name.

stdout is byte-identical under python3 and python3 -O (no asserts are used;
all guards are explicit require() checks that raise Invalid -> exit 2).
"""

import argparse
import datetime
import hashlib
import json
import math
from pathlib import Path
import re
import sys

HERE = '4-打分细则/Codex元数据值语义-2026-11-16'
UPSTREAM_PACKAGE = '4-打分细则/Codex输入面残差定位-2026-11-16'
UPSTREAM_RESULT_REL = UPSTREAM_PACKAGE + '/result.json'
PREREG_SHA256 = '824bfc0e4bb48a8fcb3377900e3783beb72b2f6108fab4cad61e9bfe2b5cd9db'
UPSTREAM_SCHEMA = 'codex-input-residual-localization-v1'
RESULT_SCHEMA = 'codex-meta-sem-v1'

CASES = ('bird-ca-schools-15', 'dabstep-payments-10', 'exercism-py-6',
         'lcb-recent-hard-4', 'tb-cargo-plan')
REPS = (1, 2, 3)
ROLES = ('developer', 'user')
ARCHIVE_MARKER = 'launch-r1109'

V2_BOUND_SECONDS = 120.0
V2_MIN_SLOTS = 14  # frozen: >=14/15 slots

# The three key paths pinned by ring-7 (hard-equality reference).
PATH_ID = 'payload.id'
PATH_CREATE_TIME = 'payload.internal_chat_message_metadata_passthrough.create_time'
PATH_TURN_ID = 'payload.internal_chat_message_metadata_passthrough.turn_id'
EXPECTED_PATHS = frozenset((PATH_ID, PATH_CREATE_TIME, PATH_TURN_ID))

BRANCH_CONFIRMED = 'B-METADATA-CONFIRMED'
BRANCH_MIXED = 'B-MIXED'
BRANCH_REFUTED = 'B-REFUTED'

RELEASE_BOUNDARY_STATEMENT = (
    '发布边界（冻结）：payload.id / internal_chat_message_metadata_passthrough.'
    'create_time / .turn_id 的原值、与 rollout 首事件的时间差、turn_id 模式、'
    'payload.id 全异布尔为元数据面，可发布；content[].text 与消息正文零提取、'
    '零发布、零摘要；私有档案根仅以 launch-r1109 标记指代，不出现真实路径。')

EVIDENCE_GRADE = (
    '证据等级声明（冻结 README 事后性条款）：三键值语义假设由环 7 键路径定位自然引出'
    '（路径名即语义提示，declared_in_prereg=true）；但「create_time 是否≈该 rep rollout '
    '起始时刻（有界差）」「turn_id 是否跨 rep 重排」「payload.id 是否同槽三 rep 全异」'
    '为本包首次检验（first_value_test=true），非验证期已见答案的确认。本包为事后值面登记'
    '（post-hoc value-plane registration over the frozen r1109 archive），0 新运行、'
    '0 新模型调用；值相关不构成因果（构建时刻与记录时刻先后不判）；n=15 槽。')

NOTE_UNIT_ALIGNMENT = (
    '单位对齐说明：create_time 以 JSON 数值承载，按量级判定单位（|v|≥1e11 判毫秒并除以 '
    '1000，否则判秒）；rollout 首事件 timestamp 为 ISO8601 UTC 字符串，解析为 epoch 秒后'
    '与 create_time 对齐比较。两处单位判定依据均逐值登记于 value_matrix。')


class Invalid(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise Invalid(message)


def sha_hex(data):
    return hashlib.sha256(data).hexdigest()


def digest_hex(value):
    require(isinstance(value, str)
            and re.fullmatch('[0-9a-f]{64}', value or '') is not None,
            'invalid SHA256 identity: not 64 lowercase hex chars')
    return value


def canon(value):
    """Canonical JSON bytes of a value (equality oracle; content-free use)."""
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


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
    require(isinstance(value, str)
            and re.fullmatch('[0-9a-f]{40}', value or '') is not None,
            'cannot resolve current HEAD commit from .git')
    return value


def slot_id(case, rep):
    return 'codex__%s__r%d' % (case, rep)


# --- time parsing (V1/V2) -----------------------------------------------------

_ISO_RE = re.compile(
    r'^(\d{4})-(\d{2})-(\d{2})[Tt ](\d{2}):(\d{2}):(\d{2})'
    r'(?:\.(\d{1,9}))?(?:[Zz]|([+-])(\d{2}):?(\d{2}))$')


def epoch_seconds_from_numeric(value):
    """Classify a JSON numeric timestamp into epoch seconds by magnitude.

    Registered unit decision evidence: |v| >= 1e11 -> milliseconds (divided
    by 1000); 1e8 <= |v| < 1e11 -> seconds; else unparseable for our window.
    """
    require(isinstance(value, (int, float)) and not isinstance(value, bool),
             'timestamp is not a JSON number')
    v = float(value)
    require(math.isfinite(v), 'timestamp is not finite')
    if abs(v) >= 1e11:
        return v / 1000.0, 'epoch_milliseconds'
    if abs(v) >= 1e8:
        return v, 'epoch_seconds'
    raise Invalid('numeric timestamp out of registered magnitude windows: %r' % (value,))


def epoch_seconds_from_iso(text):
    match = _ISO_RE.fullmatch(text)
    require(match is not None,
            'timestamp string is not a registered ISO8601 UTC form: %r' % (text,))
    year, month, day, hour, minute, second = (int(match.group(i)) for i in range(1, 7))
    frac = match.group(7) or '0'
    micros = int((frac + '000000')[:6])
    dt = datetime.datetime(year, month, day, hour, minute, second, micros,
                           tzinfo=datetime.timezone.utc)
    value = dt.timestamp()
    if match.group(8):
        offset = int(match.group(9)) * 3600 + int(match.group(10)) * 60
        if match.group(8) == '+':
            value -= offset
        else:
            value += offset
    return value, 'iso8601_utc'


def parse_any_timestamp(value):
    """Parse a create_time / event timestamp into (epoch_seconds, unit label)."""
    if isinstance(value, str):
        return epoch_seconds_from_iso(value)
    return epoch_seconds_from_numeric(value)


def parse_create_time(value):
    """V1 parser for the create_time values; returns (epoch, unit) or raises."""
    return parse_any_timestamp(value)


# --- rollout reading ----------------------------------------------------------

def load_rollout(archive_root, binding):
    """SHA-checked rollout reader.

    Returns (messages_by_role_in_stream_order, first_event_timestamp_raw).
    The first-event timestamp is the top-level `timestamp` of the first
    non-blank jsonl line (ordinal 0 event).  Message bodies/text are NOT
    retained beyond what the value matrix needs (id / create_time / turn_id).
    """
    relative = binding['archive_relative_path']
    require(isinstance(relative, str) and relative and not relative.startswith('/'),
            'trace binding path must be archive-relative')
    path = archive_root / relative
    require(path.is_file(), 'missing trace file: %s' % relative)
    raw = path.read_bytes()
    actual = sha_hex(raw)
    pinned = digest_hex(binding['sha256_verified'])
    require(actual == pinned,
            'trace SHA mismatch for %s: binding=%s actual=%s'
            % (relative, pinned, actual))
    messages = {role: [] for role in ROLES}
    first_ts = None
    for line_no, line in enumerate(raw.decode('utf-8').splitlines(), start=1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            raise Invalid('malformed jsonl line %d in %s: %s' % (line_no, relative, exc)) from None
        require(isinstance(event, dict), 'non-object jsonl line %d in %s' % (line_no, relative))
        if first_ts is None:
            require('timestamp' in event,
                    'first jsonl event lacks top-level timestamp in %s' % relative)
            first_ts = event['timestamp']
        if event.get('type') != 'response_item':
            continue
        payload = event.get('payload')
        require(isinstance(payload, dict),
                'response_item without payload object at line %d in %s' % (line_no, relative))
        if payload.get('type') != 'message':
            continue
        role = payload.get('role')
        if role in messages:
            messages[role].append(payload)
    require(first_ts is not None, 'rollout has no events: %s' % relative)
    return messages, first_ts


# --- structural diff path extraction (value-plane, path names only) ----------

def diff_paths(left, right, base):
    """Leaf value-difference paths between two payloads under base.

    Path naming follows ring-7: dotted segments, arrays contribute a bare []
    segment (no index).  Array length mismatches are fail-closed (the frozen
    archive has none; a synthetic mutation of shape must not be silently
    compared element-wise).
    """
    out = set()
    if type(left) is not type(right):
        out.add(base)
        return out
    if isinstance(left, dict):
        for key in sorted(set(left) | set(right)):
            if key not in left or key not in right:
                out.add('%s.%s' % (base, key) if base else key)
            else:
                out |= diff_paths(left[key], right[key],
                                  '%s.%s' % (base, key) if base else key)
        return out
    if isinstance(left, list):
        require(len(left) == len(right),
                'array length mismatch at %s (fail-closed)' % (base or '<payload>'))
        for index, (a, b) in enumerate(zip(left, right)):
            out |= diff_paths(a, b, '%s[]' % base)
        return out
    if canon(left) != canon(right):
        out.add(base)
    return out


def payload_path_prefix(base):
    return 'payload.' + base if base else 'payload'


def unit_diff_path_set(trio, role, k, slot_names):
    """Union of value-diff paths for one (case, role, k) over the three slot pairs."""
    paths = set()
    for i, j in ((0, 1), (0, 2), (1, 2)):
        paths |= diff_paths(trio[i][role][k], trio[j][role][k], 'payload')
    return paths


def extract_texts(payload):
    """Canonical bytes of every content[].text item (equality oracle only).

    The bytes themselves never leave this function's return value scope:
    callers only compare them for equality and register booleans.
    """
    out = []
    content = payload.get('content')
    require(isinstance(content, list), 'payload.content must be a list')
    for item in content:
        require(isinstance(item, dict), 'content item must be an object')
        if 'text' in item:
            out.append(canon(item['text']))
    return out


# --- upstream (ring-7) result loading ----------------------------------------

def load_upstream(root):
    path = root / UPSTREAM_RESULT_REL
    require(path.is_file(), 'missing upstream ring-7 result.json: %s' % UPSTREAM_RESULT_REL)
    raw = path.read_bytes()
    try:
        result = json.loads(raw.decode('utf-8'))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise Invalid('unreadable upstream result.json: %s' % exc) from None
    require(isinstance(result, dict), 'upstream result.json must be an object')
    require(result.get('schema') == UPSTREAM_SCHEMA,
            'unexpected upstream schema: %r' % (result.get('schema'),))
    bindings = result.get('trace_bindings_verified')
    require(isinstance(bindings, list) and len(bindings) == len(CASES) * len(REPS),
            'upstream trace_bindings_verified must list 15 slot records')
    expected_slots = set(slot_id(c, r) for c in CASES for r in REPS)
    seen = set()
    for entry in bindings:
        require(isinstance(entry, dict), 'trace binding entry must be an object')
        slot = entry.get('slot')
        require(slot in expected_slots, 'unexpected trace binding slot: %r' % (slot,))
        require(slot not in seen, 'duplicate trace binding for %s' % slot)
        seen.add(slot)
        for field in ('archive_relative_path', 'sha256_verified', 'file'):
            require(isinstance(entry.get(field), str) and entry[field],
                    'trace binding for %s missing %s' % (slot, field))
        digest_hex(entry['sha256_verified'])
    require(seen == expected_slots,
            'upstream trace bindings must cover exactly the 15 preregistered slots')
    groups = result.get('groups')
    require(isinstance(groups, dict) and set(groups) == set(CASES),
            'upstream groups must cover exactly the 5 preregistered cases')
    for case in CASES:
        unit = groups[case]
        require(isinstance(unit, dict) and set(unit) >= set(ROLES),
                'upstream group %s missing role records' % case)
        for role in ROLES:
            record = unit[role]
            require(isinstance(record, dict), 'upstream role record must be an object')
            for field in ('paths_metadata', 'paths_content'):
                value = record.get(field)
                require(isinstance(value, (list, dict)) and bool(value),
                        'upstream %s/%s missing registered path sets (%s)' % (case, role, field))
            registered = set(record['paths_metadata']) | set(record['paths_content'])
            require(all(isinstance(p, str) for p in registered),
                    'upstream %s/%s registered paths must be strings' % (case, role))
    return result


def upstream_stable_pairs(upstream):
    """Stable-slot pairs registered by ring-7: equal canonical byte lengths.

    Read strictly from ring-7 result.json groups[case][role].diffs[]
    slot_pairs[].byte_lengths (the registrational source named by the frozen
    README section 2, V5).  Returns a list of records with the pair slots,
    k, and the unit key path sets ring-7 registered for that pair.
    """
    pairs = []
    for case in CASES:
        for role in ROLES:
            record = upstream['groups'][case][role]
            diffs = record.get('diffs')
            if not isinstance(diffs, list):
                continue
            for diff in diffs:
                require(isinstance(diff, dict) and isinstance(diff.get('k'), int),
                        'upstream diff entry missing integer k')
                slot_pairs = diff.get('slot_pairs')
                require(isinstance(slot_pairs, list),
                        'upstream diff entry missing slot_pairs')
                for pair in slot_pairs:
                    lengths = pair.get('byte_lengths') if isinstance(pair, dict) else None
                    require(isinstance(lengths, dict) and len(lengths) == 2,
                            'upstream slot_pair must carry exactly two byte_lengths')
                    slot_a, slot_b = sorted(lengths)
                    if lengths[slot_a] != lengths[slot_b]:
                        continue
                    entry_paths = set()
                    for entry in pair.get('entries', []) or []:
                        if isinstance(entry, dict) and isinstance(entry.get('path'), str):
                            entry_paths.add(entry['path'])
                    pairs.append({'case': case, 'role': role, 'k': diff['k'],
                                  'slots': [slot_a, slot_b],
                                  'canonical_bytes': lengths[slot_a],
                                  'upstream_entry_paths': sorted(entry_paths)})
    return pairs


# --- classification helpers (V3) ---------------------------------------------

def classify_values(values):
    """Frozen three-way relation: equal / increasing / all-distinct."""
    require(len(values) >= 2, 'classification needs at least two values')
    if all(v == values[0] for v in values):
        return 'equal'
    numeric = []
    for v in values:
        if not isinstance(v, str):
            numeric = None
            break
        try:
            numeric.append(float(v))
        except ValueError:
            numeric = None
            break
    if numeric is not None and all(numeric[i] < numeric[i + 1]
                                   for i in range(len(numeric) - 1)):
        return 'increasing'
    return 'all-distinct'


# --- analysis -----------------------------------------------------------------

def analyze(root, archive_root):
    """Full package analysis; metadata-face value result (no content values)."""
    root = Path(root)
    archive_root = Path(archive_root)
    require(archive_root.is_dir(), '--archive-root must be an existing directory')
    require((archive_root / 'codex' / 'runs').is_dir(),
            'archive root lacks codex/runs layout')
    readme = root / HERE / 'README.md'
    require(readme.is_file(), 'missing prereg README.md under package directory')
    actual_prereg = sha_hex(readme.read_bytes())
    require(actual_prereg == PREREG_SHA256,
            'prereg README SHA mismatch: pinned=%s actual=%s'
            % (PREREG_SHA256, actual_prereg))
    baseline = resolve_head(root)
    upstream = load_upstream(root)

    # ---- read the 15 slots (SHA-checked), keep only the metadata value plane
    slot_names = {case: [slot_id(case, rep) for rep in REPS] for case in CASES}
    payloads = {}
    first_event = {}
    trace_records = []
    for case in CASES:
        for slot in slot_names[case]:
            binding = next(b for b in upstream['trace_bindings_verified']
                           if b['slot'] == slot)
            messages, first_ts = load_rollout(archive_root, binding)
            payloads[slot] = messages
            first_event[slot] = first_ts
            trace_records.append({'slot': slot,
                                  'file': binding['file'],
                                  'archive_relative_path': binding['archive_relative_path'],
                                  'sha256_verified': binding['sha256_verified']})

    # ---- hard equality 1: key-path sets vs ring-7 registration (fatal)
    path_checks = []
    for case in CASES:
        for role in ROLES:
            registered = set(upstream['groups'][case][role]['paths_metadata']) | \
                set(upstream['groups'][case][role]['paths_content'])
            observed = set()
            first_slot = slot_names[case][0]
            counts = [len(payloads[s][role]) for s in slot_names[case]]
            require(len(set(counts)) == 1,
                    'slot message-count mismatch in %s %s: %s' % (case, role, counts))
            for k in range(counts[0]):
                trio = [payloads[s] for s in slot_names[case]]
                observed |= unit_diff_path_set(trio, role, k, slot_names[case])
            path_checks.append({
                'case': case, 'role': role,
                'registered_paths': sorted(registered),
                'observed_paths': sorted(observed),
                'ok': observed == registered,
            })
    paths_ok = all(c['ok'] for c in path_checks)
    require(paths_ok,
            'hard equality failed: per-unit drift path sets diverge from ring-7 '
            'registration (%s)' % '; '.join(
                '%s/%s registered=%s observed=%s' % (c['case'], c['role'],
                                                     c['registered_paths'],
                                                     c['observed_paths'])
                for c in path_checks if not c['ok']))

    # ---- hard equality 2: content[].text zero-difference re-check (fatal)
    text_checks = []
    for case in CASES:
        for role in ROLES:
            counts = len(payloads[slot_names[case][0]][role])
            for k in range(counts):
                per_rep = [extract_texts(payloads[s][role][k]) for s in slot_names[case]]
                equal = per_rep[0] == per_rep[1] == per_rep[2]
                text_checks.append({'case': case, 'role': role, 'k': k,
                                    'text_items': len(per_rep[0]),
                                    'byte_identical_across_reps': equal})
    text_ok = all(c['byte_identical_across_reps'] for c in text_checks)
    require(text_ok,
            'hard equality failed: content[].text is no longer byte-identical '
            'across reps (%s)' % '; '.join(
                '%s/%s k=%d' % (c['case'], c['role'], c['k'])
                for c in text_checks if not c['byte_identical_across_reps']))

    # ---- value matrix (metadata plane only)
    value_matrix = {}
    ct_units = {}
    fe_units = {}
    v2_rows = []
    for case in CASES:
        for rep in REPS:
            slot = slot_id(case, rep)
            base_epoch, base_unit = parse_any_timestamp(first_event[slot])
            fe_units[slot] = base_unit
            slot_entry = {'first_event_timestamp': first_event[slot],
                          'first_event_unit': base_unit,
                          'first_event_epoch_seconds': base_epoch,
                          'messages': {}}
            for role in ROLES:
                rows = []
                for k, payload in enumerate(payloads[slot][role]):
                    meta = payload.get('internal_chat_message_metadata_passthrough')
                    require(meta is None or isinstance(meta, dict),
                            'internal_chat_message_metadata_passthrough must be an object')
                    create_time = meta.get('create_time') if isinstance(meta, dict) else None
                    turn_id = meta.get('turn_id') if isinstance(meta, dict) else None
                    row = {'role': role, 'k': k,
                           'payload_id': payload.get('id'),
                           'create_time': create_time,
                           'turn_id': turn_id}
                    if create_time is None:
                        row['create_time_parse'] = None
                        row['v2_delta_seconds'] = None
                    else:
                        try:
                            epoch, unit = parse_create_time(create_time)
                        except Invalid:
                            # V1 is a value-plane assertion: unparseable values are
                            # registered (V1 fail -> branch), never leaked, and the
                            # affected V2 deltas register as out-of-bound.
                            epoch = unit = None
                        if epoch is None:
                            row['create_time_parse'] = None
                            row['v2_delta_seconds'] = None
                            v2_rows.append({'slot': slot, 'role': role, 'k': k,
                                            'delta_seconds': None,
                                            'within_bound': False,
                                            'unparseable_create_time': True})
                        else:
                            ct_units.setdefault(unit, 0)
                            ct_units[unit] += 1
                            row['create_time_parse'] = {'unit': unit,
                                                        'epoch_seconds': epoch}
                            delta = abs(epoch - base_epoch)
                            row['v2_delta_seconds'] = round(delta, 6)
                            v2_rows.append({'slot': slot, 'role': role, 'k': k,
                                            'delta_seconds': round(delta, 6),
                                            'within_bound': delta <= V2_BOUND_SECONDS})
                    rows.append(row)
                slot_entry['messages'][role] = rows
            value_matrix[slot] = slot_entry

    # ---- V1: all create_time values parse under the registered format(s)
    total_ct = 0
    parseable_ct = 0
    for slot in value_matrix:
        for role in ROLES:
            for row in value_matrix[slot]['messages'][role]:
                if row['role'] not in ROLES:
                    continue
                total_ct += 1
                if row['create_time_parse'] is not None:
                    parseable_ct += 1
    v1 = {'total_values': total_ct,
          'parseable_values': parseable_ct,
          'registered_formats': dict(sorted(ct_units.items())),
          'pass': total_ct == parseable_ct and total_ct > 0}

    # ---- V2: per-slot bounded difference vs rollout first event
    slot_ok = {}
    for case in CASES:
        for rep in REPS:
            slot = slot_id(case, rep)
            rows = [r for r in v2_rows if r['slot'] == slot]
            slot_ok[slot] = bool(rows) and all(r['within_bound'] for r in rows)
    slots_pass = sum(1 for v in slot_ok.values() if v)
    worst = max((r['delta_seconds'] for r in v2_rows
                 if r['delta_seconds'] is not None), default=None)
    v2 = {'slots_total': len(slot_ok),
          'slots_within_bound': slots_pass,
          'min_required': V2_MIN_SLOTS,
          'bound_seconds': V2_BOUND_SECONDS,
          'worst_abs_delta_seconds': worst,
          'create_time_units': dict(sorted(ct_units.items())),
          'first_event_units': dict(sorted(fe_units.items())),
          'pass': slots_pass >= V2_MIN_SLOTS}

    # ---- V3: turn_id relation inside each slot + cross-slot consistency
    v3_slots = {}
    for case in CASES:
        for rep in REPS:
            slot = slot_id(case, rep)
            values = []
            for role in ROLES:
                for row in value_matrix[slot]['messages'][role]:
                    values.append(row['turn_id'])
            require(all(isinstance(v, str) for v in values),
                    'turn_id values must be strings in %s' % slot)
            v3_slots[slot] = classify_values(values)
    patterns = sorted(set(v3_slots.values()))
    across_rep = {}
    for case in CASES:
        sets = []
        for rep in REPS:
            slot = slot_id(case, rep)
            sets.append({row['turn_id']
                         for role in ROLES
                         for row in value_matrix[slot]['messages'][role]})
        disjoint = (len(sets[0] & sets[1]) == 0 and len(sets[0] & sets[2]) == 0
                    and len(sets[1] & sets[2]) == 0)
        across_rep[case] = {
            'per_rep_turn_id_sets_disjoint': disjoint,
            'slot_patterns': [v3_slots[slot_id(case, rep)] for rep in REPS],
        }
    v3 = {'per_slot_pattern': {s: v3_slots[s] for s in sorted(v3_slots)},
          'pattern_multiset': {p: sum(1 for v in v3_slots.values() if v == p)
                               for p in patterns},
          'cross_slot_consistent': len(patterns) == 1,
          'across_rep': across_rep}

    # ---- V4: payload.id all-distinct rate over the three reps
    groups_v4 = {}
    distinct_count = 0
    total_groups = 0
    for case in CASES:
        for role in ROLES:
            counts = len(payloads[slot_id(case, 1)][role])
            for k in range(counts):
                ids = [value_matrix[slot_id(case, rep)]['messages'][role][k]['payload_id']
                       for rep in REPS]
                distinct = len(set(ids)) == len(ids)
                total_groups += 1
                distinct_count += 1 if distinct else 0
                groups_v4['%s/%s/k%d' % (case, role, k)] = distinct
    v4 = {'total_groups': total_groups,
          'all_distinct_groups': distinct_count,
          'rate': (distinct_count / total_groups) if total_groups else 0.0,
          'per_group': dict(sorted(groups_v4.items())),
          'pass': total_groups > 0 and distinct_count == total_groups}

    # ---- V5: ring-7 stable pairs keep the three key values pairwise distinct
    stable_pairs = upstream_stable_pairs(upstream)
    v5_checks = []
    for pair in stable_pairs:
        slot_a, slot_b = pair['slots']
        role = pair['role']
        k = pair['k']
        rows_a = value_matrix[slot_a]['messages'][role]
        rows_b = value_matrix[slot_b]['messages'][role]
        require(k < len(rows_a) and k < len(rows_b),
                'stable pair k out of aligned range: %s' % pair)
        row_a, row_b = rows_a[k], rows_b[k]
        for key, label in (('payload_id', PATH_ID),
                           ('create_time', PATH_CREATE_TIME),
                           ('turn_id', PATH_TURN_ID)):
            v5_checks.append({
                'case': pair['case'], 'role': role, 'k': k,
                'slots': [slot_a, slot_b],
                'canonical_bytes_equal': True,
                'key_path': label,
                'pairwise_distinct': row_a[key] != row_b[key],
            })
    v5_supported = bool(v5_checks) and all(c['pairwise_distinct'] for c in v5_checks)
    v5 = {'stable_pairs': len(stable_pairs),
          'checks': len(v5_checks),
          'pairwise_distinct_checks': sum(1 for c in v5_checks if c['pairwise_distinct']),
          'supported': v5_supported,
          'registrational_only': True,
          'per_pair_keys': ['%s/%s/k%d %s %s' % (c['case'], c['role'], c['k'],
                                                 c['key_path'],
                                                 'distinct' if c['pairwise_distinct']
                                                 else 'EQUAL')
                            for c in v5_checks if not c['pairwise_distinct']]}

    # ---- frozen branch (section 3): V1 and V2(>=14/15) and V4==100%
    if v1['pass'] and v2['pass'] and v4['pass']:
        branch = BRANCH_CONFIRMED
    elif v1['pass'] or v2['pass'] or v4['pass']:
        branch = BRANCH_MIXED
    else:
        branch = BRANCH_REFUTED

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
            'archive_root_marker': ARCHIVE_MARKER,
            'upstream_package': UPSTREAM_PACKAGE,
            'upstream_schema': UPSTREAM_SCHEMA,
            'upstream_branch': upstream.get('branch'),
            'upstream_baseline_commit': upstream.get('baseline_commit'),
            'upstream_prereg_sha256': (upstream.get('preregistration') or {}).get('sha256'),
            'groups': list(CASES),
            'reps': list(REPS),
            'roles_compared': list(ROLES),
            'key_paths_under_test': sorted(EXPECTED_PATHS),
        },
        'hard_equality': {
            'key_paths_vs_ring7': {
                'rule': ('每 (case,role) 单元的重提取值差路径集合必须与环 7 result.json '
                         '登记的 paths_metadata ∪ paths_content 逐单元相等；漂移即 exit2'),
                'checks_total': len(path_checks),
                'checks_ok': sum(1 for c in path_checks if c['ok']),
                'passed': paths_ok,
                'per_unit': path_checks,
            },
            'content_text_zero_diff': {
                'rule': ('content[].text 跨 rep 同位置逐字节零差异复验（环 7 结论的再确认）；'
                         '破即 exit2；text 值零提取零发布，仅登记布尔与条数'),
                'checks_total': len(text_checks),
                'checks_ok': sum(1 for c in text_checks if c['byte_identical_across_reps']),
                'passed': text_ok,
                'per_unit': text_checks,
            },
            'trace_bindings_verified': trace_records,
        },
        'value_matrix': value_matrix,
        'v1': v1,
        'v2': v2,
        'v3': v3,
        'v4': v4,
        'v5': v5,
        'branch': branch,
        'branch_rule': ('冻结 §3：V1 ∧ V2(≥14/15 槽) ∧ V4=100% ⇒ B-METADATA-CONFIRMED；'
                        '部分成立 ⇒ B-MIXED（逐键判定）；否则 ⇒ B-REFUTED；'
                        '硬等失败 ⇒ exit2（不产出分支结论）'),
        'per_key_verdict': {
            PATH_CREATE_TIME: {'v1': v1['pass'], 'v2': v2['pass']},
            PATH_TURN_ID: {'v3_registered': True,
                           'cross_slot_consistent': v3['cross_slot_consistent']},
            PATH_ID: {'v4': v4['pass']},
        },
        'evidence_grade': EVIDENCE_GRADE,
        'release_boundary_statement': RELEASE_BOUNDARY_STATEMENT,
        'notes': [
            NOTE_UNIT_ALIGNMENT,
            ('V5 说明：稳定槽对取自环 7 result.json 的 diffs[].slot_pairs[] 中 '
             'canonical 字节长度相等的槽对（%d 对，含 lcb developer r1|r2、'
             'bird user 全对、tb user k1 全对等）；这些槽对在槽级字节合计投影下不可区分，'
             '但其三键值逐 rep 仍互异 ⇒ 漂移检测以值差为准而非键路径/合计投影；'
             '该断言为登记性，不破分支。' % len(stable_pairs)),
        ],
    }


# --- rendering ----------------------------------------------------------------

def rep_label(slot):
    return 'r' + slot.rsplit('__r', 1)[-1]


def render_summary(result):
    lines = []
    lines.append('Codex 元数据值语义检验（预注册 %s）' % result['preregistration']['sha256'][:12])
    lines.append('baseline_commit=%s schema=%s' % (result['baseline_commit'], result['schema']))
    hard = result['hard_equality']
    lines.append('硬等 1 键路径：%d/%d 单元与环 7 登记一致（%s）'
                 % (hard['key_paths_vs_ring7']['checks_ok'],
                    hard['key_paths_vs_ring7']['checks_total'],
                    'PASS' if hard['key_paths_vs_ring7']['passed'] else 'FAIL'))
    lines.append('硬等 2 content[].text：%d/%d 检查逐字节零差异（%s）'
                 % (hard['content_text_zero_diff']['checks_ok'],
                    hard['content_text_zero_diff']['checks_total'],
                    'PASS' if hard['content_text_zero_diff']['passed'] else 'FAIL'))
    lines.append('trace：15 个 rollout SHA256 全部与环 7 trace_bindings 一致')
    v1, v2, v3, v4, v5 = result['v1'], result['v2'], result['v3'], result['v4'], result['v5']
    fmt = ','.join('%s×%d' % (k, v) for k, v in sorted(v1['registered_formats'].items()))
    lines.append('V1 create_time：%d/%d 可解析（格式：%s）%s'
                 % (v1['parseable_values'], v1['total_values'], fmt,
                    'PASS' if v1['pass'] else 'FAIL'))
    units = ','.join(sorted(v2['create_time_units'])) or 'none'
    worst = ('worst=%.3fs' % v2['worst_abs_delta_seconds']) \
        if v2['worst_abs_delta_seconds'] is not None else 'worst=n/a'
    lines.append('V2 时间差：%d/%d 槽 |Δ|≤%gs（%s；create_time 单位：%s）%s'
                 % (v2['slots_within_bound'], v2['slots_total'], v2['bound_seconds'],
                    worst, units, 'PASS' if v2['pass'] else 'FAIL'))
    lines.append('V3 turn_id：within 模式 %s；跨槽一致=%s；跨 rep 两两不交 case=%d/5'
                 % (json.dumps(v3['pattern_multiset'], sort_keys=True),
                    v3['cross_slot_consistent'],
                    sum(1 for a in v3['across_rep'].values()
                        if a['per_rep_turn_id_sets_disjoint'])))
    lines.append('V4 payload.id：%d/%d 组三 rep 全异（率=%.1f%%）%s'
                 % (v4['all_distinct_groups'], v4['total_groups'],
                    v4['rate'] * 100.0, 'PASS' if v4['pass'] else 'FAIL'))
    lines.append('V5 稳定槽对：%d 对 × 3 键，逐 rep 互异检查 %d/%d（登记性断言，supported=%s）'
                 % (v5['stable_pairs'], v5['pairwise_distinct_checks'], v5['checks'],
                    v5['supported']))
    lines.append('全局分支：%s' % result['branch'])
    lines.append('证据等级：%s' % result['evidence_grade'])
    lines.append(result['release_boundary_statement'])
    return '\n'.join(lines) + '\n'


def dump_result(result):
    return (json.dumps(result, ensure_ascii=False, indent=1, sort_keys=True)
            + '\n').encode('utf-8')


def main(argv=None):
    parser = argparse.ArgumentParser(
        description='Codex input-face metadata value semantics (preregistered; '
                    'metadata-plane values only)')
    parser.add_argument('--root', required=True, help='public repo root')
    parser.add_argument('--archive-root', required=True,
                        help='private archive root (launch-r1109 marker), read-only')
    parser.add_argument('--output', default=None,
                        help='write full result.json here; refuses to overwrite '
                             '(exclusive create)')
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
