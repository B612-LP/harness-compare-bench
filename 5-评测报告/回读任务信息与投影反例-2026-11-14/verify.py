"""Read-only public verifier: synthetic specs + explicitly derived Native material.
Python 3.9 standard library. No product dependency, tool call or network.
"""
import hashlib
import json
import re
from pathlib import Path
import cleanroom as c

ROOT = Path(__file__).resolve().parent

def loads(raw):
    def unique(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('duplicate key')
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=unique,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite')))

def load(path):
    return loads(Path(path).read_text())

def tree(root, files, manifest_name):
    if root.is_symlink():
        raise ValueError('symlink package root')
    actual_files, actual_dirs = set(), set()
    for path in root.rglob('*'):
        name = path.relative_to(root).as_posix()
        if path.is_symlink():
            raise ValueError('extra or listed symlink')
        if path.is_dir():
            actual_dirs.add(name)
        elif path.is_file():
            actual_files.add(name)
        else:
            raise ValueError('nonregular package entry')
    expected = set(files) | {manifest_name}
    directories = {p.as_posix() for name in expected for p in Path(name).parents if p != Path('.')}
    if actual_files != expected or actual_dirs != directories:
        raise ValueError('recursive package inventory mismatch')
    for name, digest in files.items():
        relative = Path(name)
        if relative.is_absolute() or '..' in relative.parts or relative.as_posix() != name or name == manifest_name:
            raise ValueError('unsafe manifest file name')
        if c.sha((root / relative).read_bytes()) != digest:
            raise ValueError('package file hash')
    return len(actual_files)

def error_free(row):
    if row.get('is_error') is not False:
        raise ValueError('explicit nonerror witness required')
    metadata = row.get('native_error_fields')
    if not isinstance(metadata, dict) or set(metadata) - {'is_error','isError','error','errorCode','status','state'}:
        raise ValueError('native error metadata schema')
    if type(row.get('native_is_error_present')) is not bool or row['native_is_error_present'] != ('is_error' in metadata):
        raise ValueError('native error presence witness missing or inconsistent')
    for key, value in metadata.items():
        if key in ('is_error','isError') and value is not False:
            raise ValueError('native error flag')
        if key in ('error','errorCode') and value is not None and value is not False and value != '':
            raise ValueError('native error payload')
        if key in ('status','state') and (type(value) is not str or value not in ('completed','success','succeeded','ok')):
            raise ValueError('native failure state or unsupported status')

def read_metrics(text, source):
    listing = text.split('\n<content>\n',1)[1].rsplit('\n\n',1)[0]
    values = [line.split(': ',1)[1] for line in listing.split('\n')]
    physical = source.split('\n')
    if len(values) != len(physical):
        raise ValueError('metric line count')
    covered, markers = 0, 0
    for value, original in zip(values, physical):
        if value == original:
            visible = original
        elif value == c.prefix(original,2000) + c.MARKER and c.u16(original) > 2000:
            visible = c.prefix(original,2000)
        else:
            raise ValueError('metric source coverage')
        covered += len(visible.encode())
        markers += len(value.encode()) - len(visible.encode())
    lf = max(0,len(values)-1)
    shown = len('\n'.join(values).encode())
    raw = len(text.encode())
    path_line = len(text.splitlines(keepends=True)[0].encode())
    numbering = sum(len(str(i)+': ') for i in range(1,len(values)+1))
    footer = re.search(r'\n\n(\(End of file - total [0-9]+ lines\))\n</content>\Z',text)
    if footer is None:
        raise ValueError('metric EOF structure')
    xml, eof = len('<type>file</type><content></content>'), len(footer[1].encode())
    scaffold = text.count('\n')-lf-1
    if min(covered,markers,scaffold) < 0 or covered+lf+markers+numbering+path_line+xml+eof+scaffold != raw:
        raise ValueError('read byte components do not sum')
    return dict(numbering_bytes=numbering,path_line_bytes=path_line,xml_markup_bytes_excluding_path=xml,
        eof_footer_bytes=eof,scaffold_lf_bytes_excluding_path=scaffold,non_source_increment_bytes=raw-covered-lf,
        source_bytes=len(source.encode()), source_content_excluding_lf_bytes=covered,
        source_lf_separator_bytes=lf, source_covered_bytes=covered+lf,
        synthetic_marker_bytes=markers, displayed_reconstruction_bytes=shown,
        formatted_result_utf8_bytes=raw, wrapper_over_displayed_reconstruction_bytes=raw-shown,
        legacy_wrapper_excluding_join_lf_bytes=raw-(shown-lf))

def native(root):
    data = load(root / 'manifest.json')
    if data.get('schema') != 'safe-native-client-derivative-v2':
        raise ValueError('native schema must be v2')
    counts = dict(local_requests=6,fixtures=3,reads=4,upstream_forwards=0,model_requests=0)
    if data.get('metrics_required') is not True or json.dumps(data.get('actual_counts'),sort_keys=True) != json.dumps(counts,sort_keys=True) or len(data.get('previews',[])) != 3:
        raise ValueError('v2 metrics / counts / previews required')
    expected_end = dict(completed=True,exit_code=0,logs_withheld=False,native_identity_verified=True,
        not_global_runtime_attestation=True,own_process_group_state='absent',signal_zero_observation_only=True,timeout=False)
    if data.get('completed') is not True or json.dumps(data.get('runtime_end_witness'),sort_keys=True) != json.dumps(expected_end,sort_keys=True):
        raise ValueError('completed runtime end witness required')
    tree(root, data['files'], 'manifest.json')
    for name, digest in data['files'].items():
        relative = Path(name)
        if relative.is_absolute() or '..' in relative.parts:
            raise ValueError('unsafe relative name')
        path = root / relative
        if any(p.is_symlink() for p in [path] + list(path.parents) if p != root.parent):
            raise ValueError('symlink derivative')
        if c.sha(path.read_bytes()) != digest:
            raise ValueError('derived file hash')
    def fetched(name):
        if name not in data['files']:
            raise ValueError('uncommitted derivative file')
        return (root / name).read_bytes()
    texts = {}
    for record in data.get('sources', []):
        sid = record['source']
        if sid not in ('S', 'A', 'B') or sid in texts:
            raise ValueError('source ID')
        raw = fetched('sources/' + sid + '.txt')
        text = raw.decode('ascii')
        digest = c.sha(raw)
        if not (digest == record['source_original_sha256'] == record['derived_sha256']
                == record['fixture_payload_sha256'] == record['physical_spill_sha256']):
            raise ValueError('fullfile source binding')
        if record['synthetic_locator'] != '/synthetic/native/' + sid + '.txt':
            raise ValueError('locator mapping')
        texts[sid] = text
    if texts:
        a, b, s = (texts[k] for k in ('A', 'B', 'S'))
        if not (len(a) == len(b) == 16000 and len(s) == 16159 and s == '\n'.join(a[i:i+100] for i in range(0,16000,100))
                and a[:8007] == b[:8007] and a[8071:] == b[8071:] and a[8000:8007] == 'TARGET='
                and re.fullmatch('[0-9a-f]{64}', a[8007:8071]) and re.fullmatch('[0-9a-f]{64}', b[8007:8071])
                and a[8007:8071] != b[8007:8071]):
            raise ValueError('three-source geometry')
    previews = data.get('previews', [])
    if previews and len(previews) != 3:
        raise ValueError('three previews required')
    for i, row in enumerate(previews):
        error_free(row)
        sid = ('S','A','B')[i]
        if row['source'] != sid or row['role'] != 'user' or row['call_id'] != 'rr1114_c' + str(i+1) or row.get('args') != {}:
            raise ValueError('preview role/ID/argument binding')
        text = fetched(row['file']).decode('utf-8')
        if c.sha(text.encode()) != row['derived_sha256']:
            raise ValueError('derived preview hash')
        footer = re.search(r'\n\n\(Omitted ([0-9]+) bytes\. Full formatted result stored at: ' + re.escape('/synthetic/native/' + sid + '.txt. Use read with offset/limit, or grep this path to search within it.)') + r'\Z', text)
        if footer is None or text[:footer.start()].count('\n\n[...]\n\n') != 1:
            raise ValueError('preview structure')
        head, tail = text[:footer.start()].split('\n\n[...]\n\n')
        source = texts[sid]
        if not (head and tail and source.startswith(head) and source.endswith(tail) and int(footer[1]) == len(source.encode()) - len(head.encode()) - len(tail.encode()) > 0):
            raise ValueError('preview full-source prefix/suffix binding')
    rows = data.get('reads', [])
    if len(rows) > 4 or type(data.get('planned_reads')) is not int or data['planned_reads'] != 4 or type(data.get('session_denominator')) is not int or data['session_denominator'] != 1:
        raise ValueError('fixed denominator')
    normalized = []
    for i, row in enumerate(rows):
        error_free(row)
        sid = ('S', 'A', 'B', 'A')[i]
        path = '/synthetic/native/' + sid + '.txt'
        expected_args = {'file_path': path}
        if i == 3:
            expected_args.update(offset=1, limit=1)
        if row['source'] != sid or row['role'] != 'user' or row['call_id'] != 'rr1114_c' + str(i + 4) or row['args'] != expected_args:
            raise ValueError('read role/ID/argument binding')
        if type(row['args'].get('offset', 1)) is not int or type(row['args'].get('limit', 1)) is not int:
            raise ValueError('pagination type')
        body = fetched(row['file']).decode('utf-8')
        if re.search(r'<(?:tool_use_error|tool_error|read_error|error)(?:\s|>)', body, re.I):
            raise ValueError('tool error envelope before body witness')
        source = texts[sid]
        expected = c.project(source, offset=1, limit=1 if i == 3 else 2000, path=path)['rendered']
        uncut = '<path>' + path + '</path>\n<type>file</type>\n<content>\n' + '\n'.join('%d: %s' % (n, value) for n, value in enumerate(source.split('\n'), 1)) + '\n\n(End of file - total %d lines)\n</content>' % len(source.split('\n'))
        if body not in (expected, uncut):
            raise ValueError('safe Native display not source-bound full/prefix form')
        if c.sha(body.encode()) != row['derived_sha256']:
            raise ValueError('derived Read hash')
        if data.get('metrics_required') is True:
            derived = read_metrics(body,source)
            length = row.get('original_locator_utf8_bytes')
            if type(length) is not int or length < 1:
                raise ValueError('original locator byte witness')
            original = dict(derived)
            delta = length-len(path.encode())
            for key in ('formatted_result_utf8_bytes','wrapper_over_displayed_reconstruction_bytes','legacy_wrapper_excluding_join_lf_bytes','path_line_bytes','non_source_increment_bytes'):
                original[key] += delta
            expected_metrics = dict(original=original,derived=derived)
            if json.dumps(row.get('metrics'),sort_keys=True) != json.dumps(expected_metrics,sort_keys=True):
                raise ValueError('source coverage / marker / wrapper decomposition')
            original_fields = dict(source_bytes=len(source.encode()),source_utf16=c.u16(source),
                displayed_source_bytes=original['displayed_reconstruction_bytes'],
                displayed_source_utf16=c.u16('\n'.join(line.split(': ',1)[1] for line in body.split('\n<content>\n',1)[1].rsplit('\n\n',1)[0].split('\n'))),
                raw_result_bytes=original['formatted_result_utf8_bytes'],wrapper_bytes=original['legacy_wrapper_excluding_join_lf_bytes'])
            if json.dumps(row.get('analysis_original_fields'),sort_keys=True) != json.dumps(original_fields,sort_keys=True):
                raise ValueError('legacy field decomposition differs')
            record = next(item for item in data['sources'] if item['source'] == sid)
            if row.get('canonical_header_original_sha256') != record.get('canonical_locator_sha256'):
                raise ValueError('canonical header/source locator commitment')
            if c.sha(body.split('\n',1)[1].encode()) != row.get('normalized_body_sha256'):
                raise ValueError('normalized body commitment')
        normalized.append(body.split('\n', 1)[1])
    complete = data.get('completed') is True
    if complete and (len(rows) != 4 or len(texts) != 3):
        raise ValueError('completed denominator')
    if complete:
        targets = [texts['A'][8007:8071], texts['B'][8007:8071]]
        if targets[0] not in (root / rows[0]['file']).read_text():
            raise ValueError('Native positive control')
        if all((targets[1] if i == 2 else targets[0]) in normalized[i] for i in range(4)):
            branch = 'long_line_loss_not_reproduced'
        elif (normalized[1] == normalized[2] == normalized[3] and
              all(t not in normalized[j] for j in (1,2,3) for t in targets) and
              all(c.MARKER in normalized[j] for j in (1,2,3))):
            branch = 'read_presentation_loses_required_long_line_information_on_this_probe'
        else:
            branch = 'mixed_or_design_not_discriminating'
        if data.get('branch') != branch:
            raise ValueError('Native classification differs')
    return {'completed': complete, 'verified_read_derivatives': len(rows), 'verified_preview_derivatives': len(previews), 'planned_reads': 4,
            'session_denominator': 1, 'original_requests_publicly_replayed': False}

SPEC_JSON = '{\n  "schema": "finite-read-projection-spec-v1",\n  "implementation": "independent Python 3.9 standard library; no vendor code or runtime imports",\n  "synthetic_path": "/synthetic/same-path.txt",\n  "units": {\n    "line_prefix": "UTF16 code units, not Python codepoints or UTF8 bytes",\n    "line_cap": 2000,\n    "prefix_sentinel": 2001,\n    "byte_cap": 51200,\n    "default_offset": 1,\n    "default_limit": 2000,\n    "byte_count": "UTF8 display bytes of selected line text plus one LF between selected lines; excludes numbering/envelope"\n  },\n  "finite_projection": [\n    "Split decoded text at LF; a terminal LF creates no extra empty line.",\n    "For each source line retain at most the first 2001 UTF16 code units.",\n    "Strip a final CR from that retained prefix, not from the unbounded original line.",\n    "If the remaining prefix exceeds 2000 UTF16 units, expose first 2000 plus the declared line marker.",\n    "Select positive integer line offset/limit; reject an offset beyond source lines except an empty source at offset 1.",\n    "If a selected complete displayed line would exceed the byte cap, omit that whole line and all following lines in that window; total line count is still known.",\n    "Number lines and render the complete same-synthetic-path envelope/footer; EOF is a line-count statement."\n  ],\n  "collision_task_predicates": {\n    "crlf": "Is the newline encoding CRLF or LF?",\n    "terminal-lf": "Does the source end with LF?",\n    "terminal-cr": "Does the source end with CR?",\n    "json-decision": "How many decision values equal ALLOW in the full valid JSON?",\n    "astral-unit": "What is the original astral codepoint after the 1999 x prefix?",\n    "cr-unmarked": "Does the original source contain SECRET?"\n  },\n  "unicode_contract": {\n    "source": "The two complete sources are valid UTF8 with different astral codepoints.",\n    "projection": "A 2000-unit cut after 1999 ASCII units leaves unpaired 0xd83d.",\n    "json": "Escaping that unit as \\\\ud83d preserves it after JSON parsing.",\n    "utf8_display": "Encoding the unpaired unit as a display byte string uses U+FFFD; this is a different representation, not proof of actual wire replacement."\n  },\n  "post_execute_condition": {\n    "assumptions": ["accepted result", "no parent delegation", "declared tool-name branch"],\n    "without_own_value": {"read": "unbounded by this post-execute branch", "alias": "bounded by this branch"},\n    "own_property_bypass": ["undefined", "null", "false"],\n    "not_truthiness": true,\n    "not_global_runtime_identity_proof": true\n  },\n  "source_commitments_only": [\n    {"package_path": "@deepseek-ai/dsh-tool-fs/lib/index.js", "version": "0.2.0-rc.2", "sha256": "66742231de99695b98400cdbc7bcf47b8ef2bf24600cf86f66bb35591981427f"},\n    {"package_path": "@deepseek-ai/dsh-spill-policy/lib/index.js", "version": "0.2.0-rc.2", "sha256": "970dc4c00c488f11d96cd25ad3bbdc4d034ed754506b2c0c46563b75102291ac"},\n    {"package_path": "@deepseek-ai/dsh-fs-local/lib/index.js", "version": "0.2.0-rc.2", "sha256": "63fbb41d2c33e07111884b798be507e68c2752acab8249c821c20ade436e894f"}\n  ],\n  "limits": [\n    "Source-conditioned finite examples, not Native execution or model success.",\n    "Read line pagination can recover the byte-cap examples but cannot address columns after a single-line prefix cap.",\n    "No claim that grep, shell, edits, reformatting or every recovery strategy fails.",\n    "No universal token, traffic, cache, cost or model sample inference."\n  ]\n}\n'

def task_answer(name, text):
    if name == 'crlf':
        return 'CRLF' if '\r\n' in text else 'LF'
    if name == 'terminal-lf':
        return text.endswith('\n')
    if name == 'terminal-cr':
        return text.endswith('\r')
    if name == 'json-decision':
        def count(value):
            if isinstance(value, dict):
                return sum((key == 'decision' and item == 'ALLOW') + count(item) for key, item in value.items())
            if isinstance(value, list):
                return sum(count(item) for item in value)
            return 0
        return count(loads(text))
    if name == 'astral-unit':
        c.need(text.startswith('x' * 1999) and len(text) > 1999 and ord(text[1999]) > 0xffff, 'original astral source required')
        return 'U+%X' % ord(text[1999])
    if name == 'cr-unmarked':
        return 'SECRET' in text
    raise ValueError('unsupported task predicate')

def canonical(value):
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(',', ':'))

