# jielong-fullchain 判分规格（spec）

版本：**v0.1（2026-10-22）** ｜ 判分入口：`checker.py` ｜ 难度：**hard（区分度题）**

## 1. 用例定位

微信接龙全链路：**解析 → 别名映射 → 分单计划**。读 `environment/` 三件输入（接龙原文 13 人两段 / 匿名别名表 / 4 张订单快照），产出 `resolution.json`（逐人解析表）与 `plan.json`（逐单 add/skip/reject）。

规则来源：`5-学习笔记/题库收集-2026-10-22/02-旧仓库/素材/sztu-gym-helper/docs/requirements/peer_jielong_import.md` 的 12 条已拍板规则（昵称映射、场次语义、9:00=到达备注、本人跳过、泛称必问、容量 7 硬拦、先填满单 A、标题日期不可信等），对应题目候选 J-01/J-02 的 hard 合并版。数据全部匿名重构：假学号（2025xxxxxx）、化名昵称，不含真实姓名 / 学号 / 手机号。

**这不是 hello 题**：规则数量、规则间交互与「不许猜」约束叠加，考察长链路规则执行的完整性与守恒。

## 2. 判分模式

- **headline 为二值 0/1**（`BINARY=True`：全 PASS=1，任一 FAIL=0）。
- 逐项权重仅作加权参考，partial ≤10 口径换算 = `weighted / 10`。
- 三个守卫：**输入完整性**（三件输入副本任一被改 → 直接 0；未附副本 → 未核验不扣分）、**truth 交叉校验**（canonical 输入 SHA 与期望值启动即复算，漂移 → 退出码 2）、**未知不硬判**（副本缺失记 `unknown`）。

## 3. 观察项

| id | 观察项 | 权重 | 通过条件 | 0 分条件 |
|---|---|---:|---|---|
| artifacts_exist | 产物存在 | 8 | `resolution.json` + `plan.json` 在约定位置（根目录 / `output/` / `outputs/`） | 任一缺失 |
| input_integrity | 输入完整性（守卫） | 12 | 三件输入副本与 canonical SHA-256 一致 | 任一件被改（直接 0）；未附 → 未核验（不扣分） |
| resolution_schema | 解析表结构 | 10 | 顶层数组、恰 13 行、每行恰 6 个字段且类型正确 | 缺字段 / 多字段 / 类型错 |
| resolution_rows | 行集 | 8 | seq 1..13 升序唯一、raw 与接龙原文逐行一致 | 丢行 / 多行 / 篡改 raw |
| resolution_match | 逐人映射 | 18 | 13 人 sid + status 全对 | 编造学号 / 重名猜了 / 泛称给了学号 / 零命中硬配 / 本人未标 |
| resolution_slots | 逐人场次 | 12 | 含 9:00→20:20、only 第２场→20:20、第一场→19:00、本人→[] 等 | 到达当场次 / 限定语失效 / 全角未归一 |
| resolution_notes | note 规则 | 7 | conflict 行列全候选学号；到达行含 21:00；unmatched / 本人行非空 | 缺候选 / 缺归一时刻 / 静默丢人 |
| plan_schema | 计划结构 | 6 | 4 单、按 orders.json 单序、恰 5 个字段 | 单序错 / 字段不符 |
| plan_assignment | 逐单分配 | 15 | 4 单 add/skip/reject 与规则推演逐项一致 | 超员硬塞 / skip 重复加 / 溢出归属错 / 不按先 A 后 B |
| plan_guards | 计划守卫 | 4 | 散场单无 add；包场单不超容；add 不含已在单内者；reject 非空必带 reason | 任一违反 |

## 4. 运行目录约定

```
<run_dir>/
  resolution.json            # 必需产物（也接受 output/、outputs/ 下同名文件）
  plan.json                  # 必需产物（同上）
  jielong.txt / peers.json / orders.json   # 建议附：原样输入副本（根目录 / input/ / inputs/ / environment/）
  meta.json                  # 可选：产品/版本/模型/操作人/日期，不参与判分
```

```bash
python3 checker.py <run_dir>          # 人读报告 + RESULTS_JSON
python3 checker.py <run_dir> --json   # 只输出 JSON（供脚本聚合）
python3 checker.py --selftest         # 负控制/守卫自测，必须全 PASS 才可用于正式评分
```

退出码：`0` = reward 1；`1` = reward 0；`2` = 用法错误 / 自测失败 / 用例自身漂移（canonical 输入或期望值与 truth.json 不一致）。

## 5. 判卷器自测（三纪律）

