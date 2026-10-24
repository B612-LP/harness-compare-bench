# ledger-replay 判分规格（spec）

版本：**v0.1（2026-10-22，轻量判卷）** ｜ 判分入口：`checker.py`

## 1. 用例定位

**hard 区分度题**：乱序事件日志的状态机重建与异常对账。读 305 行脏数据事件日志，
按 `(seq, msg_id)` 重放出 100 个订单的终态与 11 条异常流水，产出
`final_state.json` + `anomalies.json`。区别于 hello 题：模型必须先想清楚
（排序键、幂等键、状态转移、金额口径）再动手，任何一步"大概排一下"都会产出
貌似合理但错误的终态。

## 2. 判分模式

- **headline 为二值 0/1**（`BINARY=True`：全 PASS=1，任一 FAIL=0）。
- 逐项权重只用于复核定位与加权参考，**不改变二值口径**（partial 参考，单题上限 10 分制下按 `weighted/100×10` 折算）。
- 三个守卫：**输入完整性**（输入被改 → 直接 0）、**truth 交叉校验**（现算重放 vs
  golden，漂移 → 退出码 2）、**金额守恒**（Σpay−Σrefund == Σ(paid−refunded)，
  对不上 → 退出码 2）。

## 3. 观察项

| id | 观察项 | 权重 | 通过条件 | 0 分条件 |
|---|---|---:|---|---|
| artifacts_exist | 两份产物存在 | 10 | `final_state.json` 与 `anomalies.json` 均在约定位置 | 任一缺失 |
| input_integrity | 输入完整性（守卫） | 10 | 运行目录附带的 `events.jsonl` 与 canonical 字节一致 | 输入被修改（直接 0）；未附副本 → **未核验**（不扣分） |
| final_state_format | final_state 结构 | 10 | JSON 数组、字段集恰为 `{order_id,state,paid_total,refunded_total}`、state 枚举、金额 `type is int`（浮点/NaN/布尔即拒）、按 order_id 升序无重复 | 任一项不满足 |
| final_state_exact | final_state 逐订单逐字段 | 30 | 与现算重放逐元素一致 | 缢单/多单/state 错/金额错/顺序错 |
| anomalies_format | anomalies 结构 | 5 | 字段集恰为 `{type,msg_id,order_id,seq}`、type 枚举、seq 整数、按 (seq, msg_id) 升序 | 任一项不满足 |
| anomalies_exact | anomalies 集合与顺序 | 30 | 与现算重放完全一致（含顺序） | 漏异常/多异常/类型错/顺序错 |
| money_conservation | 金额守恒（诊断） | 5 | 候送产物 Σ(paid−refunded) == 有效流 Σpay−Σrefund | 对不上（期望侧守恒已在启动守卫断言，失配属用例级故障 → 退出码 2） |

> 判分器内嵌**独立第二实现**的完整重放（与 `solution/replay.py` 互不引用，
> 不读 `solution/`）。启动时以 canonical 输入现算期望，并与 `truth.json` 的
> golden 交叉校验：任何一方漂移或金额守恒失配 → 退出码 2，不给判分。

## 4. 运行目录约定

```
<run_dir>/
  final_state.json   # 必需产物（也接受 run_dir/output/、run_dir/outputs/ 下同名文件）
  anomalies.json     # 必需产物（同上）
  events.jsonl       # 可选，建议附：本次运行实际使用的输入副本（用于完整性守卫）
  meta.json          # 可选：产品/版本/模型/操作人/日期等，不参与判分
```

```bash
python3 checker.py <run_dir>          # 人读报告 + RESULTS_JSON
python3 checker.py <run_dir> --json   # 只输出 JSON（供脚本聚合）
python3 checker.py --selftest         # 负控制/守卫自测，必须全 PASS 才可用于正式评分
```

