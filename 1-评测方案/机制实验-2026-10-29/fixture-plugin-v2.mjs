// Original experiment fixture: no network, shell, arbitrary path, or answer asset access.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
export const name = 'mechanism-fixture';
export const inject = ['tools'];
export function fixtureText(size) {
  const noise = size === 'large' ? Array.from({length: 420}, (_, i) => `noise-${String(i).padStart(4, '0')} checksum=${crypto.createHash('sha256').update(`fixture-v1-${i}`).digest('hex')}\n`).join('') : '';
  return 'OBSERVATION HEAD_KEY = AMBER-731\n' + noise + 'OBSERVATION TAIL_KEY = COBALT-492\n';
}
export function apply(ctx) {
  const out = process.env.MECHANISM_CAPTURE_DIR;
  const text = fixtureText(process.env.MECHANISM_SIZE);
  fs.writeFileSync(path.join(out, 'tool-output.txt'), text);
  fs.writeFileSync(path.join(out, 'tool-process.json'), JSON.stringify({kind:'in_process_deterministic_tool',exit_code:0,bytes:Buffer.byteLength(text),sha256:crypto.createHash('sha256').update(text).digest('hex')}, null, 2));
  ctx.tools.register({
    name:'fixture_output',
    description:'Return the current instrument observation: HEAD_KEY and TAIL_KEY with optional irrelevant checksum noise. Call once, then report both observed values.',
    parameters:{type:'object',properties:{},additionalProperties:false},
    output:{schema:{type:'string'},render:(_args,value)=>[{type:'text',text:value}]},
    execute:async()=>text
  });
  // This common restriction is explicit in the preregistration, not a native product limit.
  // Profile disables other tool plugins; wire capture independently verifies the only tool schema.
  ctx.provide('mechanismFixture', true);
}
