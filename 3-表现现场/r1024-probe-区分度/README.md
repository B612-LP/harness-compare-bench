# r1024-probe-区分度：换题库前的难度/区分度实测批次

> 目的：现有 5 题被 A 组两款 CLI 打满（`3-表现现场/r1023-cli-dsf-low/`，10/10），本批次用**公开模型/Agent 评测集**改造出最小五件套，先跑「小样本探针」，用实测数据判断每道候选题是否落在目标难度区（DeepSeek V4.1-Flash + thinking=low 下 pass/得分 30%–75%），再决定进 5 题的名单。
> 探针不等于正式场：每格 n=1，只作难度定标；正式批次仍按 25 场协议跑。

## 1. 协议

- 变量与 r1023 批次完全一致：Codex CLI 0.163.0 / DSH 0.2.0-rc.2，模型 `deepseek-flash`，thinking=**low**，联网关、SKILL 关、Codex 用隔离 `CODEX_HOME`、DSH 用最小 `bench-cli` profile。
- 每个 (case, agent) 一个 run_dir：`<case>__<agent>/`；`inputs/` 拷入后即为运行目录；产物落 run_dir。
- 判分 = `cases/<case>/checker.py <run_dir> --json`；headline 二值由 checker 给，另记 weighted。
- 运行器：`tools/probe.py`（与 r1023 的 `cli_batch.py` 同源，改为按 `cases/<name>/case.json` 发现用例）。

## 2. 候选题与来源（均为 2026-10-22 实拉）

| 探针题 | 来源 | 许可证 | 判分器 | 结构 |
|---|---|---|---|---|
| `dabstep-dev10` | [DABstep](https://huggingface.co/datasets/adyen/DABstep) dev 10 题 + 官方 context（payments.csv 23.5MB 等） | CC-BY-4.0 | 官方 `question_scorer`（146 行，无 LLM） | 10 题 → `answers.jsonl`，通过率 ≥0.8 记 1 |
| `bird-schools15` | [BIRD](https://bird-bench.github.io/) mini_dev `california_schools` 切片 15 题（challenging 5 / moderate 7 / simple 3）+ 11MB SQLite 库 | CC BY-SA 4.0 | 自实现 exec-accuracy（跑 gold/pred SQL 比对结果多重集） | 15 题 → `answers.jsonl`，通过率 ≥0.8 记 1 |
| `polyglot-py3` | [Aider polyglot](https://github.com/Aider-AI/polyglot-benchmark) / Exercism Python：`forth` / `poker` / `dominoes` | MIT（Exercism） | 官方 `unittest` 测试（判分前还原测试文件） | 3 题全绿记 1，weighted=通过题数比例 |
| `lcb-hard3` | LiveCodeBench lite 镜像抽 3 道 2023 年 LeetCode hard（2879 / 3223 / 3091） | MIT（LCB） | 官方题包 15 组测试（`Solution.<fn>` 调用） | 3 题，通过 ≥2 题记 1 |
| `lcb-v6-hard4` | 官方 [LiveCodeBench v6](https://github.com/LiveCodeBench/LiveCodeBench) `test6.jsonl` 近期 hard：AtCoder `abc387_f` / `abc388_f` / `abc388_g` / `abc389_g`（含 private tests） | MIT（LCB） | LCB judge 移植（stdin/stdout 逐组比对） | 4 题，通过 ≥2 题记 1 |

用例生成脚本：`tools/build_probe_cases.py`（dabstep / bird / polyglot）、`tools/build_lcb_case.py`、`tools/build_lcb_v6_case.py`；原始数据来自 `5-学习笔记/题库调研-2026-10-22-区分度/` 四份调研卡对应的实拉目录（`/tmp/tb-probe/`，不入库）。

## 3. 实测结果（2026-10-22，每格 n=1）

| 候选题 | agent | reward | weighted | 耗时 | 工具调用 |
|---|---|---|---|---|---|
| `dabstep-dev10` | codex | 1 | 80.0 | 352.7s | 62 |
| `dabstep-dev10` | dsh | 1 | 100.0 | 89.4s | 30 |
| `bird-schools15` | codex | 1 | 100.0 | 68.0s | 33 |
| `bird-schools15` | dsh | 1 | 100.0 | 26.0s | 11 |
| `polyglot-py3` | codex | 1 | 100.0 | 47.1s | 18 |
| `polyglot-py3` | dsh | 1 | 100.0 | 26.6s | 18 |
| `lcb-hard3` | codex | 1 | 100.0 | 46.9s | 8 |
| `lcb-hard3` | dsh | 1 | 100.0 | 33.2s | 6 |
| `lcb-v6-hard4` | codex | 1 | 100.0 | 414.4s | 43 |
| `lcb-v6-hard4` | dsh | 1 | 100.0 | 303.2s | 29 |

## 4. 发现

1. **公开基准的「中档」对这两款已经饱和**：BIRD 15 题（含 5 道 challenging）两款都 15/15；Exercism 三道 hard（forth/poker/dominoes）两款都 3/3；DABstep dev 也 8/10 与 10/10。→ 换题库不能只换「更有名」的题，必须换到**前沿难度**。
2. **近期竞赛 hard 也照样被打穿**：官方 LiveCodeBench v6（2025-01 窗口、含 private tests）4 道 AtCoder F/G，两款都 **4/4**（Codex 414s/43 次，DSH 303s/29 次）。→ 算法难度不是当前的分水岭，**耗时才刚开始分开**。
3. **2023 年的 LeetCode hard 不可用作难度证据**：两款各用 6–8 次工具调用、<50s 解出 3 道（其中 `countSubMultisets` 是模数 DP、`minimumChanges` 是带除数的区间 DP），高度疑似训练集污染（LCB 本身按时间窗做防污染，2023 题不在保护窗内）。
4. **过程面差异稳定存在**：同样满分，DSH 普遍比 Codex 快 2–4×、工具调用少 2–3×（BIRD 26s/11 次 vs 68s/33 次；polyglot 26.6s vs 47.1s）；DABstep 是唯一出现**结果面差异**的题（Codex 8/10，慢了 4×、调用多一倍）。→ 单题二值口径分不出高下时，「耗时/调用数/自测次数」才是可复核的 Harness 差异。
5. **探针自身教训**：第一次跑 polyglot 时 `inputs/` 被拍平到根目录，三题全 0 —— 用例包路径约定必须进 selftest，否则会把「用例打包 bug」误读成「产品失败」。

## 5. 局限与披露

- 每格 n=1，不能当通过率；只用于难度定标。
- 桌面三款未进本批次（需人工登录），本批次结论**不得反推桌面端**。
- `tool_calls` 由 `--json` 事件流解析，两款事件 schema 不同，口径只作同款内部横向对比（同一解析器）。
- `lcb-hard3` 的题面/测试来自 LCB lite 社区镜像，`lcb-v6-hard4` 来自官方 v6（含 private tests）；前者仅作污染对照，不进正式题库。
- 复跑：`python3 tools/probe.py --cases <name> --agents both --force`（需 `DEEPSEEK_API_KEY` 走 `~/.dsh/.credentials.yaml`，脚本只读内存）。

> **证据瘦身（2026-10-22）**：run_dir 里 >5MB 的 `inputs/` 副本与 `codex-home/.tmp` 插件缓存已删除（输入可从各用例 `inputs/` 重建）；保留 `prompt.txt` / `meta.json` / `agent.jsonl` / `agent.stderr.txt` / `agent-session/` / 产物 / `checker.stdout.txt`。
