#!/usr/bin/env python3
"""r1105-bare-matrix：现行五题 × 裸模型（DeepSeek V4.1-Flash）探针矩阵。

协议（PREREG l18-20261101 事项①，r1022 先例升级版）：
- /responses 单轮、无系统提示、无工具；prompt = instruction.md 原文 + 声明内联包 + 交付约定；
- arm inline-low：reasoning={"effort":"low"}（预检钉死：重思考题 reasoning_tokens 46433→18540）；
- arm inline-default：不传参数（模型默认档）——仅 bird/lcb 各 n=1 敏感性对照；
- 产物忠实抽取（不清洗内容），checker 原字节判分；
- run_dir 仓外 ~/bench-workspaces/r1105-bare-matrix/<arm>/<case>__r<rep>/；
  证据集（request/response/meta/产物/判分收据）回拷 batch dir。
- key 只从 DEEPSEEK_API_KEY 环境变量读取，绝不写入任何文件。

用法：DEEPSEEK_API_KEY=sk-... python3 bare_run_v2.py [--arms inline-low] [--reps 3] [--only <case>] [--sensitivity]
"""
from __future__ import annotations
import argparse, concurrent.futures, datetime as dt, hashlib, json, os, re, subprocess, sys, time, urllib.error, urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
BATCH = Path(__file__).resolve().parent.parent
WORK = Path.home() / "bench-workspaces" / "r1105-bare-matrix"
BASE_URL = "https://api.deepseek.com"
MODEL = "deepseek-flash"
TIMEOUT = 1800
LOW = {"reasoning": {"effort": "low"}}
FENCED = re.compile(r"```([A-Za-z0-9_+-]*)[ \t]*\n(.*?)```", re.S)

EXERCISES = ["bowling", "dominoes", "forth", "poker", "pov", "zipper"]
LCB_IDS = ["abc387_f", "abc388_f", "abc388_g", "abc389_g"]
TB_FILES = ["inputs/app/dispatch.py", "inputs/app/aircraft.py", "inputs/app/navigation.py"]

CASES = {
    "bird-ca-schools-15": {
        "inline": ["inputs/schema.sql", "inputs/questions.json", "inputs/sample_rows.json"],
        "artifacts": [{"path": "answers.jsonl", "mode": "jsonl"}],
        "copy_inputs": False,
    },
    "dabstep-payments-10": {
        "inline": ["inputs/manual.md", "inputs/questions.jsonl", "inputs/merchant_data.json",
                    "inputs/merchant_category_codes.csv", "inputs/acquirer_countries.csv"],
        "artifacts": [{"path": "answers.jsonl", "mode": "jsonl"}],
        "copy_inputs": False,
        "floor_note": "payments.csv(23.5MB)/fees.json(531KB) 超上下文未内联——预注册地板题",
    },
    "exercism-py-6": {
        "inline": ["inputs/README.md", "instruction.md"] +
                  [f"inputs/exercises/{n}/{f}" for n in EXERCISES
                   for f in (f"{n}.py", f"{n}_test.py", "README.md")],
        "artifacts": [{"path": f"inputs/exercises/{n}/{n}.py", "mode": "file-marker"}
                      for n in EXERCISES],
        "copy_inputs": True,
    },
    "lcb-recent-hard-4": {
        "inline": ["instruction.md", "inputs/problems.json"],
        "artifacts": [{"path": f"solutions/{i}.py", "mode": "file-marker"} for i in LCB_IDS],
        "copy_inputs": True,
    },
    "tb-cargo-plan": {
        "inline": ["instruction.md", "inputs/app/dispatch.py", "inputs/app/aircraft.py",
                    "inputs/app/navigation.py", "inputs/app/data/ac_flight_ids.json",
                    "inputs/app/data/airports.json", "inputs/app/data/cargo.json",
                    "inputs/app/data/flights.json"],
        "artifacts": [{"path": p, "mode": "file-marker"} for p in TB_FILES],
        "copy_inputs": True,
    },
}
DATA_FILES_FALLBACK = None  # tb data 文件名在装配时从磁盘实际清单读取


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def list_tb_data(case_dir: Path) -> list[str]:
    d = case_dir / "inputs/app/data"
    return sorted("inputs/app/data/" + p.name for p in d.glob("*") if p.is_file())


