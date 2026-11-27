// R2 跨解析器：两种模式。
//   --mode=string：R1 基线（String() 序列化，暴露浮点词型丢失）。
//   --mode=typed：v1.6 候选词型保持——递归下降解析器标注 int/float，
//     float 为有限样本候选算法（不是完整 CPython repr；A4 保留 tie 反例）。
//     本窗修订：null-prototype 对象、重复键拒绝、BigInt 整数保持；非规范冻结实现。
// 用法：node crossparse2.mjs <paydir> <corpus.jsonl> <out.jsonl> [--mode=string|typed]
import { readFileSync, writeFileSync, readdirSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { join, basename } from 'node:path';

const paydir = process.argv[2];
const corpusPath = process.argv[3];
const outPath = process.argv[4];
const mode = (process.argv.find(a => a.startsWith('--mode=')) || '--mode=typed').slice(7);

if (!['string', 'typed'].includes(mode)) throw new Error('invalid mode');
const expected = new Map();
for (const line of readFileSync(corpusPath, 'utf8').split('\n')) {
  if (!line.trim()) continue;
  const o = JSON.parse(line);
  if (expected.has(o.id)) throw new Error('duplicate expected ID');
  expected.set(o.id, o.canon_sha256);
}

function cmpCodepoint(a, b) {
  const A = Array.from(a), B = Array.from(b);
  for (let i = 0; i < Math.min(A.length, B.length); i++) {
    const ca = A[i].codePointAt(0), cb = B[i].codePointAt(0);
    if (ca !== cb) return ca - cb;
  }
  return A.length - B.length;
}

// ---- 递归下降 JSON 解析：数值标注 isFloat ----
function parseTagged(text) {
  let i = 0;
  function ws() { while (i < text.length && ' \t\n\r'.includes(text[i])) i++; }
  function value() {
    ws();
    const c = text[i];
    if (c === '{') return obj();
    if (c === '[') return arr();
    if (c === '"') return str();
    if (c === 't') { expect('true'); return { v: true, f: false }; }
    if (c === 'f') { expect('false'); return { v: false, f: false }; }
    if (c === 'n') { expect('null'); return { v: null, f: false }; }
    return num();
  }
  function expect(word) { if (text.startsWith(word, i)) i += word.length; else throw new Error('bad literal at ' + i); }
  function obj() {
    i++; const o = Object.create(null);
    ws();
    if (text[i] === '}') { i++; return { v: o, f: false }; }
    for (;;) {
      ws();
      const k = str().v;
      if (Object.hasOwn(o, k)) throw new Error('DUP_KEY');
      ws();
      if (text[i] !== ':') throw new Error('expect : at ' + i);
      i++;
      const e = value();
      o[k] = { v: e.v, f: e.f };
      ws();
      if (text[i] === ',') { i++; continue; }
      if (text[i] === '}') { i++; break; }
      throw new Error('bad obj at ' + i);
    }
    return { v: o, f: false };
  }
  function arr() {
    i++; const a = [];
    ws();
    if (text[i] === ']') { i++; return { v: a, f: false }; }
    for (;;) {
      const e = value();
      a.push({ v: e.v, f: e.f });
      ws();
      if (text[i] === ',') { i++; continue; }
      if (text[i] === ']') { i++; break; }
      throw new Error('bad arr at ' + i);
    }
    return { v: a, f: false };
  }
  function str() {
    // 直接交给 JSON.parse 保证转义语义一致
    if (text[i] !== '"') throw new Error('expect string at ' + i);
    let j = i + 1;
    while (j < text.length) {
      if (text[j] === '\\') j += 2;
      else if (text[j] === '"') break;
      else j++;
    }
    const raw = text.slice(i, j + 1);
    i = j + 1;
    return { v: JSON.parse(raw), f: false };
  }
  function num() {
    const m = /^-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?/.exec(text.slice(i));
    if (!m) throw new Error('bad num at ' + i);
    const raw = m[0];
    i += raw.length;
    const isFloat = /[.eE]/.test(raw);
    if (!isFloat) return { v: BigInt(raw), f: false };
    const v = Number(raw);
    if (!Number.isFinite(v)) throw new Error('NON_FINITE');
    return { v, f: true };
  }
  const r = value();
  ws();
  if (i !== text.length) throw new Error('trailing at ' + i);
  return r; // 保留顶层 tagged wrapper（含 float 标注）
}

// ---- Python repr 风格序列化 ----
// 最短往返表示：JS String() 的位置形式对整数值含数量级尾零（如 1.1e20 →
// '110000000000000000000'），非最短；按 toPrecision(p) 升序搜索首个往返命中。
function shortest(x) {
  for (let p = 1; p <= 17; p++) {
    const s = x.toPrecision(p);
    if (parseFloat(s) === x) return s;
  }
  return String(x);
}

// 布局按 CPython PyOS_double_to_string('r')：位置记数当 -4 <= e < 16，
// 否则指数记数（指数 ≥2 位，正指数带 '+'）；有效数字取最短往返表示。
function layoutRepr(x) {
  const s = shortest(x);
  const neg = s[0] === '-';
  const body = neg ? s.slice(1) : s;
  let digits, e;
  const em = /^(\d)(?:\.(\d+))?e([+-]\d+)$/.exec(body);
  if (em) {
    digits = em[1] + (em[2] || '');
    e = parseInt(em[3], 10);
  } else {
    const pm = /^(\d+)(?:\.(\d+))?$/.exec(body);
    if (!pm) throw new Error('bad num ' + s);
    const ip = pm[1];
    const fp = pm[2] || '';
    if (ip === '0') {
      const stripped = fp.replace(/^0+/, '');
      const k = fp.length - stripped.length;
      digits = stripped;
      e = -(k + 1);
    } else {
      digits = ip + fp;
      e = ip.length - 1;
    }
  }
  if (digits === '') return neg ? '-0.0' : '0.0';
  let out;
  if (e >= -4 && e < 16) {
    if (e >= 0) {
      const ip2 = digits.slice(0, e + 1).padEnd(e + 1, '0');
      const fp2 = digits.slice(e + 1);
      out = fp2 ? ip2 + '.' + fp2 : ip2 + '.0';
    } else {
      out = '0.' + '0'.repeat(-e - 1) + digits;
    }
  } else {
    const head = digits[0] + (digits.length > 1 ? '.' + digits.slice(1) : '');
    out = head + 'e' + (e >= 0 ? '+' : '-') + String(Math.abs(e)).padStart(2, '0');
  }
  return (neg ? '-' : '') + out;
}

function pyFloat(x) {
  if (Object.is(x, -0)) return '-0.0'; // Number.toFixed 丢 -0 符号，须特判
  if (Number.isInteger(x)) {
    // 整值浮点也要按 Python 布局：|x| >= 1e16 时 Python repr 用指数记数
    if (Math.abs(x) >= 1e16) return layoutRepr(x);
    return x.toFixed(1); // 0.0 / 1.0 / -3.0 整值浮点
  }
  return layoutRepr(x);
}

function ser(v) {
  if (v === null || typeof v === 'boolean') return JSON.stringify(v);
  if (typeof v === 'number') return String(v);
  if (typeof v === 'string') return JSON.stringify(v);
  if (Array.isArray(v)) return '[' + v.map(ser).join(',') + ']';
  if (typeof v === 'object') {
    const keys = Object.keys(v).sort(cmpCodepoint);
    return '{' + keys.map(k => JSON.stringify(k) + ':' + ser(v[k])).join(',') + '}';
  }
  throw new Error('unserializable');
}

// typed 值形如 {v, f}：f=true 的数值按 pyFloat 输出
function serT(e) {
  const v = e.v;
  if (v === null || typeof v === 'boolean') return JSON.stringify(v);
  if (typeof v === 'bigint') return v.toString();
  if (typeof v === 'number') return e.f ? pyFloat(v) : String(v);
  if (typeof v === 'string') return JSON.stringify(v);
  if (Array.isArray(v)) return '[' + v.map(serT).join(',') + ']';
  if (typeof v === 'object') {
    const keys = Object.keys(v).sort(cmpCodepoint);
    return '{' + keys.map(k => JSON.stringify(k) + ':' + serT(v[k])).join(',') + '}';
  }
  throw new Error('unserializable');
}

const out = [];
for (const f of readdirSync(paydir).sort()) {
  if (!f.endsWith('.txt')) continue;
  const id = basename(f, '.txt').replace(/__/g, '/');
  const raw = readFileSync(join(paydir, f), 'utf8');
  let verdict, note = null;
  try {
    let bytes;
    if (mode === 'string') {
      const v = JSON.parse(raw);
      bytes = Buffer.from(ser(v), 'utf8');
    } else {
      const tagged = parseTagged(raw);
      bytes = Buffer.from(serT(tagged), 'utf8');
    }
    const sha = createHash('sha256').update(bytes).digest('hex');
    verdict = (sha === expected.get(id)) ? 'match' : 'mismatch';
    if (verdict === 'mismatch') note = { node_sha: sha, py_sha: expected.get(id) };
  } catch (e) {
    verdict = 'parse_error';
    note = { error: String(e && e.message || e).slice(0, 120) };
  }
  out.push({ id, verdict, ...(note ? { note } : {}) });
}
writeFileSync(outPath, out.map(o => JSON.stringify(o)).join('\n') + '\n', {flag: 'wx'});
const match = out.filter(o => o.verdict === 'match').length;
console.log(`node[${mode}] verdicts: ${out.length} match: ${match}`);
