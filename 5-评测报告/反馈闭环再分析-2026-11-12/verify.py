"""Check frozen derived events and self-owned synthetic tests, NOT private history authenticity."""
from pathlib import Path
from hashlib import sha256
import json
import sys
import unittest
from core import strict_json

ROOT=Path(__file__).resolve().parent
EVENTS_SHA256='80ab6325402305262f890724d9db2a5f57f0b0e2e9e855648c6d102bffbe2f31'


def verify(data):
    checked=[]
    def need(value,label):
        if not value:raise ValueError(label)
        checked.append(label)
    need(data['schema']==1,'schema')
    q=data['Q1'];f=data['cases']['formal'];r=data['cases']['r1_control'];h=data['Q3']
    need(q['complete_owner']=='trusted_runner' and q['complete_is_agent_claim'] is False,'field owner')
    need(q['runner_suite_run_line']==53 and q['runner_complete_literal_line']==55,'runner static positions')
    need(q['runner_sha_matches_frozen_config'] is True,'runner freeze identity')
    need((q['legacy_F5_singleton'],q['supported_agent_false_final_cases_from_this_singleton'],
          q['insufficient_for_original_agent_claim_F5_attribution'])==(1,0,1),'legacy/support/insufficient separation')
    need(q['not_a_global_no_false_claim_assertion'] is True,'not global absence claim')
    need(q['formal_graded_pov']=={'tests':15,'failures':3,'errors':0,'exit_code':1,'complete':True},'grader failures coexist with traversal completion')
    for key,c,n,a,t,sizes in [('formal',f,65,23,42,[1785,1859]),('r1_control',r,78,29,49,[2214,2443,2438])]:
        tr=c['trace']
        need((tr['records'],tr['roles'],tr['tool_calls'])==(n,{'assistant':a,'tool':t},t),key+' complete exported-record counts')
        need(tr['all_calls_matched'] is True,key+' all available call/result pairs')
        need(tr['user_or_system_rows']==0 and tr['per_record_timestamps_present'] is False,key+' prompt/time coverage gap')
        need([v['after']['bytes'] for v in c['versions']]==sizes,key+' full version chain sizes')
        need(c['reconstructed']==c['current'] and c['matches_current_bytes'] is True,key+' current bytes only')
        for i,v in enumerate(c['versions']):
            need(v['call_line']<v['ack_line'],key+' causal call/ack order '+str(i))
            if i:need(v['before']==c['versions'][i-1]['after'] and v['prior_fragment_matches']==1,key+' unique anchored edit '+str(i))
    need([x['failures'] for x in f['pov_retests']]==[10],'formal pre-edit local failure')
    need(f['repair_chains'][0]['edit_ack_line']==65 and f['repair_chains'][0]['next_pov_result_line'] is None,'formal acknowledged edit lacks later retest')
    need(f['terminal_statement']['observed'] is False and f['trace']['final_role']=='tool','no observed formal global terminal claim')
    need([x['failures'] for x in r['pov_retests']]==[5,2,0],'positive-control same-visible-command progression')
    need([x['closure'] for x in r['repair_chains']]==['retest_still_failed','retest_success'],'positive-control two edits not one miraculous repair')
    need(r['terminal_statement']['line']==78 and r['terminal_statement']['observed'] is True,'observed positive terminal statement')
    sweep=r['full_sweep_displayed'][0]
    need(sweep['pipeline_exit_caveat'] is True,'pipeline outer zero caveat')
    need([x['tests'] for x in sweep['summaries']]==[54,37,13,31,14,15] and all(x['status']=='OK' for x in sweep['summaries']),'six displayed summaries, not outer exit alone')
    need(h['formal_scored_solution_hash'] is None and h['r1_scored_solution_hash'] is None,'historical scored-version identity remains unknown')
    need(h['same_current_bytes_not_original_scoring_attestation'] is True,'current identity not historical attestation')
    need(data['limits']['new_sample_size']==0 and data['limits']['frozen_scores_changed'] is False,'no new runs or score rewrite')
    need(data['limits']['formal_tail_cause']=='unknown' and data['limits']['formal_10_to_external_3_not_same_suite_effect'] is True,'no invented cause or suite-equivalence effect')
    return checked


def main():
    raw=(ROOT/'events.json').read_bytes()
    if sha256(raw).hexdigest()!=EVENTS_SHA256:raise ValueError('derived events bytes changed')
    data=strict_json(raw.decode('utf-8'));checks=verify(data)
    suite=unittest.defaultTestLoader.loadTestsFromName('test_core')
    run=unittest.TextTestRunner(stream=sys.stderr,verbosity=1).run(suite)
    if not run.wasSuccessful() or run.testsRun!=52:raise ValueError('self-owned synthetic tests failed/count changed')
    print(json.dumps({'status':'PASS_DERIVED_SELF_CONSISTENCY_NOT_HISTORICAL_AUTHENTICATION',
                      'events_sha256':EVENTS_SHA256,'derived_checks':len(checks),'synthetic_tests':run.testsRun,
                      'legacy_F5':1,'supported_agent_false_final_from_this_evidence':0,
                      'original_attribution_insufficient':1,'historical_scored_versions':'unknown'},indent=2))
if __name__=='__main__':main()
