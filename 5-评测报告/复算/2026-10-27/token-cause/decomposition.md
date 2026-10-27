# token-cause：A 组两 CLI token 总量差的三因子算术分解（2026-10-27）

数据源：`per_run.json`（本目录，`token_decompose.py` 生成）。所有数字为对逐场会话轨迹（codex：agent-session rollout；dsh：agent.jsonl）解析的算术结果；分解是**恒等式拆分，不是因果证明**。

- 解析成功 **44/44** 场。

## 1. A 组核心 5 题（r1025-candidates）双 CLI 对照

| case | harness | run（per_run.json 键） | call1_prefix | n_calls | 总量 total | 总输入 | 输出 |
|---|---|---|---:|---:|---:|---:|---:|
| bird-ca-schools-15 | codex | `r1025-candidates/bird-ca-schools-15__codex` | 9,553 | 33 | 1,405,427 | 1,366,556 | 38,871 |
| bird-ca-schools-15 | dsh | `r1025-candidates/bird-ca-schools-15__dsh` | 7,233 | 22 | 715,056 | 687,297 | 27,759 |
| dabstep-payments-10 | codex | `r1025-candidates/dabstep-payments-10__codex` | 9,415 | 23 | 1,440,670 | 1,384,237 | 56,433 |
| dabstep-payments-10 | dsh | `r1025-candidates/dabstep-payments-10__dsh` | 7,097 | 10 | 217,813 | 214,752 | 3,061 |
| exercism-py-6 | codex | `r1025-candidates/exercism-py-6__codex` | 9,020 | 13 | 635,320 | 613,849 | 21,471 |
| exercism-py-6 | dsh | `r1025-candidates/exercism-py-6__dsh` | 6,704 | 16 | 595,108 | 577,279 | 17,829 |
| lcb-recent-hard-4 | codex | `r1025-candidates/lcb-recent-hard-4__codex` | 9,129 | 25 | 859,747 | 826,687 | 33,060 |
| lcb-recent-hard-4 | dsh | `r1025-candidates/lcb-recent-hard-4__dsh` | 6,811 | 18 | 693,354 | 648,114 | 45,240 |
| tb-cargo-plan | codex | `r1025-candidates/tb-cargo-plan__codex` | 8,906 | 15 | 727,150 | 706,064 | 21,086 |
| tb-cargo-plan | dsh | `r1025-candidates/tb-cargo-plan__dsh` | 6,592 | 16 | 569,216 | 538,896 | 30,320 |
| **5 题合计/均值** | codex | `r1025-candidates/*__codex` | 9,205（均值） | 21.8 | 5,068,314 | 4,897,393 | 170,921 |
| **5 题合计/均值** | dsh | `r1025-candidates/*__dsh` | 6,887（均值） | 16.4 | 2,790,547 | 2,666,338 | 124,209 |

5 题总量比 codex/dsh = **1.82×**；call-1 前缀均值比 = 1.34×；调用数均值 codex=21.8 vs dsh=16.4。

## 2. 全 44 场按批汇总（均值/合计，溯源见 per_run.json 的 batch 键）

| batch | harness | 场数 | call1_prefix 均值 | n_calls 均值 | total 均值 | total 合计 |
|---|---|---:|---:|---:|---:|---:|
| r1023-cli-dsf-low | codex | 5 | 9,161 | 5.4 | 80,122 | 400,611 |
| r1023-cli-dsf-low | dsh | 5 | 6,841 | 5.6 | 64,346 | 321,732 |
| r1024-probe-区分度 | codex | 5 | 8,819 | 24.0 | 1,308,175 | 6,540,874 |
| r1024-probe-区分度 | dsh | 5 | 6,499 | 15.2 | 643,996 | 3,219,979 |
| r1025-candidates | codex | 5 | 9,205 | 21.8 | 1,013,663 | 5,068,314 |
| r1025-candidates | dsh | 5 | 6,887 | 16.4 | 558,109 | 2,790,547 |
| r1027-isolated | codex | 1 | 8,809 | 19.0 | 791,308 | 791,308 |
| r1027-isolated | dsh | 1 | 6,843 | 47.0 | 2,369,048 | 2,369,048 |
| r1028-repeats | codex | 6 | 9,204 | 23.8 | 1,269,970 | 7,619,822 |
| r1028-repeats | dsh | 6 | 6,725 | 31.8 | 1,522,210 | 9,133,259 |
| **全部** | codex | 22 | 9,089 | 19.0 | 928,224 | 20,420,929 |
| **全部** | dsh | 22 | 6,742 | 19.3 | 810,662 | 17,834,565 |

