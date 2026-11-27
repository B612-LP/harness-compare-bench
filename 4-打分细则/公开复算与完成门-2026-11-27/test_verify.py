"""Bounded checks for fixed evidence and result coverage. No candidate execution."""
from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import verify


def make(*pairs):
    return ''.join(json.dumps({'id':i,'verdict':v})+'\n' for i,v in pairs).encode()


class Completion(unittest.TestCase):
    def setUp(self):
        self.expect={'one':None,'two':None}

    def test_valid_reordered(self):
        self.assertEqual(verify.confirm(self.expect,make(('two','match'),('one','match'))),2)

    def test_empty(self):
        with self.assertRaises(verify.Failure):verify.confirm({},b'')

    def test_missing(self):
        with self.assertRaises(verify.Failure):verify.confirm(self.expect,make(('one','match')))

    def test_extra(self):
        with self.assertRaises(verify.Failure):
            verify.confirm(self.expect,make(('one','match'),('two','match'),('three','match')))

    def test_duplicate_id(self):
        with self.assertRaises(verify.Failure):verify.confirm(self.expect,make(('one','match'),('one','match')))

    def test_wrong_verdict(self):
        with self.assertRaises(verify.Failure):verify.confirm(self.expect,make(('one','skip'),('two','match')))

    def test_duplicate_member(self):
        with self.assertRaises(verify.Failure):
            verify.confirm(self.expect,b'{"id":"bad","id":"one","verdict":"match"}\n'+make(('two','match')))

    def test_missing_final_lf(self):
        with self.assertRaises(verify.Failure):
            verify.confirm(self.expect,make(('one','match'),('two','match'))[:-1])

    def test_fixed_absent(self):
        with TemporaryDirectory() as d, self.assertRaises(verify.Incomplete):verify.read_pins(Path(d))

    def test_fixed_mismatch(self):
        with TemporaryDirectory() as d:
            p=Path(d)/verify.PY;p.parent.mkdir(parents=True);p.write_bytes(b'# synthetic wrong source\n')
            with self.assertRaises(verify.Failure):verify.read_pins(Path(d))

    def test_no_node_never_pass(self):
        buf=StringIO()
        with patch.object(verify,'read_pins',return_value={}), patch.object(verify.shutil,'which',return_value=None):
            with redirect_stdout(buf):self.assertEqual(verify.main(),2)
        self.assertIn('INCOMPLETE:',buf.getvalue()); self.assertNotIn('PUBLIC R1 COMPLETE',buf.getvalue())


if __name__=='__main__':unittest.main()
