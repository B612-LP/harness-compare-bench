# 全量只读重判管线（replay_all）· 口径与首跑收据

工具：[replay_all.py](<replay_all.py>) ｜ 逐行明细：[replay-all-results.json](<replay-all-results.json>) ｜ 首跑日期：2026-10-27

一条命令把 [运行总账-2026-10-24.json](<../../5-评测报告/运行总账-2026-10-24.json>) `runs[]` 全部 95 行
按**现行** `2-用例/<case>/checker.py` 只读重判一遍，输出「重判 vs 总账记载」逐行对照 + 覆盖率报告，
作为阶段报告「证据与复核」维度的常驻证据。本脚本是
[判卷审计-2026-10-27 收紧批回放](<../判卷审计-2026-10-27/checker-tightening-B2-B8-B12-13-14/replay_2026_10_27.py>)
（3 题 × 24 场）的泛化版：同一临时副本协议，行集扩展到总账全部行。

## 1. 首跑结果（2026-10-27）

| 指标 | 数值 |
|---|---:|
| 总账 runs[] 总行数 | 95 |
| **可重判** | **57** |
| 一致（reward+weighted 与总账 raw 完全一致） | **47** |
| 已知偏移（bird q26 版本迁移，差异≠翻转） | **10** |
| 不一致 | **0**（未查因不一致 0，重判失败 0） |
| skip | **38**（归档用例 23 / 判定 X 11 / 判分产物不齐 4） |
| 退出码 | 0（= 无未查因不一致且无重判失败） |

按 case 分布（可重判 57 场）：

| case | 可重判 | 一致 | 已知偏移 | 不一致 |
|---|---:|---:|---:|---:|
| bird-ca-schools-15 | 12 | 2 | 10 | 0 |
| dabstep-payments-10 | 18 | 18 | 0 | 0 |
| exercism-py-6 | 8 | 8 | 0 | 0 |
| lcb-recent-hard-4 | 6 | 6 | 0 | 0 |
| tb-cargo-plan | 13 | 13 | 0 | 0 |

**结论：57 场重判全部可解释——47 场与总账逐分一致，10 场为 bird q26 金标 v1.1→v1.2
已收据的合同迁移偏移（非翻转），0 场未查因不一致。**

## 2. 口径

- **只读协议**（沿用先例
  [bird-q26-并入/replay_2026_10_26.py](<../判卷审计-2026-10-26/bird-q26-并入/replay_2026_10_26.py>)）：
  判分一律在 /tmp 临时副本进行——canonical inputs 副本 + 历史判分产物重组（bird/dab 回填
  answers.jsonl、lcb 重组 solutions/、cargo 覆写 inputs/app 代码、exercism 覆写 6 题候选解），
  历史 run_dir 零写入。r1028/r1029 等工作区仍带 v1.1 字节 questions.json，直接对历史目录
  重判会误触 input_integrity 守卫，必须重组。
- **逐行可复核**：每场登记判分产物 SHA-256（`artifact_sha256`）、所用 checker 路径 + SHA-256
  与自报版本（`replay.checker_*`，首跑为 bird `994be0b3…` v1.2-q26-frpm、cargo `d84b1111…`、
  lcb v0.1、dab v0.2、exercism v1.1）、run_dir 解析方式（`run_dir_how`）与耗时。
- **verdict 判定**：
  - `match`：reward 精确相等且 weighted 差 ≤0.005；
  - `known-offset`：仅认 bird q26——[bird-q26 收据 §5](<../判卷审计-2026-10-26/bird-q26-并入/README.md>)
    逐场旧→新分对照表（内嵌工具 `KNOWN_Q26_OFFSET`），且「总账=旧值 且 重判=新值」逐分对上才判；
    对不上按 mismatch 如实列出；
  - `mismatch`：其余一切差异。若 lcb r1029 doubao 复现收紧批收据 §1 已查因的负载超时抖动
    **签名**（reward=1、weighted=75.0、红项 abc389_g），附 `prior_attribution` 既往查因标注、
    不计「未查因」，但 verdict 仍如实记 mismatch。
- **退出码**：0 = 无未查因不一致且无重判失败；1 = 存在未查因不一致或 error；2 = 环境错误。
- **纪律**：只读既有证据与历史 run 目录；不改 checker/truth/总账/CHANGELOG；判分超时单场
  600s，失败记 error 不中断全局。

## 3. 用法

```bash
# 全量重判（约 10~15 分钟，exercism/lcb 实跑测试占大头）
python3 -B 4-打分细则/判卷回归/replay_all.py

# 只做行分类与 run_dir 解析干跑（秒级，验证覆盖率）
python3 -B 4-打分细则/判卷回归/replay_all.py /tmp/plan.json --plan-only

# 自定义输出路径
python3 -B 4-打分细则/判卷回归/replay_all.py /tmp/replay-all-results.json
```

## 4. 覆盖率与 skip 分析（38 行）

