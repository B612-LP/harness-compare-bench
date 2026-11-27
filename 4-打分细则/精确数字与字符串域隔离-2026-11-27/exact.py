"""Bounded type-separated exact-number JSON candidate, not a JSON standard.
Pure data parsing only; no archive command/candidate/checker execution.
Root object only, root depth=0; keys and children consume one depth.
"""
from dataclasses import dataclass
import json
import re

NUM_RE = re.compile(r'-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?\Z', re.ASCII)

class Reject(ValueError):
    pass

@dataclass(frozen=True)
class Number:
    raw: str
    token: str


def number(raw):
    if len(raw) > 1024:
        raise Reject('number_length')
    if not NUM_RE.fullmatch(raw):
        raise Reject('number_syntax')
    lower = raw.lower()
    mantissa, sep, exp = lower.partition('e')
    if sep:
        digits = exp.lstrip('+-')
        if len(digits) > 5:
            raise Reject('exponent_digits')
        e = int(exp)
        if abs(e) > 6144:
            raise Reject('raw_exponent')
    else:
        e = 0
    if '.' not in raw and not sep:
        if len(raw.lstrip('-')) > 1024:
            raise Reject('coefficient_length')
        return Number(raw, raw)
    sign = '-' if mantissa.startswith('-') else ''
    ip, _, fraction = mantissa.lstrip('-').partition('.')
    digits = (ip + fraction).lstrip('0')
    if not digits:
        return Number(raw, sign + '0e0')
    coeff = digits.rstrip('0')
    e += len(digits) - len(coeff) - len(fraction)
    if len(coeff) > 1024:
        raise Reject('coefficient_length')
    if abs(e) > 6144:
        raise Reject('normalized_exponent')
    return Number(raw, sign + coeff + 'e' + str(e))


def unique(pairs):
    result = {}
    for k, v in pairs:
        if k in result:
            raise Reject('duplicate_key')
        result[k] = v
    return result


def nonfinite(_):
    raise Reject('nonfinite')


def string(s):
    try:
        s.encode('utf-8', errors='strict')
    except UnicodeEncodeError as e:
        raise Reject('lone_surrogate') from e
    return json.dumps(s, ensure_ascii=False, separators=(',', ':'))


def canonical(value, depth=0):
    if depth > 128:
        raise Reject('depth_limit')
    if type(value) is Number:
        return value.token
    if type(value) is str:
        return string(value)
    if value is None:
        return 'null'
    if type(value) is bool:
        return 'true' if value else 'false'
    if type(value) is list:
        return '[' + ','.join(canonical(x, depth + 1) for x in value) + ']'
    if type(value) is dict:
        return '{' + ','.join(canonical(k, depth + 1) + ':' + canonical(value[k], depth + 1)
                              for k in sorted(value)) + '}'
    raise Reject('unsupported_type')


def canonicalize(raw):
    if type(raw) is bytes:
        try:
            raw = raw.decode('utf-8', errors='strict')
        except UnicodeDecodeError as e:
            raise Reject('invalid_utf8') from e
    if type(raw) is not str:
        raise Reject('input_type')
    try:
        value = json.loads(raw, parse_int=number, parse_float=number,
                           parse_constant=nonfinite, object_pairs_hook=unique)
    except json.JSONDecodeError as e:
        raise Reject('invalid_json') from e
    except RecursionError as e:
        raise Reject('depth_limit') from e
    if type(value) is not dict:
        raise Reject('object_required')
    try:
        return canonical(value).encode('utf-8')
    except RecursionError as e:
        raise Reject('depth_limit') from e
