# bird 交互量结构分解 · 执行记录（2026-11-16）

本文件是 [bird交互量结构分解](<README.md>) 包的执行记录。预注册 README（SHA256 `5b697126551d82265425cc1864da23a10f411cca4492651071cc390375661ee4`）由包内 verify.py 钉定、字节冻结不改；批次页与 bw-retest 观察页均为钉定源，本记录不改写任何被钉定页（沿用 R3 包先例：执行记录独立成文件）。

## 执行流程

1. builder 按[冻结预注册](<README.md>)实现 `verify.py` / `test_verify.py` / `result.json`；canonical 字节口径逐字复用[机制重复口径澄清 v1.1](<../../机制重复口径澄清-2026-11-12/verify.py>) 与 [机制序列口径v2](<../../机制序列口径v2-2026-11-16/verify.py>) 的约定（事件对象整体 canonical JSON，无 payload 包装）。归档真身为多帧 zstd，需 `read_across_frames=True` 读取（单帧解压会静默截断，已在实现中处理并记录）。
2. **S4 硬等通过**：三槽逐事件重算 assistant/message + tool/call canonical 字节和，与冻结钉定 551,905 / 193,745 / 517142 B 全等（exit 0）；公开骨架 29/29/27（assistant）、29/29/29（tool/call）、3/3/3（user）与旧单划线聚合全等核对通过；更正版 r2 聚合（`session-dsh__bird-ca-schools-15__r2.json`，SHA 钉定）复核 9/16/3 与 193745。
3. 测试 18/18 双模式（`python3` 与 `python3 -O`）通过；CLI stdout 跨模式逐字一致；`--output` 独占创建；存量 result.json 与重算逐字节相等。

## 如实登记的两点口径事实

- **预注册"骨架近乎一致"前提只对旧公开页成立。**真身 r2 为 9 assistant/16 tool/3 user、9 轮（错捕残留已按 [v1.1 勘误](<../../机制重复口径澄清-2026-11-12/README.md>)换回真身，SHA 与 trace-incident `new_sha` 前缀对账）；本包以真身为准，旧页值 551,905 按原样记录于 result.json `stale_record` 仅作溯源，不作本包 r2 钉定。
- **字节主载体是 assistant 文本而非大参数工具调用。**assistant/message 占 S4 约 95%/91%/95%（522,517 / 176,818 / 491,492 B）；tool/call 合计仅 29,388 / 16,927 / 25,650 B（bash 29,135/16,927/24,893，read 253/0/757）。预注册 H-A 措辞（"大参数工具调用"）在本数据上不成立为载体解释，如实报告为消息文本载体。

## 结果摘要（与 result.json 一致）

- **集中度混合**：r1 29 轮 top-5 占比 42.49%（H-B 分散）、r2 9 轮 85.05%（H-A 集中）、r3 27 轮 38.60%（H-B 分散）；≥2× 首分岔轮内字节缺口不存在（轮 1 为 4,223/5,406/5,694）。
- **结构早期分岔**：三 rep 工具名序列三方 LCP=1（全体先 bash，第 2 次调用 r1/r3 走 read、r2 走 bash），1 < min轮数 9 的一半 → early-divergence；r2 的 S4 缺口主要来自缺失第 10 轮及以后的轮次（共享步 1–9 逐轮字节已并排记录）。
- **分数并排（不构成因果）**：r1 14/15（reported 93.33333333，reward 1）、r2/r3 15/15（100.0，reward 1）；三份收据均带 judging_incident（in-run judge 早于冻结 checker truth/inputs 完成跑出，随后以同一冻结 checker 字节对归档工作区副本补判；完整 cause 原文见各 score-receipt.json 与本包 result.json `score_alignment`）。
- 窗口外事件桶：三 rep 均为空（无窗外 assistant/message 或 tool/call）；真身解压行数 189/83/181。

## 边界

内容无关结构算术：事件类型、canonical 字节数、工具名、SHA；不含消息内容、工具参数、线上字节、token 或成本。分数仅并排展示，不对 S4 结构与得分作因果主张。无新增产品运行；不改判任何分数；不动任何被钉定页。
