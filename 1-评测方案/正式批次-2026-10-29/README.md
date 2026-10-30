# 正式批次 r1030-formal-a1 协议

首批按冻结规则 `freeze-20261029-v2` 运行的正式 A 组批次。

## 与注册计划的关系

- 注册计划：[registration-plan.json](<registration-plan.json>)（`plan_id=formal-a1-20261029`，10 个 first 注册，全部早于任何运行开始）。
- 该计划的 SHA 已被 [可信冻结-2026-10-29-v2](<../../4-打分细则/可信冻结-2026-10-29-v2/README.md>) 的 config.official_slots 绑定并封印；封印提交（Git）先于任何运行。
- 运行完**全量导入**：成功、失败、诊断一律保留；不按结果选样，不补 0，不替跑。

## 变量（与 r1023/r1025/r1027 一致）

| 项 | Codex CLI | DSH CLI |
|---|---|---|
| 版本 | codex-cli 0.163.0 | DSH 0.2.0-rc.2 |
| 模型 / 思考 | `deepseek-flash` / low | 同左 |
| 路由 | 隔离 CODEX_HOME `base_url=https://api.deepseek.com`（responses） | `bench-cli` profile，provider `deepseek-official`（anthropic-messages；endpoint 未逐场观测，host 由同 provider 机制实验 12 次传输记录佐证） |
| 联网 / SKILL | 关 / 关 | 关 / 关 |
| 工作区 | `~/bench-workspaces/r1030/codex/<case>/` | `~/bench-workspaces/r1030/dsh/<case>/` |

## 判分与裁定

- 判分：各题仓库原版 `checker.py <workspace> --json`（checker/truth/case manifest SHA 全部被 v2 config 冻结）；自测收据见 `3-表现现场/r1030-formal-a1/selftest/`。
- 逐场轨迹越界扫描（模式同 r1027：`2-用例`/`truth.json`/`checker.py`/`reference/`/`solution/`/`../`/`~/Documents`/`harness-compare-bench`），0 命中才可判 `contamination_free=true`；任何命中逐条人工复核后裁定。
- `evidence_grade` 取值 `original-contemporaneous-full`（原始现场、当场全量捕获）；最终裁定 valid / invalid / suspect / infrastructure_invalid 逐场给依据。

## 产物

- 现场：`3-表现现场/r1030-formal-a1/`（逐场 meta/轨迹/会话/判分/收据）。
- 导入：`3-表现现场/r1030-formal-a1/formal-a1-events.json` → `freeze.py build --imports` → [正式主表](<../../5-评测报告/可信冻结-2026-10-29-v2/official-main-table.json>)。

## 六类分账（本批新增）

- product_run：10 个注册产品运行事件（导入）。
- self_test：5 个判分器自测（registry）。
- interface_preflight：CLI 零模型预检 + WorkBuddy 准入预检（registry）。
- offline_recompute / grading_regression / bare_model_probe：本批无新增（如实为空，不凑数）。
