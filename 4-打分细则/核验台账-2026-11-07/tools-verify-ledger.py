#!/usr/bin/env python3
"""tools-verify-ledger.py — 公开核验台账确定性生成器（2026-11-07 新建）。

落实老师 Week3 第4条：「为公开与私档材料建立第三方核验记录：文件清单、哈希、核验人、
核验时间、可公开字段与不能公开字段分开列，尤其解释当前公开 verify 无法复核的历史代际。」

输出：与本脚本同目录的 ledger.json。确定性：ledger 只依赖
  1) 生成时点 git HEAD（inventory 用 `git ls-tree -r -l HEAD` + blob 内容 sha256，
     与工作树无关）；2) 关键核验记录的入仓提交日期（`git log -1 --format=%cs`）；
  3) 可选私档 sidecar JSON 的字节内容。
同一 HEAD + 同一 sidecar 重跑 = 逐字节相同；无 now() 时间戳。
复算方法：克隆/复制本仓库 → `git checkout --detach <generation.head>` → 用同 sidecar 重跑本生成器（`git archive` 解包目录不是 Git 仓库，不可用）。

台账目录自身（本文件、README.md、ledger.json）从 inventory 排除（自引用不可能），
见 generation.excluded_paths；台账未覆盖的后续改动由下一次生成/发布护栏覆盖。

诚实边界：核验人=机器工具与 AI Agent（作者角色/非作者独审角色），无独立真人第三方
核验（用户 2026-11-04 取消该要求）。台账只登记「记录存在+哈希+角色+时点」，
不评判任何记录内容的语义正确性。

用法：
  python3 tools-verify-ledger.py [--sidecar <私档sidecar.json>] [--receipt <私档收据路径>]
  （收据 write-once，落在私档；公开仓工作树只写 ledger.json 一个文件。）
"""
import argparse
import hashlib
import re
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent          # .../4-打分细则/核验台账-20261107/
ROOT = HERE.parent.parent                        # 公开仓根
SELF_DIR_REL = "4-打分细则/核验台账-2026-11-07"

