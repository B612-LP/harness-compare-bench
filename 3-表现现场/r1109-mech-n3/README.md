# r1109-mech-n3 —— 机制独立重复（CLI 两臂 × 5 场 × n=3）

本目录是 [机制独立重复预注册-2026-11-08](<../../4-打分细则/机制独立重复预注册-2026-11-08/README.md>) 的执行现场（批次 r1109-mech-n3，2026-11-09 发射，用户当日放行）。

## 批次事实

- 预注册基线：commit `704d2bb`（预注册 README 该提交时点内容，含 [勘误 2026-11-09] 六组→10 组计数勘误）。
- 臂与场：DSH CLI、Codex CLI × bird-ca-schools-15 / dabstep-payments-10 / exercism-py-6 / lcb-recent-hard-4 / tb-cargo-plan，每场每臂 n=3 全新会话，共 30 次运行，全部完成（零 RUN-FAIL、零补跑）。
- 控制条件：模型 deepseek-flash（官方端点）、reasoning effort low、工具 schema/权限/skills 沿用 a1 批、提示与 inputs 以 a1 归档逐字节门（a1_gate：10/10 prompt_sha256 与 inputs sha256 全等）复用 a1 工作区路径。
- 判卷：一律用 v2 冻结字节（[frozen-checkers/](<frozen-checkers/>)，sha256 == [可信冻结-2026-10-29-v2 config 快照](<../../4-打分细则/可信冻结-2026-10-29-v2/config.json>)）。注意：公开仓现行 2-用例 bird checker.py 经 10-30 发布重写已非 v2 字节，本批判卷不受影响（其余四题公开树与 v2 一致）。
- 观测：DSH 臂 S3（重构输入逐字节）经 [tools-session-trace-observe](<../../4-打分细则/请求侧观测规范-2026-11-08/README.md>)，Codex 臂 R3 经 tools-request-side-observe；见各槽 `session-*`/`reqside-codex-*` 聚合与见证（在 [4-打分细则/机制独立重复预注册-2026-11-08](<../../4-打分细则/机制独立重复预注册-2026-11-08/README.md>) 执行记录引用的 observe 汇总）。

## 逐槽结果（reward / weighted%）

| 臂×场 | r1 | r2 | r3 |
| --- | --- | --- | --- |
| dsh × bird | 1 / 93.33 | 1 / 100.0 | 1 / 100.0 |
| dsh × dabstep | 0 / 70.0 | 0 / 70.0 | 0 / 70.0 |
| dsh × exercism | 1 / 100.0 | 1 / 100.0 | 1 / 100.0 |
| dsh × lcb | 1 / 100.0 | 1 / 100.0 | 1 / 100.0 |
| dsh × tb | 1 / 88.89 | 1 / 88.89 | 1 / 88.89 |
| codex × bird | 1 / 100.0 | 1 / 93.33 | 1 / 100.0 |
| codex × dabstep | 0 / 70.0 | 0 / 70.0 | 0 / 70.0 |
| codex × exercism | 1 / 100.0 | 1 / 100.0 | 1 / 100.0 |
| codex × lcb | 1 / 100.0 | 1 / 100.0 | 1 / 100.0 |
| codex × tb | 0 / 70.37 | 0 / 70.37 | 0 / 70.37 |

- 9/10 臂×场 reward 二值复现 a1（唯一例外：dsh × tb，a1 单次 0 → 本批 3/3 过，weighted 88.89 三轮一致，见执行记录分账）。
- 输入侧判定（预注册门）：DSH S3 四场 n=3 逐字节一致（bird 27738×3、exercism 25588×3、lcb 25837×3、tb 25434×3，max−min=0）；dabstep [28062, 27106, 27106] max−min=956B>100B——逐 turn 定位为 r1 轨迹含模型自主委派（subagent）事件，基础 prompt/context 字节一致，按预注册分账处理，该组不满足严格门、标方向性。Codex R3 全轨迹重构随轨迹轮数构造性增长（真身值 62,854–817,320B，即约 61KB–798KB，见 `observe/codex-r3-summary.json`；早期 files[0] 口径的 330KB–817KB 已被该文件自注 supersede），严格门不适用于全轨迹聚合；首轮控制输入（permissions / environment_context / 任务文本）内容级 n=3 逐字节一致 × 5 场（剥离 rollout 封套 id/时间戳后），故 Codex 组输入侧控制以首轮一致 + a1_gate 为准，全轨迹 R3 如实披露。

