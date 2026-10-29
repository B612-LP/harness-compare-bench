# 可重复性 n=3 验收报告（r1031-variance-n3，2026-10-29）

- 角色：judge 独立验收（只读产物：预注册 + runs 产物 + 冻结合同；未读 builder 过程叙述）
- 依据：[PREREGISTRATION.md](<../../1-评测方案/自动循环L1-2026-10-29/PREREGISTRATION.md>)（封印 `be39fc2`，文件 sha256 `2e408196…70c8bc9`）包A 锁定分析计划 + [AMENDMENT-1](<../../1-评测方案/自动循环L1-2026-10-29/AMENDMENT-1.md>)（引 commit `999d345`，文件 sha256 `542e4a7b…446d9`）
- 验收工具：[verify_var_n3.py](<verify_var_n3.py>) sha256 `e6e9a6e5…98aab5`（AMENDMENT-1 权威版，阶段2未改动）；核验矩阵 [verify-matrix-r1031-n3.json](<verify-matrix-r1031-n3.json>)；r1030 自检矩阵 [verify-matrix-selftest-r1030.json](<verify-matrix-selftest-r1030.json>) sha256 `31534cec…f7d09c`
- **n=3 只作描述，不作任何排名声明**（预注册总则#5）

## 矩阵 summary 语义声明

核验矩阵的 `passed/failed` **仅覆盖 a–d 四项过程检查**（checker SHA / meta 时序与锚点 / 加权分独立重算 / 轨迹完整性重扫），**不是**「发布值全部验证通过」。发布值的核验结论以下文「known 值对照表」与逐场重算表为准。r1031 矩阵 summary 为 0 pass / 20 fail，成因全部为下述三类已解释项，无任何分值性不一致：

| 计数 | 检查项 | 成因 | 定性 |
|---|---|---|---|
| b 20/20 fail | meta 时序 | 全批 20 场产物均无 `registered_at` 字段（批次内外、含 runs-summary 均无），`registered_at < started_at` 与 `registered_at ≥ 锚点` 两个子检查**不可验证**；可验证部分全过：`preregistration_commit=be39fc2` 20/20 ✓，`started_at`（13:35:45–14:29+08:00）全部晚于封印提交 `be39fc2`（13:22:39+08:00）✓ | 缺口披露（D1） |
| c 2/20 fail | 加权重算 | 仅 codex cargo r2/r3：收据 `reported` 写成 2 位小数（70.37/81.48），本工具按 r1030 口径（8 位精度）比对报不一致；**算术完全一致**（19/27、22/27），checker.stdout/meta/独立重算三方同值 | 格式偏差（D2） |
| d 1/20 fail | 轨迹完整性 | 仅 codex cargo r2：4 条 `reference/` 命中，经独立行级复核全部为推理散文回声，0 条进入工具调用载荷（见下） | benign-reviewed(lead-adjudicated)（D3） |
| a 20/20 pass | checker SHA | 每场 receipt SHA = 冻结 config.json `case_snapshots` SHA，20/20 一致；freeze.lock 17 pins 中 16 pins 实哈希一致，1 pin（`1-评测方案/准入预检-2026-10-29/README.md`）为包C 授权增补（wb-preflight-r2）所致漂移，评分关键 pins（freeze.py/config.json/work-registry/schema）全部完好 | ✓ + 漂移说明（D4） |

## known 值对照表（claimed vs recomputed，显式列示）

r1030 十场 known 值（自检矩阵复算，r1031 各场 rep1 取此值进入 3-rep 分析）：

