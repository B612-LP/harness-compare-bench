# 用例

每条用例必须规定三件事（公告原文要求）：**任务、输入、完成条件**。
用例采用 Harbor task 格式（`task.toml` + `instruction.md` + `environment/` + `tests/test.sh` + `solution/solve.sh`），目录本身即用例全文。

## 用例清单（2026-10-16 定稿）

两用例均已通过 oracle-gating 双向验证（nop 空跑 = 0，oracle 参考解 = 1），评分器离线自足（测试期零联网）。

### `int-sum-sort/` —— 数据处理流水线（hello 级）

- **任务**：读 `/app/input.txt`（6 个整数逐行），产出 `/app/output.txt`：第 1 行求和、第 2 行个数、其余为升序逐行整数，文件以换行结尾
- **输入**：Docker 镜像内置 `/app/input.txt`（`42 17 99 8 23 56`，固定确定性）
- **完成条件**：`tests/test.sh` 四项检查（output_exists / sum_line / count_line / sorted_block）全 PASS
- **考察点**：基础文件读写 + 指令格式精确性（末尾换行）
- **分层**：基础（流水线验证）

### `word-freq-report/` —— 词频统计与排序（中等级）

- **任务**：按给定分词规则（去首尾标点、含数字 token 丢弃、连字符保留、大小写归一）统计 `/app/corpus.txt`，产出 `/app/report.txt`：总 token 数、去重词数、Top-5 词频（频次降序，**平票按 ASCII 升序决胜**）
- **输入**：`environment/corpus.txt`（11 行文本，含刻意设计的平票：`a`/`dog`/`tests` 同为 5 次，且平票组正好卡在 Top-5 边界）
- **完成条件**：`tests/test.sh` 五项检查（output_exists / total_line / distinct_line / top5_block / trailing_newline）全 PASS；期望值由评分器按同一规则现算，非硬编码
- **考察点**：多步文本处理 + 边界规则实现精度 + **平票决胜陷阱**（只按频次排序、不做词序决胜的 agent 会把 `tests` 错排进 Top-5）
- **分层**：进阶（指令精度 + 自我验证习惯）

## 约定

- Codex 与 DSH（CLI 赛道）跑**同一批用例、同一 GLM 模型（glm-5.3-flash）**，差异归因 Harness。
- 用例评分器全部离线自足——教训案例：v1 冤案（verifier 现场联网下载工具失败，测试未跑即判 0）。
- 每用例正式评分前必须过闸门 1（nop=0）与闸门 2（oracle=1），不过则用例作废；判定标准见 `../4-打分细则/`。
- 五款桌面端对比如需引用本批用例，注意桌面端口径差异（GUI 手工执行 + 录屏），归因时单独披露。
