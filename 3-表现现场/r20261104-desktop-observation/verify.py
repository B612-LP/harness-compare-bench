#!/usr/bin/env python3
"""Read-only verification of the public derived observation bundle, not private originals."""
import argparse, hashlib, json
from pathlib import Path

def verify(root):
    manifest=json.loads((root/'manifest.json').read_text(encoding='utf-8'))
    assert manifest['representation']=='public_derived_not_original_seal'
    expected=set()
    for item in manifest['files']:
        name=item['path'];parts=Path(name).parts
        assert name and not Path(name).is_absolute() and '..' not in parts
        assert name not in expected and name!='manifest.json';expected.add(name)
        p=root/name
        assert all(not q.is_symlink() for q in (p,*p.parents)),name
        assert p.is_file(),name
        b=p.read_bytes();assert len(b)==item['bytes'],name
        assert hashlib.sha256(b).hexdigest()==item['sha256'],name
    actual={str(p.relative_to(root)) for p in root.rglob('*') if p.is_file()}
    assert actual==expected|{'manifest.json'},'extra or missing files'
    state=json.loads((root/'slots.json').read_text(encoding='utf-8'))
    assert state['formal_admissions']==0 and state['case']=='tb-cargo-plan'
    rows=state['slots'];assert [r['product'] for r in rows]==['workbuddy','doubao_work']
    for row in rows:
        assert row['create_attempts'] in (0,1) and row['submit_invocations'] in (0,1)
        assert row['submit_invocations']<=row['create_attempts']
        assert row['read_ground_truth_available'] is False
        assert row['product_read_false_negative_rate'] is None
        assert row['bait_interpretation'] in ('unknown_not_observed','observed_content_in_specific_tool_chain','observed_propagation_source_ambiguous','not_observed_no_product_task')
        if row['submit_invocations']==0:
            assert row['submission_confirmed'] is False and row['grader_executed'] is False
        if row['native_completed']:
            assert row['submission_confirmed'] is True and row['submit_invocations']==1
        if row['grader_executed']:
            assert row['native_completed'] is True and row['grader_receipt'] in expected
    if rows[1]['create_attempts']:
        assert rows[0]['native_completed'] and rows[0]['evidence_capture_ok']
    assert state['submit_invocations']==sum(r['submit_invocations'] for r in rows)<=2
    assert state['native_completed']==sum(bool(r['native_completed']) for r in rows)
    assert state['grader_executed']==sum(bool(r['grader_executed']) for r in rows)
    source_count=0
    if 'case-source-pins.json' in expected:
        repo=root.parent.parent
        for pin in json.loads((root/'case-source-pins.json').read_text(encoding='utf-8')):
            rel=Path(pin['repo_relative'])
            assert not rel.is_absolute() and '..' not in rel.parts and str(rel).startswith('2-用例/tb-cargo-plan/')
            p=repo/rel;assert all(not q.is_symlink() for q in (p,*p.parents)),str(rel)
            b=p.read_bytes();assert hashlib.sha256(b).hexdigest()==pin['sha256'],str(rel)
            source_count+=1
    return {'ok':True,'scope':'public derived bytes, slot accounting and listed case-source pins only; no raw provenance or complete read audit','case_source_files_verified':source_count,'files':len(expected)+1,'slots':2,'submit_invocations':state['submit_invocations'],'native_completed':state['native_completed'],'grader_executed':state['grader_executed'],'formal_admissions':0,'product_read_false_negative_rate':None}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,default=Path(__file__).resolve().parent);a=ap.parse_args()
    try:result=verify(a.root.resolve())
    except (AssertionError,OSError,ValueError,KeyError,TypeError) as e:
        print(json.dumps({'ok':False,'error':str(e)},ensure_ascii=False));return 1
    print(json.dumps(result,ensure_ascii=False,indent=2));return 0
if __name__=='__main__':raise SystemExit(main())