| 产品 | 场 | claimed | 来源 | recomputed | match |
|---|---|---|---|---|---|
| codex | bird-ca-schools-15 | 93.33 | r1030 README 结果矩阵 | 93.33 | ✓ |
| codex | dabstep-payments-10 | 70.0 | 同上 | 70.0 | ✓ |
| codex | exercism-py-6 | 100.0 | 同上 | 100.0 | ✓ |
| codex | lcb-recent-hard-4 | 100.0 | 同上 | 100.0 | ✓ |
| codex | tb-cargo-plan | 81.48 | 同上 | 81.48 | ✓ |
| codex | weighted 总分 | 444.81 | 同上 | 444.81 | ✓ |
| codex | headline | 3/5 | 同上 | 3 | ✓ |
| dsh | bird-ca-schools-15 | 100.0 | r1030 README 结果矩阵 | 100.0 | ✓ |
| dsh | dabstep-payments-10 | 70.0 | 同上 | 70.0 | ✓ |
| dsh | exercism-py-6 | 100.0 | 同上 | 100.0 | ✓ |
| dsh | lcb-recent-hard-4 | 100.0 | 同上 | 100.0 | ✓ |
| dsh | tb-cargo-plan | 74.07 | 同上 | 74.07 | ✓ |
| **dsh** | **weighted 总分** | **414.07** | r1030 README 总行 / 阶段报告-v4.1 / 预注册包A（gap₀=30.74） | **444.07** | **✗（勘误披露本体）** |
| dsh | headline | 3/5 | r1030 README 结果矩阵 | 3 | ✓ |

dsh 总分行即 AMENDMENT-1（`999d345` + `542e4a7b…`）勘误的事实锚点：claimed 414.07 产物不可复现，recomputed 444.07 由 checker.stdout / score-receipt / meta 与 README 自身逐场行（100+70+100+100+74.07）四方一致给出；judge 自检、auditor 盲审、修正案三方收敛。`official-main-table.json` 本身无逐行分值（ranking=null），414.07 的载体为 README/阶段报告/预注册文本。成因（bird 行误抄 dabstep 的 70.0）在修正案中标注为**假说**。

## 五段结论

### 一、观察

20 场（product ∈ {codex, dsh} × case ∈ 5 × rep ∈ {2,3}）全部完成、无重试（transport_retries 均为 0），rep1 = r1030 十场。逐 case 3-rep 分布（weighted / reward；r=reward）：

**codex**

| case | rep1 (r1030) | rep2 (r1031) | rep3 (r1031) | reward 序列 | 翻转 |
|---|---|---|---|---|---|
| bird-ca-schools-15 | 93.33 / r=1 | 100.0 / r=1 | 100.0 / r=1 | 1,1,1 | 0 |
| dabstep-payments-10 | 70.0 / r=0 | 70.0 / r=0 | 80.0 / r=1 | 0,0,1 | **1** |
| exercism-py-6 | 100.0 / r=1 | 100.0 / r=1 | 100.0 / r=1 | 1,1,1 | 0 |
| lcb-recent-hard-4 | 100.0 / r=1 | 100.0 / r=1 | 100.0 / r=1 | 1,1,1 | 0 |
| tb-cargo-plan | 81.48 / r=0 | 70.37 / r=0 | 81.48 / r=0 | 0,0,0 | 0 |
| **weighted 总分** | **444.81** | **440.37** | **461.48** | | |
| **headline** | **3/5** | **3/5** | **4/5** | | |

**dsh**

| case | rep1 (r1030) | rep2 (r1031) | rep3 (r1031) | reward 序列 | 翻转 |
|---|---|---|---|---|---|
| bird-ca-schools-15 | 100.0 / r=1 | 100.0 / r=1 | 100.0 / r=1 | 1,1,1 | 0 |
| dabstep-payments-10 | 70.0 / r=0 | 70.0 / r=0 | 70.0 / r=0 | 0,0,0 | 0 |
| exercism-py-6 | 100.0 / r=1 | 100.0 / r=1 | 100.0 / r=1 | 1,1,1 | 0 |
| lcb-recent-hard-4 | 100.0 / r=1 | 100.0 / r=1 | 100.0 / r=1 | 1,1,1 | 0 |
| tb-cargo-plan | 74.07 / r=0 | 70.37 / r=0 | 74.07 / r=0 | 0,0,0 | 0 |
| **weighted 总分** | **444.07** | **440.37** | **444.07** | | |
| **headline** | **3/5** | **3/5** | **3/5** | | |

