"""Pure memory/readonly tests. No candidate SQL, subprocess, network, or DB writes."""
import copy
import hashlib
import json
from unittest.mock import patch
import importlib.util
import math
import sqlite3
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('q62_verify', Path(__file__).with_name('verify.py'))
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)

def fixture(rows):
    # No numeric affinity: deliberately preserve INTEGER/REAL/TEXT/NULL probes.
    c = sqlite3.connect(':memory:')
    c.execute('CREATE TABLE frpm (CDSCode TEXT PRIMARY KEY, "County Name", "Charter School (Y/N)", "Free Meal Count (K-12)", "Enrollment (K-12)")')
    c.execute('CREATE TABLE schools (CDSCode TEXT PRIMARY KEY, County, Charter, School)')
    for key, free, enroll, fcharter, scharter, school, joined, fcounty, scounty in rows:
        c.execute('INSERT INTO frpm VALUES (?,?,?,?,?)', (key, fcounty, fcharter, free, enroll))
        if joined:
            c.execute('INSERT INTO schools VALUES (?,?,?,?)', (key, scounty, scharter, school))
    return c

def row(key, free, enroll, fcharter=0, scharter=0, school='present', joined=True, fcounty='Los Angeles', scounty='Los Angeles'):
    return (key, free, enroll, fcharter, scharter, school, joined, fcounty, scounty)

def run(rows):
    c = fixture(rows)
    try:
        return v.study(c)
    finally:
        c.close()

