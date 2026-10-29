# L3 自动循环验收报告 —— 机读对齐与证据机械化

- 分支 `loop3-2026-10-29`；预注册封印 `72edb519` @ 2026-10-29T17:52:27+08:00（先于一切包工作）；本报告为循环收口文件。
- 性质：**零模型调用闭环**。不产生新分数主张；L2 既有裁定（含 r1030=v2 合同记录、gap₀=0.74 口径）不受影响。

## §0 结论先行

**四包全 pass、双验通过、0 blocking；双验发现的全部 5 个 defect（D-L3-1、DF-B1、DF-C1、DF-C2、FIX-D1）循环内闭项；L2 全部遗留真闭合。** L2 设定的三项机读停止条件全部解除：活台账 schema 三方矛盾（DF-1）已对齐并可机读消费；validator 约束缺口（DF-2）已补齐且 fail-closed；`--spec` 破坏性覆盖（C-1）已非破坏化。L4 生产轮（①provider-cache 消融、②WorkBuddy 正式批次）的机读准入门已就绪，唯 U1（registered_at↔git 真实对账）须在首批证据链上执行。

## §一 交付与闭项

| 包 | 交付 | 提交 | 关键哈希 | judge | auditor |
|---|---|---|---|---|---|
| A：DF-1+⑧a/c | v3 活台账 schema 对齐（`registered_at` 入 required+时区 pattern；kind enum 6 值）；schema 校验并入结构不变量；pin_class 机械归类接线 verify_seal；tripwire 保留 | `0e276a20` | lock `544a7f96`→`bf7f9aa3`（17→38 pin，机械产出） | pass | pass |
| B：DF-2+C-1+⑦ | validator 双 enum+null 伴随 diagnostic+seal fail-closed（`--retro` 同语义）；`--spec` 非破坏化（显式 `--out`/拒已存在）；`--reconcile` 离线对账；SCHEMA v2.1-l3 | `af703db` | validator 终版 `8e423de5` | pass | pass |
| C：⑥+⑧b | evidence-kit：证据行生成器+收据规范检查器（live_doc_drift 状态行+哈希行合规+证据行复算）+联合自测+铁律 README | `23a63fc` | evidence_line `9b00febf`、receipt_check 终版 `effda0ed` | pass | pass（附 defect→已闭） |

**缺陷闭环表**（全部循环内闭项，复验方独立确认）：

| 缺陷 | 发现方 | 修复 | 闭项证据 |
|---|---|---|---|
| D-L3-1 `--reconcile --git` %-format 冲突→自相矛盾收据 | judge | `15d9d62a` 拼接修复+verdict 四态 | T8 真仓亲测六步全绿（对账封印 `72edb519`） |
| DF-B1 `--retro` 无 seal 未 fail-closed | auditor | 同上，exit 3 不落盘 | judge 临时目录核验+T7 |
| DF-C1 CJK 前贴哈希正则零命中 | auditor | `15d9d62a` 显式环视+长度一律校验 | CJK 双侧捕获、超长全记、零误报（judge+auditor 双实测） |
| DF-C2 wellformed 死数据 | auditor | 同上，并入总判定 | 字符串值反例 fail |
| FIX-D1 verdict 残留矛盾（comparison 分支未并入 non_comparison_ok） | auditor §9 | `600c21fe` 守卫+T10 | judge：矛盾形态结构性不可达，四态与 SCHEMA 一致 |

## §二 分账（全部实报）

product_run=0；bare_model_probe=0；interface_preflight=0；offline_recompute=0；grading_regression=0；API 调用=0。

self_test：v3 test_freeze **48/48**（44 继承+4 新增，0 删除）；cli-selftest **10/10**（含 T8 `--git` 真仓、T10）；`--spec` fixtures **10/10**；evidence_line 自检 **11/11**；receipt_check 自检 **14/14**；kit 联合 **2/2**（r6=`c396bb40`）；合成对账正例 ok/负例 violation+error 各一。活台账 **events=15**（builder 11 + lead 代登 2 + fixround 2），全部过 `live_registry_entry` schema，时间升序，append-only。

## §三 双验产物