| skip 原因 | 行数 | 说明 |
|---|---:|---|
| archived-case（历史用例无现行 checker） | 23 | int-sum-sort / corpus-squeeze / jielong-fullchain / ledger-replay / word-freq-report（各 3，r1021–r1023 早期批）+ lcb-hard3 / lcb-v6-hard4 / polyglot-py3（各 2，r1024 探针批）+ dabstep-dev10（1）——用例已入 `2-用例/_归档-v1`，重判无现行判卷资产 |
| adjudication-X（判定无效，重判无意义） | 11 | r1024 bird-schools15×2、dabstep-dev10×1（truth 读取污染）；r1025 dab__dsh、cargo__codex；r1026 workbuddy dab/lcb/cargo；r1029 workbuddy lcb；r1030 lcb；r20261027-workbuddy-lcb-clean2 lcb（websearch 污染/待修复重算等，详见总账 validity_reason） |
| artifact-missing（候选目录在、判分产物不齐） | 4 | r1028-repeats 四场 tb-cargo-plan（codex/dsh × r2/r3）：现场 workspace 只留输出 flight_plan.json，cargo 判分需被测方修好的 inputs/app 代码（dispatch/aircraft/navigation.py），bench-workspaces/r1028 对应目录已空——历史判分对象未归档，无法只读复算 |

覆盖率：95 行中可重判 57（60%）；在「有现行 checker 的 69 行」内覆盖 57（82.6%），
其余 12 行 = X 行 8 + 产物不齐 4。

**run_dir 解析链**（逐行记录于结果 JSON，首跑 57 场全部命中 tier=full 完整判分对象）：
`original_fields.run_dir`（28 场）→ `original_fields.judge.run_dir`（10）→ sources 路径推断（8，
含收紧批当年无法重判的 r1025 bird×2 / lcb×2 / cargo×1）→ judge_result.json 指针（4）→
bench-workspaces 批次映射（7，含 r1027-isolated→r1027 特例与 r20261026/27 yuanbao 证据包→
实际工作区兜底）。artifacts/ 证据包快照仅为最后手段（收紧批收据 §1：r20261026 快照 .py
截断），首跑未被迫退用该层。

## 5. 首跑两次执行的观察（lcb 负载抖动实录）

lcb r1029 doubao 一场两次全量执行结果不同，均为**既有已披露边界**的表现：

- 第一遍：重判 75.0 ≠ 总账 100.0（reward 均 1，红项 abc389_g）——逐分复现收紧批收据 §1
  已查因的「abc389_g #3 组机器负载 >10s 判 timeout」抖动（该场耗时 14.3s）；
- 第二遍（正式结果）：机器空闲，100.0 与总账一致。

两次都与 lcb spec §5 披露的单组 10s 口径自洽（oracle 最慢单组 1.37s）。工具对该场按
既往查因签名（reward=1 / weighted=75.0 / 红 abc389_g）自动附 `prior_attribution`，
不作为未查因翻转。工具首跑第一遍曾把 4 场 bird q26 偏移误列 mismatch（工具内
known-offset 对照表的 run_id 键未兼容收据的 `runs/` 段缩写），当日修复并以第二遍为
正式结果——工具缺陷，非判卷差异。

## 6. 改进建议（按收益排序，均属后续授权范围，本工具与本次交付未做任何改动）

1. **总账 run_dir 元数据补全**：57 场里只有 43 行带 `original_fields.run_dir`、38 行靠
   `judge.run_dir`（该字段与 run_dir 语义重复，建议统一并入 run_dir）/ sources 推断 /
   judge_result 指针 / 工作区映射兜底。新批次入库时把最终判分对象目录写入
   `original_fields.run_dir`，可把「推断兜底」降为零。
2. **r1028 四场 cargo 补归档判分对象**：现场只留 `flight_plan.json` 输出、无被测方
   inputs/app 代码，永不可复算；如需结清，需从执行机工作区备份或重跑同配置场。
3. **lcb 单组超时口径**：负载抖动会在重判时偶发复现（本次实录 75.0↔100.0）。可选：
   判分机空闲阈值约定，或 checker 对 timeout 组标注 `timed_out=true` 便于机器区分
   「真超时」与「负载超时」（属 checker 版本决策，非本工具授权）。
4. **known-offset 对照表维护**：`KNOWN_Q26_OFFSET` 内嵌自 bird-q26 收据 §5；总账若按
   新合同重算 raw（v1.2 化），这些行将自动转为 match，表条目自然失效、无需删除。

## 7. 边界

- 本收据只结清「总账可重判行的现行合同复算」这一维度；不证明判卷器一般正确，
  边界清单其余登记项（B1/B3–B7/B9–B11 及 B13b 残留）维持原状。
- 重判分仅作证据与复核，**不回写历史现场分数与总账**；总账 raw 仍登记各自评分时点的
  合同分（bird q26 偏移行即总账记 v1.1 分、重判按 v1.2 得新分的已收据差异）。
- 未触碰：CHANGELOG.md（未获授权）、2-用例（checker/truth/inputs 零改动）、3-表现现场
  与 bench-workspaces/bench-automation（只读）、判卷审计各收据目录。
