# L2 独立验收（judge，2026-10-29）

- 依据：[PREREGISTRATION.md](<../../1-评测方案/自动循环L2-2026-10-29/PREREGISTRATION.md>)（封印 `ae36f67`）+ [AMENDMENT-L2-1.md](<../../1-评测方案/自动循环L2-2026-10-29/AMENDMENT-L2-1.md>)；分支 `loop2-2026-10-29`
- 逐项检查命令/退出码/实测值：[verify-receipt.json](<verify-receipt.json>)
- 纪律：除本目录外全部只读；包A 重放输出 /tmp；包C validator 仅在 /tmp 副本运行；git 仅只读命令；不预读 builder 主张文本，仅读产物与收据

## 四包裁定

| 包 | 裁定 | 一句话依据 |
|---|---|---|
| A 判卷历史回放补证 | **pass** | judge 独立重放逐场全等（24/0/15，diff=0）；行集冻结/排除项/三 SHA/两勘误框全过 |
| B 冻结合同 v3 | **partial** | 构建与数据面全过（verify ok、v2 零字节改动、六账 110/13/7/3/5/13、7 收据各 1 次、official A=0/B=0、pin 10/7、修正案双哈希）；**但 HEAD 上 test_freeze 44 测 1 失败**（B-1） |
| C runner schema v2 | **pass** | 三 SHA/收据 canonical 620cd322//tmp 重跑全过；retro 矩阵 20 场独立复算逐项一致；--spec 覆盖缺陷确认（已披露存证，C-1） |
| D r1030 记录勘误 | **pass** | dated/原句保留/双指针可达；:308/:317 行序主张经源码独立复核成立 |

## 发现分级

### defect

- **B-1（包B）**：HEAD（`aeec36f`）上 v3 `test_freeze` 44 测 **1 失败**（exit=1）：`test_live_ledger_exists_and_empty` 断言活台账 `events==[]`，与同 commit 已登记的 5 条 L2 事件冲突（实测 `ae6b37d` 时 events=0 → builder「44/44」在其提交时点成立；`aeec36f` 后必然失败）。测试断言与活台账 append-only 生命周期矛盾。
  影响：HEAD 上验收标准「test_freeze 全过」不成立；任何复核/CI 重跑即红。
  下一步：lead 裁定修法（建议断言改为「事件结构合法且与台账实际一致」或按设计快照计数），修后重跑落新收据。
  停止条件：HEAD 测试全绿前，包B 不得在任何下游文档被引用为「44/44 全过」。
- **C-1（包C，已披露、包内闭环存证）**：`validate_runner_meta.py --spec` 无条件重写同目录 `spec-selftest-receipt.json`（judge 在 /tmp 副本运行即复现落盘行为）；覆盖事件已由 builder 以 `receipt-overwrite-evidence-20261029.json`（裸收据字节 `0f62d42a…`）+ corrections 存证；在案终态收据 canonical 重算 = `620cd322…` 成立。
  影响：真实批次误跑 `--spec` 会静默覆盖既有收据（证据破坏风险）。
  下一步：L3 lab.py 集成时改为「已存在即拒写或写旁挂」，输出路径显式化。
  停止条件：修复前禁止对任何含证据价值目录运行 `--spec`。

### observation

- **B-2（包B）**：测试对账实测 = **38 继承（0 删除）+ 6 新增 = 44**；builder 报「37 继承 + 7 新增」拆分不准（总数正确）。两个同名测试体差异均不削弱断言：`test_outcome_based_registration`（时间字面量→`self._t(61)` 相对时刻，语义等价）；`test_dab2697_is_not_inferred_capability`（仅文件尾位置差异，测试体零改动）。新增 6 个：live_doc 漂移报告制、contract 漂移硬失败、缺 live_doc pin=漂移不 crash、7 收据入六账、不重准入、活台账存在且空（即失败的那条）。
- **B-3（包B）**：活台账事件 `kind=correction`（work:l2-r1030-readme-erratum-20261029）不在 v3 config-schema `live_registry_entry.kind` enum（5 值）内；`aeec36f` 提交信息明示「kind enum 扩列留 L3」。L3 若引入活台账机读校验而未扩列，升级为 defect。

