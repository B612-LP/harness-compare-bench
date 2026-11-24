# 等价域全集：桌面轨迹 9 槽表示域补全（2026-11-25，预注册）

> 状态：已验收（冻结 trace 重投影，零新增运行）。本页把[等价表示校准](<../等价表示校准-2026-11-25/README.md>)从桌面抽样 2 槽补全为全集 9 槽（WB 6 + 豆包 3），消除「抽样成立→全集成立」的推断缺口。

## 1. 判定（合同：doubao-wb-equiv-fullset.json，SHA16 bee278c61422db06）

| 预测 | 判定 | 数据 |
|---|---|---|
| PF1 九槽 ×5 风格全 stable | PASS | 9/9（canon/indent2/ensure_ascii/orig_key_order/spaced 逐行 reparse 深等值+canon 一致） |
| PF2 语义变体与 R8 一致且全集化 | PASS | int 载体：WB 每槽全行、豆包 0/9 行全无；NFD 载体：wb dabstep r1 2 行（30,31）、**wb tb r2 2 行**（全集新增检出槽）、余 7 槽 0；detected==carrier 全槽一致 |
| PF3 R8 槽逐字节复现 | PASS | wb dabstep r1 nfc 载体首行 30 与 R8 合同一致；doubao tb r1 双无载体复现 |

## 2. 增量发现

R8 桌面抽样只含 wb dabstep r1（nfc 载体槽）与豆包 tb r1（无载体槽）；全集化后新增 **wb tb r2** 为 nfc 载体槽（2 行预组合形）。抽样推断在此处确实不完备——补全的价值实证。

## 3. 近错（4 项全过；弱式如实标注）

掉字段检出 / 行序对调检出 / 预组合字符（U+00E9）翻转检出 / 分解形往返稳定。全为合成演示类（弱式）。

## 4. 复算与测试

```sh
python3 4-打分细则/等价域全集-2026-11-25/recompute.py
python3 4-打分细则/等价域全集-2026-11-25/test_recompute.py
```

`recompute.py` 校验：schema、9 槽、风格域、hex64、stable 声明、detected==carrier、nfc 计数一致、豆包 int 载体 0、R8 复现声明、近错声明、内容无关门（任何字符串值含 mid 形或 `/` 即拒）。`test_recompute.py` 9 项（1 正常 + 8 注入）全拒。

## 5. 结论边界

本页补全 R8 的桌面覆盖面，不翻案、不改规范 v1.4 正文；合同内容无关（槽名/布尔/计数/行号，含 mid 拒绝门）；豆包全 3 槽 int 载体 0 与 R13 的结构发现（无 int 非布尔字段）互相印证。
