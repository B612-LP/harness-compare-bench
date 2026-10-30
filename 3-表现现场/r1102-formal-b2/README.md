# r1102-formal-b2：豆包×exercism 作废重跑批次现场（2026-10-31）

> 治理合同：`freeze-20261029-v5`（[注册计划](<../../1-评测方案/正式批次-2026-10-31/registration-plan.json>)；封印提交 `dec790a` 先于任何真实运行；[封印修订-2](<../../4-打分细则/可信冻结-2026-10-29-v5/README.md>) 显式披露于导入前）。本批 = formal-b1 唯一非合规终局槽位（豆包×exercism，发射期 infrastructure_invalid、零模型暴露）的配额制作废重跑。运行留痕按[模板 v2](<../../4-打分细则/轻量判卷/运行记录模板.md>)十字段（本批=**v2 首个执行批**，场级记录 [run-record.md](<runs/doubao__exercism-py-6/run-record.md>) 过 `validate_run.py --strict-evidence`）+ [桌面工作区边界判定线](<../../1-评测方案/正式批次-2026-10-31/判定线-2026-10-31-桌面工作区边界.md>)首个适用批。

## 结果

| 项 | 值 |
|---|---|
| 正式表 | [v5 official-main-table](<../../5-评测报告/可信冻结-2026-10-29-v5/official-main-table.json>)：**B_native=1 准入**（`formal-b2-doubao-exercism-py-6-01`）、A=0、rejected 98 = 96 历史 + 2 非产品事件（预检/自测，类别性拒绝） |
| 得分 | **reward 1 / weighted 83.33**（5/6 题：forth 54/54、poker 37/37、dominoes 13/13、bowling 31/31、zipper 14/14 全过；pov tests=15/15 exit=1） |
| 裁定 | **V clean**（检索维+边界维双 clean，见下）；B_native 累计 9 行（v4 8 + v5 1），A/B 不混排 |

## 运行形态（如实披露）

- 预检：01:18 `probe --product doubao` PASS（`probe-ok-1793380669`，应用正常退场）——确认 r1101 发射失败为瞬时故障。
- 发射：01:27:11 成功（会话 `38450165484162306`）；六模块在会话冻结前全部交付。
- 完成判定：2400s 上限收敛为 **timeout**（最后 36min 轨迹静默，末条 role=tool）。处置按「有效运行、产物可判」先例（元宝 lcb 的反向情形=产物齐备）：运行有效 V、checker 实测判分，不折算不豁免；静默直接原因作为场级未知如实登记（见 run-record 未知表）。
- 判定线终审（r1102 起首个适用批）：全轨迹 65 行扫描工作区外路径 **0 命中**；find/ls 类命令均限于工作区内；`session/memory/MEMORY.md` 0 字节无跨会话泄漏。
- 检索三件套终审：integrity_scan 命中 3 处 URL 字样，逐一溯源为**题面测试文件自带来源注释**（`# These tests are auto-generated with test data from: …`），非检索行为——按题面自带来源标注豁免口径（同 r1101 bird 裁定）记误报；0 检索步骤、0 题解接触。

## 证据包边界（隐私）

公开包内：冻结 checker 判分 stdout、run-record（v2 十字段）、meta/adjudication/score-receipt、TASK.md（硬条款+禁网附则）、预检收据、selftest 收据、integrity 扫描与人工终审。**不公开**：豆包会话轨迹原件（含账号侧数据，原件在私档 `bench-automation/runs/r1102/`），其存在与完整性由上列收据与机器账行级登记承载。

## 分账（六类）

product_run 1；interface_preflight 1（[豆包预检](<preflight/doubao-preflight-r1102.json>)，含 1 次微型 probe 往返）；self_test 1（[exercism 自测](<selftest/exercism-py-6.selftest.r1102.json>)，16/16 exit 0）；offline_recompute / grading_regression / bare_model_probe 本批为零（如实为空）。

## 封印修订-2 摘要

注册计划 `parent_id` 预写值与机械契约冲突（selection 全等比对 × 队列 first 语义），修订为 `null` 并级联 config plan_sha 与对应 2 个 lock pin；其余 30 pin 零变动；运行操作未受影响。全文见 [v5 README 封印修订-2](<../../4-打分细则/可信冻结-2026-10-29-v5/README.md>)。
