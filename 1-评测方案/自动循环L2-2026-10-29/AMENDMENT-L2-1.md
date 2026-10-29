# AMENDMENT-L2-1 —— 预注册哈希转写勘误

- 时刻：2026-10-29 16:5x+08:00（实钟；发现者 builder-codex，包B 构建期）
- 性质：事实转写勘误，无范围/方法/验收标准变更。依预注册 §二.1 显式程序落盘。

## 勘误条目

[PREREGISTRATION.md](<PREREGISTRATION.md>) §四（包B）所写：

> config work_registry.path → v2 台账，SHA `27974b75…`

勘误为：`27974b75…` 实为 **v1** 台账（`4-打分细则/可信冻结-2026-10-29/work-registry.json`，16 事件）的 SHA-256；**v2** 台账（`4-打分细则/可信冻结-2026-10-29-v2/work-registry.json`，23 事件，含 7 条待入账收据）实际 SHA-256 = `04944e28f243e06fd119a614c766f990c81813f4bce8a45958076e37796a93a6`。lead 转写自 v2 config 的 `work_registry` 字段——该字段恰好以 path+sha 自洽方式指向 v1 文件，这正是盲审 D2 所述「7 收据不入账」的发生机制；预注册将该哈希误标为 v2 台账所有。

## 处置

- v3 config 按实况写 `path=4-打分细则/可信冻结-2026-10-29-v2/work-registry.json` + `sha256=04944e28…`（若按预注册原文写 27974b75 则 path/sha 不自洽，verify_seal 必失败）。
- 实质要求不变：v2 registry 全部事件并入 v3 六账（按 event_id 去重）。已实现并经 lead 复核：self_test 8→13、interface_preflight 11→13，7 收据逐一在账，wb-sandbox-preflight-20261027 去重后恰 1 次。
- 双哈希实测留痕（lead，16:5x）：v1=27974b75…、v2=04944e28…。
- 包B 交付 README 同步载有 dated 勘误框（builder-codex 独立发现，先于本修正案落盘）。
