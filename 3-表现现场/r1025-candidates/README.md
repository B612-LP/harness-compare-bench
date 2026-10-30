# r1025-candidates：新 5 题的双 CLI 实测（入库前闸门）

> 目的：新题库 5 题建造完成后，用 **Codex CLI + DSH CLI**（同模型 `deepseek-flash`、thinking=low、联网关、SKILL 关）各跑一遍，作为**入库前闸门**：跑通、判分可复现、且能看出行为差异才入库。
> ~~结论：5 题全部通过闸门并入 `2-用例/`；其中 2 题出现真实结果差（dabstep 与 tb 各胜一场），3 题同分（exercism / lcb 全满分，bird 双 13/15）。~~
>
> **⚠️ 数据更正（2026-10-23）**：本批把 run_dir 放在题库仓库内，agent 可用相对路径摸到 `cases/<id>/{solution/,truth.json,checker.py}`。回查轨迹确认两格是**读答案/跑 oracle** 得来的，不是解题结果：
> - `dabstep-payments-10__dsh`：`cp ../cases/dabstep-payments-10/solution/answers.jsonl ./answers.jsonl` → 原记 1 / 100；
> - `tb-cargo-plan__codex`：读 `checker.py` / `truth.json` / `solution/*.py`，直接跑 oracle 生成计划再 diff 补丁 → 原记 1 / 100。
>
> 两格已在**仓库外工作区**重跑（[`../r1027-isolated/`](../r1027-isolated/)，题面附软约束）：**DSH×dabstep = 0 / 70.0**（错 q49/q70/q2697）、**Codex×tb = 0 / 70.37**（错 8 项），失败项分别与对方的干净格**完全一致**。修正后结论：**同模型两款 CLI 在 5 题上逐题同分，headline 均 3/5，"dabstep 胜 / tb 胜" 不成立**。下表与汇总为原件保留，带 ❌ 的两格以 r1027 为准。

## 1. 协议

- 变量与 r1023 一致：Codex CLI 0.163.0 / DSH 0.2.0-rc.2，`deepseek-flash`，thinking=low，联网关，SKILL 关；Codex 用隔离 `CODEX_HOME`，DSH 用最小 `bench-cli` profile。
- 运行器 `tools/probe.py`：按 `cases/<id>/case.json` 发现用例，把 `inputs/` 拷进 run_dir，prompt 取 `instruction.md`（`{run_dir}` 占位符替换）。
- 判分：`python3 cases/<id>/checker.py <run_dir> --json`；headline 二值 + weighted 半程分。
- 每格 n=1（闸门用，不是正式通过率）；正式 N 场仍按 25 场协议另行跑。

## 2. 实测矩阵（2026-10-22，n=1/格）

| 用例 | Codex reward / weighted / 耗时 / 调用 | DSH reward / weighted / 耗时 / 调用 | 判读 |
|---|---|---|---|
| `dabstep-payments-10` | **0** / 70.0 / 274.0s / 40 | ~~**1** / 100.0 / **23.7s** / 14~~ ❌ 作弊格 | 修正：DSH 重跑 **0** / 70.0（错 q49/q70/q2697，与 Codex 同错） |
| `bird-ca-schools-15` | 1 / 86.67 / 176.6s / 60 | 1 / 86.67 / 128.5s / 35 | 平：双款同错 q26/q27（13/15） |
| `exercism-py-6` | 1 / 100.0 / 95.4s / 29 | 1 / 100.0 / 78.8s / 37 | 平：6 题全绿 |
| `lcb-recent-hard-4` | 1 / 100.0 / **182.0s** / 23 | 1 / 100.0 / 236.3s / 18 | 平：4 题全过；Codex 略快 |
| `tb-cargo-plan` | ~~**1** / 100.0 / **97.0s** / 37~~ ❌ 作弊格 | **0** / 70.37 / 155.1s / 16 | 修正：Codex 重跑 **0** / 70.37（8 项红，与 DSH 同错） |

**汇总（原件，后两行见 §2.1 修正）**

| 口径 | Codex | DSH |
|---|---|---|
| headline（5 题） | 4/5 → **修正 3/5** | 3/5 |
| weighted 总分（500） | 456.67 → **修正 427.04** | 457.04 → **修正 427.04** |
| 总耗时 | 825.0s | **622.4s**（快 24.6%） |
| 总工具调用 | 189 | **120**（少 36.5%） |

## 2.1 修正后矩阵（2026-10-23，两格在仓库外隔离工作区重跑）

| 用例 | Codex | DSH | 判读 |
|---|---|---|---|
| `dabstep-payments-10` | 0 / 70.0 | 0 / 70.0 | **同错 q49/q70/q2697** |
| `bird-ca-schools-15` | 1 / 86.67 | 1 / 86.67 | 同错 q26/q27 |
| `exercism-py-6` | 1 / 100.0 | 1 / 100.0 | 同分 |
| `lcb-recent-hard-4` | 1 / 100.0 | 1 / 100.0 | 同分 |
| `tb-cargo-plan` | 0 / 70.37 | 0 / 70.37 | **同错 8 项（重量/燃油/时间/可行性）** |
| **headline** | **3/5** | **3/5** | 逐题同分，错项集合完全一致 |

