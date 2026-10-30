# r1030-formal-a1：首批正式准入批次现场（2026-10-29）

> 本说明经隐私整理，字节与历史版本不同，不能按旧版文件哈希通过封印核验。历史冻结及运行原始记录的可公开复核范围见[报告索引](<../../5-评测报告/README.md>)；修改说明不改变原始运行产物和历史裁定。

历史规则：`freeze-20261029-v2`（[计划记录](<../../1-评测方案/正式批次-2026-10-29/registration-plan.json>)，旧 Git 锚点 `213013b`）。当时记录为全部 10 场有效、零污染、无重试，并非当前公开副本重新认证。

DSH 的五份压缩轨迹因包含私人用户级规则，公开侧现为不同名的 `session.public-derived.jsonl.zstd`，同目录附 `privacy-provenance.json`，原件不公开。任务与工具事件保留，私人指令块省略；这一背景变量的影响未被排除，不能从摘要证明输入完全一致或旧完整性裁定。当前公开复算为 5 pass、0 fail、5 incomplete，分值不变；详见[复核边界](<../../5-评测报告/可重复性-n3-2026-10-29/RESULTS.md>)。

## 结果矩阵（n=1/格，全量导入不选优）

| 用例 | Codex reward/weighted | DSH reward/weighted | 耗时 C/D | 历史对照（r1027 干净口径） |
|---|---|---|---|---|
| bird-ca-schools-15 | **1** / 93.33 | **1** / 100.0 | 218.9s / 196.9s | 1/86.67 · 1/86.67 |
| dabstep-payments-10 | 0 / 70.0 | 0 / 70.0 | 257.6s / 436.6s | 0/70.0 · 0/70.0 |
| exercism-py-6 | 1 / 100.0 | 1 / 100.0 | 86.2s / 72.6s | 1/100 · 1/100 |
| lcb-recent-hard-4 | 1 / 100.0 | 1 / 100.0 | 281.1s / 278.2s | 1/100 · 1/100 |
| tb-cargo-plan | 0 / 81.48 | 0 / 74.07 | 332.7s / 171.9s | 0/70.37 · 0/70.37 |
| **headline** | **3/5** | **3/5** | 总 1176.5s / 1156.2s | 3/5 · 3/5 |
| weighted 总分(500) | 444.81 | 444.07 | — | 427.04 · 427.04 |

判读（n=1，不做排名声明）：headline 与失败格局（dabstep+cargo 达标线以下）与历史完全一致；weighted 总分差（444.81 vs 444.07）由 bird（14/15 vs 15/15）与 cargo（22/27 vs 20/27）两次单项波动构成，对照 r1025/r1027 的逐题结果，这一单场差异的原因尚不确定，不能据此认定稳定差异或归因于方差；dabstep 错误格局与历史同错（q49/q70/q2697 待逐场复核）。逐场证据见 [runs/](<runs/>)，判分原始输出与收据双源打包。

> 勘误（2026-10-29）：DSH weighted 总分曾误记为 **414.07**，产物复算值为 **444.07**，与 0.74 的差值一致。可参见[事后勘误摘要](<../../1-评测方案/评测依据-重复性与预检-2026-10-29/AMENDMENT-1.md>)及[复算矩阵](<../../5-评测报告/可重复性-n3-2026-10-29/verify-matrix-selftest-r1030.json>)；原勘误文件不公开，摘要不继承其封印。原文把单场差异归为方差，证据不足；后续重复运行仅作[小样本观察](<../../5-评测报告/可重复性-n3-2026-10-29/RESULTS.md>)，不证明稳定差异或统计等效。

## 无污染裁定

工作区在仓库外（`~/bench-workspaces/r1030/`，只有 inputs+TASK.md，隔离断言通过）；会话轨迹按八类模式重扫：Codex 5 场 0 命中；DSH 5 场各 1 命中=运行时注入的用户级说明文本（`~/.dsh/AGENTS.md` 含 `~/Documents` 字样），非模型访问，判 benign（与 r1023/r1025/r1027 条件一致），逐场见 [integrity-rescan.json](<runs/>) 与 [汇总](<integrity-rescan-summary.json>)。

## 归档缺陷披露（r1030#1，已修正）

首轮运行器的 `agent.jsonl`（runner 侧 stdout 事件流）写入证据目录内，被归档 `rmtree` 连带删除：运行本身（工作区、产物、会话轨迹、判分、meta）完好，但 stdout 流不可恢复，且首轮 `meta.integrity` 扫描空转。处置：`tools/lab.py` 已修（日志经 staging 移动）；全部 10 场以更完整的**会话轨迹重扫**替代并显式修正 meta（保留 `corrections` 记录，不静默改写）。证据等级相应记为 `original-contemporaneous-full`（会话轨迹完整、runner 流缺失已披露）。

> **[勘误 2026-10-29 15:59:56 +0800]（r1031#1 证伪）** 上段「处置：`tools/lab.py` 已修（日志经 staging 移动）」的**「已修」声明不成立**：实测该文件 `shutil.rmtree(ev)` 在 :308，staging 移动块自 :317 起——rmtree 先于日志移动执行，写在证据目录内的日志在移动前已被删除，该代码级修复从未生效（r1031 第 1 场 bird r2 复现实证，raw stdout/stderr 同机制丢失）。实际生效的修复是 r1031 侧 `tools-dsh/lab.py` 的结构性修复：日志自落盘起即写入证据目录外的 staging，证据目录可安全重建。逐场披露与处置记录见 [r1031 tools-dsh/README.md §批内发现并修复](<../r1031-variance-n3/tools-dsh/README.md>) 与 r1031 `dsh/runs/dsh__bird-ca-schools-15__r2/meta.json` 的 `corrections`（id `r1031-archiver-log-loss`）。本节其余内容（缺陷机理、会话轨迹重扫替代、证据等级）不受影响；r1030 代码与收据按纪律不做回改。

## 六类分账（本批）

product_run 10（导入 [formal-a1-events.json](<formal-a1-events.json>)，v2 `validate-import` 通过）；self_test 5（[selftest/](<selftest/>)）；interface_preflight 2（[preflight/](<preflight/cli-preflight.json>) + [WorkBuddy 准入预检](<../../1-评测方案/准入预检-2026-10-29/wb-preflight.json>)）；其余三类本批无新增（如实为空）。
