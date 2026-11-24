# 合法等价表示校准（真实原档，2026-11-25）

观测规范的等价域声明（「换行、空白、键序、Unicode 转义或合法重压缩可改变原始字节，不改变该算法下的受检值」）此前只有 synthetic 自测夹具；本页把该声明施于 **r1109 冻结批真实原档**：同一原件换预声明的合法等价表示后，投影级判定必须逐字节不变（[第 1 条老师反馈](<../../反馈/2026-11-18-第五轮/README.md>)对照类①的真档层执行）。

## 结果（4 槽 × 15 表示组合）

| 槽 | 行数 | 表示组合 | 投影级判定 |
|---|---|---|---|
| dsh__dabstep-payments-10__r1 | 356 | canon / indent2 / ensure_ascii / orig_key_order / spaced | 全稳定 |
| codex__dabstep-payments-10__r1 | 484 | 前 4 种 | 全稳定 |
| wb__dabstep-payments-10__r1 | 85 | 前 3 种 | 全稳定 |
| doubao__tb-cargo-plan__r1 | 45 | 前 3 种 | 全稳定 |

- 每表示对每行：reparse(重序列化) 与原解析对象**深等值**（含 int/float 类型保真），canon 规范字节逐行一致 → 派生判定（计数/等值面/usage 账）不变。声明域在真档成立，**未发现解析器不稳**。
- 三格式（CLI 事件层/CLI rollout/桌面轨迹）表示级行为一致；不同顶层 schema 不影响等价域判定。

## 语义级变体（声明为内容级、非表示级）

| 变体 | dsh | codex | wb | doubao |
|---|---|---|---|---|
| int→float（canon 必须翻转） | detected（行 0） | detected（行 0） | detected（行 0） | no-carrier（全 45 行无 int 非布尔字段） |
| NFC→NFD（规范声明不做正规化→必须翻转） | no-carrier | no-carrier | detected（行 30） | no-carrier |

- no-carrier 是**如实登记**：该槽全部行不含可检载体（如豆包轨迹的数值字段全为浮点/字符串），不代表变体无害；detected 证明探针具备检出真实内容变化的能力（非恒过探针）。

## 措辞与登记

- PREREG 预测「int→float 在中位行检出」：实际执行改为**全行首载体普查**（超集仪器）——DSH/Codex/WB 行 0 检出；豆包中位行及全行均无 int 载体，预测按原中位行口径不成立，如实登记不回改 PREREG。
- 探针缺陷订正（执行中发现）：中位行无载体时初版误标 MISSED（vacuous）→ 改为载体普查口径（detected 附载体行号 / no-carrier 显式声明）。

## 近错（5/5）

掉字段表示检出（对象不等值+canon 翻转）；行序对调检出（canon 流配对破坏）；合成已知 int 报 detected（防 vacuous）；合成 NFC 预组合形报翻转；ensure_ascii 表示级往返等值（校准核心反向成立）。

## 复算

- `recompute.py --contract equiv-calibration-contract.json`：校验 schema、四槽名序、表示数（5/4/3/3）、表示在声明域内、逐表示投影稳定、语义判定合法（detected 必附载体行）。`CONTRACT OK {slots: 4, representations_total: 15, semantic_detected: 4, semantic_no_carrier: 4}`。行数真值不由复算器独立锚定，由各槽 `raw_sha256` 外部锚定（原档字节级）。
- `test_recompute.py`：6 夹具（schema 篡改/槽翻转/投影翻假/表示剔除/非法判定/detected 缺载体行）全部拒绝。

## 边界

- 单批 r1109、每格式 1 槽深检；表示组合是声明域的实例化采样（5 风格），非穷举。
- 等价域成立不等于「任意重序列化都安全」：语义级变体（数值域/正规化/掉字段/行序）在真档与合成层均被正确检出为内容变化。
- 内容无关：合同只含文件级 SHA、行数、表示级判定与变体普查（载体行级），不含事件内容字节。
