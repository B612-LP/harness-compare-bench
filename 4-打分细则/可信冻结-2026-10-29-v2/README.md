# 第二代冻结（freeze-20261029-v2）：首批正式准入的预注册封印

本目录是 [第一代冻结](<../可信冻结-2026-10-29/README.md>) 的**新一代合同**，专为首批正式准入批次（r1030-formal-a1）建立。与 v1 的差异**只有三处**：

1. `rule_version`：`freeze-20261029-v1` → `freeze-20261029-v2`；
2. `official_slots`：由空 → 绑定 10 个正式格（A 组 Codex/DSH × 5 题），每个格绑定 `{plan_id, slot_id, plan_sha256}`，计划源为 [registration-plan.json](<../../1-评测方案/正式批次-2026-10-29/registration-plan.json>)（SHA `5e4452b55dd92e00420eb91761a1b775dff608237bf8f7a100c7aa25aea2d466`）；
3. `effective_at/collected_at` 推进到本代封印时刻；[工作台账](<work-registry.json>) 追加本批自测与预检收据（5 自测 + 2 预检）。

验证器代码（freeze.py）除三个常量外与 v1 逐字节相同；测试（test_freeze.py）原样复用。**v1 目录与产物一个字节未动**，其封印与独立复核基线继续有效。

## 为什么需要第二代

v1 封印时 `official_slots` 为空：历史运行没有前瞻冻结，不能倒填注册（v1 README「固定选样」节）。正式准入要求事件所属格在**冻结配置**中绑定唯一 `group|product|case_id → {plan_id, slot_id, plan_sha256}`，且注册时间早于运行开始时间、运行开始晚于 `effective_at`。因此建立本代：先写计划 → 封印并提交（外部锚点）→ 再运行 → 全量导入。

## 首批正式批次（r1030-formal-a1）

- 组：A_same_model；产品：Codex CLI（codex-cli 0.163.0，隔离 CODEX_HOME，`base_url=https://api.deepseek.com`，wire `responses`）+ DSH CLI（0.2.0-rc.2，`bench-cli` profile，provider `deepseek-official`，wire `anthropic-messages`）。
- 模型 `deepseek-flash`、思考档 low、联网关、SKILL 关；工作区在 `~/bench-workspaces/r1030/<product>/<case>/`（仓库外，只含 inputs + TASK.md）。
- WorkBuddy 不在本批：路由主机与模型 id 证据缺口，见[准入预检](<../../1-评测方案/准入预检-2026-10-29/README.md>)。
- 每格 n=1（order=1, first）；全量导入，不选最高分；infrastructure 失败仅以 selection=null 诊断事件登记，不补 0、不替跑冲分。

## 信任边界（继承 v1）

SHA 封条不是数字签名；语义审查、可信证据作者与人工裁定（证据有效/无污染/最终裁定）是机器校验之外的明确信任边界。官方 host + alias 仍不能证明服务端权重 build 一致。
