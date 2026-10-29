#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""l4_fixture.py — judge CLI/cache harness 共享 /tmp fixture 仓构建器。

镜像真实仓布局（parents[N] 推导全部成立），真实字节只拷 plan/contract/execution_seal/
gate/工具链三件套；用例树为 harness 自造 fake（零真值内容）；真 git 构造 D/E/HEAD。
"""
from __future__ import annotations

import datetime as dt
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
from pathlib import Path

TZ8 = dt.timezone(dt.timedelta(hours=8))
REAL_REPO = Path("/Users/b612-lp/Documents/harness-compare-bench")


def sha_file(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def jdump(p: Path, obj) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
                 encoding="utf-8")


def git(*args, cwd, env_extra=None):
    env = dict(os.environ, TZ="Asia/Shanghai")
    env.update(env_extra or {})
    return subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True, env=env)


SENTINEL_SITE = r'''
import socket, os as _os
_LOG = _os.environ.get("JUDGE_SENTINEL_LOG")
_orig_connect = socket.socket.connect
_orig_create = socket.create_connection
def _check(addr):
    try:
        host = addr[0]
    except Exception:
        host = str(addr)
    ok = isinstance(host, str) and (host in ("127.0.0.1", "::1", "localhost"))
    if _LOG:
        with open(_LOG, "a") as f:
            f.write("connect %s allowed=%s\n" % (host, ok))
    if not ok:
        raise AssertionError("JUDGE-SENTINEL: non-local connect refused: %r" % (addr,))
def _pc(self, address):
    _check(address)
    return _orig_connect(self, address)
def _pcc(address, *a, **k):
    _check(address)
    return _orig_create(address, *a, **k)
socket.socket.connect = _pc
socket.create_connection = _pcc
'''


def write_sentinel(libdir: Path) -> None:
    libdir.mkdir(parents=True, exist_ok=True)
    (libdir / "sitecustomize.py").write_text(SENTINEL_SITE, encoding="utf-8")


FAKE_CHECKER = """#!/usr/bin/env python3
# judge fixture checker: int reward + float weighted（对齐真冻结 checker dtype，
# lead 2026-10-29 checker-interface-negative 实测五题 reward=int/weighted=float）
import json, sys
from pathlib import Path
ws = Path(sys.argv[1])
if "--help" in sys.argv:
    print("usage: checker.py WS [--json]"); raise SystemExit(2)
ok = (ws / "output.txt").is_file()
guard_ok = (ws / "inputs" / "answer.txt").is_file()
earned = 3 if ok else 0
checks = ([{"id": "input_integrity", "pass": bool(guard_ok)}]
          + [{"id": "a%d" % i, "pass": bool(ok)} for i in (1, 2, 3)])
print(json.dumps({"reward": int(ok), "weighted": round(100.0 * earned / 3, 2),
                  "checks": checks, "guards_used": ["input_integrity"]}))