44 场合计总量比 codex/dsh = **1.15×**。

## 3. 总量差因子分解（恒等式拆分，c=codex、d=dsh，逐题配对）

定义：`Δtotal = total_c − total_d`；`结构×编排 = (prefix_c−prefix_d)×n_d + (n_c−n_d)×prefix_d`；`余项 = Δtotal − 结构×编排`（= 交叉项 + 对话增长 + 输出差，见下）。**这是代数恒等式，不是因果证明。**

### r1025-candidates（A 组核心 5 题）

| case | Δtotal | 结构×编排 | 余项 | ├ 交叉项 | ├ 对话增长(c−d) | ├ 输出差(c−d) | runs |
|---|---:|---:|---:|---:|---:|---:|---|
| bird-ca-schools-15 | 690,371 | 130,603 | 559,768 | 25,520 | 523,136 | 11,112 | `r1025-candidates/bird-ca-schools-15__codex`+`r1025-candidates/bird-ca-schools-15__dsh` |
| dabstep-payments-10 | 1,222,857 | 115,441 | 1,107,416 | 30,134 | 1,023,910 | 53,372 | `r1025-candidates/dabstep-payments-10__codex`+`r1025-candidates/dabstep-payments-10__dsh` |
| exercism-py-6 | 40,212 | 16,944 | 23,268 | -6,948 | 26,574 | 3,642 | `r1025-candidates/exercism-py-6__codex`+`r1025-candidates/exercism-py-6__dsh` |
| lcb-recent-hard-4 | 166,393 | 89,401 | 76,992 | 16,226 | 72,946 | -12,180 | `r1025-candidates/lcb-recent-hard-4__codex`+`r1025-candidates/lcb-recent-hard-4__dsh` |
| tb-cargo-plan | 157,934 | 30,432 | 127,502 | -2,314 | 139,050 | -9,234 | `r1025-candidates/tb-cargo-plan__codex`+`r1025-candidates/tb-cargo-plan__dsh` |
| **合计(5 对)** | 2,277,767 | 382,821 | 1,894,946 | 62,618 | 1,785,616 | 46,712 | — |

占比（对 Δtotal=2,277,767）：结构×编排 **17%**，余项 **83%**（交叉项 3%、对话增长 78%、输出差 2%；四块相加=100%，符号可负）。

### r1023 + r1024（各 5 题）

