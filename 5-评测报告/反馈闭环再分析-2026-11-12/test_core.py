"""Synthetic parser boundaries only. No historical implementation is executed."""
import copy
import json
import unittest
from core import parse_trace, replay_file, successful_file_ack, strict_json, unittest_summary, pov_retests, terminal_claim

P = 'SYNTHETIC/pov/pov.py'

def assistant(cid='a', name='Write', args=None, content=''):
    return {'role':'assistant','content':content,'tool_calls':[{'id':cid,'function':{'name':name,'arguments':json.dumps(args or {'file_path':P,'content':'x=1\n'})}}]}

def returned(cid='a', content=None):
    return {'role':'tool','tool_call_id':cid,'content':content if content is not None else 'The file '+P+' has been updated successfully.'}

def encode(rows):
    return ('\n'.join(json.dumps(x,ensure_ascii=False) for x in rows)+'\n').encode()

def trace(rows): return parse_trace(encode(rows))

class Parsing(unittest.TestCase):
    def test_assistant_only_export_start(self):
        t=trace([assistant(),returned()]);self.assertEqual(t['roles'],{'assistant':1,'tool':1})
    def test_parallel_returns_bound_by_id_not_position(self):
        a=assistant();a['tool_calls']+=assistant('b')['tool_calls']
        self.assertEqual(len(trace([a,returned('b'),returned()])['calls']),2)
    def test_empty(self):
        with self.assertRaises(ValueError):parse_trace(b'')
    def test_invalid_utf8(self):
        with self.assertRaises(UnicodeDecodeError):parse_trace(b'\xff')
    def test_blank_row(self):
        with self.assertRaises(ValueError):parse_trace(encode([assistant(),returned()])+b'\n')
    def test_duplicate_decoded_key(self):
        with self.assertRaises(ValueError):strict_json('{"role":1,"r\\u006fle":2}')
    def test_nested_duplicate(self):
        with self.assertRaises(ValueError):strict_json('{"x":{"k":1,"k":2}}')
    def test_nan(self):
        with self.assertRaises(ValueError):strict_json('NaN')
    def test_infinity(self):
        with self.assertRaises(ValueError):strict_json('Infinity')
    def test_exponent_overflow(self):
        with self.assertRaises(ValueError):strict_json('1e999')
    def test_invalid_surrogate(self):
        with self.assertRaises(UnicodeEncodeError):strict_json('"\\ud800"')
    def test_orphan(self):
        with self.assertRaises(ValueError):trace([returned()])
    def test_forward_return(self):
        with self.assertRaises(ValueError):trace([returned(),assistant()])
    def test_wrong_call_id(self):
        with self.assertRaises(ValueError):trace([assistant(),returned('b')])
    def test_duplicate_return(self):
        with self.assertRaises(ValueError):trace([assistant(),returned(),returned()])
    def test_duplicate_call_id(self):
        with self.assertRaises(ValueError):trace([assistant(),returned(),assistant(),returned()])
    def test_missing_return(self):
        with self.assertRaises(ValueError):trace([assistant()])
    def test_interposed_turn(self):
        with self.assertRaises(ValueError):trace([assistant(),{'role':'assistant','content':'done'},returned()])
    def test_role(self):
        with self.assertRaises(ValueError):trace([{'role':'unknown'}])
    def test_user_cannot_own_call(self):
        row=assistant();row['role']='user'
        with self.assertRaises(ValueError):trace([row,returned()])
    def test_list_arguments(self):
        row=assistant();row['tool_calls'][0]['function']['arguments']='[]'
        with self.assertRaises(ValueError):trace([row,returned()])

