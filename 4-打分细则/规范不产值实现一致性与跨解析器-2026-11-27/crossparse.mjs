// R1 跨解析器比对：node v24 JSON.parse + 同规则 canon vs Python 钉定 canon SHA。
// 规则：键按 Unicode 码点排序；分隔符 , :；ensure_ascii=False（字面 UTF-8，转义规则对齐 Python ensure_ascii=False）。
import { readFileSync, writeFileSync, readdirSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { join, basename } from 'node:path';

const paydir = process.argv[2];
const corpusPath = process.argv[3] || new URL('./corpus.jsonl', import.meta.url).pathname;
const outPath = process.argv[4] || new URL('./crossparse_verdict.jsonl', import.meta.url).pathname;
const expected = new Map();
for (const line of readFileSync(corpusPath, 'utf8').split('\n')) {
  if (!line.trim()) continue;
  const o = JSON.parse(line);
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

function canonStr(v) {
  return JSON.stringify(v, (key, val) => val);
}
// 键序需要码点序：JSON.stringify 的数组键序=插入序，所以需要自建序列化器。
function ser(v) {
  if (v === null || typeof v === 'boolean') return JSON.stringify(v);
  if (typeof v === 'number') return String(v);
  if (typeof v === 'string') return JSON.stringify(v);
  if (Array.isArray(v)) return '[' + v.map(ser).join(',') + ']';
  if (typeof v === 'object') {
    const keys = Object.keys(v).sort(cmpCodepoint);
    return '{' + keys.map(k => JSON.stringify(k) + ':' + ser(v[k])).join(',') + '}';
  }
  throw new Error('unserializable: ' + typeof v);
}

const out = [];
for (const f of readdirSync(paydir).sort()) {
  if (!f.endsWith('.txt')) continue;
  const id = basename(f, '.txt').replace(/__/g, '/');
  const raw = readFileSync(join(paydir, f), 'utf8');
  let verdict, note = null;
  try {
    const v = JSON.parse(raw);
    const bytes = Buffer.from(ser(v), 'utf8');
    const sha = createHash('sha256').update(bytes).digest('hex');
    verdict = (sha === expected.get(id)) ? 'match' : 'mismatch';
    if (verdict === 'mismatch') {
      note = { node_sha: sha, py_sha: expected.get(id), node_bytes: bytes.length };
    }
  } catch (e) {
    verdict = 'parse_error';
    note = { error: String(e && e.message || e).slice(0, 120) };
  }
  out.push({ id, verdict, ...(note ? { note } : {}) });
}
writeFileSync(outPath,
  out.map(o => JSON.stringify(o)).join('\n') + '\n');
console.log('node verdicts:', out.length, 'match:', out.filter(o => o.verdict === 'match').length);
