import contextlib
import io
import subprocess
import unittest
from unittest import mock
import verify as v

class FrameTests(unittest.TestCase):
    def test_nonempty_exact_reordered(self):
        got=v.coverage([{'id':'a'},{'id':'b'}],[{'id':'b','verdict':'reject'},{'id':'a','verdict':'accept','canonical':'{}'}])
        self.assertEqual(set(got),{'a','b'})

    def test_empty(self):
        with self.assertRaises(ValueError):v.coverage([],[])

    def test_bad_expected_id(self):
        for ident in ('',None,4):
            with self.assertRaises(ValueError):v.coverage([{'id':ident}],[{'id':ident,'verdict':'reject'}])

    def test_duplicate_expected(self):
        with self.assertRaises(ValueError):v.coverage([{'id':'a'},{'id':'a'}],[])

    def test_missing(self):
        with self.assertRaises(ValueError):v.coverage([{'id':'a'}],[])

    def test_extra(self):
        with self.assertRaises(ValueError):v.coverage([{'id':'a'}],[{'id':'a','verdict':'reject'},{'id':'b','verdict':'reject'}])

    def test_duplicate_result(self):
        with self.assertRaises(ValueError):v.coverage([{'id':'a'}],[{'id':'a','verdict':'reject'}]*2)

    def test_invalid_result_id(self):
        for ident in ('',None,4):
            with self.assertRaises(ValueError):v.coverage([{'id':'a'}],[{'id':ident,'verdict':'reject'}])

    def test_bad_verdict(self):
        with self.assertRaises(ValueError):v.coverage([{'id':'a'}],[{'id':'a','verdict':'pass'}])

    def test_missing_canonical(self):
        with self.assertRaises(ValueError):v.coverage([{'id':'a'}],[{'id':'a','verdict':'accept'}])

    def test_node_absence_is_not_pass(self):
        output=io.StringIO()
        with mock.patch.object(v.shutil,'which',return_value=None),contextlib.redirect_stdout(output):
            self.assertEqual(v.main(),2)
        self.assertIn('INCOMPLETE',output.getvalue())
        self.assertNotIn('FINITE EXPECTATIONS MET',output.getvalue())

    def test_wrong_source_pin(self):
        with mock.patch.object(v,'PINS',{'exact.py':'0'*64}):
            with self.assertRaisesRegex(ValueError,'pin mismatch'):v.main()

    def test_synthetic_count_loss_is_not_pass(self):
        with mock.patch.object(v,'fixtures',return_value=([],[])):
            with self.assertRaisesRegex(ValueError,'coverage count'):v.main()

    def test_empty_fake_node_cannot_pass(self):
        def fake(args,**kwargs):
            v.Path(args[3]).write_text('')
            return subprocess.CompletedProcess(args,0,'','')
        with mock.patch.object(v.shutil,'which',return_value='fake-node'),mock.patch.object(v.subprocess,'run',side_effect=fake):
            with self.assertRaisesRegex(ValueError,'missing/extra'):v.main()

    def test_timeout_is_not_pass(self):
        with mock.patch.object(v.shutil,'which',return_value='fake-node'),mock.patch.object(v.subprocess,'run',side_effect=subprocess.TimeoutExpired('fake-node',60)):
            with self.assertRaises(subprocess.TimeoutExpired):v.main()

if __name__=='__main__':unittest.main()