def assemble(case_dir: Path, spec: dict) -> tuple[str, list[str]]:
    inline = list(spec["inline"])
    if spec["artifacts"] and spec["artifacts"][0]["mode"] == "file-marker" and case_dir.name.startswith("tb-"):
        inline = [f for f in inline if not f.startswith("inputs/app/data/")] + list_tb_data(case_dir)
    parts = [(case_dir / "instruction.md").read_text(encoding="utf-8")]
    missing = []
    body_blocks = []
    for rel in inline:
        p = case_dir / rel
        if not p.exists():
            missing.append(rel)
            continue
        lang = "json" if rel.endswith((".json", ".jsonl")) else ("sql" if rel.endswith(".sql") else "")
        body_blocks.append(f"### FILE: {rel}\n```{lang}\n{p.read_text(encoding='utf-8', errors='replace')}\n```")
    arts = "\n".join(f"- `FILE: {a['path']}`" for a in spec["artifacts"])
    parts.append("\n\n---\n\n## 附 1：输入材料（与正式批 inputs/ 同源的逐字原文；你没有文件系统/工具/网络，一切所需信息都在上文）\n\n"
                 + "\n\n".join(body_blocks))
    parts.append("\n\n---\n\n## 附 2：交付约定（裸模型协议）\n\n"
                 f"- 必需产物清单：\n{arts}\n"
                 "- 每个必需产物：先写一行 `FILE: <相对路径>`（与清单完全一致），紧随一个围栏代码块给出完整文件内容。\n"
                 "- JSONL 产物：使用 ```jsonl 围栏，一行一个 JSON 对象。\n"
                 "- 除产物与其 FILE 标记外，不要输出其他内容。")
    prompt = "".join(parts)
    return prompt, missing


