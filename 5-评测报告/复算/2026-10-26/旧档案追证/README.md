# 旧档案追证（2026-10-26，第二轮，比首轮更彻底）

针对 `5-评测报告/未知登记.json` 两条 open 项 `env-netflake`、`env-v1-verifier-download` 的第二轮追证。
执行者：archive-hunter 子代理；约束：除本目录外全系统只读、未动 CHANGELOG、未 git add/commit、时间盒 30 分钟（实际约 25 分钟收口）。

## 结论先行

| 条目 | 本轮结果 | 建议 |
| --- | --- | --- |
| `env-netflake` | **找到**。2 次失败尝试原始日志（exception/trial.log/result.json）2/2 全部命中 | 转 **accepted**（依据=本目录；决定权留 Lead） |
| `env-v1-verifier-download` | **找到**。verifier/test-stdout.txt + reward.txt=0 + result.json（2026-10-13 坐实） | 转 **accepted**（依据=本目录；决定权留 Lead） |

证据：见 `证据清单.json`（每件 SHA-256 + tarball 内路径 + 宿舍机原始绝对路径）与 `evidence/`（10 个文件，共约 30KB）。

## 证据从哪来（链条）

1. 原始落盘：宿舍机 `/mnt/c/Users/Administrator/Desktop/harness-compare-bench/jobs/`（各 result.json `trial_uri` 自证）。
2. 2026-10-22 前后，「宿舍机素材」拷入学习笔记题库收集（`03-宿舍机/素材/Desktop/harness-compare-bench-old/jobs/`）。
3. 2026-10-25 16:46 打包为 `~/bench-archive/5-学习笔记-20261025.tar.gz`（SHA-256 `6386f775…bd874`，1,953,455 B）。
4. 本轮 `tar -xzOf` 流式提取最小片段入 `evidence/`（交付目录外零落盘）。

关键突破：旧档案仓在本机 **不存在**（Desktop 已空、Spotlight 全库无 `harness-compare-bench-old`），它实际住在**宿舍机 Desktop**；本机唯一副本是上述 tarball——`mdfind -name 学习笔记` 一击命中，属于任务清单之外但合理的档案面。

## 搜索面记录（每处：命令 → 命中/未命中）

### a) 本仓库 git 历史

- `git log --all --oneline | head`：全历史共 **21 个提交**（76c1455 2026-10-16 init → 967de9a/9a85ea5 2026-10-26）。
- `git grep netflake $(git rev-list --all)`：命中仅 4 个**叙述性文档**（3-表现现场/README.md、5-评测报告/未知登记.json、阶段报告-v1.0.md、阶段报告-骨架-v0.1.md）；**无任何原始日志**。
- `git grep test-stdout / verifier $(git rev-list --all)`：命中均为本仓重跑现场（r1016-*/r1016x-* 的 verifier/test-stdout.txt）、工具链与 task.toml；demo 原件不在。
- 否定性验证（原始日志从未入仓的铁证）：
  - `git grep NetworkConnectionError $(git rev-list --all)` → **零命中**；
  - `git grep NonZeroAgentExitCodeError $(git rev-list --all)` → **零命中**；
  - `git grep 9twujcB / gpt2-codegolf__9twujcB $(git rev-list --all)` → **零命中**；
  - `git grep superseded-r1016x-wordfreq-codex-netflake` → 仅 3-表现现场/README.md 一处目录名提及。
- 旁证：commit 5646806（2026-10-19）「旧档案仓更名 harness-compare-bench-old，7 个 run-*.sh 的 BENCH 指向 Desktop/harness-compare-bench-old」→ 旧仓在**宿舍机 Desktop**，不在本机。

### b) 本机目录只读搜

| 面 | 命令 | 结果 |
| --- | --- | --- |
| `~/bench-workspaces/`（478M） | `find ~/bench-workspaces -iname "*netflake*" -o -iname "*word-freq*" -o -iname "*gpt2-codegolf*"` | **零命中**；顶层仅 r1027–r20261026 时代工作区，无 10-13/10-16 旧痕 |
| `~/bench-automation/` 含 `runs/`（1.7G） | `find … -iname "*netflake*" -o -iname "*superseded*" -o -iname "*codex-glm-demo*"`；`grep -rl netflake …` | **零命中**；runs/ 仅 r1025+ |
| `~/.dsh/attachments/`（70M） | `find ~/.dsh/attachments -iname …`；列目录 | 无有效命中：仅 `v1/objects/<hash>` 内容寻址 blob 库（"v1"是库 schema 版本，与评测 v1 无关），无索引、文件名即哈希，无法归属到任何评测现场 |
| `~/Documents` 其他仓库 | `find ~/Documents -maxdepth 6 (netflake|codex-glm-demo|harness-compare-bench-old)`（排除本仓） | **零命中** |
| `~/.Trash` | `ls -la ~/.Trash`；`find ~/.Trash -maxdepth 3` | **空** |
| **命中面**：`~/bench-archive/` | `mdfind -name 学习笔记` | **命中** `5-学习笔记-20261025.tar.gz`（见上链条第 3 步） |