| case | Δtotal | 结构×编排 | 余项 | ├ 交叉项 | ├ 对话增长(c−d) | ├ 输出差(c−d) | runs |
|---|---:|---:|---:|---:|---:|---:|---|
| corpus-squeeze | -14,554 | 1,101 | -15,655 | -6,966 | -9,935 | 1,246 | `r1023-cli-dsf-low/corpus-squeeze__codex`+`r1023-cli-dsf-low/corpus-squeeze__dsh` |
| int-sum-sort | 22,113 | 15,605 | 6,508 | 2,318 | 3,121 | 1,069 | `r1023-cli-dsf-low/int-sum-sort__codex`+`r1023-cli-dsf-low/int-sum-sort__dsh` |
| jielong-fullchain | 12,787 | 19,263 | -6,476 | 2,320 | -6,965 | -1,831 | `r1023-cli-dsf-low/jielong-fullchain__codex`+`r1023-cli-dsf-low/jielong-fullchain__dsh` |
| ledger-replay | 27,860 | 1,992 | 25,868 | -4,640 | 27,475 | 3,033 | `r1023-cli-dsf-low/ledger-replay__codex`+`r1023-cli-dsf-low/ledger-replay__dsh` |
| word-freq-report | 30,673 | 19,936 | 10,737 | 4,640 | 4,612 | 1,485 | `r1023-cli-dsf-low/word-freq-report__codex`+`r1023-cli-dsf-low/word-freq-report__dsh` |
| bird-schools15 | 139,936 | 42,811 | 97,125 | 6,960 | 79,451 | 10,714 | `r1024-probe-区分度/bird-schools15__codex`+`r1024-probe-区分度/bird-schools15__dsh` |
| dabstep-dev10 | 2,426,208 | 225,921 | 2,200,287 | 62,640 | 2,084,774 | 52,873 | `r1024-probe-区分度/dabstep-dev10__codex`+`r1024-probe-区分度/dabstep-dev10__dsh` |
| lcb-hard3 | 36,408 | 16,226 | 20,182 | 0 | 16,579 | 3,603 | `r1024-probe-区分度/lcb-hard3__codex`+`r1024-probe-区分度/lcb-hard3__dsh` |
| lcb-v6-hard4 | 614,697 | 147,072 | 467,625 | 27,864 | 437,527 | 2,234 | `r1024-probe-区分度/lcb-v6-hard4__codex`+`r1024-probe-区分度/lcb-v6-hard4__dsh` |
| polyglot-py3 | 103,646 | 31,538 | 72,108 | 4,644 | 63,148 | 4,316 | `r1024-probe-区分度/polyglot-py3__codex`+`r1024-probe-区分度/polyglot-py3__dsh` |
| **合计(10 对)** | 3,399,774 | 521,465 | 2,878,309 | 99,780 | 2,699,787 | 78,742 | — |

占比（对 Δtotal=3,399,774）：结构×编排 **15%**，余项 **85%**（交叉项 3%、对话增长 79%、输出差 2%；四块相加=100%，符号可负）。

### r1028-repeats（3 题 × r2/r3）

| case | Δtotal | 结构×编排 | 余项 | ├ 交叉项 | ├ 对话增长(c−d) | ├ 输出差(c−d) | runs |
|---|---:|---:|---:|---:|---:|---:|---|
| bird-ca-schools-15 | 266,785 | 71,010 | 195,775 | 4,960 | 184,262 | 6,553 | `r1028-repeats/runs/codex__bird-ca-schools-15__r2`+`r1028-repeats/runs/dsh__bird-ca-schools-15__r2` |
| bird-ca-schools-15 | -37,582 | 33,150 | -70,732 | -4,960 | -78,205 | 12,433 | `r1028-repeats/runs/codex__bird-ca-schools-15__r3`+`r1028-repeats/runs/dsh__bird-ca-schools-15__r3` |
| dabstep-payments-10 | 341,223 | 65,503 | 275,720 | -14,874 | 290,041 | 553 | `r1028-repeats/runs/codex__dabstep-payments-10__r2`+`r1028-repeats/runs/dsh__dabstep-payments-10__r2` |
| dabstep-payments-10 | -778,866 | 25,585 | -804,451 | -34,706 | -760,069 | -9,676 | `r1028-repeats/runs/codex__dabstep-payments-10__r3`+`r1028-repeats/runs/dsh__dabstep-payments-10__r3` |
| tb-cargo-plan | -103,650 | 6,243 | -109,893 | -19,816 | -94,807 | 4,730 | `r1028-repeats/runs/codex__tb-cargo-plan__r2`+`r1028-repeats/runs/dsh__tb-cargo-plan__r2` |
| tb-cargo-plan | -1,201,347 | -42,602 | -1,158,745 | -49,540 | -1,078,841 | -30,364 | `r1028-repeats/runs/codex__tb-cargo-plan__r3`+`r1028-repeats/runs/dsh__tb-cargo-plan__r3` |
| **合计(6 对)** | -1,513,437 | 158,889 | -1,672,326 | -118,936 | -1,537,619 | -15,771 | — |