> 重跑证据：[`../r1027-isolated/runs/`](../r1027-isolated/runs/)（`dsh__dabstep-payments-10`、`codex__tb-cargo-plan`，`integrity.violations=0`）。

## 3. 发现（按修正后数据重写）

1. **同模型下两款 CLI 结果完全一致**：5 题逐题同分（86.67 / 100 / 70 / 100 / 70.37），失败项集合也相同。原「Codex 赢 tb、DSH 赢 dabstep」是作弊产生的假差异，已作废。→ 这两款 Harness 在**结果面**对同模型没有可测差异；差异若存在，只能落在过程指标（耗时 / 调用数）与取证能力上。
2. **过程面差异仍在**：即便结果同分，耗时差 24.6%、调用数差 36.5%（原件数据，未受污染的 8 格）。→ 报告里必须并列过程指标，否则「同分」会被误读成「无差异」。
3. **仍有两题饱和**：exercism-py-6 与 lcb-recent-hard-4 双款全满分。这两题保留为「能力达标位」，但**不能作为区分度来源**；要继续加区分度应加题量/更近期题，而不是加难度。
4. **用例缺陷信号**：bird 双款同错 q26/q27（同为 13/15）——两题 gold 口径涉及行数与去重细节，疑似 BIRD 标注尖角，已登记进 `2-用例/README.md` 已知问题，待人工复核。
5. **两道 hard 题对同模型是硬墙**：dabstep 与 tb 双款都只到 70 分（0.8 线下），且错项高度一致。这比「谁赢谁输」更有信息量——说明失分来自**模型对口径/多文件推理的能力上限**，不是脚手架差异。

## 4. 闸门结论（是否入库）

| 用例 | 闸门项 | 结论 |
|---|---|---|
| dabstep-payments-10 | selftest 20 组全绿 / oracle=1 / nop=0 / 双款可跑出分 | ✅ 入库 |
| bird-ca-schools-15 | selftest 19/19 / oracle=1 / nop=0 / 双款可跑出分 | ✅ 入库（附已知问题） |
| exercism-py-6 | selftest 10/10 / oracle=1 / nop=0 / 双款可跑出分 | ✅ 入库（区分度弱，标注） |
| lcb-recent-hard-4 | selftest 11/11 / oracle=1 / nop=0 / 双款可跑出分 | ✅ 入库（区分度弱，标注） |
| tb-cargo-plan | selftest 全绿 / oracle=1 / nop=0（空跑 9/27 由门槛阻断）/ 双款可跑出分 | ✅ 入库 |

## 5. 目录

```
r1025-candidates/
  BUILD-GUIDE.md          # 建造规范（builder 用）
  tools/probe.py          # 通用运行器（读 cases/<id>/case.json）
  tools/review_cases.py   # 静态审查 + selftest 跑批
  cases/<id>/             # 入库前的候选（与 2-用例/<id>/ 内容一致，保留 selftest 证据）
  <id>__<agent>/          # 10 个 run_dir：prompt / meta / agent.jsonl / agent-session / checker.stdout
  probe-results.json      # 10 场汇总
  selftest/<id>.log       # 各例 checker --selftest 原始输出
```

## 6. 复跑

```bash
export PATH=/opt/homebrew/bin:$PATH
python3 tools/probe.py --cases dabstep-payments-10,bird-ca-schools-15,exercism-py-6,lcb-recent-hard-4,tb-cargo-plan --agents both --force
python3 tools/review_cases.py        # 静态审查 + selftest
```

密钥只从 `~/.dsh/.credentials.yaml` 读进内存，不落盘；run_dir 里不含凭据。

## 7. 披露

- 每格 n=1，只能作闸门/难度定标，不能当通过率；正式排名以 25 场协议为准。
- 桌面三款未进本批次（需人工登录）；本批结论不得反推桌面端。
- `tool_calls` 由各自的 `--json` 事件流解析，两款 schema 不同，只作同款横向对比。
- `dabstep-payments-10` 的 23.5MB `payments.csv` 与 `bird-ca-schools-15` 的 11.1MB SQLite 库为本批最大输入；桌面端上传体积上限未测，列入桌面批次待观察项。

> **证据瘦身（2026-10-22）**：run_dir 里 >5MB 的 `inputs/` 副本与 `codex-home/.tmp` 插件缓存已删除（输入可从各用例 `inputs/` 重建）；保留 `prompt.txt` / `meta.json` / `agent.jsonl` / `agent.stderr.txt` / `agent-session/` / 产物 / `checker.stdout.txt`。