### note

- **X-1**：`AMENDMENT-L2-1.md` 位于预注册目录、builder-codex 撰写、lead 提交——不在包B 申报 write-scope 内，但属预注册 §二.1 修正案程序授权文件，非越界。
- **X-2**：pin 分类中 `import-example.json`/`example-source.json` 归 live_doc——示例文件分类学边界（既非判分输入亦非叙述），不构成风险。

## 关键实测值摘录

- 包A：重放 `n_replayed=24 / n_flipped=0 / ledger_match=15`，与在案收据逐场 before/after/flip/ledger_match **全等（diff=0）**；after 轨三 SHA = `994be0b3…`/`63845361…`/`d84b1111…` ✓；冻结行集 41 行（24+17），排除 `r20261027-wb-lcb-sandbox/workbuddy/lcb-recent-hard-4`（lead 裁决 B，收据 corrections 留痕）✓；README 两处勘误框 dated `2026-10-29 16:06:56 +0800`、原句保留 ✓。
- 包B：v3 verify `ok=true, live_doc_drift=[]`（exit 0）；v2 双目录 `git status --porcelain` 与 `git diff HEAD --stat` 均空；v2 verify `ok=true`（exit 0，Ran 38 OK）；six-ledgers `110/13/7/3/5/13`，7 收据各恰 1 次、wb-sandbox 去重后 1 次；official v3 `A=0, B=0`；pins 17 = 10 contract + 7 live_doc；AMENDMENT-L2-1 双哈希自算 v1=`27974b75…` ✓、v2=`04944e28…` ✓，v3 config path/sha 自洽。
- 包C：三交付物 SHA `a98f11af…`/`ac2e4b7c…`/`12cd3354…` ✓；收据字节 `5c6177fd…` ✓、canonical `620cd322…` ✓；/tmp 副本 `--spec` 全过且与在案收据逐项一致；retro 矩阵独立复算（judge 自扫 20 场 meta）：registered_at 缺 20/20、dsh 六字段各缺 10/10、transport_retries dsh=list 10/10（codex=int）、codex 2dp 收据 2 场（cargo r2/r3）、dsh rep 字符串型 10/10、meta.weighted 8dp delta 4 场（双产品 cargo r2/r3）——**与 builder 矩阵逐项一致**；SCHEMA 动机锚点 D1/D2/D5 逐条在（43 必备 + archived_stdout=44）。
- 包D：勘误框 dated `2026-10-29 15:59:56 +0800`；原句「tools/lab.py 已修…」原段保留；指针 `r1031-variance-n3/tools-dsh/README.md §批内发现并修复`（:36 存在）与 `dsh__bird-ca-schools-15__r2/meta.json#corrections`（id `r1031-archiver-log-loss`）均可达；`shutil.rmtree` :308 先于 staging :317 经源码复核成立。
- 横切：五 commit 路径 vs write-scope 无越界；活台账 5 事件 source sha256 实时复算 5/5 吻合（台账 `7db00c3e…`）；builder 交付物抽查无评测分析性结论。

## 复现

```bash
# 包A 重放（judge 同款，只读，输出自定）
python3 -B "4-打分细则/判卷审计-2026-10-27/checker-tightening-B2-B8-B12-13-14/replay_b13a_2026_10_29.py" /tmp/<your-out>.json
# 包B
python3 -B "4-打分细则/可信冻结-2026-10-29-v3/freeze.py" verify          # 仓库根运行
python3 -B "4-打分细则/可信冻结-2026-10-29-v3/test_freeze.py"            # HEAD 当前 1 失败（B-1）
python3 -B "4-打分细则/可信冻结-2026-10-29-v2/freeze.py" verify          # v2 仍绿
# 包C（务必在副本）
cp -r "1-评测方案/工具链/runner-schema-v2" /tmp/pkgc && cd /tmp/pkgc
python3 validate_runner_meta.py --spec --fixtures fixtures
```

*judge 出品 · 每项检查含命令/退出码/实测值见 verify-receipt.json · 五段整体结论归 lead 验收报告*
