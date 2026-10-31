# 公开产物的分数复核

本入口重建判卷工作区，复核公开原字节产物的 checker 分数；**不等于完整原始轨迹重演**。删节的私人上下文不能从公开包恢复；公开轨迹证据边界与产物分数可复算边界应分开判断。

先完整阅读本场候选代码、额外模块和实际工具行为，核对 [产物清单](<runs/dabstep-payments-10/artifact-manifest.json>) 或对应其他用例的同名清单。不盲跑候选代码，不在仓库或原始工作区运行，不修改题库。`CASE` 只选本批三项之一；下面示范 DAB，LCB/cargo 按原相对路径 overlay，**不能直接把不含 inputs 的 artifacts 目录当 run_dir**。

以下为 macOS、系统 Python3 与 `sandbox-exec` 可用环境的模板。所有路径改为你自己的绝对路径；`WORK` 必须为仓外不存在的新目录。先审查下列命令及隔离规则，再执行。隔离只限制文件访问/写入和网络，不声称抵御系统漏洞或任意资源耗尽；实际隔离不生效就停止，不降级为直接执行。

```bash
set -e
REPO='/absolute/path/to/clone'
CASE='dabstep-payments-10'  # 或 lcb-recent-hard-4 / tb-cargo-plan
WORK='/absolute/path/outside/clone/new-wb-recompute'
EVID="$REPO/3-表现现场/r20261031-wb-replacement/runs/$CASE"

# 在任何复制前确认仓外独占目标；已有目录即停止，不覆盖历史复核。
python3 - "$REPO" "$WORK" <<'PY'
import pathlib, sys
repo, work = [p.resolve() for p in map(pathlib.Path, sys.argv[1:])]
assert repo.is_dir() and not work.exists()
assert not work.is_relative_to(repo), 'WORK 必须在仓外'
PY
# mkdir 不加 -p。
mkdir "$WORK" || exit 1
cp -R "$REPO/2-用例/$CASE/inputs" "$WORK/inputs" || exit 1
cp -R "$EVID/artifacts/." "$WORK/" || exit 1
cp "$EVID/TASK.md" "$WORK/TASK.md" || exit 1
mkdir "$WORK/.grade-tmp" || exit 1

# 校验 overlay 原字节及所有引用的 canonical inputs；不执行候选代码。
python3 - "$REPO" "$EVID" "$WORK" <<'PY'
import hashlib, json, pathlib, sys
repo, evidence, work = map(pathlib.Path, sys.argv[1:])
assert not work.resolve().is_relative_to(repo.resolve()), 'WORK 必须在仓外'
manifest = json.loads((evidence / 'artifact-manifest.json').read_text())
for entry in manifest['files']:
    data = (work / entry['path']).read_bytes()
    assert hashlib.sha256(data).hexdigest() == entry['sha256'], entry['path']
print('Artifact/input SHA verification passed; not a candidate-code safety review')
PY

# 隔离候选子进程：拒绝网络，写入仅独占判卷临时目录；仅豁免当前
# 重建工作区和当前 canonical case 的用户目录读取。系统运行时读仍开放。
python3 - "$REPO/2-用例/$CASE" "$WORK" <<'PY'
import json, pathlib, sys
case, work = [p.resolve() for p in map(pathlib.Path, sys.argv[1:])]
tmp = work / '.grade-tmp'
q = lambda p: json.dumps(str(p), ensure_ascii=False)
profile = '(version 1)\n(allow default)\n(deny network*)\n(deny file-write*)\n'
profile += '(deny file-read* (subpath "/Users") (subpath "/private/var/folders") (subpath "/private/tmp"))\n'
for p in (case, work, tmp):
    profile += '(allow file-read* (subpath ' + q(p) + '))\n'
profile += '(allow file-write* (subpath ' + q(tmp) + '))\n'
(work / 'checker.sb').write_text(profile)
PY

# 仅在已经独立检查候选代码、隔离可用且规则路径符合本机情况后执行。
TMPDIR="$WORK/.grade-tmp" PYTHONDONTWRITEBYTECODE=1 \
  /usr/bin/sandbox-exec -f "$WORK/checker.sb" \
  python3 -I -S -B "$REPO/2-用例/$CASE/checker.py" "$WORK" --json
```

对照本场[完整 checker JSON](<runs/dabstep-payments-10/checker.stdout.json>) 的检查项，以及[分数收据](<runs/dabstep-payments-10/score-receipt.json>)的 earned/possible、reward、checker SHA（此处链接为 DAB 示例，其他用例使用各自目录同名文件）。DAB 默认 official-compat；完整 JSON 同时记录 strict-contract，不互换、不覆盖，q2697 仍禁止能力归因。重新判卷产生的是新的 **offline_recompute** 收据，不是新的产品运行，也不能补救既有越界或补全删节轨迹。
