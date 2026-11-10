# 派生分析：元宝 n=3 批八场 0 分的构成（2026-11-09）

**身份**：探索性派生分析（事后）。数据源=已有批次 [r20261101-yuanbao-n3](<../../3-表现现场/r20261101-yuanbao-n3/README.md>) 的判卷原件与收割记录（私档，`archive://launch-r1109/../yuanbao-n3-20261101/` 定位），本文只补构成事实，**零发射、不改正式 25 行、不改任何判卷与批次记录**。批 README 原文只记「其余八场全部 0 分」，本文补齐 0 分由什么构成。

## 结论

八场 0 分（reward=0、weighted=0.0）的构成，**2026-11-11 更正后归并为同一大类（交付终点无模型产物）的两个表现**（更正依据见下方[更正节](#2026-11-11-更正exercism-三场判卷对象为夹具骨架空壳零交付)；下方原 v1 两分类表格保留原判据事实，分类名以更正节为准）：

| 构成（v1 分类，B 类已于 2026-11-11 更正） | 槽 | 判卷证据 |
| --- | --- | --- |
| **A 交付管线终点无产物**（5 场） | dabstep r2/r3（`answers_format` 缺失 answers.jsonl→10 题全「未回答」）；lcb r1b/r2/r3b（4 个 `solutions/*.py` 全 `fail_kind=missing`） | 五场 `filelink-harvest` 收割结果 `saved=[]` 全空（`file_cards`：dabstep 两场与 lcb r2 记 0，lcb r1b/r3b 无 assembly-notes 记 null，同为 0 卡片事实）；当时已按 bird 先例做过卡片收割尝试，仍无产物。会话文本层（api-dump 逐快照机械计数，`session_py_fences`/`session_write_calls`）：dabstep 两场 0/0（会话内无答案与代码文本）；lcb 三场 65/25、55/55、65/0（会话内存在大量 python 代码块与 write 型工具调用展示，但交付终点仍无文件卡片） |
| **B 完成回执在档但六项测试全不达标**（3 场；**2026-11-11 更正：实为零交付，判卷对象为夹具骨架空壳**，见更正节） | exercism r1b/r2/r3 | 六项 check `pass=false` 全成立；回执测试数 forth 54/poker 37/dominoes 13/bowling 31/zipper 14/pov 15，除 dominoes 回执 `succeeded=6/13` 外其余项 `succeeded=0`；dominoes 虽 6/13 成功仍因 `identities_match=false` 判负。三轮回执逐值一致 |

机械汇总见 [yuanbao-zero-constitution.json](<yuanbao-zero-constitution.json>)（逐槽 `failed_check_ids`/`delivery_missing`/`harvest_saved`/`file_cards`/`answer_blocks`/`receipt_detail`；**2026-11-11 v2 起新增 exercism 三槽 `workspace_impl_equals_fixture_skeleton`/`workspace_impl_all_skeleton` 判定字段与 `summary.exercism_impl_all_skeleton_slots`**），由 [collect-yuanbao-zero-constitution.py](<collect-yuanbao-zero-constitution.py>)（**当前 v2 sha256 `4e0b086d7c520061283281e1cb63348cca14aac9b0ed0bd6c4adc73ec552cd8d`，与私档副本同值**；v1 原版 sha256 `2cf08a6cb0b60923d61321c6aaa661c6223a9aca17b96e5cb8d81e1b70976481` 留档私档窗口目录，只读生成）；私档数据根以第二参数传入（`python3 collect-yuanbao-zero-constitution.py <输出.json> <判卷原件根目录>`，v2 运行时 cwd=公开仓根以取公开骨架基准），脚本本体不含私有路径。

## 2026-11-11 更正：exercism 三场判卷对象为夹具骨架空壳（零交付）

v1 将 exercism 三场归为「B 完成回执在档但六项测试全不达标」，隐含「模型实现已交付、测试未通过」。**该定性有误**，机械复算（可复算，骨架基准为公开仓 tracked 文件）更正如下：

- **workspace 六个实现文件与公开夹具骨架逐字节一致**：三场 `workspace/inputs/exercises/<ex>/<ex>.py` 的 sha256 与公开夹具骨架（`2-用例/exercism-py-6/inputs/exercises/` 下同路径文件，git tracked）完全相同（六题逐一同码，JSON v2 `workspace_impl_all_skeleton=true`）。骨架为空壳（如 `def evaluate(input_data): pass`）。
- **会话代码与交付终点零字节重叠**：三场会话 assistant 文本中的 python 代码块（110/45/5 个）无一与终态实现文件字节相同——会话内展示/讲解的代码从未落到判卷 workspace；`filelink-harvest saved=[]`（与 A 类五场同事实）。
- **回执数值的真实来源**：判分器（全量通过语义：每题须官方测试全数通过且回执身份三列表全等）跑的是骨架空壳——forth/poker/bowling 骨架 `pass` 函数体致断言全 fail，zipper 为纯 err 型失败（errors=14/failures=0）、pov 为混合型（failures=9+errors=6），dominoes 6/13 为骨架行为下的残差；回执数值本身真实，但其含义是「骨架的判分」，不是「模型实现的判分」。
- **更正后的构成结论**：元宝批八场 0 分全部为**交付终点问题**（3 场 lcb 收割无产物+2 场 dabstep 无 answers+3 场 exercism 骨架原样），**不含「模型实现已交付但失败」的证据**；三场 exercism 的会话内代码质量无法从交付终点事实推断，不作能力判断。
- **同步更正的其它公开件**：[批 README r20261101-yuanbao-n3](<../../3-表现现场/r20261101-yuanbao-n3/README.md>) 观察段的 0 分构成括注同步加更正标注（指向本节），判分数值与登记零改动。
- **正式行/历史判卷零改动**：本更正只修正机理披露，判分结果（0/8）与登记不变。

## 边界与解释

- **产品黑盒边界**：A 类五场只能证明「交付管线终点无产物」，不能区分产品侧交付机制的归属，不作产品缺陷因果归因；模型封闭（B 组）亦不可与 A 组同模型对照。会话文本层细分（机械计数）：dabstep 两场=会话内无答案/代码文本（`blocks=0`、围栏 0）；lcb 三场=会话内存在代码块与 write 型调用展示（围栏 65/55/65），即工作痕迹在会话内可见而文件卡片终点为空——两者在「终点无产物」这一判分事实上同层，机理披露如实分开。
- **能力对照事实**：bird r2c/r3 两槽曾以文件卡片成功交付并经 reassembly 判分（86.67），说明同一产品同批内卡片交付管线可以走通；上述五场是「该管线此番终点为空」，而非管线不可用。
- **与 A/B/W 分轨的关系**：同题 WorkBuddy 形态 dabstep 三轮 weighted=60–70（答案错误但交付在档）、lcb 三轮 100.0，A/B 分轨差异在交付层同样显著；该差异只能作分轨描述，不外推产品能力结论。

## 与正式行/报告的关系

- 正式 25 行（n=1 口径）与 §4.3-4.6 判据零改动；本分析不改变 [r20261101-yuanbao-n3](<../../3-表现现场/r20261101-yuanbao-n3/README.md>) 已有披露，只把「其余八场全部 0 分」的构成补为可复核事实。
- 复算指引：私档判卷原件（`evidence-tools/grading/<slot>/checker.stdout.txt`）与收割记录（`runs/<slot>/filelink-harvest.json`、`assembly-notes.json`）以 `archive://launch-r1109/../yuanbao-n3-20261101/` 定位；脚本只读，重跑输出逐字节一致。