占比（对 Δtotal=-1,513,437）：结构×编排 **-10%**，余项 **110%**（交叉项 8%、对话增长 102%、输出差 1%；四块相加=100%，符号可负）。

注：同题配对键 = (batch, case, 重复轮次)；未配对场（不进分解表，仅入 per_run.json）：`r1027-isolated/runs/codex__tb-cargo-plan`。

**口径说明**：A 组 codex 顶层 `agent.jsonl` 只含 1 条 `turn.completed`（末次全场累计），真实逐调用取自 `agent-session/rollout-*.jsonl` 的 `token_count`（`total_token_usage` 为全场累计、`last_token_usage` 为单次）；两来源末次累计一致性 **22/22 场 match**（字段 `cross_check_turn_completed`）。dsh 无 rollout，逐调用来自 `agent.jsonl` 的 `status/step_end.usage`。题给两因子公式的交叉项 `(n_c−n_d)(prefix_c−prefix_d)` 在 n_c≈n_d 时数值有限，公式可用；解读仍推荐下表精确三因子。

### 3-sup. 精确三因子拆分（三块相加恰等于 Δtotal）

对任一会话 `total = prefix + G + out`（G = 输入合计 − call-1 前缀，即首调之后的全部输入：多调用对话复利 + 新增轮次）。于是 `Δtotal = (prefix_c−prefix_d) + (G_c−G_d) + (out_c−out_d)` 恒等成立。「调用数」不单独成项：其效应并入增长差 G。②为负 = dsh 增长更快（抵消 codex 前缀差）。

| 范围 | Δtotal | ① call-1 前缀差 | ② 对话增长差(c−d) | ③ 输出差 | 占比 ①/②/③ |
|---|---:|---:|---:|---:|---|
| r1025 bird-ca-schools-15 | 690,371 | 2,320 | 676,939 | 11,112 | 0% / 98% / 2% |
| r1025 dabstep-payments-10 | 1,222,857 | 2,318 | 1,167,167 | 53,372 | 0% / 95% / 4% |
| r1025 exercism-py-6 | 40,212 | 2,316 | 34,254 | 3,642 | 6% / 85% / 9% |
| r1025 lcb-recent-hard-4 | 166,393 | 2,318 | 176,255 | -12,180 | 1% / 106% / -7% |
| r1025 tb-cargo-plan | 157,934 | 2,314 | 164,854 | -9,234 | 1% / 104% / -6% |
| r1023 5 题合计 | 78,879 | 11,600 | 62,277 | 5,002 | 15% / 79% / 6% |
| r1024 5 题合计 | 3,320,895 | 11,602 | 3,235,553 | 73,740 | 0% / 97% / 2% |
| r1025 5 题合计 | 2,277,767 | 11,586 | 2,219,469 | 46,712 | 1% / 97% / 2% |
| r1028 6 场合计 | -1,513,437 | 14,872 | -1,512,538 | -15,771 | -1% / 100% / 1% |
| 全部配对（21 对） | 4,164,104 | 49,660 | 4,004,761 | 109,683 | 1% / 96% / 3% |

## 4. 消融批（r20261027-ablation，外部目录只读）

