# 用例

每条用例必须规定三件事（公告原文要求）：**任务、输入、完成条件**。
用例采用 Harbor task 格式（`task.toml` + `instruction.md` + `environment/` + `tests/test.sh` + `solution/solve.sh`），目录本身即用例全文。
**2026-10-21 v0.3 起**：正式评分入口改为轻量判卷器 `checker.py <run_dir>`（产物目录判分，见 [`4-打分细则/轻量判卷/`](../4-打分细则/轻量判卷/README.md)）；同目录另有 `spec.md`（观察项/权重/行为锚点）与 `truth.json`（输入 SHA-256 + 期望值）。Harbor `tests/test.sh` 保留为历史实现，二值口径不变。

## 用例清单（2026-10-16 定稿）

两用例均已通过 oracle-gating 双向验证（nop 空跑 = 0，oracle 参考解 = 1），评分器离线自足（测试期零联网）。

## hard 带用例（2026-10-22 新增，回应「满分区间无区分度」）

三道 hard 题按「多源冲突重建 / 契约级输出精确 / 连续量验收」三条区分度轴布局，均为纯产物判分（五件套：instruction.md / environment|inputs / checker.py / spec.md / truth.json，附 solution/ 参考解）。lead 已实测：三题 `--selftest`（10/12/12 组）全绿、oracle reward=1；corpus-squeeze 另有朴素解负对照 reward=0。hard 带入库纪律：空跑预期 ≤0.3、oracle=1（对齐 WorkBuddy Bench 准入闸门），阈值题须在 spec.md 留实测校准记录。难度依据与下一批改造清单见 `5-学习笔记/题库收集-2026-10-22/01-网络题源/05-困难题源-GitHub清单.md`（本地档案）。

### `jielong-fullchain/` —— 微信接龙解析与分单全链路（hard·两栖）

- **任务**：读 13 人两段接龙 + 匿名别名表 + 4 张包场单，产出 `resolution.json`（逐人 seq/raw/sid/status/slots/note）与 `plan.json`（逐单 add/skip/reject/reason）
- **陷阱**：日期笔误头、「9:00」是到达备注非场次、emoji 剥离 vs 原样双路径、全角归一、重名→conflict 不许猜、泛称/零命中→unmatched、先填满单 A 再溢出、skip_existing、散场单拒收带 reason；账本守恒 13 = 9 matched + 1 本人 + 2 unmatched + 1 conflict，6 add / 1 skip / 7 reject
- **考察点**：多源冲突消解 + 契约级输出精确（规则数量 × 单数据流级联，无局部修复）

### `ledger-replay/` —— 乱序事件日志的状态机重建与异常对账（hard·两栖偏 CLI）

- **任务**：重放 305 行乱序事件日志，产出 `final_state.json`（100 订单终态+金额）与 `anomalies.json`（11 条异常分类清单）
- **规则**：按 seq 升序重放（同 seq 按 msg_id 字典序）、重复 msg_id 幂等去重、cancel-after-complete 状态不变、unacked 生效但记异常、负金额拒生效、金额整数分禁浮点
- **考察点**：冲突状态重建（物理序≠逻辑序×tie-break×幂等）+ 四类异常两两不同的处置 + 金额守恒双向夹逼

### `corpus-squeeze/` —— 受限压缩达标（hard·迭代优化，RE-Bench 风格，CLI 为主）

- **任务**：对 204,180B 确定性语料交付 `compressed.bin` + `decompress.py`（≤8KB、仅 stdlib、禁 zlib/lzma/bz2、只读 argv），压缩率 ≤0.35 且解压逐字节还原
- **校准**：阈值 0.35 实测锁定——纯 order-0 Huffman 0.806（挂）→ 必须自实现 LZ；参考解 LZ77+Huffman 0.2303（余量 34.2%）；朴素 RLE 1.0006（负对照）
- **考察点**：连续量验收 + 「写→自测→调优→再验证」迭代任务链（行为锚点记自测/报告/重试）

### `int-sum-sort/` —— 数据处理流水线（hello 级）

- **任务**：读 `/app/input.txt`（6 个整数逐行），产出 `/app/output.txt`：第 1 行求和、第 2 行个数、其余为升序逐行整数，文件以换行结尾
- **输入**：`environment/input.txt`（`42 17 99 8 23 56`，固定确定性；v0.3 起落盘，字节与旧 Dockerfile 一致）
- **完成条件**：`checker.py`（v0.3）六项全 PASS——产物存在 / 输入完整性（输入被改直接 0）/ 严格格式（8 行、纯 LF、恰好一个结尾换行、每行一个规范整数）/ sum_line / count_line / sorted_block；`tests/test.sh` 为 v0.2 历史实现
- **考察点**：基础文件读写 + 指令格式精确性（末尾换行）
- **分层**：基础（流水线验证）

### `word-freq-report/` —— 词频统计与排序（中等级）

- **任务**：按给定分词规则（去首尾标点、含数字 token 丢弃、连字符保留、大小写归一）统计 `/app/corpus.txt`，产出 `/app/report.txt`：总 token 数、去重词数、Top-5 词频（频次降序，**平票按 ASCII 升序决胜**）
- **输入**：`environment/corpus.txt`（11 行文本，含刻意设计的平票：`a`/`dog`/`tests` 同为 5 次，且平票组正好卡在 Top-5 边界）
- **完成条件**：`checker.py`（v0.3）六项全 PASS——产物存在 / 输入完整性 / 严格格式（7 行、单空格、纯 LF、恰好一个结尾换行）/ total_line / distinct_line / top5_block；期望值现算并与 `truth.json` 交叉校验（非硬编码）。`tests/test.sh` 为 v0.2 历史实现
- **考察点**：多步文本处理 + 边界规则实现精度 + **平票决胜陷阱**（只按频次排序、不做词序决胜的 agent 会把 `tests` 错排进 Top-5）
- **规格修正**：任务书标点数 12→11（实际只列 11 个字符；语料不含第 12 个候选字符，行为无变化）
- **分层**：进阶（指令精度 + 自我验证习惯）

## 约定

- Codex 与 DSH（CLI 赛道）跑**同一批用例、同一 GLM 模型（glm-5.3-flash）**，差异归因 Harness。
- 用例评分器全部离线自足——教训案例：v1 冤案（verifier 现场联网下载工具失败，测试未跑即判 0）。
- 每用例正式评分前必须过闸门 1（nop=0）与闸门 2（oracle=1），不过则用例作废；判定标准见 `../4-打分细则/`。
- **v0.3 起**：`checker.py --selftest` 必须全 PASS（≥6 组负例，含篡改输入）才可评正式分；改 checker 后须重跑自测 + oracle 回归（参考解产物 → reward=1）。
- 五款桌面端对比如需引用本批用例，注意桌面端口径差异（GUI 手工执行 + 录屏），走 `../4-打分细则/轻量判卷/` 的产物判分 + 行为锚点；归因时单独披露。
