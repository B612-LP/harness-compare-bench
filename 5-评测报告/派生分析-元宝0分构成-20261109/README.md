# 派生分析：元宝 n=3 批八场 0 分的构成（2026-11-09）

**身份**：探索性派生分析（事后）。数据源=已有批次 [r20261101-yuanbao-n3](<../../3-表现现场/r20261101-yuanbao-n3/README.md>) 的判卷原件与收割记录（私档，`archive://launch-r1109/../yuanbao-n3-20261101/` 定位），本文只补构成事实，**零发射、不改正式 25 行、不改任何判卷与批次记录**。批 README 原文只记「其余八场全部 0 分」，本文补齐 0 分由什么构成。

## 结论

八场 0 分（reward=0、weighted=0.0）分两类，机械证据互斥：

| 构成 | 槽 | 判卷证据 |
| --- | --- | --- |
| **A 交付管线终点无产物**（5 场） | dabstep r2/r3（`answers_format` 缺失 answers.jsonl→10 题全「未回答」）；lcb r1b/r2/r3b（4 个 `solutions/*.py` 全 `fail_kind=missing`） | 五场 `filelink-harvest` 收割结果 `saved=[]` 全空（`file_cards`：dabstep 两场与 lcb r2 记 0，lcb r1b/r3b 无 assembly-notes 记 null，同为 0 卡片事实）；dabstep 两场会话答案块 `blocks=0`，lcb r2 `blocks=22` 但 0 卡片。当时已按 bird 先例做过卡片收割尝试，仍无产物 |
| **B 完成回执在档但六项测试全不达标**（3 场） | exercism r1b/r2/r3 | 六项 check `pass=false` 全成立；回执测试数 forth 54/poker 37/dominoes 13/bowling 31/zipper 14/pov 15，除 dominoes 回执 `succeeded=6/13` 外其余项 `succeeded=0`；dominoes 虽 6/13 成功仍因 `identities_match=false` 判负。三轮回执逐值一致 |

机械汇总见 [yuanbao-zero-constitution.json](<yuanbao-zero-constitution.json>)（逐槽 `failed_check_ids`/`delivery_missing`/`harvest_saved`/`file_cards`/`answer_blocks`/`receipt_detail`），由 [collect-yuanbao-zero-constitution.py](<collect-yuanbao-zero-constitution.py>)（sha256 `b871e159bdb62dc0…`，与私档副本同值）只读生成；私档数据根以第二参数传入（`python3 collect-yuanbao-zero-constitution.py <输出.json> <判卷原件根目录>`），脚本本体不含私有路径。

## 边界与解释

- **产品黑盒边界**：A 类五场只能证明「交付管线终点无产物」，不能区分 agent「未产出」与「产出未送达交付终点」，不作产品缺陷因果归因；模型封闭（B 组）亦不可与 A 组同模型对照。
- **能力对照事实**：bird r2c/r3 两槽曾以文件卡片成功交付并经 reassembly 判分（86.67），说明同一产品同批内卡片交付管线可以走通；上述五场是「该管线此番终点为空」，而非管线不可用。
- **与 A/B/W 分轨的关系**：同题 WorkBuddy 形态 dabstep 三轮 weighted=60–70（答案错误但交付在档）、lcb 三轮 100.0，A/B 分轨差异在交付层同样显著；该差异只能作分轨描述，不外推产品能力结论。

## 与正式行/报告的关系

- 正式 25 行（n=1 口径）与 §4.3-4.6 判据零改动；本分析不改变 [r20261101-yuanbao-n3](<../../3-表现现场/r20261101-yuanbao-n3/README.md>) 已有披露，只把「其余八场全部 0 分」的构成补为可复核事实。
- 复算指引：私档判卷原件（`evidence-tools/grading/<slot>/checker.stdout.txt`）与收割记录（`runs/<slot>/filelink-harvest.json`、`assembly-notes.json`）以 `archive://launch-r1109/../yuanbao-n3-20261101/` 定位；脚本只读，重跑输出逐字节一致。
