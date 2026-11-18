#!/usr/bin/env python3
"""Read-only consistency check for this single anonymized projection, not original verification."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import re

DIGEST = hashlib.sha256(bytes(range(256)) * 2).hexdigest()
PLAN = dict(open_ns=100_000_000, action_ns=260_000_000, sample_ns=420_000_000, close_ns=900_000_000, tolerance_ns=35_000_000, collector_max_ns=250_000_000, barrier_lead_ns=300_000_000)


class Invalid(ValueError):
    pass


def need(ok, name):
    if not ok:
        raise Invalid(name)


def obj(data, *keys):
    need(type(data) is dict and set(data) == set(keys), 'shape')
    return data


def integers(*xs):
    need(all(type(x) is int for x in xs), 'integer_type')


def pair(x):
    need(type(x) is list and len(x) == 2, 'interval_shape')
    integers(*x)
    need(0 <= x[0] <= x[1], 'interval_order')
    return x


def phase(p, name, *xs):
    lo = p[name+'_ns']
    need(all(lo <= x <= lo+p['tolerance_ns'] for x in xs), 'phase_'+name)


def unique(pairs):
    d = {}
    for k,v in pairs:
        need(k not in d, 'duplicate_json_member')
        d[k]=v
    return d


def no_constant(_):
    raise Invalid('invalid_json_constant')


def parse(data):
    need(type(data) is bytes and len(data) <= 32768, 'json_size')
    return json.loads(data.decode('utf-8'),object_pairs_hook=unique,parse_constant=no_constant)


def verify(e):
    obj(e,'schema','capsule','fixture_size_bytes','positive_request_bytes','plan','observed','source_commitments','decision')
    need(e['schema'] == 'paired-read-offset-derived-v1' and e['capsule'] == 'one_fixed_four_arm_block','schema')
    integers(e['fixture_size_bytes'],e['positive_request_bytes'])
    need((e['fixture_size_bytes'],e['positive_request_bytes']) == (1024,512),'fixture_dimensions')
    p = obj(e['plan'],*PLAN)
    integers(*p.values())
    need(p == PLAN,'fixed_plan')
    commits = obj(e['source_commitments'],'preregistration_sha256','implementation_sha256','start_sha256','receipt_sha256')
    need(all(type(s) is str and re.fullmatch('[0-9a-f]{64}',s) is not None for s in commits.values()),'source_commitment_format')
    x = obj(e['observed'],'arms','confirmed_common_hold_rel_ns','collector_envelope_rel_ns','collector_claims','fixture_claims')
    c = obj(x['collector_claims'],'healthy_exit_and_empty_stderr','same_regular_identity_all_arms','exact_scoped_pid_fd_rows','one_sample_after_all_actions')
    f = obj(x['fixture_claims'],'same_nonroot_euid','independent_fd_per_arm','one_selected_shared_monotonic_barrier','all_owned_children_reaped_fixture_removed')
    need(all(b is True for b in (*c.values(),*f.values())),'binding_or_cleanup_claim_missing')
    arms = obj(x['arms'],*'ABCD')
    holds = []
    actions = []
    feature_truth = []
    for a,op,wants_offset,wants_read in zip('ABCD',('pread','open_only','seek','read'),(0,0,512,512),(True,False,False,True)):
        row = obj(arms[a],'operation','open_rel_ns','action_rel_ns','close_rel_ns','worker_offsets','seek_return','content_reads','returned_content_bytes','content_sha256','collector_offset')
        need(row['operation'] == op,'arm_operation')
        opened, action, close = (pair(row[k]) for k in ('open_rel_ns','action_rel_ns','close_rel_ns'))
        phase(p,'open',*opened); phase(p,'action',*action); phase(p,'close',*close)
        holds.append((opened[1],close[0])); actions.append(action)
        offsets=row['worker_offsets']
        need(type(offsets) is list and len(offsets)==3,'worker_offsets_shape')
        integers(*offsets,row['content_reads'],row['returned_content_bytes'])
        need(offsets==[0,wants_offset,wants_offset],'independent_native_offsets')
        if op=='seek':
            integers(row['seek_return']); need(row['seek_return']==512,'seek_return')
        else:
            need(row['seek_return'] is None,'unexpected_seek')
        truth=(row['content_reads'],row['returned_content_bytes'],row['content_sha256'])
        need(truth == ((1,512,DIGEST) if wants_read else (0,0,None)), 'independent_content_truth')
        native_observed = row['collector_offset']
        need(native_observed is not None,'collector_offset_unknown_not_imputed')
        integers(native_observed)
        need(native_observed == wants_offset,'collector_offset_unconfirmed')
        feature_truth.append((native_observed, truth[0] == 1))
    lo,hi = pair(x['confirmed_common_hold_rel_ns'])
    need(lo == max(o for o,_ in holds) and hi == min(c for _,c in holds),'common_hold_calculation')
    need(all(lo < a <= b < hi for a,b in actions),'action_not_in_common_hold')
    s0,s1 = pair(x['collector_envelope_rel_ns'])
    phase(p,'sample',s0)
    need(lo < s0 and max(b for _,b in actions) < s0 < s1 < hi and s1-s0<=p['collector_max_ns'], 'collector_envelope_not_in_stable_hold')
    seen={}
    for off,witness in feature_truth:
        seen.setdefault(off,set()).add(witness)
    need(seen == {0:{False,True},512:{False,True}} and e['decision']=='offset_not_sufficient','collision_classification')
    return e['decision']


def self_test(e):
    def change(container,key,value):
        container[key] = value
    probes=(
        lambda z: change(z['observed']['arms']['A'],'collector_offset',None),
        lambda z: change(z['observed']['arms']['B'],'collector_offset',False),
        lambda z: change(z['observed']['arms']['C'],'collector_offset',0),
        lambda z: change(z['observed']['arms']['D'],'returned_content_bytes',511),
        lambda z: change(z['observed']['arms']['A'],'content_sha256','0'*64),
        lambda z: change(z['observed']['arms']['C'],'content_reads',1),
        lambda z: change(z['observed']['arms']['A'],'worker_offsets',[0,512,512]),
        lambda z: change(z['observed']['fixture_claims'],'same_nonroot_euid',1),
        lambda z: change(z['observed']['collector_claims'],'same_regular_identity_all_arms',False),
        lambda z: change(z['observed']['collector_envelope_rel_ns'],1,z['observed']['confirmed_common_hold_rel_ns'][1]),
        lambda z: change(z['observed']['confirmed_common_hold_rel_ns'],0,z['observed']['confirmed_common_hold_rel_ns'][0]+1),
        lambda z: change(z['observed']['collector_envelope_rel_ns'],0,419_999_999),
        lambda z: change(z,'unexpected_private_field',1),
    )
    for i,probe in enumerate(probes):
        z=copy.deepcopy(e); probe(z)
        try: verify(z)
        except Invalid: continue
        raise Invalid('self_test_accepted_'+str(i))
    parse_cases=(b'{"arms":{"x":1,"x":2}}', b'{"x":NaN}')
    for b in parse_cases:
        try: parse(b)
        except Invalid: continue
        raise Invalid('self_test_accepted_malformed_json')
    return len(probes)+len(parse_cases)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('evidence',nargs='?',type=Path,default=Path(__file__).with_name('evidence.json'))
    p.add_argument('--self-test',action='store_true')
    a=p.parse_args()
    try:
        with a.evidence.open('rb') as f: e=parse(f.read(32769))
        result=verify(e)
        print('derived projection consistent:',result)
        if a.self_test: print('rejected in-memory near misses:',self_test(e))
        return 0
    except (OSError,ValueError,TypeError,KeyError,RecursionError) as why:
        print('unknown: derived projection not qualified:',why)
        return 1


if __name__=='__main__':
    raise SystemExit(main())