def static(root):
    c.need(canonical(load(root / 'specs.json')) == canonical(loads(SPEC_JSON)), 'finite spec contract differs')
    saved = load(root / 'proof.json')
    rows = saved.get('collisions')
    c.need(type(rows) is list and len(rows) == 6, 'six stored collisions required')
    for (name, _, _, _, _), row in zip(c.pairs(), rows):
        a, b = [(root / ('static/sources/' + name + '-' + side + '.txt')).read_bytes().decode('utf-8') for side in ('A', 'B')]
        aa, ab = task_answer(name, a), task_answer(name, b)
        c.need(a != b and canonical(aa) != canonical(ab), 'static sources or task answers not distinct:' + name)
        va, vb = c.project(a)['rendered'], c.project(b)['rendered']
        c.need(va == vb, 'static complete projections differ:' + name)
        display = load(root / ('static/displays/' + name + '.json'))
        c.need(type(display) is dict and set(display) == {'same_path_complete_projection'} and display['same_path_complete_projection'] == va, 'stored JSON projection differs:' + name)
        c.need((root / ('static/displays/' + name + '.txt')).read_bytes() == c.display_bytes(va), 'stored UTF8 display differs:' + name)
        actual = dict(id=name, source_A=c.fingerprint(a), source_B=c.fingerprint(b), task_answers=[aa,ab],
            complete_display_equal=True, display_utf8_sha256=c.sha(c.display_bytes(va)),
            display_utf16le_sha256=c.sha(va.encode('utf-16-le','surrogatepass')),
            display_utf8_bytes=len(c.display_bytes(va)),display_utf16_units=c.u16(va),
            marker_present=c.MARKER in va,eof_present='(End of file' in va,
            json_roundtrip_same_units=json.loads(json.dumps(va,ensure_ascii=True)) == va)
        c.need(canonical(row) == canonical(actual), 'stored collision proof differs:' + name)
    calculated = c.proof()
    c.need(canonical(saved) == canonical(calculated), 'stored cleanroom proof')
    return calculated

def main():
    tree_count = tree(ROOT, load(ROOT / 'MANIFEST.json')['files'], 'MANIFEST.json')
    proof = static(ROOT)
    result = {'static': True, 'finite_collisions': len(proof['collisions']), 'recursive_inventory': tree_count,
              'native': native(ROOT / 'native')}
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
