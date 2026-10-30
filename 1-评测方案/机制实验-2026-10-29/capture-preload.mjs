// Original, process-local observer. Never reads or serializes request/response headers.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
const dir=process.env.MECHANISM_CAPTURE_DIR;
const original=globalThis.fetch;
let count=0;
const sha=s=>crypto.createHash('sha256').update(s).digest('hex');
function publish(text) {
  return text.replaceAll(process.env.MECHANISM_WORKSPACE || '\u0000','<WORKSPACE>').replaceAll(process.env.HOME || '\u0000', '<HOME>');
}
function save(name, value) { fs.writeFileSync(path.join(dir,name),typeof value==='string'?value:JSON.stringify(value,null,2)); }
globalThis.fetch=async function(input,init={}) {
  const url=new URL(typeof input==='string'?input:input.url);
  if(url.protocol!=='https:' || url.host!=='api.deepseek.com' || !url.pathname.endsWith('/messages')) throw new Error('Experiment only permits official HTTPS Messages endpoint');
  if(++count>3) throw new Error('Preregistered per-run request budget exceeded');
  const id=String(count).padStart(2,'0');
  const raw=typeof init.body==='string'?init.body:'';
  // Abort before sending if unrequested user context or obvious credentials entered the body.
  const disallowed=/sk-[A-Za-z0-9_-]{16,}|Bearer\s+[A-Za-z0-9._-]{12,}|BEGIN [A-Z ]*PRIVATE KEY|MNEMON RUNTIME MEMORY SNAPSHOT|<skill_content|secret-context|vault\/context/i;
  if(disallowed.test(raw)) { save(`${id}-blocked.json`,{reason:'unexpected_private_context_or_credential_pattern',raw_sha256:sha(raw)}); throw new Error('Private context safety gate'); }
  let body;
  try { body=JSON.parse(publish(raw)); } catch { throw new Error('Expected JSON model request'); }
  save(`${id}-request.json`,body);
  if(body.model!=='deepseek-flash' || body.output_config?.effort!=='low' || body.max_tokens!==1024 || body.tools?.length!==1 || body.tools[0].name!=='fixture_output') {save(`${id}-blocked.json`,{reason:'route_effort_budget_or_tool_control_mismatch'});throw new Error('Model route control gate');}
  if(count===1) {
    const visible=Object.fromEntries(['model','system','messages','tools','thinking','output_config','max_tokens','temperature','tool_choice'].filter(k=>k in body).map(k=>[k,body[k]]));
    const baseline=path.join(path.dirname(dir),'first-request-canonical.json');
    const serialized=JSON.stringify(visible);
    if(fs.existsSync(baseline)) {
      if(JSON.stringify(JSON.parse(fs.readFileSync(baseline,'utf8')))!==serialized) {save(`${id}-blocked.json`,{reason:'first_model_visible_request_mismatch'});throw new Error('First request control gate');}
    } else fs.writeFileSync(baseline,JSON.stringify(visible,null,2));
    save('first-request-control.json',{canonical_sha256:sha(serialized),matches_baseline:true,selected_model_input_fields:Object.keys(visible)});
  }
  save(`${id}-transport.json`,{started_at:new Date().toISOString(),host:url.host,path:url.pathname,method:init.method||'GET',raw_body_sha256:sha(raw),published_body_compact_json_sha256:sha(JSON.stringify(body)),headers_recorded:false,redactions:['workspace path before HOME path'],hash_note:'raw_body is exact sent UTF-8 before path redaction; published is compact reserialization of redacted body, not the pretty file byte hash'});
  const start=performance.now();
  try {
    const response=await original(input,init);
    save(`${id}-response-meta.json`,{status:response.status,received_at:new Date().toISOString(),headers_latency_ms:performance.now()-start});
    const chunks=[];
    const tap=new TransformStream({transform(chunk,controller){chunks.push(Buffer.from(chunk));controller.enqueue(chunk);},flush(){save(`${id}-response.sse`,publish(Buffer.concat(chunks).toString('utf8')));save(`${id}-complete.json`,{finished_at:new Date().toISOString(),elapsed_ms:performance.now()-start,raw_response_sha256:sha(Buffer.concat(chunks))});}});
    return new Response(response.body.pipeThrough(tap),{status:response.status,statusText:response.statusText,headers:response.headers});
  } catch(error) {save(`${id}-fetch-error.json`,{at:new Date().toISOString(),name:error.name,message:publish(error.message)});throw error;}
};
