# r1023-cli-dsf-low —— A 组 CLI 批次（Codex / DSH × DeepSeek V4.1-Flash × thinking=low）

> **定位**：五款 × 五题矩阵的 CLI 半边（2 款 × 5 题 = 10 场）。桌面三款 15 场另见后续批次。
> **跑批时间**：2026-10-22 17:38–17:43（Asia/Shanghai）｜**跑批工具**：[`tools/cli_batch.py`](tools/cli_batch.py)｜**结果**：[`batch-results.json`](batch-results.json)
>
> **⚠ 路径变更（2026-10-22 晚）**：本批所用 5 道自建用例已在题库换代中退役，移入 [`2-用例/_归档-v1/`](../../2-用例/_归档-v1/)。`tools/cli_batch.py` 的 `CASES_DIR` 仍指 `2-用例/`，若需复跑本批旧题，把 `CASES_DIR` 改指 `2-用例/_归档-v1/` 即可（checker 与输入不变）；本批结论（旧题 10/10 满分、区分度 0）正是换库依据。

## 1. 变量钉死（本批唯一的自变量是 Harness）

| 变量 | 值 | 落点 |
|---|---|---|
| 模型 | DeepSeek V4.1-Flash（`deepseek-flash`） | Codex `codex-home/config.toml`；DSH `bench-cli` profile `agent-default-model` |
| 思考档位 | **low** | Codex `model_reasoning_effort="low"`；DSH `reasoningEffort: low`（会话内 `request/header` 可复核） |
| 联网 | 关 | Codex `web_search="disabled"`；DSH 禁用 `tool-web` / `web-search-deepseek` / `web-fetch-http` |
| SKILL 工具 | 关 | Codex `[skills] include_instructions=false` + `bundled.enabled=false`；DSH 禁用 `tool-skill` / `skill-filesystem` |
| 版本 | Codex 0.163.0 · DSH 0.2.0-rc.2 · Node 24.22.0 | `meta.json` 与 `agent.jsonl` 首行 |
| 形态 | CLI（headless/exec），非桌面端 | 结论不外推到桌面端 |

隔离措施：Codex 用本目录独立 `CODEX_HOME`（不碰用户 `~/.codex`）；DSH 用新建 `bench-cli` profile（仅 base + headless，**无 mnemon / agent-team**，不注入额外记忆或子代理）。两者都改不到用户日常配置。

## 2. 协议

1. 每个 `(用例, 产品)` 一个运行目录 `3-表现现场/r1023-cli-dsf-low/<case>__<agent>/`。
2. 输入按用例约定复制（`/app/*` 形态用例复制到根目录；`environment/`、`inputs/` 形态保留子目录），SHA-256 记入 `meta.json`。
3. 任务书取 `2-用例/<case>/instruction.md` 原文；**只做一处改写**：`/app/` 前缀替换为运行目录绝对路径（`meta.json.prompt_rewrites` 记录），并追加一段评测环境说明。其余措辞一字未改。
4. agent 的 cwd = 运行目录，产物直接落该目录。
5. 判分只认 `python3 2-用例/<case>/checker.py <run_dir> --json`（absolute path）。

## 3. 结果（10/10 全过）

| 用例 | Codex | DSH | 备注 |
|---|---|---|---|
| int-sum-sort | ✅ 1（14.5s / 5 工具调用） | ✅ 1（5.3s / 3） | 格式关 |
| word-freq-report | ✅ 1（15.8s / 5） | ✅ 1（8.0s / 2） | 平票陷阱未拦住 |
| jielong-fullchain | ✅ 1（48.5s / 9） | ✅ 1（58.5s / 10） | hard |
| ledger-replay | ✅ 1（29.7s / 7） | ✅ 1（26.9s / 6） | hard |
| corpus-squeeze | ✅ 1（39.1s / 8） | ✅ 1（36.5s / 9） | ratio 0.2187（阈值 0.35） |

每场 `agent-session/` 内含完整轨迹（Codex rollout JSONL；DSH `session.v4.jsonl.zstd`，`zstd -dc` 可读），`checker.stdout.txt` 与 `meta.json.reward` 可复核。

## 4. 发现（按「现象 / 线索 / 验证状态」表述）

1. **现象：结果面完全饱和**——同模型同档位下，两款产品把 5 道题（含 3 道 hard）全部打满，binary 全 1。
   - 线索：hard 题没有出现「差一半」的部分分信号，`weighted` 也全是 100。
   - 状态：**已验证**（10 场产物 + checker 逐项 PASS 在案）。含义：这批题在 CLI × low 档位下**区分不出两款 Harness**，只能支撑「能力达标」；排名需靠过程面或加难度。
2. **现象：过程面存在稳定差异**——DSH 每场工具调用更少、耗时更短（int-sum 5.3s vs 14.5s、word-freq 2 次 vs 5 次），Codex 每场固定多出一次 `error` 事件（模型元数据 fallback 警告）+ 更多 shell 轮次。
   - 状态：**已验证**（`meta.json.process` 与 `agent.jsonl` 可复算）；**未定性**——差异来自编排策略还是重试策略，需再看轨迹。
3. **现象：`corpus-squeeze` 两款产出的 `compressed.bin` 字节完全相同**（`sha256 add724ae…`），但 `decompress.py` 不同（2444B / 3407B）。
   - 线索：两份解压器都是 LSB-first 位读取的 LZSS+Huffman 经典布局，属「同一教科书方案收敛」；两侧轨迹里均无跨目录复制痕迹（`../` 只出现在目录列举输出中）。
   - 状态：**独立性待查**（不判作弊、也不当巧合忽略）；下一步是换一组语料变体重跑，若仍字节相同则说明题目只考到了唯一解空间。
4. **发现一个判卷器真实缺陷**：`corpus-squeeze/checker.py` 在 `run_dir` 传**相对路径**时，roundtrip 子进程拿到被截断的路径（stderr 显示 `...__co`），解压器 exit=2 → 误判 0 分；传绝对路径则 1 分。
   - 状态：**已验证可复现**（同一 run_dir 相对/绝对两次判分 0 vs 1）。属「修复一个判卷漏洞」的现成素材，修法=checker 入口处 `run_dir = run_dir.resolve()`。

## 5. 已知偏差与披露

- Codex 不认识第三方模型 id：每场报 `Model metadata for deepseek-flash not found`，回落到 272k 上下文 fallback。可用 `model_catalog_json` 修，本批未修（记录在案，不影响判定）。
- Codex 启动时向 `chatgpt.com/backend-api/plugins/featured` 发一次请求（401），属产品内置插件目录拉取，未参与工具循环，已披露。
- DSH 会话轨迹不含 token usage 事件，本批**不给 DSH token 数**；token 口径保持 `5-评测报告/未知登记.json` 的 `token-cause` 开放状态，不做跨产品 token 对比。
- `int-sum-sort__dsh` 曾因单场调试产生两条会话记录，清理后重跑一次；`agent-session/` 内仅保留重跑那条。

## 6. 复算

```bash
cd 3-表现现场/r1023-cli-dsf-low
python3 tools/cli_batch.py --cases all --agents both --force      # 重跑 10 场
python3 2-用例/corpus-squeeze/checker.py "$(pwd)/corpus-squeeze__codex"   # 单场复核（务必绝对路径）
zstd -dc jielong-fullchain__dsh/agent-session/session.v4.jsonl.zstd | head
```
