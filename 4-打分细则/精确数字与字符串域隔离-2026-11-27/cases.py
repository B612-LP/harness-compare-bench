"""Fixed finite synthetic inputs, not independent product trials."""
import random

def fixtures():
    result=[]
    def add(name,raw,expected='accept'):
        result.append({'id':'synthetic/'+name,'raw':raw,'expected':expected,'group':'synthetic'})
    vals={'int0':'0','neg_int0':'-0','int1':'1','dec1':'1.0','exp1':'1e0',
          'dec0':'0.0','neg_dec0':'-0.0','dec_a':'1.50','dec_b':'1.5',
          'tie_pos':'1000000000000000.2','tie_neg':'-1000000000000000.2',
          'bigint':'9007199254740993','exp23':'1e23','large_int':'1000000000000000000000',
          'high_exp':'1e6144','low_exp':'1e-6144','double_overflow':'1e309',
          'double_underflow':'1e-400','int1024':'1'*1024}
    for name,token in vals.items():add(name,'{"v":'+token+'}')
    for name,raw in [
      ('sentinel_number','{"v":"\\u0000NUM:1\\u0000"}'),
      ('sentinel_true','{"v":"\\u0000NUM:true\\u0000"}'),
      ('sentinel_null','{"v":"\\u0000NUM:null\\u0000"}'),
      ('sentinel_key','{"\\u0000NUM:1\\u0000":2}'),
      ('sentinel_nested','{"v":["\\u0000NUM:1\\u0000",1]}'),
      ('sentinel_empty','{"v":"\\u0000NUM:\\u0000"}'),
      ('sentinel_arbitrary','{"v":"\\u0000NUM:wat\\u0000"}'),
      ('unicode_literal','{"v":"中\u2028\u2029😀"}'),
      ('unicode_escaped','{"v":"\\u4e2d\\u2028\\u2029\\ud83d\\ude00"}'),
      ('key_order_a','{"中":1,"a":2}'),('key_order_b','{ "a":2,"中":1 }'),
      ('nfc','{"v":"é"}'),('nfd','{"v":"é"}'),
      ('special_keys','{"__proto__":1,"constructor":"x","v":false}'),
      ('depth128','{"v":'+'['*127+'0'+']'*127+'}')]:add(name,raw)
    for name,raw in [
      ('dup','{"x":1,"x":2}'),('escaped_dup','{"x":1,"\\u0078":2}'),
      ('surrogate_value','{"x":"\\ud800"}'),('surrogate_key','{"\\udfff":1}'),
      ('nan','{"v":NaN}'),('infinity','{"v":Infinity}'),
      ('syntax_plus','{"v":+1}'),('syntax_leading','{"v":01}'),
      ('raw_exp_high','{"v":1e6145}'),('raw_exp_low','{"v":1e-6145}'),
      ('zero_raw_exp_high','{"v":0e6145}'),('exp_digits','{"v":1e000001}'),
      ('normalized_high','{"v":10e6144}'),('normalized_low','{"v":0.1e-6144}'),
      ('raw1025','{"v":'+'1'*1025+'}'),('depth129','{"v":'+'['*128+'0'+']'*128+'}'),
      ('root_scalar','1'),('root_array','[]')]:add(name,raw,'reject')
    # Fixed-seed decimal pairs. Expected normalized token derives directly from construction,
    # not binary floats. No random value is claimed an independent product experiment.
    rng=random.Random(20261127)
    pairs=[]
    for i in range(200):
        coeff=''.join(str(rng.randrange(1,10) if j==0 else rng.randrange(10)) for j in range(rng.randrange(1,31)))
        if coeff[-1]=='0':coeff=coeff[:-1]+'1'
        sign='-' if rng.randrange(2) else ''
        exponent=rng.randrange(-500,501)
        a=sign+coeff+'e'+str(exponent)
        b=sign+coeff+'.0e'+str(exponent)
        one='random/%03d/a'%i;two='random/%03d/b'%i
        raw_a='{"z":[true,"\\u0000NUM:1\\u0000"],"v":'+a+'}'
        raw_b='{ "v":'+b+', "z": [true,"\\u0000NUM:1\\u0000"]}'
        expected='{"v":'+a+',"z":[true,"\\u0000NUM:1\\u0000"]}'
        for ident,raw in ((one,raw_a),(two,raw_b)):
            result.append({'id':ident,'raw':raw,'group':'random','expected':'accept','expected_canonical':expected})
        pairs.append((one,two))
    return result,pairs