- judge：`5-评测报告/L3独立验收-2026-10-29/`（verify-receipt-l3.json=`7aa54b1c`、fix-verification-20261029.md=`5dd7fedf`、README=`98cbb2d6`）——33+ 条款逐项独立验收+六疑点钉死+修复轮/FIX-D1 复验；其收据过 receipt_check all_ok=true（⑧b 首次真实使用即抓出 judge 自身 2 处违规，机制有效性实证）。
- auditor：`5-评测报告/对抗性盲审-L3-2026-10-29/AUDIT.md`（终版=`639880ed`）——0 blocking；攻击面全实证（自写 schema 校验器非 stub、A4 逃逸样本被生产路径硬拒、B6 三态、38 pin 制度自洽）；§9 修复轮敌意复核抓出 FIX-D1 残留。

## §四 五段结论

**观察**：L3 将 L2 双验的披露性缺陷与循环内教训全部转为机器强制后，三包交付一次通过双验，但双验仍在修复轮后抓出 1 个同类残留（FIX-D1）。
**证据**：§一闭项表+§二计数+双验产物（全部可脚本复算）；v2/v1 字节冻结保持（verify exit 0）。
**解释**：机读约束的引入是「把诚实从纪律变成默认」——B-1 式矛盾（测试与 schema 立场不一）、C-1 式覆盖、手打哈希误报在 L3 中均被机械层当场拦截（含 judge 收据被抓、lead 转述哈希笔误被抓两起自我应用）；残留 defect 集中在「新分支语义未满覆盖」处，说明约束实现本身也需要对抗性覆盖，这正是双验结构的价值。
**未排除因素**：U1（真实批次 registered_at↔git 对账）未做——溯源仍是机制级而非实证级；`--retro` 矩阵的下游消费纪律（标签级拦截的消费者侧）未制度化；evidence-kit 正则白名单边界（长 hex 摘要引用恒不过检）未在 README 显式化。
**可复现实验**：`python3 -B '4-打分细则/可信冻结-2026-10-29-v3/freeze.py' verify`（0）；`python3 -B '…/test_freeze.py'`（48/48）；`L3_ALLOW_GIT=1 python3 '1-评测方案/工具链/runner-schema-v2/cli-selftest-l3.py' --out <新路径>`（10/10）；`python3 '1-评测方案/工具链/runner-schema-v2/validate_runner_meta.py' --spec --out <新路径>`（PASS）；`python3 '1-评测方案/工具链/evidence-kit/receipt_check.py' --selftest`（0）。

## §五 unknown 与 L4 池

**U1**（承 L2）：真实批次 registered_at↔git 提交时刻对账未做（L3 仅合成+封印对账）。影响：溯源未达实证级。下一步：L4 首个真实批次执行。停止条件：对账吻合即闭。**前置已就绪**（D-L3-1/FIX-D1 已修）。

**L4 池**：① provider-cache 语义请求级验证+runner 代际 spread 消融（需 API，生产轮）；② WorkBuddy 正式批次（slots+O6 撞名）；③ builder 事实汇报仓内归档制度（N-1）；④ receipt 写入硬化（悬空 symlink/原子写，auditor note）；⑤ O-2 活台账 source 哈希新鲜度对账；⑥ FIX-O1 seal 块 policy 标签与密封状态对齐；⑦ N1–N4（计数语义区分 pending/r5 留痕用例粒度/--no-drift-require 分支对称性文档化/正则白名单 README 显式化）；⑧ N-3 自检收据内嵌 live_doc_drift 键（L4 起统一）；⑨ `--retro` 无 seal 矩阵下游消费规约。

## §六 执行披露

- 合并前 sweep 期间 lead 两次命令误用（cli-selftest 默认收据路径拒写=正确行为、`--spec` 误传位置参数），修正后全绿，零字节副作用；lead 在派发转述中手打哈希一笔误（`82393b1b`↔`82393b1f`）被 judge 当场抓出——⑥ 教训第三次在册实例，制度答案不变：**哈希/时刻一律脚本生成**。
- lead 行文时刻两度先写占位/手打后以实钟脚本修正（循环台账），已原样保留修正轨迹； auditor 活台账登记与 judge 产物引用由 lead 代登（`c4935e69`，执行者只读约束，2026-10-29 18:52 裁定）。

## §七 提交链

`72edb519` 封印 → `6820329f` 章程 → `0e276a20` 包A → `af703db` 包B → `23a63fc` 包C → `281ab3e2` 双验+台账 → `15d9d62a` 修复轮 → `5a5f28c2` 复验+裁定 → `600c21fe` FIX-D1 闭项 → `c4935e69` 代登收口
