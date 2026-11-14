"""Read-only grouped semantic counterexamples; no new product/model operations."""
import copy,json,os,sys,unittest
from pathlib import Path
from unittest import mock
import verify as v

def guard(event,args):
    if event in ('socket.__new__','socket.getaddrinfo','subprocess.Popen','os.system','os.kill','os.killpg'):raise RuntimeError('offline_readonly_tests')
    if event=='open':
        p,mode,flags=args
        if (isinstance(mode,str) and any(x in mode for x in 'wax+')) or (isinstance(flags,int) and flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND)):raise RuntimeError('readonly_tests')
sys.addaudithook(guard)
class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.root=Path(__file__).resolve().parent;cls.data,cls.files=v.load(cls.root)
    def rejected(self,change):
        data=copy.deepcopy(self.data);files=dict(self.files);change(data,files)
        # Defeat only integrity/baseline shortcuts: actual semantic checks must reject.
        files['evidence.json']=v.canonical(data)
        with mock.patch.object(v,'BASELINE',v.sha(v.canonical(data))):
            with self.assertRaises(ValueError):v.verify(data,files)
    def test_selected_disks_positive_and_no_numeric_inner(self):
        result=v.verify(self.data,self.files);self.assertEqual(result['decoded_bytes_each'],72);self.assertIsNone(result['numeric_inner_exit_code']);self.assertEqual(result['scientific_confirm_sessions'],1)
    def test_actual_source_geometry_even_after_rehash(self):
        def wrong(data,files):
            files['sources/B.txt']=files['sources/A.txt'];row=data['observations'][1];row['source_original_sha256']=row['source_derived_sha256']=v.sha(files['sources/B.txt'])
        self.rejected(wrong)
        self.rejected(lambda d,f:d['design'].update(known_pair_differing_byte=8008))
    def test_result_rebound_coherently_but_wrong_source_or_LF(self):
        def wrong(d,f):
            r=d['observations'][1];raw=f['outputs/A.txt'];f['outputs/B.txt']=raw;r['result_original_text_sha256']=r['result_derived_text_sha256']=v.sha(raw);r['wire_block']['content'][0]['text']=raw.decode();r['native_event']['result']=raw.decode()
        self.rejected(wrong)
        def no_lf(d,f):f['outputs/A.txt']=f['outputs/A.txt'][:-1]
        self.rejected(no_lf)
    def test_native_wire_error_presence_and_original_text_schema(self):
        changes=[lambda d,f:d['observations'][0]['wire_block'].pop('is_error'),lambda d,f:d['observations'][0]['wire_block'].update(is_error=True),lambda d,f:d['observations'][0]['wire_block'].update(content=d['observations'][0]['native_event']['result']),lambda d,f:d['observations'][0]['native_event'].update(status='error'),lambda d,f:d['observations'][0]['native_event'].update(truncated=False),lambda d,f:d['observations'][0]['wire_position'].update(message_index=4)]
        for change in changes:self.rejected(change)
    def test_end_status_cleanup_typed_unknown_not_success(self):
        for key,value in (('completed',False),('exit_code',False),('failure',{}),('timeout',True),('launch_failure','unknown'),('cleanup_attempts',True),('native_identity_verified',False)):
            self.rejected(lambda d,f,k=key,x=value:d['ends']['confirm'].update({k:x}))
        self.rejected(lambda d,f:d['ends']['confirm']['owned_group_cleanup'].update(state='unknown'))
        self.rejected(lambda d,f:d['ends']['confirm']['owned_group_cleanup'].update(scope='all_processes'))
    def test_counts_reachability_numeric_and_http_units(self):
        for change in (lambda d,f:d['counts'].update(confirm_scientific_sessions=2),lambda d,f:d['counts'].update(real_model_calls=False),lambda d,f:d['limits'].update(inner_exit_code=0),lambda d,f:d['limits'].update(numeric_inner_exit_code_observed=True),lambda d,f:d['limits'].update(unknown_256_bit_increment_measured=True),lambda d,f:d['design'].update(agent_strategy_tested=True),lambda d,f:d['design'].update(valid_zero_or_one_counterbranch_covered=True),lambda d,f:d['requests'][1].update(raw_request_body_bytes=72),lambda d,f:d['requests'][0].update(raw_request_sha256=d['requests'][0]['formatted_json_file_sha256'])):self.rejected(change)
    def test_original_derived_commands_alias_and_coverage(self):
        for change in (lambda d,f:d['observations'].append(copy.deepcopy(d['observations'][0])),lambda d,f:d['observations'].pop(),lambda d,f:d['observations'][0].update(source_transform='content_anonymized'),lambda d,f:d['observations'][0]['arguments'].update(command='echo TARGET=known'),lambda d,f:d['observations'][0].update(original_arguments_sha256=d['observations'][0]['derived_arguments_sha256']),lambda d,f:d['provenance'].update(original_raw_authenticated_by_public_package=True),lambda d,f:d.update(schema='field-selection-selected-v0')):self.rejected(change)
    def test_privacy_inventory_no_extras_symlinks_or_json_downgrade(self):
        with self.assertRaises(ValueError):v.privacy(('/'+'Users/'+'someone/file').encode())
        with self.assertRaises(ValueError):v.parse('{"x":1,"x":2}')
        with self.assertRaises(ValueError):v.parse('{"x":NaN}')
        extra=dict(self.files);extra['extra.txt']=b''
        with self.assertRaises(ValueError):v.verify_inventory(extra)
        with mock.patch.object(Path,'is_symlink',return_value=True):
            with self.assertRaises(ValueError):v.load(self.root)
        original=Path.iterdir
        def extra_dir(path):
            result=list(original(path));return iter(result+[path/'extra-empty']) if path==self.root else iter(result)
        if (self.root/'evidence.json').exists():
            with mock.patch.object(Path,'iterdir',extra_dir):
                with self.assertRaises(ValueError):v.load(self.root)
    def test_cleanup_final_present_rejected_after_inventory_and_rebaseline(self):
        data=copy.deepcopy(self.data);files=dict(self.files)
        cleanup=data['ends']['confirm']['owned_group_cleanup']
        cleanup['events'].append({'signal':0,'result':'present'})
        self.assertEqual(cleanup['state'],'absent')
        self.assertTrue(any(event['result']=='absent' for event in cleanup['events']))
        files['evidence.json']=v.canonical(data)
        files['SHA256SUMS.json']=json.dumps({name:v.sha(raw) for name,raw in files.items() if name!='SHA256SUMS.json'},sort_keys=True).encode()
        v.verify_inventory(files)
        with mock.patch.object(v,'BASELINE',v.sha(v.canonical(data))):
            with self.assertRaisesRegex(ValueError,'final_owned_group_absence_witness'):v.verify(data,files)
if __name__=='__main__':unittest.main(verbosity=2)
