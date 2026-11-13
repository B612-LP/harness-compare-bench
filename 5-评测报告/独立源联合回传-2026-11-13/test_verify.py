"""Local counterexamples; no models/network, same checks under python -O."""
import copy
import json
import pathlib
import unittest
import verify as v

ROOT = pathlib.Path(__file__).resolve().parent

class DerivedEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.data, cls.files = v.load(ROOT)

    def fresh(self): return copy.deepcopy(self.data), dict(self.files)

    def reject(self, data, files, reason):
        with self.assertRaisesRegex(ValueError, reason): v.verify(data, files)

    def rewrite_answer(self, cell, files, raw):
        files[cell['answer']['file']] = raw
        cell['answer']['sha256'] = v.sha(raw); cell['answer']['bytes'] = len(raw)

    def test_actual_selected_faces(self):
        report = v.verify(self.data, self.files)
        self.assertEqual(report['posthoc_exact'],'4/4')
        self.assertEqual(report['original_gate'],'FAIL 0/4; not reclassified')

    def test_nonce_and_exact_json(self):
        for mode, reason in (('wrong','wrong_nonce'),('extra','answer_top_keys'),('duplicate','duplicate_json_key')):
            d, f = self.fresh(); cell = d['cells'][0]
            answer = v.parse(f[cell['answer']['file']].decode().strip().removeprefix('```json\n').removesuffix('\n```'))
            if mode=='wrong':
                s=answer['packet_a']['head_nonce']; answer['packet_a']['head_nonce']=('0' if s[0]!='0' else '1')+s[1:]
            if mode=='extra': answer['extra']='not allowed'
            raw=json.dumps(answer).encode()
            if mode=='duplicate': raw=b'{"packet_a":{},'+raw[1:]
            self.rewrite_answer(cell,f,raw); self.reject(d,f,reason)

    def test_duplicate_not_independent(self):
        d,f=self.fresh(); d['cells'][1]['calls'][1]['source']='A1'
        self.reject(d,f,'duplicate_as_independent')

    def test_geometry_and_information(self):
        for field, value, reason in (('M_source',2800,'forged_M'),('omitted_bytes',14267,'forged_omitted'),('source_intervals',[[0,869],[15136,16000]],'source_interval_union')):
            d,f=self.fresh(); d['cells'][1]['calls'][0][field]=value; self.reject(d,f,reason)
        d,f=self.fresh(); d['cells'][1]['I_text']=1400; self.reject(d,f,'forged_I')
        d,f=self.fresh(); d['cells'][1]['two_call_source_bytes_sum']=1732; self.reject(d,f,'source_vs_joint_M')
        d,f=self.fresh(); call=d['cells'][1]['calls'][0]; raw=f[call['file']].replace(b'Omitted 14268',b'Omitted 14267')
        f[call['file']]=raw; call['derived_text_sha256']=v.sha(raw); self.reject(d,f,'forged_omitted')

    def test_missing_duplicate_cell_or_call(self):
        for mode in ('missing_cell','duplicate_cell','missing_call','duplicate_call','wrong_link'):
            d,f=self.fresh()
            if mode=='missing_cell': d['cells'].pop()
            if mode=='duplicate_cell': d['cells'][1]=d['cells'][0]
            if mode=='missing_call': d['cells'][0]['calls'].pop()
            if mode=='duplicate_call': d['cells'][0]['calls'][1]=d['cells'][0]['calls'][0]
            if mode=='wrong_link': d['cells'][0]['calls'][0]['result_tool_use_id']='different'
            self.reject(d,f,'missing_or_duplicate|call_linkage')

    def test_first_wire_usage_and_posthoc_labels(self):
        d,f=self.fresh(); d['cells'][0]['first_wire']['sha256']='0'*64; self.reject(d,f,'first_wire_commitment')
        d,f=self.fresh(); d['cells'][0]['provider_usage_events'][0]['provider_usage_events'][-1]['usage']['inferred_total_tokens']=516
        self.reject(d,f,'usage_original_fields_only')
        d,f=self.fresh(); d['cells'][0]['provider_usage_events'][0]['provider_usage_events'][-1]['usage']['cache_creation_input_tokens']=False
        self.reject(d,f,'usage_integer_fields')
        d,f=self.fresh(); d['limits']['usage_arithmetic_performed']=True; self.reject(d,f,'limits_or_usage_merge')
        d,f=self.fresh(); d['posthoc_gate']['preregistered_pass']=True; self.reject(d,f,'posthoc_not_preregistered')
        d,f=self.fresh(); d['original_gate']['valid']=4; self.reject(d,f,'original_gate_not_pass')

    def test_privacy_marking_and_path_residue(self):
        d,f=self.fresh(); d['cells'][0]['calls'][0]['path_transform']['applied']=False
        self.reject(d,f,'privacy_transform_not_marked')
        d,f=self.fresh(); f['unexpected.txt']=(chr(47)+'Users'+chr(47)+'private').encode()
        self.reject(d,f,'private_path_or_trace_residue')
        d,f=self.fresh(); d['privacy']['derived_not_raw_trace']=False; self.reject(d,f,'privacy_label')

if __name__=='__main__': unittest.main(verbosity=2)