退出码：`0` = reward 1；`1` = reward 0；`2` = 用法错误/自测失败/**用例自身不一致**。

投喂口径：任务书按 `/app/events.jsonl` → `/app/final_state.json`、`/app/anomalies.json`
陈述；手工/批跑时把输入副本与两份产物收进 run_dir 即可对齐上述约定。

## 5. 判卷器自测（三纪律）

1. **验外部产物**：只读运行目录里的文件，不采信产品自述、不读仓库内真值进产品目录。
2. **负控制必须能变红**：`--selftest` 固定跑 12 组样例——2 组正例（golden 附输入副本
   =1；未附输入副本=1，未核验不扣分）+ 10 组违规必须 0 分：
   漏去重、late_cancel 改了状态、漏 unacked、负金额生效、anomalies 按文件序、
   金额用浮点、缺整单、篡改输入、同 seq tie-break 弄反、缺产物。
3. **用例自身一致性**：`truth.json` 记录 canonical 输入 SHA-256 + golden 产物；
   checker 启动时现算重放并与 golden 交叉校验，输入/golden/守恒任何一方被改动都会
   `ERROR` 并以退出码 2 终止。

**修改 checker 后必须重跑**：`--selftest` + oracle 回归（必须 reward=1）。

## 6. 输入与 truth 重建（复核口径）

```bash
# ① 重建输入（固定种子 SEED=20261022，字节级一致）
python3 environment/tools/gen_events.py --out environment/events.jsonl
# ② 重算 golden（oracle 参考实现）
python3 solution/replay.py environment/events.jsonl --outdir <golden_dir>
# ③ 重建 truth.json（golden 嵌入 + canonical SHA-256）
python3 environment/tools/build_truth.py --events environment/events.jsonl \
    --golden <golden_dir> --out truth.json
# ④ oracle 回归（两条独立实现互证，必须 reward=1）
python3 checker.py <golden_dir>
```

生成器内置 mini 重放器在源头自证（mini 重放 == 按订单生命周期构造的终态 ==
金额守恒，任一不符即断言失败）；`solution/replay.py` 与 `checker.py` 内嵌实现
为另外两份独立重放，三者对同一 canonical 输入必须产出逐字节一致的 golden。

## 7. oracle 回归（2026-10-22 建题实测）

- `solution/replay.py` 产物与 truth golden 逐字节一致；`checker.py <golden_dir>`
  → `REWARD 1 (binary)  WEIGHTED 100/100  INPUT verified`，退出码 0。
- 附输入副本同分；未附副本 `INPUT unverified` 不扣分；篡改 run_dir 输入 →
  `input_integrity` FAIL 退出码 1；篡改 canonical 输入 → `ERROR` 退出码 2。
- `--selftest` 12 组样例全 PASS（2 正例 + 10 负例），退出码 0。

## 8. 难度论证（为何 hard）

**三重排序陷阱**（每条都对准一种"顺手写法"）：

1. **物理序 ≠ seq 序**：305 行中 302 行的位置与 seq 序错位，按文件顺序重放几乎
   必错；事件裸 `sort()`（默认字典序）同样错。
2. **同 seq 的 msg_id tie-break**：5 组事件共享 seq（3 组 create+pay、2 组
   pay+refund）。字典序升序才等于因果序（create<pay<refund 首字母天然保序）；
   降序或稳定文件序会把 3 个订单打回 `created`、2 个订单的退款凭空消失——
   每种错法都有对准它的貌似合理产物（已固化为 selftest 负例）。
3. **ts 是诱饵**：全部 305 条事件存在同秒聚集（每构造序 3 条共享一秒），按 ts
   排序是一条看似可行的死路；题面明确 ts 仅展示字段。

**幂等 + 四类异常分类**：3 个重复 msg_id（跳过 + 记 `duplicate_msg_id`）、
2 个 cancel-after-complete（状态不变 + 记 `late_cancel`）、4 个 ack=false
（**仍生效** + 记 `unacked`）、2 个负金额（**拒绝生效** + 记
`negative_amount`）。四种处置两两不同（跳过 / 拒生效 / 生效但记 / 状态否决），
11 条异常散布在 305 行中，产物要求**集合与顺序**全对，漏一类或多记一类即红。

**金额守恒 + 整数分状态机**：部分退款（refunded_total 达到 paid_total 才转
`refunded`）+ 多笔 pay 累计 + 守恒断言（Σpay−Σrefund == Σ(paid−refunded)）
双向夹逼；金额必须全程整数分，浮点尾差直接判 0。

组合复杂度：状态机 × 幂等 × 多键排序必须同时想对——单独看每条规则都不难，
但 305 行 × 100 单的规模下手工不可行，脚本需要一次写对三件事；这正是
"模型必须先想清楚再动手"的区分点（候选反馈"太简单"后的加难带新题）。

## 9. 行为分（仅人工跑时使用）

自动批跑（CLI）没有过程观察，行为分记 N/A，不计入。若人工执行，按 0–3 档打分
并写入运行记录（schema v1）：

| 观察项 | 0 | 1 | 2 | 3 |
|---|---|---|---|---|
| 交付完整性 | 无产物 | 产物缺失/结构非法 | 两产物齐全但值有错 | 一次交付且逐字段正确 |
| 规则理解（回传说明） | 无说明 | 只说"完成了" | 说明排序/幂等口径 | 说明排序、幂等、四类异常处置与自查方式 |
| 异常处理 | 静默忽略脏数据 | 提到脏数据但未分类 | 分类但处置有误 | 四类脏数据分类、处置与数量都能对上 |

## 10. 变更记录

- 2026-10-22 v0.1：建题（事件日志状态机回放 hard）。305 行确定性脏数据日志
  （乱序 302 处 / 3 重复 msg_id / 2 late_cancel / 4 unacked / 2 负金额 / 5 组同
  seq / 同秒 ts 诱饵）+ 独立双实现重放判分 + 金额守恒守卫 + 12 组自测样例；
  oracle 回归 reward=1。