def call_api(prompt: str, key: str, arm: str) -> tuple[dict, float]:
    body = {"model": MODEL, "input": prompt}
    if arm == "inline-low":
        body.update(LOW)
    data = json.dumps(body, ensure_ascii=False).encode()
    last = None
    for attempt in range(3):  # 1 次原始 + ≤2 次重试（PREREG：5xx/限流退避）
        req = urllib.request.Request(BASE_URL + "/responses", data=data,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"}, method="POST")
        t0 = time.time()
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                return json.loads(resp.read().decode()), time.time() - t0
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode(errors="replace")[:300]
            if exc.code in (429, 500, 502, 503, 504) and attempt < 2:
                time.sleep(30 * (attempt + 1)); last = f"HTTP {exc.code}: {detail}"; continue
            raise RuntimeError(f"HTTP {exc.code}: {detail}") from exc
        except Exception as exc:
            if attempt < 2:
                time.sleep(30 * (attempt + 1)); last = str(exc)[:200]; continue
            raise RuntimeError(f"网络失败: {last}") from exc
    raise RuntimeError(last or "unreachable")


def extract_text(response: dict) -> str:
    t = response.get("output_text")
    if isinstance(t, str) and t.strip():
        return t
    parts = []
    for item in response.get("output") or []:
        if isinstance(item, dict) and item.get("type") == "message":
            for b in item.get("content") or []:
                if isinstance(b, dict) and isinstance(b.get("text"), str):
                    parts.append(b["text"])
    return "\n".join(parts)


def extract_jsonl(answer: str, run_dir: Path, spec: dict) -> dict:
    best, best_n, best_note = None, 0, ""
    spans = [(m.group(1).lower(), m.group(2)) for m in FENCED.finditer(answer)]
    for i, (lang, body) in enumerate(spans):
        if lang not in ("jsonl", "json", ""):
            continue
        s = body.strip()
        lines, n, note = None, 0, ""
        if s.startswith("["):
            try:  # JSON 数组形态：内容保真的逐元素重排（申报的归一化）
                arr = json.loads(s)
                if isinstance(arr, list):
                    lines = [json.dumps(x, ensure_ascii=False) for x in arr]
                    n, note = len(lines), f"fenced#{i} 数组→jsonl 逐元素重排"
            except Exception:
                pass
        if lines is None:
            cand = [l for l in s.splitlines() if l.strip()]
            ok = True
            for l in cand:
                try:
                    json.loads(l)
                except Exception:
                    ok = False; break
            if ok and cand:
                lines, n, note = cand, len(cand), f"fenced#{i} 逐行可解析 ×{len(cand)}"
        if lines is not None and n > best_n:
            best, best_n, best_note = lines, n, note
    out = run_dir / spec["artifacts"][0]["path"]
    if best:
        out.write_text("\n".join(best) + "\n", encoding="utf-8")
        return {spec["artifacts"][0]["path"]: best_note or "fenced jsonl"}
    out.write_text(answer, encoding="utf-8")
    return {spec["artifacts"][0]["path"]: "无可解析围栏——整段答案兜底（预期判 0）"}


def extract_file_marker(answer: str, run_dir: Path, spec: dict) -> dict:
    notes = {}
    lines = answer.splitlines()
    # 位置索引：每个 FILE: 标记后第一个围栏
    spans = [(m.start(), m.group(2)) for m in FENCED.finditer(answer)]
    used = set()
    remaining = list(spec["artifacts"])
    for i, line in enumerate(lines):
        m = re.match(r"\s*FILE:\s*(\S+)", line)
        if not m:
            continue
        rel = m.group(1).strip("`")
        target = next((a for a in remaining if a["path"] == rel), None)
        if target is None:
            continue
        pos = len("\n".join(lines[: i + 1]))
        for s, body in spans:
            if s >= pos and s not in used:
                p = run_dir / target["path"]
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(body, encoding="utf-8")
                notes[target["path"]] = f"FILE 标记精确配对（fenced@{s}）"
                used.add(s); remaining.remove(target)
                break
    if remaining:
        py = [(s, b) for s, b in spans if s not in used]
        if len(py) >= len(remaining):
            for (s, body), a in zip(py, remaining):
                p = run_dir / a["path"]
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(body, encoding="utf-8")
                notes[a["path"]] = "顺序兜底（无 FILE 标记）"
                used.add(s)
            remaining = []
    for a in remaining:
        notes[a["path"]] = "未抽取到（缺产物，交 checker 判 0）"
    return notes


def run_one(case: str, spec: dict, arm: str, rep: int, key: str) -> dict:
    case_dir = REPO / "2-用例" / case
    prompt, missing = assemble(case_dir, spec)
    if missing:
        return {"case": case, "arm": arm, "rep": rep, "error": f"内联缺文件: {missing}"}
    run_dir = WORK / arm / f"{case}__r{rep}"
    if run_dir.exists():
        return {"case": case, "arm": arm, "rep": rep, "error": f"run_dir 已存在（write-once）: {run_dir}"}
    run_dir.mkdir(parents=True)
    started = dt.datetime.now().astimezone().isoformat(timespec="seconds")
    t0 = time.time()
    try:
        response, dur = call_api(prompt, key, arm)
    except Exception as exc:
        (run_dir / "error.txt").write_text(str(exc)[:500], encoding="utf-8")
        return {"case": case, "arm": arm, "rep": rep, "error": str(exc)[:300], "status": "U"}
    (run_dir / "bare-request.json").write_text(
        json.dumps({"model": MODEL, "input": prompt, "arm": arm,
                    "reasoning_param": LOW if arm == "inline-low" else None},
                   ensure_ascii=False, indent=2), encoding="utf-8")
    (run_dir / "bare-response.json").write_text(
        json.dumps(response, ensure_ascii=False, indent=2), encoding="utf-8")
    if spec["copy_inputs"]:
        import shutil
        shutil.copytree(case_dir / "inputs", run_dir / "inputs")
    answer = extract_text(response)
    mode = spec["artifacts"][0]["mode"]
    notes = (extract_jsonl if mode == "jsonl" else extract_file_marker)(answer, run_dir, spec)
    usage = response.get("usage") or {}
    truth = json.loads((case_dir / "truth.json").read_text(encoding="utf-8"))
    checker = subprocess.run(
        [sys.executable, "-B", str(case_dir / "checker.py"), str(run_dir), "--json"],
        capture_output=True, text=True, timeout=3600)
    results = None
    try:
        results = json.loads(checker.stdout)
    except json.JSONDecodeError:
        (run_dir / "checker-stderr.txt").write_text(checker.stderr[-2000:], encoding="utf-8")
    if results is not None:
        (run_dir / "RESULTS_JSON").mkdir(exist_ok=True)
        (run_dir / "RESULTS_JSON" / "result.json").write_text(
            json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    meta = {
        "run_id": f"r1105/{arm}/{case}__r{rep}",
        "batch": "r1105-bare-matrix",
        "arm": arm,
        "case": case,
        "case_version": truth.get("checker_version"),
        "contract_revision": truth.get("contract_revision"),
        "product": "bare-deepseek-flash",
        "product_version": f"bare-protocol-v2 (tools sha256 {sha256(Path(__file__))[:12]})",
        "model": response.get("model") or MODEL,
        "tools": [],
        "permissions": {"filesystem": "none", "network": "none", "single_turn": True},
        "skills": "none（裸模型无技能注入）",
        "duration_s": round(dur, 1),
        "started_at": started,
        "evidence_grade": "original-contemporaneous-full（raw request/response + 产物 + checker 收据）",
        "integrity_verdict": "valid" if results is not None else "U-api-failed",
        "final_adjudication": None,  # 判分后回填
        "reasoning_param": "reasoning.effort=low（预检钉死）" if arm == "inline-low" else "未传参（模型默认档）",
        "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
        "prompt_bytes": len(prompt.encode()),
        "usage": usage,
        "protocol": {
            "instruction_verbatim": True,
            "inline_manifest": [f for f in spec["inline"] if (case_dir / f).exists()],
            "inline_missing": missing,
            "floor_note": spec.get("floor_note"),
            "answer_to_artifacts": notes,
            "workspace": str(run_dir),
        },
    }
    (run_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    row = {"case": case, "arm": arm, "rep": rep, "run_id": meta["run_id"],
           "reward": (results or {}).get("reward"), "weighted": (results or {}).get("weighted"),
           "reasoning_tokens": (usage.get("output_tokens_details") or {}).get("reasoning_tokens"),
           "total_tokens": usage.get("total_tokens"), "duration_s": meta["duration_s"],
           "checker_exit": checker.returncode}
    print(json.dumps(row, ensure_ascii=False), flush=True)
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arms", default="inline-low")
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--only", default=None)
    ap.add_argument("--sensitivity", action="store_true", help="附加 inline-default：bird/lcb × n=1")
    ap.add_argument("--workers", type=int, default=3)
    args = ap.parse_args()
    key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not key:
        print("缺少 DEEPSEEK_API_KEY", file=sys.stderr); sys.exit(2)
    jobs = []
    for case, spec in CASES.items():
        if args.only and case != args.only:
            continue
        for arm in args.arms.split(","):
            for rep in range(1, args.reps + 1):
                jobs.append((case, spec, arm, rep))
    if args.sensitivity:
        for case in ("bird-ca-schools-15", "lcb-recent-hard-4"):
            jobs.append((case, CASES[case], "inline-default", 1))
    print(f"jobs={len(jobs)} workers={args.workers}", flush=True)
    rows = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = [ex.submit(run_one, c, s, a, r, key) for c, s, a, r in jobs]
        for f in concurrent.futures.as_completed(futs):
            try:
                rows.append(f.result())
            except Exception as exc:
                rows.append({"error": str(exc)[:300]})
    (BATCH / "batch-results.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    ok = [r for r in rows if r.get("reward") is not None]
    print(f"\n=== 汇总：判分完成 {len(ok)}/{len(rows)} ===")
    for r in sorted(rows, key=lambda x: (x.get("arm", ""), x.get("case", ""), x.get("rep", 0))):
        print(r.get("arm"), r.get("case"), f"r{r.get('rep')}", "reward=", r.get("reward"),
              "weighted=", r.get("weighted"), r.get("error", ""))


if __name__ == "__main__":
    main()
