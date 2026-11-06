# 核验台账（2026-11-07）

本目录落实老师 Week3 反馈第 4 条：「为公开与私档材料建立第三方核验记录：文件清单、哈希、
核验人、核验时间、可公开字段与不能公开字段分开列，尤其解释当前公开 verify 无法复核的
历史代际。」由机器生成器 [`tools-verify-ledger.py`](<tools-verify-ledger.py>) 产出
[`ledger.json`](<ledger.json>)，一份文件回答四个问题：

1. **文件清单+哈希**：`inventory` 覆盖生成时点 HEAD（`generation.head`）的全部 5,425 个
   tracked 文件，每文件给内容 sha256（s）、git blob sha1（b）、字节数（z），克隆内可逐条复算。
2. **核验记录索引**：`verification_index.public` 登记 37 份公开核验记录（归档核对、判卷审计、
   判卷器可信度协议、判据边界复核、正式行复核、独立复核/独立验收、冻结包 lock、未知登记、
   修订复算收据等），每条含覆盖物、记录路径、核验人角色、核验时间（=该记录最后修订的
   提交日期，机器取自 git log）。
3. **公开/非公开字段分开**：`fields_split` 两节互斥列出；私档收据在本台账只保留
   sha256/角色/时点四个字段，**私档文件路径不入任何公开文档**（`verification_index.private`）。
4. **公开 verify 无法复核项**：`not_publicly_recheckable` 列 5 项（历史代际语义、私档原始
   收据、发布前封印链、桌面原生轨迹、发射锁），每项附原因与公开文档锚点
   （[公开核验范围与限制](<../../5-评测报告/L6独立复核-2026-10-30/公开核验范围与限制.md>)、
   [历史封印复核限制](<../../1-评测方案/历史封印复核限制.md>)、竞品评测报告 v1.9 §4.5）。

## 核验人口径（必须先读）

- 角色：`tools:<工具名>`＝机器工具产出；`agent:author`＝作者 Agent；`agent:non-author-review`＝
  非作者 Agent 独立评审/验收。完整词表见 `role_vocabulary`。
- **全部核验人为 AI Agent 与机器工具，无独立真人第三方核验**：用户 2026-11-04 已明确取消
  独立真人核验要求。本台账如实按 Agent 角色登记，不冒称真人核验。
- 台账只登记「记录存在 + 哈希 + 角色 + 时点」，**不评判任何记录内容的语义正确性**。

## 边界与复算

- 台账目录自身（生成器、本 README、ledger.json）不在 inventory 中（自引用不可能），
  见 `generation.excluded_paths`；本批新增文件（含 6-周报 write-once 守卫改动）由下一次
  生成或发布护栏覆盖。
- `ledger.json` 是**快照**：绑定 `generation.head`。同 HEAD 重跑逐字节相同
  （无时间戳；确定性已实测）。复算方法（须真实 Git 工作副本）：克隆或复制本仓库 →
  `git checkout --detach <generation.head>` → `python3 tools-verify-ledger.py --sidecar <同一私档 sidecar>` →
  与提交内 ledger.json 逐字节比对。生成器需要 Git 仓库上下文；`git archive` 解包目录不是 Git 仓库，不可用于复算。
- 私档 sidecar 保存在仓外私档目录，其路径不写入公开文档；无 sidecar 重跑时
  `verification_index.private` 为空表且 `generation.sidecar.used=false`。