class Tests(unittest.TestCase):
    def test_canonical(self):
        result = v.verify()
        self.assertEqual([result['cells'][x]['counts']['star'] for x in ['F18%','F0.18%','J18%','J0.18%']], [201,1,201,1])
        self.assertEqual(result['branch'], 'fixed_database_unit_numeric_decomposition')

    def test_unit_and_unavailable_F_School(self):
        result = run([row('unit',1,100)])
        self.assertEqual(result['cells']['F18%']['counts']['star'],1)
        self.assertEqual(result['cells']['F0.18%']['counts']['star'],0)
        self.assertIsNone(result['cells']['F18%']['counts']['School'])
        self.assertEqual(result['cells']['F18%']['School_count_status'],'unavailable_in_F')

    def test_null_School_changes_branch(self):
        result = run([row('null-school',0,100,school=None)])
        self.assertEqual(result['cells']['J0.18%']['counts'], {'star':1,'CDSCode':1,'School':0})
        self.assertEqual(result['branch'],'table_or_count_contribution')

    def test_charter_conflict_and_interaction(self):
        result = run([row('conflict',1,100,scharter=1)])
        self.assertEqual(result['decomposition']['filter_then_unit'],[-1,0])
        self.assertEqual(result['decomposition']['unit_then_filter'],[-1,0])
        self.assertEqual(result['decomposition']['interaction'],1)
        self.assertEqual(result['branch'],'table_or_count_contribution')

    def test_missing_join_key(self):
        result=run([row('missing',0,100,joined=False)])
        self.assertEqual(len(result['differences']['0.18%']['F_only']),1)
        self.assertEqual(result['all_frpm_link_audit']['missing_school_key'],1)

    def test_equal_counts_do_not_imply_equal_rowsets(self):
        # A near-error independent of the numerical-unit conclusion: opposite charter conflicts.
        result=run([row('left',0,100,scharter=1),row('right',0,100,fcharter=1)])
        self.assertEqual(result['cells']['F0.18%']['counts']['star'],result['cells']['J0.18%']['counts']['star'])
        self.assertFalse(result['differences']['0.18%']['same_multiset'])
        self.assertEqual(result['branch'],'table_or_count_contribution')

    def test_null_zero_and_charter_unknown(self):
        result=run([row('null-free',None,100),row('null-enroll',1,None),row('zero',1,0),row('unknown-charter',0,100,fcharter=None,scharter=None)])
        self.assertEqual(result['populations']['F']['rows'],3)
        self.assertEqual(result['cells']['F0.18%']['null_value'],3)
        self.assertEqual(result['cells']['F0.18%']['counts']['star'],0)
        self.assertEqual(result['populations']['F']['null_free'],1)
        self.assertEqual(result['populations']['F']['null_enroll'],1)
        self.assertEqual(result['populations']['F']['zero_enroll'],1)

    def test_integer_real_and_text(self):
        result=run([row('integer',1,500),row('real',1.0,500.0),row('text','1','500')])
        # INTEGER and numeric TEXT can truncate in the uncast historical expression.
        self.assertEqual(result['cells']['J0.18%']['counts']['star'],0)
        self.assertEqual(result['uncast_percent']['J']['counts']['star'],2)
        self.assertFalse(result['uncast_same_as_cast']['J'])
        self.assertEqual(result['all_frpm_types'],[
            {'types':['integer','integer'],'n':1}, {'types':['real','real'],'n':1}, {'types':['text','text'],'n':1}])

    def test_strict_boundaries_independent(self):
        # Direct bound parameter probes do not infer their oracle from the four-cell output.
        c=sqlite3.connect(':memory:')
        try:
            for value, expected in [(math.nextafter(0.18,-math.inf),1),(0.18,0),(math.nextafter(0.18,math.inf),0)]:
                self.assertEqual(c.execute('SELECT ? < 0.18',(value,)).fetchone()[0],expected)
        finally:
            c.close()
        result=run([row('ratio-equality',18,100),row('percent-equality',9,5000)])
        self.assertEqual(result['cells']['J18%']['equal_boundary'],1)
        self.assertEqual(result['cells']['J0.18%']['equal_boundary'],1)
        self.assertEqual(result['cells']['J0.18%']['counts']['star'],0)

    def test_negative_and_non_numeric_are_not_cleaned(self):
        result=run([row('negative',-1,100),row('bad-text','not numeric',100)])
        # SQLite coercion itself permits these; do not silently call this a valid school model.
        self.assertEqual(result['cells']['J0.18%']['counts']['star'],2)
        self.assertEqual(result['branch'],'fixed_database_unit_numeric_decomposition')

    def test_count_result_types_sensitive_under_optimization(self):
        value={'count':1,'pass':[False,True]}
        for mutated in [{'count':1.0,'pass':[False,True]}, {'count':True,'pass':[False,True]}, {'count':1,'pass':[0,1]}]:
            self.assertFalse(v.typed_equal(value,mutated))
        self.assertTrue(v.typed_equal(value,copy.deepcopy(value)))
        # End-to-end reader perturbation: even a matching refreshed manifest cannot
        # turn float/bool data into the independently computed integer result.
        original_read = Path.read_text
        original_digest = v.digest
        for scalar in (201.0, True):
            data = json.loads(original_read(v.HERE/'results.json', encoding='utf-8'))
            data['cells']['F18%']['counts']['star'] = scalar
            text = json.dumps(data)
            manifest = json.loads(original_read(v.HERE/'SHA256.json', encoding='utf-8'))
            manifest['results.json'] = hashlib.sha256(text.encode()).hexdigest()
            def replacement_read(path, *args, **kwargs):
                if path == v.HERE/'results.json':
                    return text
                if path == v.HERE/'SHA256.json':
                    return json.dumps(manifest)
                return original_read(path, *args, **kwargs)
            def replacement_digest(path):
                return manifest['results.json'] if Path(path) == v.HERE/'results.json' else original_digest(path)
            with patch.object(Path, 'read_text', replacement_read), patch.object(v, 'digest', replacement_digest):
                with self.assertRaisesRegex(ValueError, 'typed result mismatch'):
                    v.verify()

    def test_unknown_missing_cells_never_zero(self):
        self.assertEqual(v.classify(None),'unknown')
        self.assertEqual(v.classify({'F18%':{'row_keys':[]}}),'unknown')
        self.assertEqual(v.classify({name:{'row_keys':[]} for name in ['F18%','F0.18%','J18%','J0.18%']}),'unknown')

    def test_source_guard_fails_closed(self):
        # In-memory replacement only; no source modification.
        original=v.digest
        try:
            v.digest=lambda path:'0'*64
            with self.assertRaisesRegex(ValueError,'source hash mismatch'):
                v.check_inputs()
        finally:
            v.digest=original

    def test_sql_authorizer_blocks_write(self):
        # Separately demonstrate the same authorizer policy, on disposable memory only.
        c=fixture([])
        try:
            allowed={sqlite3.SQLITE_SELECT,sqlite3.SQLITE_READ,sqlite3.SQLITE_FUNCTION,sqlite3.SQLITE_RECURSIVE}
            c.set_authorizer(lambda op,a,b,d,e:sqlite3.SQLITE_OK if op in allowed else sqlite3.SQLITE_DENY)
            with self.assertRaises(sqlite3.DatabaseError):
                c.execute('DELETE FROM frpm')
        finally:
            c.close()

if __name__=='__main__':
    unittest.main(verbosity=2)
