#!/usr/bin/env python3
"""Read-only finite rehash counterexamples; software tests are not science samples."""
from pathlib import Path
import copy,sys,os,unittest
from unittest import mock
import verify as v

def guard(event,args):
    if event in ('subprocess.Popen','os.system','socket.__new__','socket.getaddrinfo','os.kill','os.killpg'):raise RuntimeError('offline_readonly_test')
    if event=='open':
        _,mode,flags=args
        if (isinstance(mode,str) and any(x in mode for x in 'wax+')) or (isinstance(flags,int) and flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND)):raise RuntimeError('no_test_file_writes')
sys.addaudithook(guard)
class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.files=v.load(Path(__file__).resolve().parent);cls.data=v.parse(cls.files['evidence.json'])
    def check(self,data=None,files=None):return v.verify(self.data if data is None else data,self.files if files is None else files)
    def reject(self,change):
        data=copy.deepcopy(self.data);files=dict(self.files);change(data,files)
        # Recommit the complete data, intentionally bypassing only the consistency seal.
        # Semantic failures must survive an attacker recomputing inventory/value hashes.
        with mock.patch.object(v,'BASELINE',v.baseline(data)):
            with self.assertRaises(ValueError):self.check(data,files)
    def test_real_selected_files_positive_and_byte_units(self):
        v.verify_inventory(self.files);r=self.check();self.assertEqual(r['counts'],[1,1,0,1]);self.assertEqual(r['final_source_bytes'],1470)
        self.assertEqual(self.data['queries'][0]['geometry']['final_source_intervals'],[[0,647],[1177,2000]])
        self.assertEqual(len(self.files),14);self.assertFalse(r['unpublished_raw_authenticated'])
    def test_static_source_semantics_survive_rehash(self):
        def same(data,files):
            files['sources/B.txt']=files['sources/A.txt'];data['sources'][1]['original_sha256']=data['sources'][1]['derived_sha256']=v.sha(files['sources/B.txt'])
        self.reject(same)
        data=copy.deepcopy(self.data);files=dict(self.files);same(data,files)
        with mock.patch.dict(v.SOURCE_HASHES,{'B':v.sha(files['sources/A.txt'])}),mock.patch.object(v,'BASELINE',v.baseline(data)):
            with self.assertRaisesRegex(ValueError,'not_exact_one_byte_source_pair'):self.check(data,files)
        self.reject(lambda d,f:d['sources'][0].update(original_sha256='f'*64))
        self.reject(lambda d,f:d['sources'][0].update(transform='anonymous_full_redaction'))
    def test_actual_result_and_format_files_are_not_just_inventory(self):
        def wrong(d,f):
            f['formatted/Q1.txt']=f['formatted/Q1.txt'].replace(b'HEAD=',b'HEAd=');d['queries'][0]['derived_formatted_sha256']=v.sha(f['formatted/Q1.txt'])
        self.reject(wrong)
        def omitted(d,f):
            f['results/Q1.txt']=f['results/Q1.txt'].replace(b'Omitted 530',b'Omitted 529');d['queries'][0]['derived_result_sha256']=v.sha(f['results/Q1.txt'])
        self.reject(omitted)
        for key,value in (('final_source_bytes',2000),('preformatted_bytes',16000),('final_wrapper_bytes',False),('final_source_intervals',[[0,2000]])):
            self.reject(lambda d,f,k=key,x=value:d['queries'][0]['geometry'].update({k:x}))
    def test_Native_wire_exact_and_error_field_presence(self):
        def contradiction(d,f):
            e=d['selected_results'][5];e['native_event']['result']='No matches found';e['derived_native_event_canonical_sha256']=v.sha(v.canonical(e['native_event']))
        self.reject(contradiction)
        for field,value in (('status','error'),('status','unknown'),('truncated',False),('result','Found 1 match')):
            self.reject(lambda d,f,k=field,x=value:d['selected_results'][2]['native_event'].update({k:x}))
        self.reject(lambda d,f:d['selected_results'][4]['wire_block'].pop('is_error'))
        self.reject(lambda d,f:d['selected_results'][4]['wire_block'].update(is_error=0))
        self.reject(lambda d,f:d['selected_results'][4].update(wire_is_error_present=False))
        self.reject(lambda d,f:d['selected_results'][0]['wire_block']['content'].append({'type':'text','text':'unissued target text'}))
        self.reject(lambda d,f:d['selected_results'][0].update(wire_role='assistant'))
    def test_zero_is_only_exact_completed_NoMatches_on_this_source(self):
        for value in (False,1,None):self.reject(lambda d,f,x=value:d['queries'][2].update(count=x))
        def text_error(d,f):
            f['results/Q3.txt']=b'Error: No matches found';d['queries'][2]['derived_result_sha256']=v.sha(f['results/Q3.txt'])
        self.reject(text_error)
        self.reject(lambda d,f:d['selected_results'][4]['wire_block'].update(is_error=True))
        self.reject(lambda d,f:d['queries'][2].update(source='B'))
        self.reject(lambda d,f:d['queries'][3].update(pattern=v.G))
    def test_coverage_version_history_and_scientific_scope(self):
        self.reject(lambda d,f:d.update(format='native-match-selected-20261114-v1'))
        self.reject(lambda d,f:d['queries'].pop())
        self.reject(lambda d,f:d['queries'].__setitem__(1,copy.deepcopy(d['queries'][0])))
        self.reject(lambda d,f:d['selected_results'].pop())
        self.reject(lambda d,f:d['coverage'].update(scientific_confirm_sessions=4))
        self.reject(lambda d,f:d['coverage'].update(real_models=False))
        self.reject(lambda d,f:d['private_replay_relations'].update(all_five_history_increments_closed=1))
        self.reject(lambda d,f:d['limits'].update(not_whole_context_equality=False))
        self.reject(lambda d,f:d['provenance']['scientific_audit'].update(status='full_runtime_certified'))
    def test_terminal_state_meta_and_owned_group_scope(self):
        for field,value in (('exit_code',False),('exit_code',1),('timeout',True),('native_identity_verified',None),('failure',{}),('completed',1),('never_resubmit',False)):
            self.reject(lambda d,f,k=field,x=value:d['runtime_end']['confirm'].update({k:x}))
        self.reject(lambda d,f:d['runtime_end']['confirm'].pop('native_identity_verified'))
        self.reject(lambda d,f:d['runtime_end']['confirm']['owned_group_witness'].update(start_new_session=1))
        self.reject(lambda d,f:d['runtime_end']['confirm']['owned_group_witness'].update(scope='all_descendants_certified_absent'))
        self.reject(lambda d,f:d['request_commitments'][0].update(upstream_forwards=False))
        self.reject(lambda d,f:d['request_commitments'][0].update(status='200'))
        self.reject(lambda d,f:d['request_commitments'][0].update(raw_request_sha256=d['request_commitments'][0]['formatted_json_file_sha256']))
    def test_privacy_inventory_and_strict_json(self):
        for text in ('/'+ 'Users/'+'person/data','bench'+'-private/x','dsh'+'-spill-identity'):
            with self.assertRaises(ValueError):v.privacy(text.encode())
        for raw in (b'{"a":1,"a":2}',b'{"a":NaN}'):
            with self.assertRaises(ValueError):v.parse(raw)
        files=dict(self.files);files['extra.txt']=b'x'
        with self.assertRaises(ValueError):v.verify_inventory(files)
        self.reject(lambda d,f:d['sources'][0].update(source_path_placeholder='../source/A/X'))
if __name__=='__main__':unittest.main(verbosity=2)
