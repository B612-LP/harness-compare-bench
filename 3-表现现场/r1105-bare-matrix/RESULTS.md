# r1105-bare-matrix 结果（2026-11-01）

> 协议：PREREG l18-20261101（SHA `8856759c…`，先于实现）；裸模型 = deepseek-flash @ `/responses` 单轮、无系统提示、无工具；prompt = instruction.md 原文 + 声明内联包 + 交付约定（逐场 prompt SHA-256 与字节数在 meta.json）；arm `inline-low` 钉 `reasoning.effort=low`（[预检收据](<preflight-reasoning-pin.md>)），arm `inline-default` 不传参。**bare 行不入正式表（PREREG 预声明）；本批结果不改变报告 v1.2 任何数字。**

## 结果矩阵

| 用例 | inline-low（n=3） | inline-default（n=1） | CLI 正式账对照（v2 官方表） |
|---|---|---|---|
| bird-ca-schools-15 | reward 1,1,1（93.33/100/100） | 1（93.33） | 达标（双 CLI 同题均高，bird 为 A 组两项单项波动之一） |
| dabstep-payments-10 | reward 0,0,0（weighted 10.0×3，预注册数据规模地板） | — | 未达标（0/70.0，双 CLI 稳定未达标题） |
| exercism-py-6 | reward 1,1,1（83.33/100/100） | — | 达标 |
| lcb-recent-hard-4 | reward 1,1,1（**100×3**） | 1（100） | 达标 |
| tb-cargo-plan | reward 0,0,0（**weighted 70.37×3**） | — | 未达标（0/70.37，双 CLI 稳定未达标题） |

成本：17 场 API 调用全成功、零重发；reasoning_tokens 场级明细在 events/meta。

## 结论一：现行五题上裸模型与双 CLI 的结果面完全同构（Harness 执行层在结果面贡献≈0）

- **观察**：bare inline-low headline 3/5（bird/exercism/lcb 全 3/3 达标；dabstep/tb 全 0/3 不达标）——达标/未达标题集与 A 组双 CLI 正式账完全重合；tb 裸模型 weighted 70.37 与 CLI 的 70.37 逐字一致。
- **证据**：[bare-matrix-events.json](<bare-matrix-events.json>) 17 行（category=bare_model_probe）；runs/ 逐场 raw request/response + 原字节 checker 收据；对照 [v2 官方表](<../../5-评测报告/可信冻结-2026-10-29-v2/official-main-table.json>)与 r1030 正式账。
- **解释**：这五题的结果面差异由「模型×任务」决定，Harness 执行层贡献≈0——能交付的题给足信息后裸模型同分，不能交付的题裸模型同败。r1022（旧五题、任务书原文、无内联）0/5 地板与本矩阵（同信息内联）3/5 之间的差 = 信息可达性与交付结构的价值，而非推理能力差。
- **未排除因素**：裸臂 n=3 且单轮无迭代（CLI 可多轮自纠）；内联包 ≠ 文件系统探索（bird r1 的 93.33 差 1 题可能与不能试跑 SQL 有关）；tb 70.37 同分不排除判分结构巧合（见结论四复现项）；dabstep 为预注册地板题（见结论四），其裸分不构成能力证据；桌面两产品不在本矩阵内。
- **可复现实验**：`tools/bare_run_v2.py`（write-once run_dir）+ [预检收据](<preflight-reasoning-pin.md>) + 逐场 prompt SHA；checker 原字节 `--json` 复算；内联包逐文件与 canonical SHA 对账（meta.inline_manifest）。

## 结论二：thinking 档位在易/中题上无结果面敏感性（r1022 未知#1 部分收口）

- **观察**：bird/lcb 各 1 场 default 档与 low 档同分同 weighted（93.33 / 100）；预检探针显示档位差在 reasoning_tokens（46,433→18,540），不在结果。
- **证据**：[preflight-reasoning-pin.md](<preflight-reasoning-pin.md>)（5 次探针）+ 2 场 sensitivity 事件。
- **解释**：档位控制思考预算而非答案质量——CLI 统一 low 的档位约定（2026-10-22 定案）在这些题上不构成结果面变量；r1022 欠账按其「下一步」口径收口一半。
- **未排除因素**：n=1/题；dabstep/tb 未做 default 对照（地板题增加对照无信息增量）；「普遍无敏感」不可外推。
- **可复现实验**：`--sensitivity` 扩展到全部五题 × n=3。
- **登记**：r1022 未知#1 状态 → 部分结清（易/中题档位无敏感性成立；hard 题档位敏感性仍未测）。

## 结论三：dabstep 预注册地板题——数据规模是裸模型的结构性墙（也是 CLI 相对裸模型的真实贡献点，但必要不充分）

- **观察**：dabstep 裸臂 0/3，weighted 10.0/场；payments.csv（23.5MB/13.8 万行）与 fees.json（531KB/千条规则）按预注册声明未内联。
- **证据**：meta.protocol.floor_note 逐场在案；[spec](<../../2-用例/dabstep-payments-10/spec.md>) 的数据体量描述。
- **解释**：数据体量超单上下文 → 无工具不可解是结构属性；CLI 的文件工具提供了数据可达性——但 CLI 正式账在该题同样 0/70 双败，即数据可达性必要不充分（规则交叉推理本身未过）。
- **未排除因素**：地板分母是内联包裁剪决策（若模型可外部读文件则不成立，这正是 Harness 的定义性差异，不构成混淆）；10.0 weighted 的构成未逐项分析。
- **可复现实验**：内联清单在 meta.inline_manifest 逐文件可查；给裸模型挂只读文件工具的变体属新预注册范畴。

## 结论四：tb-cargo weighted 逐字同分（70.37×3）需要逐项对照确认

- **观察**：裸模型三场 weighted 全部 70.37，与 CLI 正式账完全一致；reward 同为 0。
- **证据**：runs/ 三场 checker result.json + v2 官方表对应行。
- **解释**：初步指向「同一组断言集通过、同一组失败」——即失败项与 Harness 无关、由任务难度决定；但 weighted 同值也可能来自判分结构（部分 credit 档位稀疏），需逐断言对照才能下「完全同构」强结论。
- **未排除因素**：n=3 全同值本身可疑地稳定（可能反映了模型的确定性解题路径，也可能反映判分粒度）；三文件修复的抽取走 FILE 标记，全部精确配对（meta.answer_to_artifacts 可查）。
- **可复现实验**：对 bare r1 vs CLI 正式场的 checker 明细逐断言 diff（本批未做，列为下一步——属结果解读项，不影响本批分数与裁定）。

## 执行期事件（如实）

- **抽取器 r1 事件**：首轮 7 场（全部 JSONL 题）因工具签名 bug（`extract_jsonl` 期望产物字典、实收 case 字典 → KeyError 'path'）未落产物；API 响应原样在案，**零重发**，修复后离线重抽取+原字节判分。涉及运行在 meta.json `postmortem` 字段逐场标注；首轮输出存档 [batch-results.run1-extractor-bug.json](<batch-results.run1-extractor-bug.json>)。
- **工具版本化失误（第二次，如实）**：buggy 版脚本未在被覆写前留档（当前 `.r1-postmortem.py.bak` 为修复一半的中间态）；r1 行为可由 error 行 + 响应原文完全复现，但背书源码不在盘。纪律自 L17 已立，执行又犯——自本批起工具落盘即先 `cp` 版本副本再动手。
- 场级十字段：meta.json 逐场含（run_id/题目版本/产品版本/模型/工具=[]/权限/技能=none/duration_s/证据等级/最终裁定 V|F）。