每产品 weighted 总分 3-rep 极差：**codex spread = 21.11**（440.37–461.48，rep1=444.81 居中）；**dsh spread = 3.70**（440.37–444.07）。headline 3-rep 分布：codex {3,3,4}，dsh {3,3,3}。逐 case reward 翻转合计：codex 1（dabstep rep2→rep3 翻绿 70.00→80.00，跨阈值 0.8 线），dsh 0。以上均为 n=3 描述，不构成排名。

### 二、证据

- 独立重算：全部 150 个 case×rep 分值（r1031 20 场 × 5 题 = 100，r1030 自检 10 场 × 5 题 = 50）从 `checker.stdout.json` 按 GUARDS-不计分、分母=全题数（15/10/6/4/27）独立重算，与 checker.stdout、meta、score-receipt 三方逐一对账；唯一不一致为 D2 所列 2 个收据精度格式项（算术一致）。
- checker 冻结链：20/20 场 receipt `checker_sha256` 与冻结 `config.json case_snapshots` 一致（cargo=`d84b1111…`，5 题各自 SHA 见矩阵）；freeze.lock 16/17 pins 实哈希一致（D4：包C 授权增补的准入预检 README 漂移，评分关键 pins 完好）。
- 轨迹完整性：20 场独立重扫八类越界模式，19 场 0 命中；codex cargo r2 共 4 条 `reference/` 命中——行级复核（judge 独立执行）：4/4 位于 assistant `reasoning` 文本及其 `item_completed` 镜像（内容为模型复述「instructions say don't seek grader/reference/test」纪律原文并自行决定实现），**0 条位于 function_call/工具调用载荷**；与 lead 裁定一致，归入 **benign-reviewed(lead-adjudicated)，origin=prose-echo（散文回声）**，与 r1030 DSH 的 runtime-injection（运行时注入）分列、不混写。builder 翻案以 meta `corrections` 条目落盘（非静默改写），矩阵 `own_artifacts/agreement` 字段可见。
- 时序锚点：20/20 场 `preregistration_commit=be39fc2` ✓；`started_at` 全部 ≥ 13:35:45+08:00，晚于封印提交 13:22:39+08:00 ✓；`registered_at` 缺失（D1 披露，见下）。
- 工程项核验（预注册包A 随批项）：a) stdout 完整落盘 ✓（codex 各场 `stdout_bytes` 125,526–620,069 字节，注明无 8192 截断路径；dsh 侧 meta 无对应字段，D5 披露）；b) 逐调用 usage 含 cache 字段入库 ✓（`per_call` 明细在库）。
- 分账：本批 product_run 20 场；验收工具自检（r1030 十场）与离线复算均为独立台账，未与产品运行混计。

### 三、解释

按 AMENDMENT-1 主判据 **gap₀ = 0.74**（= |444.81 − 444.07|，产物可复现值）：

- codex spread 21.11 ≥ 0.74 → 触发预注册结论分支：「**r1030 产品差与重复性方差不可区分**」；
- dsh spread 3.70 ≥ 0.74 → 同上。

敏感性对照（原锁定值 gap₀ = 30.74，已降级）：两产品 spread 均小于 30.74，比值 codex = 30.74/21.11 = **1.46**，dsh = 30.74/3.70 = **8.31**。若未做锚点勘误，该比值会被误读为「产品差远大于重复性方差」；校正后的实情相反：r1030 单场产品差（0.74）比任一产品的重复性波动（3.70 / 21.11）小一个数量级以上。这同时回答了 r1030 README 勘误块的 O5 悬置——「单场方差」判读句在 n=3 下获得直接支持：codex 的 headline 翻转（3/5→4/5）由 dabstep 单题组跨阈值（70→80）驱动，而两产品 3-rep 总分区间大量重叠（codex 440.37–461.48，dsh 440.37–444.07）。两种判据口径下均**不产生任何排名**。

### 四、未排除因素

按老师验收要求#4，以下未知/缺口如实列示，不折算、不记为失败：

