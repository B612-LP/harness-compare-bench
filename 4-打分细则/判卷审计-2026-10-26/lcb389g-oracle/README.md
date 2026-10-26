# lcb389g-oracle：ABC389G「Odd Even Graph」独立参考解（候选 staging solution）

日期：2026-10-26 ｜ 产物负责人：lcb389g-oracle（teammate） ｜ 对应未知登记：`lcb-389g-oracle`

## 结论（三选一）：**可入 staging solution**

`solution_abc389_g.py` 已按「层级扩展 DP / 生成函数」方向实现并通过全部可得证据的真实跑测，
建议作为 `2-用例/lcb-recent-hard-4/solution/abc389_g.py` 重放夹具的替换候选。
**是否替换由 Lead 决定**（登记 next_step 约束）；替换后须用本仓 checker 重跑 `--selftest` 与 oracle 回归。

## 实现标注：**editorial-converged**

- 本次工作通过检索看到了官方 editorial 的核心刻画（按距离分层 + 「每个距离 i 的点至少连 1 个距离 i-1 的点」+ 同层边自由），
  与登记 next_step 指的「层级扩展 DP/生成函数」同方向，故按任务规则如实标 **editorial-converged**，不作「independent」标注。
- 实现代码为本仓全新独立编写（未复制仓内夹具或任何题解代码）；交叉验证使用与 DP 完全无共享逻辑的
  全枚举器（`brute_force.py`）与 AtCoder 官方抓取样例两条独立路径。
- 引用：
  - 题面（官方）：<https://atcoder.jp/contests/abc389/tasks/abc389_g>（页面存档 `official_page_abc389_g.html`，2026-10-26 抓取）
  - Editorial（官方，nok0）：<https://atcoder.jp/contests/abc389/editorial/11929>（仅吸收其「按距离分层」刻画思路）

## 证据分层（重要：夹具 truth 的定位）

| 证据 | 结果 | 性质 |
|---|---|---|
| A. AtCoder 官方样例 3 组（2026-10-26 抓取，存档同目录） | 3/3 PASS | **独立可解性证据**（样例逐字取自官方页） |
| B. `brute_force.py` 全枚举 N∈{2,4,6} × 3 素数，共 9 组 | 9/9 PASS | **独立可解性证据**（逐图 BFS，与 DP 无共享逻辑；连通图总数 1/38/26704 与 OEIS A001187 锚点一致，枚举器自身也经核验） |
| C. `truth.json` 全部 43 组（3 公开 + 40 隐藏）按 checker 同口径实跑 | 43/43 PASS | **仅管路一致性证据**：truth 期望输出出自仓内重放夹具链，本组只证明参考解与夹具链一致，**不作为可解性的独立证据**（夹具链本身未经独立验证——这正是未知登记的问题） |

> 夹具 truth 只能验证判分管路与实现一致性，不能当可解性证据；可解性由 A+B 独立支撑。

## 实测（真实运行，Python 3.9.6，本机 Mac）

日志：`logs/run_tests.stdout.txt`（stdout 原样存档）。复现：
`cd 4-打分细则/判卷审计-2026-10-26/lcb389g-oracle && python3 run_tests.py`

| 项 | 数值 |
|---|---|
| 官方样例 | 3/3（N=4/6/10） |
| 全枚举交叉验证 | 9/9（N=2/4/6 × P∈{998244353, 924844033, 100000039}） |
| truth 43 组 | 43/43（N 覆盖 2..30 全部偶数档 {2,4,…,28,30}） |
| **单组最大耗时** | **1.312s**（`30 100000007`，即 N=30 最坏档） |
| 43 组累计 | 4.693s |
| 限额 | 本仓 checker 单组 10s（AtCoder 官方 TL 为 5s）→ 实测余量 ~7.6×（对 10s）/ ~3.8×（对 5s） |

结构自检（与理论一致）：N=30 输出 407 项（M=29..435）；所有 N>2 时末位（M=C(N,2)）为 0
（完全图下各点到 1 距离全为 1，奇侧 N−1 ≠ 偶侧 1）；N=2 输出 `1`。

## 算法摘要（实现见 `solution_abc389_g.py`）

按 BFS 距离分层 L₀={1}, L₁, …, L_k。连通图 ⟺ 分层 + 满足：
① 每个 Lᵢ(i≥1) 至少一点与 L_{i-1} 相邻；② 无 |i−j|≥2 的跨层边；③ 同层边自由。
固定层大小 (1,b₁..b_k)：标号数 = ∏C(剩余, bᵢ)；边数 GF（x 计边）中，相邻层 a→b
「b 侧每点 ≥1 边」容斥为 Σⱼ(−1)ʲC(b,j)(1+x)^{a(b−j)}，层内 (1+x)^{C(b,2)}。
代换 y=1+x 后每因子仅 b+1 项。DP 状态 (上层大小 a, 偶侧已用 e, 奇侧已用 o)（奇偶由轮次隐含），
值 = y 稀疏多项式；终态要求 e=o=N/2。设 Σ_q c_q y^q，则 M 边答案 = Σ_q c_q·C(q,M) mod P。
N=30 时状态 ≤ ~10³/轮、y 指数 ≤ 435，实测最坏 1.31s。

## 文件清单

| 文件 | 说明 |
|---|---|
| `solution_abc389_g.py` | 参考解（stdin→stdout，Python≥3.9 仅标准库；可直接落位 `solutions/abc389_g.py`） |
| `brute_force.py` | 独立全枚举校验器（N≤6，位运算 BFS，A001187 锚点自检） |
| `run_tests.py` | 跑测脚本（A/B/C 三段 + 计时 + 末行 RESULTS_JSON；只读冻结区） |
| `official_samples.json` / `official_page_abc389_g.html` | 官方样例与页面存档（2026-10-26 抓取） |
| `logs/run_tests.stdout.txt` | 真实运行 stdout 日志（本次实测） |

## 边界与风险

- P 覆盖登记约束全区间（10⁸–10⁹ 素数），truth 已含 5 个不同 P；取模链路（含 C(b,j) ≡ 0 mod P 剔除）已实现。
- 未测 P 整除中间组合数造成大面积零系数的极端组合（约束下 P≥10⁸，C(30,j)≤1.55×10⁸，仅 j=15 一处可能；代码已按 0 系数剔除处理，逻辑安全）。
- 时间盒：实现+全量验证约 15 分钟完成，未触发 45 分钟停止条件。
- 硬约束遵守：未改 `CHANGELOG.md`、未改 `2-用例/`（只读）、未动现有 checker 与夹具、未 git add/commit；
  本目录外无任何写入。

## 给 Lead 的建议

1. 若采纳替换：`cp solution_abc389_g.py 2-用例/lcb-recent-hard-4/solution/abc389_g.py`，
   随后跑 `python3 2-用例/lcb-recent-hard-4/checker.py <run_dir>`（oracle 回归）与 `--selftest`（11 项），
   并按仓库规则申请 CHANGELOG 授权登记。
2. 若暂不替换：本目录作为「可解性实证」存档，未知登记 `lcb-389g-oracle` 的
   「报告中标注该题无仓内可解性实证」一节可据 A+B 证据改写为「已实证可解，候选解在 lcb389g-oracle/」。