## 事件与更正（全程收据保留，公开件为派生）

1. 判卷事故（bird）：in-run 判卷时 frozen-checkers 尚缺 truth/inputs（canonical 输入缺失）→ dsh bird r1–3 in-run judge=null；全树修复后 retro-judge（同一 v2 checker 字节），score-receipt 带 judging_incident 披露，原空判输出保留于 checker-error-prefix.json。
2. 判卷来源澄清：共享 a1 工作区会被后续 rep 覆盖，各 rep 判卷一律以其归档 workspace 副本为对象；复测判定与原批一致。
3. 会话轨迹对账：DSH 捕获曾发生同 slug 先到先得错配（bird r2、dabstep r3、tb r2 归档为相邻 rep 副本；dabstep r1 误捕模型自主 subagent 轨迹）——已逐一从活会话根换回真身，S3 汇总以真身后为准。Codex 捕获为加性污染（每槽多含上一槽 rollout，共享 CODEX_HOME 所致），已逐槽识别真身 rollout（时间戳==槽 start），邻槽 rollout 移存 neighbor-* 不删除，integrity/R3 均按真身重算。逐槽对账收据的公开汇总见 [observe/trace-accounting-summary.json](<observe/trace-accounting-summary.json>)（30/30 槽真身在档；轨迹原件与逐槽 trace-incident.json 存私档，archive://launch-r1109/ 定位）。
4. integrity 越界模式扫描（八类，真身轨迹终值）：非零槽共 5 个——codex bird r2=2、tb r1=2、tb r2=2（reasoning/事件文本 mention 级命中 `reference/`）；dsh dabstep r2=1（reasoning 文本 mention `solution/`）、dsh exercism r2=4（`../` 相对寻址，属用例说明书规定的就地实现动作）；其余 25 槽 0。逐条摘录见各槽 `integrity-rescan.json`；lead 复核（mention 级/任务规定动作/环境回显判定 + 受保护路径 tool/function_call 级扫描全 0）见 [reviews/lead-integrity-review.json](<reviews/lead-integrity-review.json>)，复核人=AI Agent（与核验台账同一署名口径）。3 个槽的 in-run violation 曾系邻槽轨迹污染计数（codex bird r3、codex tb r3、dsh dabstep r3），真身重扫为 0。
5. runner 缺陷（不阻塞）：共享 ws 使 archived meta 仅 r1 份 → dsh 臂 12 槽 adjudication 补写（post-batch-fix；更正登记收据存私档 archive://launch-r1109/meta-corrections.json）；bird 三槽 meta.judge 曾被误写标量 15，已按 score-receipt 回填为完整判卷字典。in-run adjudication 状态分布：25 槽 valid；codex 5 槽（bird r2/r3、tb r1/r2/r3）曾为 infrastructure_invalid、dsh 3 槽（dabstep r2/r3、exercism r2）曾为 pending-review——8 槽均经 lead 复核终结为 valid（见 reviews/lead-integrity-review.json；槽内原始裁决文件 write-once 不改写，该复核文件为终态裁定层）。
6. codex dabstep r1 期间模型自主 spawn subagent（parentSession 本槽，合法运行证据），其轨迹单独入档并在 S3/S4 分账披露。

## 文件结构

- `runs/<arm>__<case>__r<rep>/`：meta.public-derived.json（workspace 键去除；run_dir 等键保留运行工作区路径，为公开惯例）、score-receipt、checker.stdout、adjudication、integrity-rescan、agent.jsonl.full、workspace/（TASK.md + answers.jsonl）。私档路径以 `archive://launch-r1109/` 标签替代。
- `frozen-checkers/<case>/`：判卷所用 v2 冻结 checker/truth/instruction 副本（sha256 对 v2 config 快照核验）。
- `preflight/`、`tools/`、`adjudications.json`、`integrity-rescan-summary.json`：发射前预检、两臂运行器与串行批脚本、逐槽裁决、逐槽扫描汇总。