- **D1（defect｜证据缺口）**：r1031 全批无 `registered_at` 产物字段，「注册先于运行」只能以 `preregistration_commit=be39fc2` + `started_at` 时序间接佐证，无法逐场复核注册时间戳。影响： prospective 抽样的可复核性降级为锚点级。下一步：lead 决定是否要求 builder 补登记台账（仅登记事实，不改历史产物）；停止条件：用户放行下一循环前明确该字段是否列为下轮 runner 必备项。
  **lead 裁决（2026-10-29 14:48+08:00 记录）**：不回填——事后补戳比缺失更糟；注册先于运行已由可验证锚传递证明（封印 `be39fc2`@13:22:39 < 首场 `started_at` 13:35:45，20/20 场 started_at 均晚于封印，`preregistration_commit` 全场落盘）。D1 以「缺口披露+补偿锚」闭项入问题池；下一轮 runner 必备字段 `registered_at`（值=预注册封印提交的时间戳引用），停止条件=下一循环启动前完成 runner schema 修订。
- **D2（observation｜格式偏差）**：codex builder 收据 `reported` 为 2 位小数（r1030 为 8 位），2 场受影响，算术无差。下一步：统一收据精度规范。
- **D3（已裁定）**：codex cargo r2 的 4 条散文回声命中，lead 裁定 benign-reviewed；judge 独立行级复核无矛盾。若未来复核发现真实访问证据，裁定让位于证据（升级通道已约定）。
- **n=3 样本量**：spread/翻转均为小样本描述；rep1 与 rep2/3 由两代 runner 产出（r1030 曾披露归档缺陷 r1030#1 并修复；r1031 为新 runner 且 stdout 不截断），runner 代际差异未单独消融。
- **provider-cache 语义（预注册工程项 b 观察点）**：responses 路由 20 场 `cache_creation_tokens` 全为 0，而 `cache_read_tokens` 合计 19,159,168 tokens（逐调用明细在库）。「只读不写」是路由侧计费/回传语义还是真实缓存行为，未经请求级证据验证——不排除其影响长任务成本模型，但不影响本轮任何分值。
- **builder 间 schema 差异（observation）**：dsh 侧 meta 无 `selection/attempts/stdout_bytes` 字段、`transport_retries` 为列表型（codex 为整型）；均为记账层差异，零重试事实两方一致。
- **D4（observation）**：freeze.lock 1 pin 漂移（准入预检 README，包C 授权增补）；建议下轮封印对「活文档 pin」与「合同 pin」分列管理。
- r1025/r1027 历史同分格局与本轮 dabstep/cargo 双低格局的一致性属描述性对齐，未做统计检验。

### 五、可复现实验

```bash
# 自检（r1030 十场，只读）——复现 known 值对照表
python3 "5-评测报告/可重复性-n3-2026-10-29/verify_var_n3.py" --profile r1030 \
  --out "5-评测报告/可重复性-n3-2026-10-29/verify-matrix-selftest-r1030.json"
# 阶段2验收（r1031 二十场，只读）
python3 "5-评测报告/可重复性-n3-2026-10-29/verify_var_n3.py" --profile r1031 \
  --out "5-评测报告/可重复性-n3-2026-10-29/verify-matrix-r1031-n3.json"
# 判据覆写示例（默认已按 AMENDMENT-1：主 0.74 / 敏感性 30.74）
#   --gap0-main 0.74 --gap0-sensitivity 30.74
```

哈希链：工具 `e6e9a6e50f8cf0a6f043e6f242bada54842d852ee011885e2b5542a0ec98aab5`；自检矩阵 `31534cec32ffdda781f2ea2127acd1b015eb6f8e06eabfde7aab5bdf89f7d09c`；r1031 矩阵（本报告依据，见同目录 [verify-matrix-r1031-n3.json](<verify-matrix-r1031-n3.json>)）；PREREGISTRATION（封印 `be39fc2`）sha256 `2e408196…70c8bc9`；AMENDMENT-1 引 `999d345` + sha256 `542e4a7b…446d9`。产物边界说明：`292cf18`/`474a8ed` 仅作勘误链证据，不作产物边界。

---

*judge 出品 · 五段结构 · n=3 只描述不排名 · 结论不产生排名*
