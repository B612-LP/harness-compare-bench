// Bounded exact-decimal candidate; Node >=18, stdlib only.
// Numeric tokens are class instances, never sentinel strings or binary floats.
// This is NOT CPython repr, a general JSON standard, or a frozen profile.
import { readFileSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
import { TextDecoder } from 'node:util';

export const LIMITS = Object.freeze({ rawNumberChars: 1024, rawExponentDigits: 5,
  exponentAbs: 6144, coefficientDigits: 1024, depth: 128 });
export class CanonicalizationError extends Error {
  constructor(reason) { super(reason); this.name = 'CanonicalizationError'; this.reason = reason; }
}
const fail = reason => { throw new CanonicalizationError(reason); };
class ExactNumber {
  constructor(token) { this.token = token; Object.freeze(this); }
}
function unicodeScalarString(s) {
  for (let i = 0; i < s.length; i++) {
    const c = s.charCodeAt(i);
    if (c >= 0xd800 && c <= 0xdbff) {
      const next = s.charCodeAt(++i);
      if (!(next >= 0xdc00 && next <= 0xdfff)) fail('LONE_SURROGATE');
    } else if (c >= 0xdc00 && c <= 0xdfff) fail('LONE_SURROGATE');
  }
  return s;
}
function strictText(raw) {
  if (typeof raw === 'string') return raw;
  if (raw instanceof Uint8Array) {
    try {
      // Preserve BOM so JSON grammar rejects it instead of silently stripping it.
      return new TextDecoder('utf-8', { fatal: true, ignoreBOM: true }).decode(raw);
    } catch { fail('INVALID_UTF8'); }
  }
  fail('RAW_TYPE');
}
function exactNumber(raw) {
  if (raw.length > LIMITS.rawNumberChars) fail('NUMBER_LENGTH');
  const m = /^(-?)(0|[1-9][0-9]*)(?:\.([0-9]+))?(?:[eE]([+-]?)([0-9]+))?$/.exec(raw);
  if (!m) fail('NUMBER_SYNTAX');
  const [, sign, integer, fraction, exponentSign, exponentDigits] = m;
  let exponent = 0;
  if (exponentDigits !== undefined) {
    // Count all raw exponent digits, including leading zeros (PREREG literal limit).
    if (exponentDigits.length > LIMITS.rawExponentDigits) fail('RAW_EXPONENT_DIGITS');
    exponent = Number((exponentSign || '') + exponentDigits); // bounded integer only
    if (Math.abs(exponent) > LIMITS.exponentAbs) fail('RAW_EXPONENT_BOUND');
  }
  if (fraction === undefined && exponentDigits === undefined) {
    if (integer.length > LIMITS.coefficientDigits) fail('COEFFICIENT_BOUND');
    return new ExactNumber(raw); // Integer -0 is intentionally distinct from 0.
  }
  const digits = integer + (fraction || '');
  const nonzero = digits.replace(/^0+/, '');
  if (!nonzero) return new ExactNumber(sign + '0e0');
  const coefficient = nonzero.replace(/0+$/, '');
  exponent += nonzero.length - coefficient.length - (fraction || '').length;
  if (coefficient.length > LIMITS.coefficientDigits) fail('COEFFICIENT_BOUND');
  if (Math.abs(exponent) > LIMITS.exponentAbs) fail('NORMALIZED_EXPONENT_BOUND');
  return new ExactNumber(sign + coefficient + 'e' + String(exponent));
}
function parseDocument(raw) {
  const text = strictText(raw);
  let i = 0;
  function ws() { while (i < text.length && ' \t\r\n'.includes(text[i])) i++; }
  function string() {
    if (text[i] !== '"') fail('STRING_EXPECTED');
    const start = i++;
    let closed = false;
    while (i < text.length) {
      if (text[i] === '\\') i += 2;
      else if (text[i++] === '"') { closed = true; break; }
    }
    if (!closed) fail('STRING_SYNTAX');
    let s;
    try { s = JSON.parse(text.slice(start, i)); } catch { fail('STRING_SYNTAX'); }
    return unicodeScalarString(s);
  }
  function value(depth) {
    if (depth > LIMITS.depth) fail('DEPTH_BOUND');
    ws();
    const c = text[i];
    if (c === '{') return object(depth);
    if (c === '[') return array(depth);
    if (c === '"') return string();
    for (const [literal, v] of [['true', true], ['false', false], ['null', null]]) {
      if (text.startsWith(literal, i)) { i += literal.length; return v; }
    }
    if (text.startsWith('NaN', i) || text.startsWith('Infinity', i) || text.startsWith('-Infinity', i)) fail('NON_FINITE');
    const m = /^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?/.exec(text.slice(i));
    if (!m) fail('VALUE_SYNTAX');
    i += m[0].length;
    return exactNumber(m[0]);
  }
  function object(depth) {
    i++; ws();
    const out = new Map();
    if (text[i] === '}') { i++; return out; }
    for (;;) {
      ws();
      if (depth + 1 > LIMITS.depth) fail('DEPTH_BOUND'); // keys are depth+1 too
      const key = string();
      if (out.has(key)) fail('DUP_KEY');
      ws(); if (text[i++] !== ':') fail('COLON_EXPECTED');
      out.set(key, value(depth + 1));
      ws();
      if (text[i] === '}') { i++; return out; }
      if (text[i++] !== ',') fail('OBJECT_SYNTAX');
    }
  }
  function array(depth) {
    i++; ws();
    const out = [];
    if (text[i] === ']') { i++; return out; }
    for (;;) {
      out.push(value(depth + 1)); ws();
      if (text[i] === ']') { i++; return out; }
      if (text[i++] !== ',') fail('ARRAY_SYNTAX');
    }
  }
  const root = value(0); ws();
  if (i !== text.length) fail('TRAILING_DATA');
  if (!(root instanceof Map)) fail('OBJECT_REQUIRED');
  return root;
}
function compareCodepoint(a, b) {
  const aa = Array.from(a), bb = Array.from(b);
  for (let i = 0; i < Math.min(aa.length, bb.length); i++) {
    const d = aa[i].codePointAt(0) - bb[i].codePointAt(0);
    if (d) return d;
  }
  return aa.length - bb.length;
}
function serialize(v) {
  if (v instanceof ExactNumber) return v.token;
  if (v instanceof Map) return '{' + [...v.keys()].sort(compareCodepoint)
    .map(k => JSON.stringify(k) + ':' + serialize(v.get(k))).join(',') + '}';
  if (Array.isArray(v)) return '[' + v.map(serialize).join(',') + ']';
  if (v === null || typeof v === 'boolean' || typeof v === 'string') return JSON.stringify(v);
  fail('INTERNAL_TYPE');
}
/** Return canonical JSON text; throws CanonicalizationError on unsupported payload.
 * Object root only, root depth=0; children AND keys add one. No Unicode normalization.
 * Decimal numbers use exact signed coefficient e exponent; integers retain lexical -0.
 * Uint8Array/Buffer input strictly validates UTF-8; string input validates parsed scalars.
 */
export function canonicalize(raw) { return serialize(parseDocument(raw)); }

export function runCLI(inputPath, outputPath) {
  const text = strictText(readFileSync(inputPath));
  const lines = text.split('\n');
  if (lines[lines.length - 1] === '') lines.pop();
  if (!lines.length) fail('EMPTY_TRANSPORT');
  const seen = new Set(), envelopes = [];
  for (const line of lines) {
    if (!line.trim()) fail('BLANK_TRANSPORT_LINE');
    const e = parseDocument(line);
    if (e.size !== 2 || !e.has('id') || !e.has('raw')) fail('TRANSPORT_FIELDS');
    const id = e.get('id'), raw = e.get('raw');
    if (typeof id !== 'string' || !id.trim()) fail('TRANSPORT_ID');
    if (typeof raw !== 'string') fail('TRANSPORT_RAW');
    if (seen.has(id)) fail('DUP_TRANSPORT_ID');
    seen.add(id); envelopes.push({ id, raw });
  }
  const records = envelopes.map(({ id, raw }) => {
    try { return { id, verdict: 'accept', canonical: canonicalize(raw) }; }
    catch (e) {
      if (!(e instanceof CanonicalizationError)) throw e;
      return { id, verdict: 'reject', reason: e.reason };
    }
  });
  writeFileSync(outputPath, records.map(r => JSON.stringify(r)).join('\n') + '\n', { flag: 'wx' });
  return records; // A record's reject is not an overall payload-correctness claim.
}
if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  try {
    if (process.argv.length !== 4) fail('USAGE: node exact.mjs <input.jsonl> <out.jsonl>');
    const rows = runCLI(process.argv[2], process.argv[3]);
    console.log(JSON.stringify({ rows: rows.length,
      accept: rows.filter(r => r.verdict === 'accept').length,
      reject: rows.filter(r => r.verdict === 'reject').length }));
  } catch (e) {
    console.error(e instanceof CanonicalizationError ? e.reason : String(e.message || e));
    process.exitCode = 2;
  }
}