1. **验外部产物**：只读运行目录文件；不采信产品自述，不把仓库内真值写进产品目录。
2. **负控制必须能变红**：`--selftest` 固定 10 组样例——1 组 golden 必须 1 分，9 组违规必须 0 分：编造学号（海獭🦦 unmatched→编 sid）、重名猜了（小鹿 conflict→擅自选 2025000142）、超员硬塞（单 0001 剩 2 位塞 5 人）、泛称给了学号（朋友帮带）、日期笔误当成两天（标题 10.19 带偏成全空计划）、skip 的人被重复加（2025000101 已在单内仍 add）、缺 unmatched（静默丢行）、9:00 当成场次、篡改输入副本（守卫判 0）。
3. **用例自身一致性**：`truth.json` 记录三件 canonical 输入 SHA-256 与期望值；checker 与参考解各自现算并与之比对，任何一方漂移即报错退出码 2。

**修改 checker 后必须重跑**：`--selftest` 全绿 + `solution/solve.py` golden 产物 oracle 回归 reward=1。

## 6. oracle 回归

```bash
# 参考解（独立第二套实现）生成 golden 运行目录，再交给 checker 互证
python3 solution/solve.py <out_dir>
python3 checker.py <out_dir>        # 须 reward=1
python3 solution/solve.py --verify  # 参考解现算与 truth.json 互证（须 VERIFY OK）
```

checker 与 solve.py 为两套独立实现（解析 / 归一 / 分单逻辑互不复制），加上 truth.json 手工期望值构成三方互证。

## 7. 行为分（仅人工跑时使用）

自动批跑（CLI）没有过程观察，行为分记 N/A 不计入。人工执行按 0–3 档打分并写入运行记录：

| 观察项 | 0 | 1 | 2 | 3 |
|---|---|---|---|---|
| 交付完整性 | 无产物 / JSON 不可解析 | 缺一件产物或大片字段缺失 | 产物完整但个别规则错、需返工 | 一次交付且 13 人 / 4 单全对 |
| 回传说明 | 无说明 | 只说「完成了」 | 说明产物位置与内容概览 | 位置 + 概览 + unmatched/reject 去向与自查方式 |
| 异常处理 | 静默失败或静默丢人 | 报错但无原因 | 说明冲突/泛称/散场的处置 | 列候选学号、给归一时刻、reject 原因与下一步建议 |

## 8. 难度论证（为何 frontier 模型一次做不齐）

- **规则数量**：instruction 11 条显式规则，覆盖行识别、日期行跳过、全角归一、emoji 剥离、精确匹配与冲突判别、泛称、本人、到达时刻换算、限定语、容量算术、幂等 skip、散场拒收——每条都有对应的判分点。
- **单条数据流的级联放大**：解析错 → 映射错 → 分单错，无局部修复机会。把 9:00 当场次会同时错 resolution 行、19:00 分单人数与 20:20 容量算术；把标题 10.19 当真会整体跑偏成空计划。
- **「不许猜」静默点 4 处**：重名（小鹿 → 2025000142/2025000157 必须列候选）、泛称（朋友帮带不许赋学号）、零命中（海獭🦦不许编造）、散场溢出（7 人必须显式 reject 而非硬塞或丢弃）——每处都对抗模型「乐于帮忙补全」的默认倾向。
- **容量算术 3 处边界**：单 0001 剩 2 位（5+2=7 恰满）、单 0003 剩 1 位（6+1=7 恰满）、单 0004 散场 0 位；且填充严格按接龙序号——seq1 山茶恰好吃掉 0003 最后一位，seq2 温泉蛋（21:00 到达者）反而被溢出拒收，反直觉但规则唯一确定。
- **双时间陷阱方向相反**：标题 `10.19` 是要忽略的噪声，行尾 `9:00` 是要归一换算（+12h）的有效信息，两种「长得像关键信息」的文本需不同处置。
- **守恒约束**：13 行 = 9 可加 + 1 本人 + 2 unmatched + 1 conflict；6 add + 1 skip + 7 reject 分布于 4 张单，两级账本必须同时自洽。逐字段比对下，任何一处守恒破坏即 0 分；规则数量 × 交互 × 不许猜的乘积效应使其难以无返工一次做齐。

## 9. 变更记录

- 2026-10-22 v0.1：初版（task-5）。13 人两段接龙 + 匿名别名表（重名/零命中/泛称）+ 4 单（容量 5+2 / 6+1 / 散场拒收）；checker v0.1（10 观察项 + selftest 1 正例 9 负例）；solution/solve.py oracle 三方互证通过。