# 关键公开核验记录（curated）：(covers, record_path, role)
# role 词表见 README/ledger role_vocabulary；路径相对仓库根，均为 tracked 公开文件/目录。
PUBLIC_RECORDS = [
    ("6-周报 周报连续性+首期字节+补充材料53指纹（--through 2026-10-24）", "6-周报/归档核对-2026-10-24.json", "tools:verify_archive.py"),
    ("6-周报 周报连续性+首期字节+补充材料53指纹（--through 2026-10-31）", "6-周报/归档核对-2026-10-31.json", "tools:verify_archive.py"),
    ("6-周报 周报连续性+首期字节+补充材料53指纹（--through 2026-11-07）", "6-周报/归档核对-2026-11-07.json", "tools:verify_archive.py"),
    ("判卷器可信度 κ 协议+测项池60条（direct17/拆槽21/构造22）", "4-打分细则/判卷器可信度协议-2026-11-03/README.md", "agent:author + tools:tools-judge-agreement.py v1.1(T1–T8)"),
    ("LCB可见性/DAB q49金额率/Cargo航向 三判据边界复核", "4-打分细则/判据边界复核-2026-11-05/audit.json", "agent:author + tools:该目录 verify.py"),
    ("判卷回归 全量回放", "4-打分细则/判卷回归/replay-all-results.json", "tools:判卷回归运行器"),
    ("判卷审计-2026-10-24（execution/lcb/numeric 冻结与验收）", "4-打分细则/判卷审计-2026-10-24/execution/final-validation.json", "tools:该目录运行器"),
    ("判卷审计-2026-10-26（bird-q26并入+lcb389g oracle+mutation 负例）", "4-打分细则/判卷审计-2026-10-26/mutation-negatives/results.json", "tools:该目录运行器"),
    ("判卷审计-2026-10-27（checker收紧B组+上游第三方样本）", "4-打分细则/判卷审计-2026-10-27/checker-tightening-B2-B8-B12-13-14/replay-results.json", "tools:该目录运行器"),
    ("可信冻结 v1（2026-10-29）freeze.lock", "4-打分细则/可信冻结-2026-10-29/freeze.lock.json", "tools:冻结运行器"),
    ("可信冻结 v2", "4-打分细则/可信冻结-2026-10-29-v2/freeze.lock.json", "tools:冻结运行器"),
    ("可信冻结 v3", "4-打分细则/可信冻结-2026-10-29-v3/freeze.lock.json", "tools:冻结运行器"),
    ("可信冻结 v4", "4-打分细则/可信冻结-2026-10-29-v4/freeze.lock.json", "tools:冻结运行器"),
    ("可信冻结 v5", "4-打分细则/可信冻结-2026-10-29-v5/freeze.lock.json", "tools:冻结运行器"),
    ("可信冻结 v6", "4-打分细则/可信冻结-2026-10-29-v6/freeze.lock.json", "tools:冻结运行器"),
    ("可信冻结 wb-v1（2026-10-31）", "4-打分细则/可信冻结-20261031-wb-v1/freeze.lock.json", "tools:冻结运行器"),
    ("可信冻结 wb-v2（2026-10-31）", "4-打分细则/可信冻结-20261031-wb-v2/freeze.lock.json", "tools:冻结运行器"),
    ("盲态可判性审计（盲态协议+合成κ）", "4-打分细则/盲态可判性审计-2026-11-04/manifest.json", "agent:author + tools:盲态审计运行器"),
    ("公开材料独立复核（L25 非作者评审：criteria+独立抽取+复核摘要）", "5-评测报告/独立复核-2026-10-29/README.md", "agent:non-author-review"),
    ("L4 独立验收（realdata 重算+gate 准入）", "5-评测报告/L4独立验收-2026-10-29/realdata-cache/pairs-recomputed.json", "agent:non-author-review"),
    ("L4 首请求前评审（adversarial/live-drift 序列，含失败留档）", "5-评测报告/L4首请求前评审-2026-10-29/gate-adversarial-v4.json", "agent:non-author-review"),
    ("L5 独立复核（r4 验收/历史 reproduced 收据）", "5-评测报告/L5独立复核-2026-10-30/README.md", "agent:non-author-review"),
    ("L5 独立验收（canonical gate+逐槽发射检查+U1 封印内容检查）", "5-评测报告/L5独立验收-2026-10-30/canonical-gate-admission.json", "agent:non-author-review"),
    ("L6 独立复核（含 公开核验范围与限制.md 声明）", "5-评测报告/L6独立复核-2026-10-30/公开核验范围与限制.md", "agent:non-author-review"),
    ("L5 判卷修订（gate-v2 验收+历史重算收据）", "5-评测报告/L5判卷修订-2026-10-30/gate-v2-acceptance-receipt.json", "tools:gate-v2 运行器"),
    ("L6 判卷修订（l6-meta 重算+l6c 自指历史回放；VOIDED 序列如实保留）", "5-评测报告/L6判卷修订-2026-10-30/l6-meta-recompute-receipt.json", "tools:重算运行器"),
    ("验证器 L7 修订复算（r1–r6 VOIDED 如实保留+终版收据）", "5-评测报告/验证器修订证据-2026-10-30/修订与复算/l7-gate-recompute-receipt.json", "tools:重算运行器"),
    ("正式 25 行来源复核（402 来源逐行机器复核）", "5-评测报告/正式行复核-2026-11-05/README.md", "agent:author + tools:verify.py"),
    ("现场复核加固（source-pins 钉定）", "5-评测报告/现场复核加固-2026-11-05/README.md", "agent:author + tools:verify.py"),
    ("证据口径 lineage：30尝试→5替代→25正式 机器账", "5-评测报告/证据口径-2026-11-03/source-ledger.public-derived.json", "agent:author"),
    ("证据口径 access-calibration：公开/私档清单 schema+第三方交接件", "5-评测报告/证据口径-2026-11-03/access-calibration/manifest.json", "agent:author"),
    ("发布清单（2026-11-04 口径）", "5-评测报告/证据口径-2026-11-04/publication-manifest.json", "agent:author"),
    ("未知三件套登记 r1–r10（未知≠失败口径）", "5-评测报告/未知登记-2026-11-05-r10.json", "agent:author"),
    ("补充材料 2026-10-24（独立验收+解压复跑验收+附件清单）", "5-评测报告/补充材料/2026-10-24/解压复跑验收.json", "tools:验收运行器"),
    ("历史封印复核限制 公开声明", "1-评测方案/历史封印复核限制.md", "agent:author"),
    ("工具链 evidence-kit/l4/runner-schema 自检收据（含 VOIDED 误报如实保留）", "1-评测方案/工具链/runner-schema-v2/cli-regression-receipt-l3-fixd1-20261029.json", "tools:工具链自检"),
    ("表现现场 l4 探针/自检收据", "3-表现现场/l4-20261029-cache/probe-receipt.json", "tools:现场探针"),
]