class Replay(unittest.TestCase):
    def test_write_edit_and_hashes(self):
        rows=[assistant(),returned(),assistant('b','Edit',{'file_path':P,'old_string':'x=1','new_string':'x=2'}),returned('b')]
        raw,versions=replay_file(trace(rows),P)
        self.assertEqual(raw,b'x=2\n');self.assertEqual(versions[1]['old_string_matches'],1)
        self.assertEqual(versions[1]['before'],versions[0]['after'])
    def test_inert_code_never_executed(self):
        raw,_=replay_file(trace([assistant(args={'file_path':P,'content':'raise RuntimeError("DO_NOT_EXECUTE")\n'}),returned()]),P)
        self.assertIn(b'DO_NOT_EXECUTE',raw)
    def test_unicode_bytes_not_characters(self):
        raw,v=replay_file(trace([assistant(args={'file_path':P,'content':'x="é"\n'}),returned()]),P)
        self.assertEqual(v[0]['after']['bytes'],len(raw));self.assertGreater(len(raw),len(raw.decode()))
    def test_no_prior_write(self):
        with self.assertRaises(ValueError):replay_file(trace([assistant(name='Edit',args={'file_path':P,'old_string':'x','new_string':'y'}),returned()]),P)
    def test_no_write_for_target(self):
        with self.assertRaises(ValueError):replay_file(trace([assistant(),returned()]),P+'other')
    def test_missing_old_string(self):
        rows=[assistant(),returned(),assistant('b','Edit',{'file_path':P,'old_string':'absent','new_string':'y'}),returned('b')]
        with self.assertRaises(ValueError):replay_file(trace(rows),P)
    def test_repeated_old_string(self):
        rows=[assistant(args={'file_path':P,'content':'x=1\ny=1\n'}),returned(),assistant('b','Edit',{'file_path':P,'old_string':'=1','new_string':'=2'}),returned('b')]
        with self.assertRaises(ValueError):replay_file(trace(rows),P)
    def test_overlapping_old_string(self):
        rows=[assistant(args={'file_path':P,'content':'x="aaa"\n'}),returned(),assistant('b','Edit',{'file_path':P,'old_string':'aa','new_string':'b'}),returned('b')]
        with self.assertRaises(ValueError):replay_file(trace(rows),P)
    def test_empty_old_string(self):
        rows=[assistant(),returned(),assistant('b','Edit',{'file_path':P,'old_string':'','new_string':'b'}),returned('b')]
        with self.assertRaises(ValueError):replay_file(trace(rows),P)
    def test_replace_all_forbidden(self):
        rows=[assistant(),returned(),assistant('b','Edit',{'file_path':P,'old_string':'x','new_string':'y','replace_all':True}),returned('b')]
        with self.assertRaises(ValueError):replay_file(trace(rows),P)
    def test_ack_error(self):
        with self.assertRaises(ValueError):replay_file(trace([assistant(),returned(content='Error')]),P)
    def test_ack_wrong_path(self):
        with self.assertRaises(ValueError):replay_file(trace([assistant(),returned(content='The file ELSEWHERE has been updated successfully.')]),P)
    def test_ack_success_quoted_in_error(self):
        self.assertFalse(successful_file_ack(P,'Error quoting: The file '+P+' has been updated successfully.'))
    def test_invalid_python_syntax(self):
        with self.assertRaises(SyntaxError):replay_file(trace([assistant(args={'file_path':P,'content':'not valid syntax !!!'}),returned()]),P)
    def test_pre_edit_failure_is_not_final_version(self):
        rows=[assistant(),returned(),assistant('b','Edit',{'file_path':P,'old_string':'1','new_string':'2'}),returned('b')]
        _,v=replay_file(trace(rows),P);self.assertNotEqual(v[0]['after']['sha256'],v[1]['after']['sha256'])

class Evidence(unittest.TestCase):
    def test_failed_is_complete_traversal_not_agent_claim(self):
        x=unittest_summary('Ran 15 tests in 0.001s\n\nFAILED (failures=3)\n',1)
        self.assertEqual(x['failures'],3)
    def test_ok(self):self.assertEqual(unittest_summary('Ran 15 tests in 0.1s\nOK\n',0)['failures'],0)
    def test_ok_nonzero_reject(self):
        with self.assertRaises(ValueError):unittest_summary('Ran 15 tests in 0.1s\nOK',1)
    def test_failed_zero_reject(self):
        with self.assertRaises(ValueError):unittest_summary('Ran 15 tests in 0.1s\nFAILED (failures=3)',0)
    def test_counts_exceed_tests(self):
        with self.assertRaises(ValueError):unittest_summary('Ran 1 test in 0.1s\nFAILED (failures=3)',1)
    def test_multiple_summaries(self):
        with self.assertRaises(ValueError):unittest_summary('Ran 1 test in 0.1s\nOK\nRan 1 test in 0.1s\nOK',0)
    def test_no_summary(self):
        with self.assertRaises(ValueError):unittest_summary('All green',0)
    def test_trailing_unrecognized_status(self):
        with self.assertRaises(ValueError):unittest_summary('Ran 15 tests in 0.1s\nOK\nunknown',0)
    def test_prior_local_green_not_final(self):
        rows=[{'role':'assistant','content':'Zipper all green; pov next'},assistant(),returned()]
        self.assertFalse(terminal_claim(trace(rows))['observed'])
    def test_prospective_task_goal_not_final(self):
        rows=[assistant(name='task_create',args={'description':'pov official tests all green'}),returned(content='created')]
        self.assertFalse(terminal_claim(trace(rows))['observed'])
    def test_final_statement_is_not_semantic_success_detector(self):
        x=terminal_claim(trace([{'role':'assistant','content':'I could not finish'}]))
        self.assertTrue(x['observed']) # Semantic claim type must be coded separately.
    def test_empty_final_not_claim(self):self.assertFalse(terminal_claim(trace([{'role':'assistant','content':' '}]))['observed'])
    def test_tool_final_not_agent(self):self.assertFalse(terminal_claim(trace([assistant(),returned()]))['observed'])
    def test_wrong_shell_wrapper_reject(self):
        cmd='cd SYNTHETIC/pov && python3 -m unittest -q pov_test.py'
        rows=[assistant(name='Bash',args={'command':cmd}),returned(content="Command 'other' exited with code 0. stdout: Ran 15 tests in 0.1s\nOK")]
        with self.assertRaises(ValueError):pov_retests(trace(rows),P)
    def test_wrong_suite_not_pov_evidence(self):
        cmd='cd SYNTHETIC/pov && python3 -m unittest -q zipper_test.py'
        rows=[assistant(name='Bash',args={'command':cmd}),returned(content="Command '"+cmd+"' exited with code 0. stdout: Ran 14 tests in 0.1s\nOK")]
        self.assertEqual(pov_retests(trace(rows),P),[])
    def test_changed_pov_count_reject(self):
        cmd='cd SYNTHETIC/pov && python3 -m unittest -q pov_test.py'
        rows=[assistant(name='Bash',args={'command':cmd}),returned(content="Command '"+cmd+"' exited with code 0. stdout: Ran 14 tests in 0.1s\nOK")]
        with self.assertRaises(ValueError):pov_retests(trace(rows),P)

if __name__=='__main__':unittest.main()
