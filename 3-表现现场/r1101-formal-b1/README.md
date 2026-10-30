# r1101-formal-b1：B 组首批正式准入批次现场（2026-10-30/31）

> 治理合同：`freeze-20261029-v4`（[注册计划](<../../1-评测方案/正式批次-2026-10-30/registration-plan.json>) 封印提交 `56369a5` **先于任何真实运行**；plan SHA `87af87b5…` 绑定 config.official_slots）。设计：B_native|元宝专家模式 ×5 + B_native|豆包办公 ×5，n=1/格，每 slot 仅 1 次 first 发射（配额制）。检索口径：两产品均按[落表三件套](<../../4-打分细则/检索口径-2026-10-27-落表.md>)（任务书禁网条款 + 逐会话披露 + 批后 integrity_scan + 人工终审）。运行留痕按[模板 v2](<../../4-打分细则/轻量判卷/运行记录模板.md>)十字段。

## 结果矩阵（全量导入不选优）

| 用例 | 元宝 reward/weighted | 元宝裁定 | 豆包 reward/weighted | 豆包裁定 |
|---|---|---|---|---|
| bird-ca-schools-15 | **1** / 93.33 | V clean | **1** / 93.33 | V clean |
| dabstep-payments-10 | 0 / 20.0 | V clean | 0 / 70.0 | V clean |
| exercism-py-6 | **1** / 100.0 | V clean（六文件全回收） | —（发射期基础设施失败，无会话零模型暴露，配额制作废） | infrastructure_invalid |
| lcb-recent-hard-4 | 0 / 0.0（8min 冻结无答案块） | V clean（无产物=0，B22 同形态先例） | **1** / 75.0 | V clean |
| tb-cargo-plan | 0 / 0.0 | V clean | 1 / 100.0 | **X 污染坐实**（见下），原分留档不采用 |

**正式表实算（build 后）**：B_native 准入 **8 行**（元宝 5——含 lcb「有效运行、任务未达标 0 分」行（B22 同形态先例）+ 豆包 3）；rejected 101 = 96 历史行 + 豆包 cargo（gate:contamination_free + final_adjudication=invalid）+ 豆包 exercism（infrastructure_invalid）+ 3 个非产品事件（预检×2/自测，类别性拒绝）。A_same_model=空（v4 时代无 A 注册）。

## 污染裁定（豆包×tb-cargo-plan，X）

轨迹 [integrity 扫描](<integrity/doubao-integrity-scan.json>) + [人工终审](<integrity/integrity-adjudication-r1101.json>)：agent 出工作区在全盘检索 cargo 材料（`Documents-backup/harness-compare-bench-feedback` → `bench-private/harness-compare-bench` → iCloud 归档树），tool result 列出私档树中 r1029 场的 truth.json/checker.py/spec.md 路径，assistant 自述读 oracle 与 checker「align with intended semantics」，实读 checker 源码，自述「output matches the expected truth」。`session/memory/MEMORY.md` 为 0 字节，非跨会话记忆泄漏；属**桌面 agent 全盘文件访问的结构性越界**（工作区隔离不构成桌面 agent 的行为边界，与 r1026 WB×tb 同类）。处置按判定纪律：X 整场排除、不按子题豁免，原分 1/100 留档不采用。

## 元宝 lcb 形态说明

完成判定 v3 于 8min 冻结无答案块（与 r20261027 B22 同形态：能力墙，389_g）；会话证据完整，检索口径不适用且无命中；人工终审裁定运行有效、结果可判（无产物=0），不折算不豁免。

## 证据包边界（隐私）

公开包内：逐场冻结 checker 判分 stdout、TASK.md、run_meta（batch 级元数据+判分+检索审计汇总）、预检收据、integrity 扫描与人工终审、selftest 收据。**不公开**：元宝会话 API dump 与豆包会话轨迹原件（含账号侧数据，原件在 `bench-automation/runs/r1101/` 私档），其存在与完整性由上列收据与机器账行级登记承载。

## 分账（六类）

product_run 10（含豆包 exercism infrastructure_invalid 诊断场）；interface_preflight 2（[元宝](<preflight/yuanbao-preflight.json>) 16 检查 PASS、[豆包](<preflight/doubao-preflight.json>) 6 检查 PASS 含 1 次微型 probe 往返）；self_test 1（[五题 checker 自测](<selftest/checker-selftests.stdout.txt>)，5/5 exit 0）；offline_recompute / grading_regression / bare_model_probe 本批为零（如实为空）。