# 公开 verify 无法复核项（curated，全部有公开文档锚点）
NOT_PUBLIC = [
    ("历史代际报告 v1.1–v1.8 与早期判卷器代际的语义正确性", "公开仓保留版本序列文件本体（哈希在本台账 inventory），但无逐代语义复算的公开收据；verify_archive.py 只核周报连续性/首期字节/补充材料指纹。", "5-评测报告/L6独立复核-2026-10-30/公开核验范围与限制.md；5-评测报告/竞品评测报告-v1.9.md §4.5"),
    ("模型批次原始收据（发射、判卷输出原件、裸模型探针）", "私档封存（隐私与封印链）；公开仅有派生摘录（public-derived 标注件）。", "5-评测报告/证据口径-2026-11-03/access-calibration/；1-评测方案/历史封印复核限制.md"),
    ("2026-10-30 发布前完整私档封印链", "公开发布收据为私档文件（本台账 private 节按 sha+角色+时点登记，路径不入公开文档）。", "5-评测报告/竞品评测报告-v1.9.md §4.5"),
    ("桌面产品（WB/豆包）原生会话原件", "公开 3-表现现场 为导出/脱敏件；原生轨迹在用户设备私域，导出与原件的一致性核对记录在私档。", "5-评测报告/证据口径-2026-11-03/source-ledger.public-derived.json"),
    ("发射锁（judge-agreement 发射阶段）", "协议与工具公开（T1–T8 自测通过），真实 judge 调用未放行、无记录。", "4-打分细则/判卷器可信度协议-2026-11-03/README.md"),
]

FIELDS_SPLIT = {
    "public": [
        "inventory: 每个tracked文件的路径 p / 内容sha256 s / git blob sha1 b / 字节数 z",
        "verification_index.public: covers / record(公开路径) / role / verified_at(入仓提交日期)",
        "not_publicly_recheckable: item / reason / documented_at(公开文档锚点)",
    ],
    "non_public": [
        "私档收据的文件路径与目录结构（ledger 与公开 README 均不出现，只登记 sha256/角色/时点）",
        "私档原件内容（模型原始响应、判卷输出原件、封印链哈希链细节、内部工具绝对路径）",
        "私档 sidecar 本体（保存在仓外私档目录）",
    ],
    "note": "两节字段互斥；private 节每条只保留 covers/record_sha256/role/verified_at 四个字段。",
}

ROLE_VOCAB = {
    "tools:<工具名>": "机器工具产出的收据/清单（确定性可复算）",
    "agent:author": "作者 Agent（lead）产出的记录与文档",
    "agent:non-author-review": "非作者 Agent 独立评审/验收（独立复核、独立验收、独审目录）",
    "agent:author + tools:<工具名>": "作者 Agent 用机器工具生成（工具名见后缀）",
    "说明": "全部核验人为 AI Agent 与机器工具；无独立真人第三方核验（用户 2026-11-04 取消该要求，见 README）。",
}


