# r1022-cbase-deepseekflash —— C 组裸模型基线批次（2026-10-22）

> **定位**：统一模型定案（DeepSeek V4.1-Flash）后的第一批现场。C 组裸模型基线：验证「无 Harness 时模型能走多远」，为 A−C 归因提供底数；同时是下轮验收「判卷器也要被测试」的实战样例（5 个 checker 各自对真实模型产物判分）。
> **协议**：与 r1016x 老现场同款（`infra/bare_model.py`）：请求体 `{"model", "input": 任务书原文}` 打 `/responses` 端点，无系统提示、无工具、单轮、模型看不到输入文件；答案文本按用例约定落盘为产物，再交 `2-用例/<题>/checker.py <run_dir>` 判分。
> **跑批工具**：[`tools/bare_run.py`](tools/bare_run.py)（key 只从环境变量读取，未落任何文件）。

## 结果（2026-10-22，binary headline，全部 0/5）

| 用例 | reward | weighted | 失败项 | tokens（总/其中 reasoning） |
|---|---|---|---|---|
| int-sum-sort | 0 | 20/100 | format_strict, sum_line, count_line, sorted_block | 1,831 / 1,598 |
| word-freq-report | 0 | 20/100 | format_strict, total_line, distinct_line, top5_block | 3,916 / 3,352 |
| jielong-fullchain | 0 | 20/100 | resolution_schema, plan_schema, plan_assignment | 35,736 / 30,212 |
| ledger-replay | 0 | 20/100 | final_state_*, anomalies_*, money_conservation | 7,899 / 6,302 |
| corpus-squeeze | 0 | 10/100 | artifacts_exist, decompress_constraints, roundtrip, ratio | 757 / 160 |

每个 `*_bare1/` 运行目录内含：`bare-request.json`（原文请求）、`bare-response.json`（原文响应）、产物、输入副本、`meta.json`、`RESULTS_JSON/result.json`。

## 发现（按「现象 / 线索 / 验证状态」表述）

1. **现象**：裸模型 5/5 全 0，且失败形态不是「不会算」而是「执行结构缺失」——无工具读不到 `/app/*` 输入，部分题直接幻觉产物。
   线索：int-sum-sort 的 request 里根本没有输入数据（协议如此），响应却给出确定数字 → 编造。
   状态：已验证（request/response 原文在案可复核）。
2. **现象**：deepseek-flash 默认思考档全开（每个响应都有大额 reasoning_tokens，jielong 一题烧 30,212 reasoning tokens 仍 0 分）。
   线索：vault 端点说明「请求体加 thinking.enabled 可控」；本批为忠实复刻老协议未传 thinking 参数。
   状态：**未钉死**——按统一模型三变量纪律，后续批次应显式钉 thinking 档位并登记（见未知 1）。
3. **现象**：与 2026-10-16 mimo 批次 C 组 0/2「试图调用不存在的工具」跨模型一致。
   状态：两个模型各 1 次采样，方向一致；样本量小，不下强结论。
4. **本批对归因的含义**：C 组地板 = 0 且两代模型一致 → **Harness 的文件/工具执行层贡献了全部产物分**；「老题满分区间无区分度」的对照（A 组 hard vs 老题）仍缺 A 组现场——见未知 2。

## 未知登记

| # | 未知 | 影响 | 下一步 / 停止条件 |
|---|---|---|---|
| 1 | thinking 档位未钉死（本批全为模型默认） | C 组分数对 thinking 档位的敏感性未知 | 下批起显式传 `thinking`+`reasoning_effort` 并分档各跑 1 题；若同题不同档 reward 差异 >0 即钉档入方案 |
| 2 | A 组（Codex/DSH × deepseek-flash）现场缺失 | 「hard 题低分 vs 老题满分」的对照暂不能在本批内闭合 | 需 CLI 跑批环境（本机无 node/codex/dsh/docker；老链路在宿舍机 WSL）。补齐环境后 5 题 × 2 harness + 空跑闸门一次补齐 |
| 3 | 多产物题的文本→文件抽取用了启发式（围栏配对/顺序兜底） | 可能宽松放行错误产物（倾向多扣不冤枉） | 抽取注记在 meta.json `answer_to_artifacts` 可复核；必要时对 jielong/ledger 补跑一次人工核验 |

## 复跑

```bash
DEEPSEEK_API_KEY=sk-... python3 3-表现现场/r1022-cbase-deepseekflash/tools/bare_run.py [--only <slug>]
```

成本：全批 5 题 ≈ 5.0 万 tokens（V4.1-Flash 费率下可忽略）。
