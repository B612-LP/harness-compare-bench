import unittest
import exact as x

class ExactTests(unittest.TestCase):
    def c(self, raw):
        return x.canonicalize(raw)

    def test_integer(self):
        for n in ('0','-0','1','-1','9007199254740993','1000000000000000000000'):
            self.assertEqual(self.c('{"v":'+n+'}'), ('{"v":'+n+'}').encode())

    def test_decimal(self):
        pairs=[('1.50','15e-1'),('1.5','15e-1'),('1.5e3','15e2'),('15e2','15e2'),
               ('0.005','5e-3'),('4.0e2','4e2'),('0.0','0e0'),('-0.0','-0e0'),
               ('1e0','1e0'),('1.0','1e0'),('1000000000000000.2','10000000000000002e-1'),
               ('-1000000000000000.2','-10000000000000002e-1')]
        for a,b in pairs:
            self.assertEqual(self.c('{"v":'+a+'}'), ('{"v":'+b+'}').encode())

    def test_types_distinct(self):
        self.assertNotEqual(self.c('{"v":1}'),self.c('{"v":1.0}'))
        self.assertNotEqual(self.c('{"v":-0}'),self.c('{"v":0}'))
        self.assertNotEqual(self.c('{"v":-0.0}'),self.c('{"v":0.0}'))

    def test_sentinel_stays_string(self):
        raw=b'{"v":"\\u0000NUM:1\\u0000"}'
        self.assertEqual(self.c(raw),raw)
        self.assertNotEqual(self.c(raw),self.c('{"v":1}'))

    def test_sentinel_key_stays_key(self):
        self.assertEqual(self.c(b'{"\\u0000NUM:1\\u0000":2}'),b'{"\\u0000NUM:1\\u0000":2}')

    def test_nested_sentinel(self):
        self.assertEqual(self.c(b'{"v":["\\u0000NUM:true\\u0000",true]}'),b'{"v":["\\u0000NUM:true\\u0000",true]}')

    def test_unicode_and_order(self):
        self.assertEqual(self.c('{"中":1,"a":"\\u4e2d\\u2028\\u2029"}'),self.c('{ "a":"中\u2028\u2029", "中":1}'))
        self.assertEqual(self.c('{"\\ud83d\\ude00":1}'),self.c('{"😀":1}'))
        self.assertNotEqual(self.c('{"v":"é"}'),self.c('{"v":"é"}'))

    def test_no_control_loss(self):
        self.assertEqual(self.c(b'{"v":"\\n\\u0000\\t"}'),b'{"v":"\\n\\u0000\\t"}')

    def test_reject_duplicate(self):
        for raw in ('{"a":1,"a":2}','{"a":1,"\\u0061":2}','{"__proto__":1,"__proto__":2}'):
            with self.assertRaisesRegex(x.Reject,'duplicate_key'):self.c(raw)

    def test_reject_nonfinite(self):
        for raw in ('{"x":NaN}','{"x":Infinity}','{"x":-Infinity}'):
            with self.assertRaisesRegex(x.Reject,'nonfinite'):self.c(raw)

    def test_finite_decimal_not_float_domain(self):
        self.assertEqual(self.c('{"v":1e309}'),b'{"v":1e309}')
        self.assertEqual(self.c('{"v":1e-400}'),b'{"v":1e-400}')

    def test_reject_bad_grammar(self):
        for raw in ('{"x":01}','{"x":+1}','{"x":1.}','{"x":1e}','{"x":"a\x00"}'):
            with self.assertRaises(x.Reject):self.c(raw)

    def test_reject_surrogate(self):
        for raw in ('{"x":"\\ud800"}','{"\\udfff":1}'):
            with self.assertRaisesRegex(x.Reject,'lone_surrogate'):self.c(raw)

    def test_reject_invalid_utf8(self):
        with self.assertRaisesRegex(x.Reject,'invalid_utf8'):self.c(b'{"v":"\xff"}')

    def test_outer_object(self):
        for raw in ('[]','1','null','true','"s"'):
            with self.assertRaisesRegex(x.Reject,'object_required'):self.c(raw)

    def test_number_bounds(self):
        self.assertEqual(x.number('1e6144').token,'1e6144')
        self.assertEqual(x.number('1e-6144').token,'1e-6144')
        self.assertEqual(x.number('1'*1024).token,'1'*1024)
        for raw in ('1e6145','0e6145','1e000001','1'*1025,'0.1e-6144'):
            with self.assertRaises(x.Reject):x.number(raw)

    def test_normalized_bounds(self):
        with self.assertRaisesRegex(x.Reject,'normalized_exponent'):x.number('10e6144')
        self.assertEqual(x.number('0e-6144').token,'0e0')

    def test_depth_boundary(self):
        okay='{"v":'+'['*127+'0'+']'*127+'}'
        bad='{"v":'+'['*128+'0'+']'*128+'}'
        self.c(okay)
        with self.assertRaisesRegex(x.Reject,'depth_limit'):self.c(bad)

    def test_no_number_method_for_text(self):
        with self.assertRaisesRegex(x.Reject,'unsupported_type'):x.canonical(1.0)

if __name__=='__main__':unittest.main()