def git(*args):
    r = subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True)
    if r.returncode != 0:
        print(f"FATAL: git {' '.join(args)}: {r.stderr.strip()[:200]}", file=sys.stderr)
        sys.exit(2)
    return r.stdout


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sidecar", type=Path, default=None)
    ap.add_argument("--receipt", type=Path, default=None)
    args = ap.parse_args()

    head = git("rev-parse", "HEAD").strip()
    head_date = git("log", "-1", "--format=%cs", "HEAD").strip()

    # ---- inventory: git ls-tree -r -l HEAD（路径排序确定性）+ blob 内容 sha256
    entries = []
    for line in git("ls-tree", "-r", "-l", "HEAD").splitlines():
        meta, path = line.split("\t", 1)
        mode, otype, blob, size = meta.split()
        if path == SELF_DIR_REL or path.startswith(SELF_DIR_REL + "/"):
            continue
        entries.append({"p": path, "b": blob, "z": int(size)})
    proc = subprocess.Popen(["git", "-C", str(ROOT), "cat-file", "--batch"],
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    assert proc.stdin and proc.stdout
    f = proc.stdout  # 逐条写读交替（避免管道缓冲死锁）: header 行 + size 字节 + \n
    for e in entries:
        proc.stdin.write(e["b"].encode() + b"\n")
        proc.stdin.flush()
        hdr = f.readline().decode().strip()
        parts = hdr.split()
        assert len(parts) == 3 and parts[1] == "blob", hdr
        n = int(parts[2])
        h = hashlib.sha256()
        remaining = n
        while remaining:
            chunk = f.read(min(1 << 20, remaining))
            h.update(chunk)
            remaining -= len(chunk)
        f.readline()  # trailing \n
        e["s"] = h.hexdigest()
    proc.stdin.close()
    proc.wait()

    # ---- public verification index（verified_at=记录最后修订提交日期）
    pub_rows = []
    for covers, record, role in PUBLIC_RECORDS:
        if subprocess.run(["git", "-C", str(ROOT), "cat-file", "-e", f"HEAD:{record}"],
                          capture_output=True).returncode != 0:
            print(f"FATAL: HEAD 缺少登记记录 {record}（清单与仓库漂移，须同步）", file=sys.stderr)
            sys.exit(2)
        verified_at = git("log", "-1", "--format=%cs", "HEAD", "--", record).strip()
        if not re.match(r"^(tools:.+|agent:author|agent:non-author-review|agent:author \+ tools:.+)$", role) or "（" in role:
            print(f"FATAL: role 超词表: {role!r} ({covers[:30]})", file=sys.stderr); sys.exit(2)
        pub_rows.append({"covers": covers, "record": record, "role": role, "verified_at": verified_at})

    # ---- private rows from sidecar（只取四字段，路径不入公开文档）
    sidecar_used, priv_rows, sidecar_sha = False, [], None
    if args.sidecar is not None:
        raw = args.sidecar.read_bytes()
        sidecar_sha = hashlib.sha256(raw).hexdigest()
        data = json.loads(raw)
        for r in data["private_receipts"]:
            priv_rows.append({"covers": r["covers"], "record_sha256": r["record_sha256"],
                              "role": r["role"], "verified_at": r["verified_at"]})
        sidecar_used = True

    payload = {
        "tool": "tools-verify-ledger.py (2026-11-07)",
        "generation": {
            "head": head, "head_date": head_date,
            "generator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "sidecar": {"used": sidecar_used, "rows": len(priv_rows),
                        "sidecar_sha256": sidecar_sha,
                        "note": "私档 sidecar 保存在仓外；其文件路径不入公开文档"},
            "excluded_paths": [SELF_DIR_REL + "/（台账自身：生成器、README、本 ledger）"],
            "regeneration": "克隆/复制仓库 → git checkout --detach <generation.head> → 以同 sidecar 重跑本生成器 = 逐字节相同",
        },
        "role_vocabulary": ROLE_VOCAB,
        "inventory": {"legend": {"p": "path", "s": "sha256(blob字节)", "b": "git blob sha1", "z": "字节数"},
                      "file_count": len(entries), "files": entries},
        "verification_index": {"public": pub_rows, "private": priv_rows},
        "not_publicly_recheckable": [
            {"item": i, "reason": r, "documented_at": d} for i, r, d in NOT_PUBLIC],
        "fields_split": FIELDS_SPLIT,
    }
    out = HERE / "ledger.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=1, sort_keys=False) + "\n",
                   encoding="utf-8")
    print(json.dumps({"head": head, "files": len(entries), "public_records": len(pub_rows),
                      "private_rows": len(priv_rows), "out": out.name}, ensure_ascii=False))
    if args.receipt is not None:
        rec = {"ledger_sha256": hashlib.sha256(out.read_bytes()).hexdigest(),
               "head": head, "sidecar_sha256": sidecar_sha}
        try:
            with open(args.receipt, "x", encoding="utf-8") as fh:
                json.dump(rec, fh, ensure_ascii=False, indent=1)
                fh.write("\n")
        except FileExistsError:
            print(f"FATAL: 收据已存在（write-once）: {args.receipt}", file=sys.stderr)
            return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