### c) mdfind / find 按文件名碎片

| 碎片 | 命令 | 结果 |
| --- | --- | --- |
| `harness-compare-bench-old` | `mdfind -name` | **零命中**（旧仓不在本机） |
| `netflake` | `mdfind -name` | **零命中**（带该名的文件只在 tarball 内部，Spotlight 不索引压缩包内容） |
| `test-stdout` | `mdfind -name` | 14 命中，全部是**本仓重跑现场**的 verifier/test-stdout.txt，非 demo 原件 |
| `superseded` | `mdfind -name` | **零命中** |
| `2026-10-13`（仓外） | `mdfind -name` | **零命中** |
| `word-freq-report`（仓外） | `mdfind -name` | **零命中** |

## 条目一 `env-netflake`：2/2 失败尝试原始日志全部找到

仓内叙述「node tarball 撕裂 ×1、codex 平台二进制缺失 ×1」与 tarball 内**两个** superseded 目录一一对应（数量、失败形态均吻合）：

1. **attempt1**（node tarball 撕裂）：`superseded-r1016x-wordfreq-codex-netflake/word-freq-report__MvXwWec`
   - `NetworkConnectionError`，`curl: (56) OpenSSL SSL_read … decryption failed or bad record mac`，`nodejs.org/dist/v22.23.3/…tar.xz` 下载失败；`occurred_at 2026-10-16T10:54:06Z`；
   - 任务 word-freq-report，agent codex 0.162.1 + mimo-v2.6-flash（config-xiaomi.toml + compose-proxy-overlay-v2）。
2. **attempt2**（codex 平台二进制缺失）：`superseded-r1016x-wordfreq-codex-netflake-a1/word-freq-report__3UprjXj`
   - `NonZeroAgentExitCodeError`（exit 1），`Error: Missing optional dependency @openai/codex-linux-x64`；`occurred_at 2026-10-16T11:26:07Z`（与 attempt1 相隔 32 分钟，符合重试时序）。

每件均含 `exception.txt` / `trial.log` / `result.json` 原始三件套（已提取入库，哈希见清单）。tarball 中 netflake 目录有且仅有这两个（`tar -tzf | grep -c` 各 18 条目）。

## 条目二 `env-v1-verifier-download`：冤案原始证据找到

`codex-glm-demo/gpt2-codegolf__9twujcB`（2026-10-13T04:42:52Z–04:53:34Z，即北京时间 12:42 起；codex 0.162.1 + glm-5.3-flash；题源 terminal-bench-2 gpt2-codegolf）：

- `verifier/test-stdout.txt`（全文 23 行，已入库）关键三连：
  `curl: (56) Failure when receiving data from the peer` → `failed to download uv 0.9.5 …` → `/tests/test.sh: line 10: /root/.local/bin/env: No such file or directory`、`line 19: uvx: command not found`——**测试根本没跑**；
- `verifier/reward.txt` = `0`；`result.json`：`verifier_result.reward=0.0` 且 `exception_info=null`（verifier 进程"正常完成"，判 0）——与「0 分先读 test-stdout」教训的叙述逐字吻合；
- 同目录 `codex-glm-demo-v4/`（__C3zCt4N）为修复后重跑件，本轮未提取（超出该条最小取证范围，仅备注）。

## 给 Lead 的建议（决定权在 Lead）

- **`env-netflake` → 建议 `open` 转 `accepted`**：本条停止条件为「旧档案不可得或补取成本高于收益时，保持 open 仅作过程备注」。现档案已取得且 2/2 对应，「环境层失败数不可复核」的影响解除：2 次失败可升级为**可核对的失败计数**（仍不计入运行数、不参与结论，口径不变，但依据从「口述备注」变为「仓内原始日志」）。若采纳，next_step 可改写为指向本目录证据。
- **`env-v1-verifier-download` → 建议 `open` 转 `accepted`**：停止条件同款触发反转——档案可得。该案例可从「教训叙述」升级为**仓内可复核的方法学案例**（环境层下载失败 → 测试未跑 → 误判 0 → 先读 test-stdout），并作为环境层失败形态的正面样例；按其停止条件，它仍不作产品能力对比的分值证据，仅支撑原则与方法。
- 保留意见（如实披露）：证据是宿舍机快照的 tarball 副本，非本机原盘直读；两条 result.json 自带的 trial_uri/时间戳/哈希链足以自洽，但若 Lead 要求最强证据链，可再从宿舍机 `work-01` 的 `/mnt/c/Users/Administrator/Desktop/harness-compare-bench/jobs/` 对原盘哈希做一次只读比对（本任务范围外，未执行）。

## 未做的事（边界）

- 未提取 config.json / lock.json / agent 轨迹 / artifacts（最小片段原则之外）；
- 未 SSH 宿舍机（任务面限定本机只读）；
- 未改动 未知登记.json / CHANGELOG.md / 任何 git 状态（`git status` 应只显示本目录为新增未跟踪）。
