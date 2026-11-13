#!/usr/bin/env python3
"""Read-only offline counterexamples; normal and -O use the same explicit checks."""
import copy
import sys
import unittest
from pathlib import Path
import verify as V

def audit(event,args):
    if event.startswith(('socket.','subprocess.','os.system','os.exec','os.spawn')): raise RuntimeError('offline_only')
    if event=='open' and isinstance(args[1],str) and any(x in args[1] for x in 'wax+'): raise RuntimeError('read_only')
sys.addaudithook(audit)
ROOT=Path(__file__).resolve().parent

class Pure(unittest.TestCase):
    def test_numbered_known_lf(self):
        source=('head_nonce='+'a'*700+'\n'+''.join('row'+str(i)+'\n' for i in range(190))+'tail_nonce='+'b'*700+'\n').encode()
        path='X'*160
        text='<path>'+path+'</path>\n<type>file</type>\n<content>\n'+'\n'.join(str(i)+': '+line for i,line in enumerate(source.decode().splitlines(),1))+'\n\n(End of file - total 192 lines)\n</content>'
        got=V.read_lines(text,path,source); self.assertEqual(got['numbered_lines'],192)
        for bad in (text.replace('100: ','101: '),text.replace('total 192','total 193'),text.replace('row99','wrong'),text.replace('</content>','</content>junk')):
            with self.assertRaises(ValueError): V.read_lines(bad,path,source)
    def test_error_precedes_presentation(self):
        with self.assertRaisesRegex(ValueError,'error_envelope'): V.read_lines('<tool_use_error>denied</tool_use_error>','X',b'')
        with self.assertRaisesRegex(ValueError,'error_envelope'): V.error_first('valid looking',True)
        with self.assertRaises(ValueError): V.parse('{"a":1,"a":2}')
        with self.assertRaises(ValueError): V.parse('{"a":NaN}')

@unittest.skipUnless((ROOT/'evidence.json').exists(),'actual export not present; no fabricated final result')
class Actual(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.data,cls.files=V.load(ROOT)
    def test_positive_inventory(self):
        V.verify_inventory(self.files); self.assertEqual(V.verify(self.data,self.files)['selected_faces'],18)
    def rejected(self,mutate):
        data=copy.deepcopy(self.data); files=dict(self.files); mutate(data,files)
        with self.assertRaises(ValueError): V.verify(data,files,False)
    def test_coverage_and_original_failure(self):
        for edit in (lambda d,f:d['cases'].pop(),lambda d,f:d['cases'][0]['frames'].pop(),lambda d,f:d['earlier'].update(actual_native_reads=4),lambda d,f:d['counts'].update(cumulative_seen_local=8),lambda d,f:d['counts'].update(new_remote_forwards=1)):
            self.rejected(edit)
    def test_roles_position_target_parameters(self):
        edits=(lambda d,f:d['cases'][0]['frames'][3].update(role='assistant'),lambda d,f:d['cases'][0]['frames'][3].update(position=[4,0]),lambda d,f:d['cases'][0]['frames'][3].update(target_source='A1'),lambda d,f:d['cases'][0]['calls'][2]['input'].update(offset=1),lambda d,f:d['cases'][1].update(read_order=['packet_a','packet_b']),lambda d,f:d['cases'][0]['calls'][0].update(alias='longerID'))
        for edit in edits: self.rejected(edit)
    def test_rehash_cannot_fix_source_or_history(self):
        def mutate(d,f,kind):
            frame=d['cases'][0]['frames'][-1]; text=frame['text']
            if kind=='line': text=text.replace('100: ','101: ')
            elif kind=='nonce': text=text.replace('head_nonce=','head_nonce=f',1)
            elif kind=='error': text='<error>denied</error>'+text
            else: text=text.replace('End of file - total 192','Output capped. Showing lines 1-192')
            frame['text']=text; frame['derived_text_sha256']=V.sha(text.encode()); frame['derived_block_sha256']=V.sha(V.canonical(V.block(text,frame['call_alias']))); frame['original_text_bytes']=len(text.encode())
        for kind in ('line','nonce','error','footer'): self.rejected(lambda d,f:mutate(d,f,kind))
    def test_bytes_transform_and_layer_boundaries(self):
        edits=(lambda d,f:d['cases'][0]['frames'][0]['measurement'].update(retained_source_bytes=16000),lambda d,f:d['cases'][0]['frames'][0]['path_transforms'][0].update(start_utf8=0),lambda d,f:d['cases'][0]['paths']['packet_a'].update(target_source='B1'),lambda d,f:d['sources']['A1'].update(original_sha256='0'*64),lambda d,f:d['boundaries'].update(model_score=True),lambda d,f:d['defaults'].update(file_policy='danger-full-access'))
        for edit in edits: self.rejected(edit)
    def test_lf_identity_not_common_middle_or_stdout(self):
        def rewrite(d,f,kind):
            frame=d['cases'][0]['frames'][-1]; text=frame['text']
            if kind=='preview': text=text.encode()[:8192].decode()
            elif kind=='lf': text=text.replace('\n','\r\n')
            else:
                own=f['sources/B1.txt'].decode().splitlines(); other=f['sources/A1.txt'].decode().splitlines()
                if kind=='wrong_source':
                    for i,(a,b) in enumerate(zip(own,other),1): text=text.replace(str(i)+': '+a,str(i)+': '+b)
                else: text=text.replace('192: '+own[-1],'192: '+other[-1])
            frame['text']=text; frame['derived_text_sha256']=V.sha(text.encode()); frame['derived_block_sha256']=V.sha(V.canonical(V.block(text,frame['call_alias']))); frame['original_text_bytes']=len(text.encode())
        for kind in ('preview','lf','wrong_source','mixed_tail'): self.rejected(lambda d,f:rewrite(d,f,kind))
        self.rejected(lambda d,f:d['cases'][0]['native_read_previews'][0].update(truncated=False))
        self.rejected(lambda d,f:d['cases'][0]['frames'][-1]['line_sha256'].pop())
    def test_privacy_and_inventory(self):
        with self.assertRaises(ValueError): V.privacy(('/'+'Users/'+'person/secret').encode())
        f=dict(self.files); f['extra.txt']=b'extra'
        with self.assertRaises(ValueError): V.verify_inventory(f)
        f=dict(self.files); f['sources/A1.txt']+=b'x'
        with self.assertRaises(ValueError): V.verify_inventory(f)

if __name__=='__main__': unittest.main()