| cell | result.json | call1_prefix | n_calls | total | 状态 |
|---|---|---:|---:|---:|---|
| dabstep-payments-10__codex-base | ✓ | 9,330 | 39 | 2,944,885 | 已解析 |
| dabstep-payments-10__codex-skill | ✓ | 9,523 | 33 | 2,354,945 | 已解析 |
| dabstep-payments-10__codex-gpt | ✓ | 12,546 | 7 | 201,483 | 已解析 |
| dabstep-payments-10__dsh-base | ✓ | 6,383 | 62 | 4,103,911 | 已解析 |
| dabstep-payments-10__dsh-skill | ✓ | 6,673 | 47 | 2,317,382 | 已解析 |
| tb-cargo-plan__codex-base | ✓ | 8,820 | 19 | 751,808 | 已解析 |
| tb-cargo-plan__codex-skill | ✓ | 9,013 | 18 | 797,945 | 已解析 |
| tb-cargo-plan__codex-gpt | ✓ | 12,070 | 8 | 162,005 | 已解析 |
| tb-cargo-plan__dsh-base | ✓ | 5,875 | 20 | 648,949 | 已解析 |
| tb-cargo-plan__dsh-skill | ✓ | 6,165 | 19 | 712,540 | 已解析 |
- dabstep-payments-10 技能注入体积（codex-skill − codex-base）：**193** tokens（9,523 − 9,330）。

- dabstep-payments-10 原生模型前缀差（codex-gpt − codex-base）：**3,216** tokens（12,546 − 9,330）。

- tb-cargo-plan 技能注入体积（codex-skill − codex-base）：**193** tokens（9,013 − 8,820）。

- tb-cargo-plan 原生模型前缀差（codex-gpt − codex-base）：**3,250** tokens（12,070 − 8,820）。


## 5. 结论草案（待更多轮次验证；数字溯源见各表 run 列与 per_run.json）

1. **形态**：两 CLI 都是「小前缀起步、多调用滚动增长」。真实调用数均值 codex 19.0 vs dsh 19.3（dsh 略多但同量级）；call-1 前缀均值 codex 9,089 vs dsh 6,742（codex 首调多约 2,347 tok，主要为系统提示+工具模式差异）。A 组 codex 顶层 agent.jsonl 只存末次累计（turn.completed×1），逐调用真值在 agent-session rollout 的 token_count，两来源末次累计 22/22 场一致。

2. **体量**：总量比全 44 场合计 1.15×、r1025 核心 5 题 1.82×；同题配对比值区间 0.32×–6.61×（最小 r1028-repeats/runs/codex__tb-cargo-plan__r3，最大 r1025-candidates/dabstep-payments-10__codex）；单场均值 codex 928,224 vs dsh 810,662。

3. **三因子占比（全部 21 对配对，Δtotal=4,164,104）**：前缀差 49,660（1%）、对话增长差 4,004,761（96%）、输出差 109,683（3%）。主导项是**② 对话增长差**；输出两侧几乎相当，总量差基本是输入侧（前缀结构 + 对话增长斜率）之争。

   斜率佐证：单次调用平均输入 codex 47,335 vs dsh 40,771 tok（调用总数 418 vs 424，几乎相同）。即多出来的量是 codex 每次调用回放的上下文更大；codex reasoning_output_tokens 合计 351,501 tok（dsh 轨迹无 reasoning 拆分，无法对齐比较）——「codex 将 reasoning 项回放进后续调用上下文」是待验证假设，非本文结论。

   r1025 核心 5 题（Δtotal=2,277,767）：前缀差 1% / 对话增长差 97% / 输出差 2%。

4. **缓存命中结构**：输入中命中占比 codex 97.4% vs dsh 96.7%。两 CLI 均高度依赖缓存读，总量差主要发生在「未命中」与「输出」的绝对量上，而非缓存策略差异。

5. **边界**：以上为恒等式/会计拆分，不构成因果证明；n=1/格，不排除单场波动（r1028 r2/r3 同题重跑间 codex 调用数与前缀即有明显波动）；call-1 前缀代理含首条用户消息，跨题不可比，仅同题同款内可比；codex 首调前缀略高于 dsh 的解释（系统提示/工具模式）是假设，待消融批补齐后用 codex-skill−codex-base、codex-gpt−codex-base 验证。

