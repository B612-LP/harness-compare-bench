#!/usr/bin/env python3
"""Codex 复制运行器：large 夹具经 MCP stdio 提供，无 spill 策略。产品自报用量为证据上限（无请求级抓取）。"""
import argparse, datetime as dt, hashlib, json, os, pathlib, platform, re, shutil, subprocess, time, uuid

ROOT = pathlib.Path(__file__).resolve().parent
PROMPT = 'Call fixture_output exactly once. Then return only a JSON object with HEAD_KEY and TAIL_KEY containing the two observed values. Ignore checksum noise. Do not call any additional tool.'
CODEX_CONFIG = '''model = "deepseek-flash"
model_provider = "deepseek"
model_reasoning_effort = "low"
approval_policy = "never"
sandbox_mode = "danger-full-access"
web_search = "disabled"

[skills]
include_instructions = false
[skills.bundled]
enabled = false

[model_providers.deepseek]
name = "DeepSeek"
base_url = "https://api.deepseek.com"
env_key = "DEEPSEEK_API_KEY"
wire_api = "responses"

[mcp_servers.fixture]
command = "python3"
args = ["{server}"]
env = {{ "MECHANISM_SIZE" = "large", "MECHANISM_CAPTURE_DIR" = "{capture}" }}
'''

def sha(p): return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def save(p, x): p.write_text(json.dumps(x, ensure_ascii=False, indent=2) + '\n')
def now(): return dt.datetime.now(dt.timezone.utc).isoformat()
def redact(s, work): return s.replace(str(work), '<WORKSPACE>').replace(str(pathlib.Path.home()), '<HOME>')

def load_api_key():
    text = (pathlib.Path.home() / '.dsh' / '.credentials.yaml').read_text(encoding='utf-8')
    m = re.search(r'^refs:\n((?:  .*\n)+)', text, re.M)
    for line in m.group(1).splitlines():
        k, _, v = line.partition(':')
        if k.strip() == 'DEEPSEEK_API_KEY':
            return v.strip()
    raise SystemExit('credentials: DEEPSEEK_API_KEY 未找到')

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--workspace', type=pathlib.Path, required=True)
    ap.add_argument('--evidence', type=pathlib.Path, required=True)
    a = ap.parse_args()
    work = a.workspace.expanduser().resolve(); evidence = a.evidence.resolve()
    work.mkdir(parents=True, exist_ok=True); evidence.mkdir(parents=True, exist_ok=True)
    out = evidence / ('repl-codex-large-01-' + uuid.uuid4().hex[:8]); out.mkdir()
    capture = out / 'capture'; capture.mkdir()
    chome = work / 'codex-home'; (chome / 'sessions').mkdir(parents=True, exist_ok=True)
    (chome / 'config.toml').write_text(CODEX_CONFIG.format(server=str(ROOT / 'mcp-fixture-server.py'), capture=str(capture)), encoding='utf-8')
    cwd = work / 'agent-workspace'; cwd.mkdir(exist_ok=True)
    meta = {'run_id': 'repl-codex-large-01', 'start': now(), 'case_version': 'fixture-v1-mcp', 'size': 'large', 'arm': 'no-spill-policy',
            'model': {'provider': 'deepseek', 'model': 'deepseek-flash', 'reasoning_effort': 'low'},
            'product': 'Codex CLI', 'product_version': subprocess.check_output(['codex', '--version'], text=True).strip(),
            'group': 'research', 'experiment': True, 'category': 'product_run',
            'route': {'host': 'api.deepseek.com', 'provider_id': 'deepseek', 'wire_protocol': 'responses', 'endpoint': 'https://api.deepseek.com'},
            'permissions': 'sandbox_mode=danger-full-access; approval_policy=never', 'skills': 'off',
            'tool_channel': 'MCP stdio server（字节级相同夹具文本，tool-output.txt+tool-process.json 同约定）',
            'usage_evidence_grade': 'product-reported（agent.jsonl/会话 rollout），无请求级抓取',
            'workspace': '<WORKSPACE>/agent-workspace', 'codex_home': '<WORKSPACE>/codex-home'}
    save(out / 'run-meta.json', meta)
    env = dict(os.environ, CODEX_HOME=str(chome), DEEPSEEK_API_KEY=load_api_key(), RUST_LOG='warn',
               MECHANISM_CAPTURE_DIR=str(capture), MECHANISM_SIZE='large')
    start = time.monotonic()
    proc = subprocess.run(['codex', 'exec', '--json', '--skip-git-repo-check', '-C', str(cwd), '-m', 'deepseek-flash',
                           '-c', 'model_reasoning_effort="low"', '-'],
                          cwd=str(cwd), env=env, input=PROMPT, text=True, capture_output=True, timeout=300)
    (out / 'stdout.txt').write_text(redact(proc.stdout, work)); (out / 'stderr.txt').write_text(redact(proc.stderr, work))
    # 会话 rollout（完整对话与 token 事件）
    sessions = sorted((chome / 'sessions').rglob('*.jsonl'), key=lambda p: p.stat().st_mtime, reverse=True)
    if sessions:
        shutil.copy2(sessions[0], out / 'session-rollout.jsonl')
    (chome / 'config.toml').replace(out / 'codex-config.toml') if False else shutil.copy2(chome / 'config.toml', out / 'codex-config.toml')
    meta.update({'end': now(), 'duration_seconds': time.monotonic() - start, 'exit_code': proc.returncode,
                 'captured_files': sorted(p.name for p in out.iterdir())})
    save(out / 'run-meta.json', meta)
    print(json.dumps({'run': meta['run_id'], 'exit_code': proc.returncode, 'dir': redact(str(out), work)}, ensure_ascii=False))

if __name__ == '__main__':
    main()
