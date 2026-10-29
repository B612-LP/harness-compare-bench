# L4 六类分账（candidate r1，机器生成）

- 生成：2026-10-30T00:29:23+08:00（脚本实钟）；builder sha256_8=aaeafc81
- 基准：D=bb14897a E=5674de65 registered_at=2026-10-29T23:13:56+08:00
- 计划槽：**35 = 17 product + 18 probe**；activity_group 合计 **18**（group≠次数≠用例）
- 状态：candidate，待 lead 审核+串行登记；formal_admission 本账不判定（judge/lead 主裁），raw 原分照实保留。

## 1. product_run（计划 17）

- executed **16/17**，not_executed 1（WB bird，基础设施 startup-render-not-ready，score=null 不折算）
- codex 6/6：dab 70.0×3、cargo 70.37037037×3；无重启/无补跑（X 系 7/7）
- dsh 6/6：dab 70/80/70、cargo 70.37037037/74.07407407/74.07407407；**usage 维度 null 原样保留（marker 缺陷）**；gate formal=0；recoveries 晚补档独立
- wb 4/5 执行：dab 50.0、exercism 100.0、lcb 100.0、cargo 70.37；bird not_executed
- 每槽 evidence（meta/notexecuted 路径+sha256）见 six-ledger.json；逐槽 formal 归 judge。

## 2. bare_model_probe（计划 18）

- executed **18/18**（每槽恰 1 次 HTTP 200；6 pair=3 wire×2 block）；REPORT missing 断言已经 dated erratum 2 更正（C10 PASS；映射层=coverage limitation，见 AUDIT §AUD-D1/C5c）。

## 3. interface_preflight

- **事故独立**：accidental CLI start ×1，chatgpt.com 401 证实；**DeepSeek provider requests=unknown**；证据 incomplete；不并 35 槽/不得称零调用
- cache dryrun ×1；wb 零模型预检（次数未持久=unknown/null）

## 4. self_test（8 组，group≠用例数）

- selftest:lead-seal：test_case_n=unknown/null
- selftest:l4-execution-gate：test_case_n=unknown/null
- selftest:l4-execution-replay-dual：test_case_n=unknown/null
- selftest:cache-probe：test_case_n=32（receipt_at=2026-10-29T21:04:05+08:00，以落盘收据版本为准）
- selftest:codex-runner：test_case_n=73（receipt_at=2026-10-29T21:52:45+08:00，以落盘收据版本为准）
- selftest:wb-gateway：test_case_n=unknown/null
- selftest:judge-fake-e2e：test_case_n=unknown/null
- selftest:auditor-tools：test_case_n=11

## 5. offline_recompute（3 组）

- dual-archive codex 6 槽投影（等价模拟完备性终审留 judge）；cache erratum sidecar（judge 独立核）；auditor 五阶段独立复算收据

## 6. grading_regression = 0（不适用）

- 本环无 checker 修订：contract 继承冻结 checker 字节；不为凑六账新跑

## 未知登记（null/unknown 不捏造）

- l4-20261029-cli-dsh-dabstep-payments-10-r1: usage_observation=null(marker 缺陷原样保留)
- l4-20261029-cli-dsh-tb-cargo-plan-r1: usage_observation=null(marker 缺陷原样保留)
- l4-20261029-cli-dsh-tb-cargo-plan-r2: usage_observation=null(marker 缺陷原样保留)
- l4-20261029-cli-dsh-dabstep-payments-10-r2: usage_observation=null(marker 缺陷原样保留)
- l4-20261029-cli-dsh-dabstep-payments-10-r3: usage_observation=null(marker 缺陷原样保留)
- l4-20261029-cli-dsh-tb-cargo-plan-r3: usage_observation=null(marker 缺陷原样保留)
- l4-20261029-wb-gateway-dabstep-payments-10-r1: usage_observation=null(marker 缺陷原样保留)
- l4-20261029-wb-gateway-exercism-py-6-r1: usage_observation=null(marker 缺陷原样保留)
- l4-20261029-wb-gateway-lcb-recent-hard-4-r1: usage_observation=null(marker 缺陷原样保留)
- l4-20261029-wb-gateway-tb-cargo-plan-r1: usage_observation=null(marker 缺陷原样保留)
- wb-gateway 预检次数：unknown（未持久）
- WB actual_request_model/actual_gateway：null（managed unknown，不参与同路由归因）
- 事故 DeepSeek provider requests：unknown（incomplete）

---

**live_doc_drift: none（0 项）**

机器产物：six-ledger.json（同构全量数据，含逐槽 sha256/输入哈希）；本文件由 ledger_build.py 同步渲染。