raise SystemExit(0 if ok else 1)
"""

FAKE_INSTRUCTION = "# FAKE case（judge harness fixture）\n把 inputs/answer.txt 复制为 output.txt。\n"


def _fake_case(cdir: Path) -> None:
    (cdir / "inputs").mkdir(parents=True, exist_ok=True)
    (cdir / "inputs" / "answer.txt").write_text("FAKE-INPUT-FOR-HARNESS\n", encoding="utf-8")
    (cdir / "instruction.md").write_text(FAKE_INSTRUCTION, encoding="utf-8")
    (cdir / "checker.py").write_text(FAKE_CHECKER, encoding="utf-8")
    (cdir / "case.json").write_text('{"timeout_source": "plan"}\n', encoding="utf-8")


STUBS = {
    "3-表现现场/l4-20261029-wb-gateway/runner/l4_wb_runner.py": "# stub (fixture)\n",
    "3-表现现场/l4-20261029-wb-gateway/driver-snapshot/workbuddy_driver.py": "# stub (fixture)\n",
    "3-表现现场/r1030-formal-a1/tools/lab.py": "# stub r1030 (fixture)\n",
    "3-表现现场/r1031-variance-n3/tools-codex/lab.py": "# stub r1031c (fixture)\n",
    "3-表现现场/r1031-variance-n3/tools-dsh/lab.py": "# stub r1031d (fixture)\n",
    "3-表现现场/l4-20261029-cli/codex/config/codex-config.toml": "# fixture config\n",
    "3-表现现场/l4-20261029-cache/config/probe-config.json": "{}\n",
}

TOOLCHAIN = ("1-评测方案/工具链/runner-schema-v2/validate_runner_meta.py",
             "1-评测方案/工具链/evidence-kit/evidence_line.py",
             "1-评测方案/工具链/evidence-kit/receipt_check.py")


def _external_required(home, codex_live_cfg, es=None):
    """seal required_external_paths() 的 fixture 镜像。

    es（已加载的 execution_seal 模块）在位时：直接调 required_external_paths() 动态枚举
    （含 dsh lib/*.js glob、package.json、codex native 钉扎），HOME 前缀重写到 fixture home。
    否则退回旧静态超集（兼容旧快照）。"""
    if es is not None:
        real_home = Path.home()
        out = {}
        for p in es.required_external_paths():
            p = Path(p).resolve()
            try:
                fp = home / p.relative_to(real_home)
            except ValueError:
                fp = p
            if not fp.is_file():
                raise RuntimeError("seal 外部件在 fixture 缺失: %s (源 %s)" % (fp, p))
            out[str(fp)] = sha_file(fp)
        for q in (home / ".dsh" / ".credentials.yaml", codex_live_cfg):
            out.setdefault(str(q.resolve()), sha_file(q))
        return out
    import shutil as _sh
    qs = [home / ".dsh" / ".credentials.yaml",
          home / ".dsh" / "AGENTS.md",
          home / ".dsh" / "profiles" / "bench-cli" / "cordis.patch.yml",
          home / ".dsh" / "profiles" / "bench-cli" / "package.json",
          codex_live_cfg,
          Path("/Applications/WorkBuddy.app/Contents/Info.plist"),
          Path("/Applications/WorkBuddy.app/Contents/Resources/app.asar")]
    # REQUIRED_EXECUTABLES：枚举 PATH 全命中（构建环境解析到 homebrew 真件；
    # 准入子进程 PATH 前置 fixture/bin 桩——manifest 必须同时覆盖两种解析）
    seen = set()
    hit = {"dsh": False, "codex": False}
    for exe in hit:
        for d in os.environ.get("PATH", "").split(os.pathsep):
            cand = Path(d) / exe
            if not cand.exists():
                continue
            hit[exe] = True
            try:
                rp = cand.resolve()
            except OSError:
                continue
            if rp.is_file() and rp not in seen:
                seen.add(rp)
                qs.append(rp)
    missing = [e for e, h in hit.items() if not h]
    if missing:
        raise RuntimeError("execution_seal REQUIRED_EXECUTABLES missing on host: " + str(missing))
    return qs


def build_fixture(snap: Path, work: Path, plan_override=None, trees=("codex", "cache")) -> dict:
    REPO = work / "repo"
    L4 = REPO / "1-评测方案" / "自动循环L4-2026-10-29"
    GATED = REPO / "1-评测方案" / "工具链" / "l4-execution"
    CASE = REPO / "2-用例"
    for d in (L4, GATED, CASE):
        d.mkdir(parents=True, exist_ok=True)
    shutil.copy2(snap / "plan.json", L4 / "plan.json")
    shutil.copy2(snap / "contract.json", L4 / "contract.json")
    shutil.copy2(snap / "execution_seal.py", L4 / "execution_seal.py")
    for name in ("PREREGISTRATION.md", "CLARIFICATION-L4-1.md", "test_execution_seal.py"):
        src = REAL_REPO / "1-评测方案/自动循环L4-2026-10-29" / name
        if src.is_file():
            shutil.copy2(src, L4 / name)
    shutil.copy2(snap / "gate.py", GATED / "gate.py")
    if "codex" in trees:
        shutil.copytree(snap / "src-codex", REPO / "3-表现现场" / "l4-20261029-cli" / "codex")
    if "dsh" in trees and (snap / "src-dsh").is_dir():
        shutil.copytree(snap / "src-dsh", REPO / "3-表现现场" / "l4-20261029-cli" / "dsh")
        STUBS.pop("3-表现现场/l4-20261029-cli/dsh/tools/lab.py", None)
    if "cache" in trees:
        shutil.copytree(snap / "src-cache", REPO / "3-表现现场" / "l4-20261029-cache")
    for rel, content in STUBS.items():
        p = REPO / rel
        if p.exists():
            continue  # 树拷贝已带真字节，桩不覆盖
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    # RUNTIME_ROOTS 全部目录必须存在（execution_seal.required_files 硬性要求）
    for d, f in (("3-表现现场/l4-20261029-cli/codex/tools", "lab.py"),
                 ("3-表现现场/l4-20261029-cli/dsh/tools", "lab.py"),
                 ("3-表现现场/l4-20261029-cache/tools", "cache_probe.py"),
                 ("3-表现现场/l4-20261029-wb-gateway/runner", "l4_wb_runner.py"),
                 ("3-表现现场/l4-20261029-wb-gateway/driver-snapshot", "workbuddy_driver.py")):
        (REPO / d).mkdir(parents=True, exist_ok=True)
        placeholder = REPO / d / f
        if not placeholder.exists():
            placeholder.write_text("# judge fixture stub\n", encoding="utf-8")
    for rel in TOOLCHAIN:
        src = REAL_REPO / rel
        dst = REPO / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst) if src.is_file() else dst.write_text("# stub\n", encoding="utf-8")
    # fake 用例（codex 两题）
    for case in ("dabstep-payments-10", "tb-cargo-plan"):
        _fake_case(CASE / case)
    # contract checker sha 对齐 fake checker（fixture 自洽；bird 也强制 fake——
    # 防 builder selftest fixture 的 stub checker 混入判分链）
    contract = json.loads((L4 / "contract.json").read_text(encoding="utf-8"))
    for case in ("dabstep-payments-10", "tb-cargo-plan", "bird-ca-schools-15",
                 "exercism-py-6", "lcb-recent-hard-4"):
        cdir = CASE / case
        if not cdir.is_dir():
            _fake_case(cdir)
        contract["checker_sha256"][case] = sha_file(cdir / "checker.py")
        files_map = {}
        for q in sorted(cdir.rglob("*")):
            if q.is_file():
                rel = str(q.relative_to(cdir))
                files_map[rel] = sha_file(q)
        contract["case_snapshots"][case]["files"] = files_map
        contract["case_snapshots"][case]["checker.py"] = sha_file(cdir / "checker.py")
        contract["denominators"][case] = 3  # fake checker：q1–q3 三计分项
    # plan 覆写（超时负例等）：contract.plan_sha256 同步
    if plan_override is not None:
        (L4 / "plan.json").write_text(
            json.dumps(plan_override, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    plan_bytes = (L4 / "plan.json").read_bytes()
    contract["plan_sha256"] = hashlib.sha256(plan_bytes).hexdigest()
    (L4 / "contract.json").write_text(
        json.dumps(contract, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    # fake HOME + 假凭据 + bin/
    home = Path(os.path.realpath(work)) / "home"  # canonical：/tmp→/private/tmp 对齐 gate Path.home()
    (home / ".dsh").mkdir(parents=True, exist_ok=True)
    (home / ".dsh" / ".credentials.yaml").write_text(
        "refs:\n  DEEPSEEK_API_KEY: FAKE-JUDGE-HARNESS-NOT-A-KEY\n", encoding="utf-8")
    # 新 gate 必需外部配置闭包（~/.dsh 三件）——fixture 桩件
    (home / ".dsh" / "AGENTS.md").write_text(
        "# fixture AGENTS.md (judge harness stub)\n", encoding="utf-8")
    prof = home / ".dsh" / "profiles" / "bench-cli"
    prof.mkdir(parents=True, exist_ok=True)
    (prof / "cordis.patch.yml").write_text("# fixture cordis.patch.yml stub\n", encoding="utf-8")
    (prof / "package.json").write_text("{}\n", encoding="utf-8")
    bin_ = work / "bin"
    bin_.mkdir(parents=True, exist_ok=True)
    harness = Path(__file__).resolve().parent
    if "codex" in trees:
        shutil.copy2(harness / "fake_codex.py", bin_ / "codex")
        os.chmod(bin_ / "codex", 0o755)
    # git D/E/HEAD
    git("init", "-q", "-b", "main", cwd=REPO)
    git("config", "user.email", "judge-fixture@invalid", cwd=REPO)
    git("config", "user.name", "judge-fixture", cwd=REPO)
    t_now = dt.datetime.now(TZ8)
    tD = (t_now - dt.timedelta(minutes=20)).isoformat(timespec="seconds")
    tE = (t_now - dt.timedelta(minutes=10)).isoformat(timespec="seconds")
    denv = lambda t: {"GIT_AUTHOR_DATE": t, "GIT_COMMITTER_DATE": t}
    spec = importlib.util.spec_from_file_location("fx_seal", L4 / "execution_seal.py")
    es = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(es)
    required = sorted(es.required_files())
    codex_live_cfg = (home / "bench-workspaces" / "l4-20261029-cli" / "codex"
                      / "_codex-home" / "config.toml")
    sealed_cfg = snap / "src-codex" / "config" / "codex-config.toml"
    if not codex_live_cfg.is_file():
        codex_live_cfg.parent.mkdir(parents=True, exist_ok=True)
        if sealed_cfg.is_file():
            shutil.copyfile(sealed_cfg, codex_live_cfg)
        else:
            codex_live_cfg.write_text("# fixture codex config (judge harness)\n",
                                      encoding="utf-8")
    manifest = {"schema_version": 1, "design_commit": None, "generated_at": tD,
                "files": {rel: sha_file(REPO / rel) for rel in required},
                "external_files": dict(_external_required(home, codex_live_cfg, es)),
                "live_doc_drift": []}
    git("add", "-A", cwd=REPO)
    git("commit", "-q", "-m", "D fixture", cwd=REPO, env_extra=denv(tD))
    D = git("rev-parse", "HEAD", cwd=REPO).stdout.strip()
    manifest["design_commit"] = D
    (L4 / "execution-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    git("add", "-A", cwd=REPO)
    git("commit", "-q", "-m", "E fixture", cwd=REPO, env_extra=denv(tE))
    E = git("rev-parse", "HEAD", cwd=REPO).stdout.strip()
    manifest_sha = sha_file(L4 / "execution-manifest.json")
    (REPO / "HEADNOTE.txt").write_text("head after E\n", encoding="utf-8")
    git("add", "-A", cwd=REPO)
    git("commit", "-q", "-m", "post-E", cwd=REPO, env_extra=denv(tE))

    def binding(released: bool) -> Path:
        b = {"schema_version": 1, "design_commit": D,
             "preregistration_commit": E, "execution_seal_commit": E,
             "registered_at": tE, "execution_manifest_sha256": manifest_sha,
             "plan_sha256": sha_file(L4 / "plan.json"),
             "contract_sha256": sha_file(L4 / "contract.json"),
             "released_for_model_calls": bool(released),
             "generated_at": tE, "live_doc_drift": []}
        p = L4 / "runtime-binding.json"
        jdump(p, b)
        return p

    return {"REPO": REPO, "L4": L4, "CASE": CASE, "home": home, "bin": bin_,
            "CODEX": REPO / "3-表现现场" / "l4-20261029-cli" / "codex",
            "CACHE": REPO / "3-表现现场" / "l4-20261029-cache",
            "D": D, "E": E, "tD": tD, "tE": tE, "binding": binding,
            "sentinel_lib": work / "sentinel-lib"}


def harness_env(fx, log_name="sentinel.log", extra=None) -> dict:
    write_sentinel(fx["sentinel_lib"])
    log = fx["sentinel_lib"].parent / log_name
    log.touch()
    env = dict(os.environ, HOME=str(fx["home"]), PATH=str(fx["bin"]) + os.pathsep + os.environ["PATH"],
               PYTHONPATH=str(fx["sentinel_lib"]), JUDGE_SENTINEL_LOG=str(log),
               PYTHONDONTWRITEBYTECODE="1")
    env.update(extra or {})
    return env
