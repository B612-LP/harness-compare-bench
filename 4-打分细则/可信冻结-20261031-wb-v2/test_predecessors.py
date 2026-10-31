#!/usr/bin/env python3
"""SYNTHETIC FIXTURES ONLY. Not product runs, timestamps or adjudication evidence."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
SPEC=importlib.util.spec_from_file_location('wb_v2_contract',Path(__file__).with_name('freeze.py'));v=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(v)

class PredecessorTests(unittest.TestCase):
    def setUp(self):
        self.parents=[]
        for case in v.CASES:
            self.parents.append(dict(event_id='SYNTHETIC-PARENT:'+case,category='product_run',group='W_gateway',product='workbuddy',experiment=False,case_id=case,identity={'value':{'run_id':'SYNTHETIC-RUN:'+case}},selection=dict(kind='first',order=1,parent_id=None,plan_id='r20261031-wb-formal',slot_id='workbuddy|'+case),facts={'rule_version':{'value':v.V1_RULE},'final_adjudication':{'value':'valid'}},gates={g:{'state':'known','value':True} for g in v.BAD_GATES.values()},score={'value':{'reported':30,'reward':0}},sources=[]))
        self.case=v.CASES[1];self.parent=self.parents[1];self.parent['facts']['final_adjudication']['value']='invalid';self.parent['gates']['contamination_free']['value']=False
        self.link=dict(parent_event_id=self.parent['event_id'],child_event_id='SYNTHETIC-CHILD:'+self.case,child_slot_id='SYNTHETIC-NEW-SLOT|'+self.case,reason='contamination',semantic_kind='replacement',replacement_index=1,max_replacements=1)
        self.config=dict(plan_id='SYNTHETIC-REPLACEMENT-PLAN',predecessors={self.case:self.link},invalid_cases=[self.case])
        self.table={'groups':{'W_gateway':[e['event_id'] for e in self.parents if e is not self.parent],'A_same_model':[],'B_native':[]},'rejected':[{'event_id':self.parent['event_id'],'reasons':['gate:contamination_free','final_adjudication_not_valid']}]}
        self.registration=dict(event_id=self.link['child_event_id'],plan_id=self.config['plan_id'],slot_id=self.link['child_slot_id'],order=1,kind='first',parent_id=None,reason='fixed_first',registered_at='2099-01-01T00:00:00+00:00')
        self.plan={'plan_id':self.config['plan_id'],'rule_version':v.RULE,'design':{'semantic_kind':'invalid_only_replacement','predecessor_plan':'r20261031-wb-formal','max_replacements_per_parent':1,'no_valid_low_score_replacement':True,'automatic_retry':False,'automatic_replacement':False},'predecessors':{self.case:dict(parent_event_id=self.parent['event_id'],semantic_kind='replacement',reason='contamination',replacement_index=1,evidence='SYNTHETIC-adjudication.json')},'registrations':[self.registration]}
        self.child=copy.deepcopy(self.parent);self.child.update(event_id=self.link['child_event_id'],selection=self.registration,identity={'value':{'run_id':'SYNTHETIC-NEW-RUN'}})

    def valid(self):return v.validate_predecessors(self.config,self.parents,self.table)
    def test_positive_explicit_replacement_mechanical_first(self):
        self.valid();v.validate_plan(self.plan,self.config,self.parents);v.child_completeness([self.child],self.config)
    def test_parent_valid_low_score_not_eligible(self):
        self.parent['facts']['final_adjudication']['value']='valid'
        with self.assertRaises(v.Invalid):self.valid()
    def test_parent_unknown_not_eligible(self):
        self.parent['facts']['final_adjudication']['value']=None
        with self.assertRaises(v.Invalid):self.valid()
    def test_parent_suspect_eligible_with_false_gate(self):
        self.parent['facts']['final_adjudication']['value']='suspect';self.valid()
    def test_parent_not_first_rejected(self):
        self.parent['selection']['kind']='replacement'
        with self.assertRaises(v.Invalid):self.valid()
    def test_second_replacement_index_rejected(self):
        self.link['replacement_index']=2
        with self.assertRaises(v.Invalid):self.valid()
    def test_cap_relaxation_rejected(self):
        self.link['max_replacements']=2
        with self.assertRaises(v.Invalid):self.valid()
    def test_reason_does_not_match_gate_rejected(self):
        self.link['reason']='case_invalid'
        with self.assertRaises(v.Invalid):self.valid()
    def test_score_low_not_valid_replacement_reason(self):
        self.link['reason']='score_low'
        with self.assertRaises(v.Invalid):self.valid()
    def test_gate_unknown_not_eligible(self):
        self.parent['gates']['contamination_free']={'state':'unknown','value':None}
        with self.assertRaises(v.Invalid):self.valid()
    def test_false_gate_without_rejected_reason_rejected(self):
        self.table['rejected'][0]['reasons']=['final_adjudication_not_valid']
        with self.assertRaises(v.Invalid):self.valid()
    def test_parent_still_official_rejected(self):
        self.table['groups']['W_gateway'].append(self.parent['event_id'])
        with self.assertRaises(v.Invalid):self.valid()
    def test_full_original_five_required(self):
        with self.assertRaises(v.Invalid):v.validate_predecessors(self.config,self.parents[:-1],self.table)
    def test_wrong_parent_case(self):
        self.link['parent_event_id']=self.parents[0]['event_id']
        with self.assertRaises(v.Invalid):self.valid()
    def test_wrong_parent_product(self):
        self.parent['product']='codex'
        with self.assertRaises(v.Invalid):self.valid()
    def test_no_unqualified_first_disclosure(self):
        self.plan['design']['semantic_kind']='first'
        with self.assertRaises(v.Invalid):v.validate_plan(self.plan,self.config,self.parents)
    def test_keep_original_queue_semantics(self):
        self.registration['kind']='replacement';self.registration['order']=2;self.registration['parent_id']=self.parent['event_id']
        with self.assertRaises(v.Invalid):v.validate_plan(self.plan,self.config,self.parents)
    def test_missing_child(self):
        with self.assertRaises(v.Invalid):v.child_completeness([],self.config)
    def test_extra_child(self):
        with self.assertRaises(v.Invalid):v.child_completeness([self.child,self.child],self.config)
    def test_wrong_child_group(self):
        self.child['group']='A_same_model'
        with self.assertRaises(v.Invalid):v.child_completeness([self.child],self.config)
    def test_no_valid_first_batch_readmission(self):
        with self.assertRaises(v.Invalid):v.child_completeness([self.child,self.parents[0]],self.config)
    def test_parent_bytes_not_mutated(self):
        before=json.dumps(self.parents,sort_keys=True);self.valid();v.validate_plan(self.plan,self.config,self.parents);v.child_completeness([self.child],self.config)
        self.assertEqual(json.dumps(self.parents,sort_keys=True),before)
    def test_locked_subset_cannot_expand(self):
        self.config['invalid_cases'].append(v.CASES[0])
        with self.assertRaises(v.Invalid):self.valid()
    def test_bad_path_escape(self):
        with self.assertRaises(v.Invalid):v.public(Path('/tmp'),'../outside')
    def test_adapter_preserves_all_non_version_rejection_reasons(self):
        class FakeV1:
            @staticmethod
            def reasons(event,config):return ['rule_version_not_frozen','score_receipt_rule_or_checker_mismatch','gate:contamination_free','unknown:tools','same_model_not_proven']
        event=copy.deepcopy(self.child);event['facts']['rule_version']['value']=v.RULE;event['score']['value']=dict(rule_version=v.RULE,checker_sha256='a'*64)
        config={'case_snapshots':{self.case:{'checker.py':'a'*64}}}
        self.assertEqual(v.admission_reasons(FakeV1,event,config),['gate:contamination_free','same_model_not_proven','unknown:tools'])
    def test_adapter_rechecks_its_own_rule_and_checker(self):
        class FakeV1:
            @staticmethod
            def reasons(event,config):return []
        event=copy.deepcopy(self.child);event['score']['value']=dict(rule_version=v.V1_RULE,checker_sha256='b'*64)
        config={'case_snapshots':{self.case:{'checker.py':'a'*64}}}
        self.assertEqual(v.admission_reasons(FakeV1,event,config),['rule_version_not_frozen','score_receipt_rule_or_checker_mismatch'])
    def test_prompt_revision_requires_actual_sent_proof(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get('WB_TEST_TMPDIR'),prefix='SYNTHETIC-PROMPT-') as directory:
            root=Path(directory);revision=root/'revision.json';revision.write_text('{}');revision_pin=v.pin(root,'revision.json');self.child['sources']=[revision_pin];prompt_pin={'path':'prompt.txt','sha256':'a'*64}
            with self.assertRaises(v.Invalid):v.prompt_binding(root,self.child,revision_pin,prompt_pin)
            prompt=root/'prompt.txt';prompt.write_text('SYNTHETIC ONLY\n'+v.BOUNDARY_TEXT);prompt_pin=v.pin(root,'prompt.txt')
            proof=root/'proof.json';proof.write_text(v.dump(dict(event_id=self.child['event_id'],sent_prompt_sha256=prompt_pin['sha256'],prompt_path='prompt.txt',prompt_revision_sha256=revision_pin['sha256'])))
            self.child['sources']=[revision_pin,prompt_pin,v.pin(root,'proof.json')];v.prompt_binding(root,self.child,revision_pin,prompt_pin)
            prompt.write_text('SYNTHETIC MISSING BOUNDARY');prompt_pin=v.pin(root,'prompt.txt');proof.write_text(v.dump(dict(event_id=self.child['event_id'],sent_prompt_sha256=prompt_pin['sha256'],prompt_path='prompt.txt',prompt_revision_sha256=revision_pin['sha256'])))
            self.child['sources']=[revision_pin,prompt_pin,v.pin(root,'proof.json')]
            with self.assertRaises(v.Invalid):v.prompt_binding(root,self.child,revision_pin,prompt_pin)

if __name__=='__main__':unittest.main(verbosity=2)
