# 判卷回归一键化

一条命令跑完「判卷器自测 + 审计收据完整性校验」，产出机器可读的 `results.json` 与人读的 markdown 汇总。仅依赖 Python 3 标准库，不联网、不装包、不需要模型或历史绝对路径；不改任何既有判卷资产（只读校验，自测内部使用临时副本）。

## 用法

仓库根目录执行：

```bash
python3 4-打分细则/判卷回归/run_regression.py
```

可选参数：

| 参数 | 默认 | 说明 |
|---|---|---|
| `--output PATH` | `4-打分细则/判卷回归/results.json` | 机器结果 JSON 输出路径 |
| `--timeout N` | `600` | 单个 selftest 超时秒数 |

退出码：`0` = 全部通过；`1` = 任一自测或 SHA 校验失败；`2` = 环境/参数错误（如找不到仓库结构）。失败项会全部列出后才退出，便于一次看清所有红项。

实测全绿耗时约 40 s（其中 lcb-recent-hard-4 自测约 28 s，exercism-py-6 约 7 s）；全量日志收据见 [run-2026-10-26.stdout.txt](<run-2026-10-26.stdout.txt>)（首次真跑，exit 0）。每次重要变更后建议另存一份带日期的 stdout 收据，如 `run-YYYY-MM-DD.stdout.txt`。

## 校验范围

### 1) 五题自测

依次执行 `python3 2-用例/<case>/checker.py --selftest`，捕获退出码与输出尾部（stdout 末 2000 字符 + stderr 末 1000 字符，均入 `results.json`）：

| 用例 | 首跑（2026-10-26） |
|---|---|
| bird-ca-schools-15 | exit 0，25/25 |
| dabstep-payments-10 | exit 0，23 组 |
| exercism-py-6 | exit 0，16/16 |
| lcb-recent-hard-4 | exit 0，11/11 |
| tb-cargo-plan | exit 0，nop/oracle/6 负例全过 |

判定标准：退出码非 0 即失败（这些 checker 约定 2=用例/契约 ERROR，selftest 失败也非 0）。

### 2) 审计收据存在性 + SHA-256 校验（47 条）

清单固化在脚本 `SHA_MANIFEST`，**SHA 快照日期 2026-10-26，判卷资产变更时需刷新**（重算对应条目的 SHA-256 并更新脚本注释、本 README 与新收据）。覆盖：

| 族 | 条数 | 内容 |
|---|---|---|
| [判卷审计-2026-10-24](<../判卷审计-2026-10-24/README.md>) 总 README | 1 | 审计总结 |
| execution（执行族） | 16 | README、frozen-artifacts.json、红绿证据 before/after JSON+log、修前冻结 checker/spec/truth ×2 题、final-validation.json、grade-copy-smoke.json、grade-copy.py、reproduce.py |
| numeric（数值族） | 10 | README、run_audit.py、results.json（40/40）、BIRD/DAB selftest stdout、frozen/sha256.json 与 v1.0 冻结 checker/truth ×2 题 |
| lcb（lcb 族） | 3 | README、oracle-sha256.json、selftest-2026-10-26.stdout.txt（11/11） |
| [bird-q26-并入](<../判卷审计-2026-10-26/bird-q26-并入/README.md>) | 7 | README、sha256-manifest.json、selftest stdout（25/25）、replay 脚本与结果、q27_verify 脚本与结果 |
| 现行判卷资产（`2-用例/` 现行文件，审计 README 明示声明） | 10 | exercism checker/trusted_runner/truth + cargo checker/truth（值取自 execution/frozen-artifacts.json）；bird checker/truth/questions.json/db/answers.jsonl（值取自 bird-q26 sha256-manifest.json §3 v1.2 现行列） |

校验方式：逐条「文件存在 + 当前实际 SHA-256 == 清单期望值」；缺失或漂移均计失败。审计 README 中同时声明的新旧版本对照哈希（如 v1.1/v1.2）不重复固化，以各审计目录自带清单为准，本脚本只固化「当前实际值」。lcb 私有 staging oracle（`staging/solution/*.py`）不入仓库正文，其哈希已由 [lcb/oracle-sha256.json](<../判卷审计-2026-10-24/lcb/oracle-sha256.json>)（本身被固化）收编，不在本机可校验范围。

### 3) 输出

- stdout：markdown 汇总表（自测表 + 输出尾部摘录 + SHA 47 行明细 + 总体结论）。
- `results.json`：结构化结果（`overall` / `exit_code` / `summary` / 逐条 `selftests` 与 `sha_checks`），供后续自动化消费。

## 扩展点（本期未启用，不依赖相应目录存在）

脚本按「阶段列表」组织：每阶段一个函数，返回 `(逐条结果, 是否全过)`，`main()` 顺序执行并聚合退出码。新增校验只需写一个阶段函数并挂进执行序列，无需改动现有两阶段：

1. **mutation 负例矩阵**：若后续建立统一的 mutation 负例目录（如 `4-打分细则/判卷回归/mutation-matrix/`，每条负例一个 `case.json` 声明 `runner 命令 + 期望退出码 + 期望 reward/weighted`），可新增 `stage_mutation_matrix()`：遍历目录逐条跑命令、比对期望、把每条结果并入 `results.json["mutation_matrix"]`。目录不存在时建议默认跳过并在汇总表标注「未启用」，避免阻断现有流水。
2. **lcb389g oracle 检查**：`lcb-389g-oracle` 已登记未知（真解缺失，现用 truth 重放夹具）。若日后恢复真解（如入库 `2-用例/lcb-recent-hard-4/solution/abc389_g.py` 或独立 oracle 目录），可新增 `stage_lcb389g_oracle()`：组装临时 run_dir 跑该题 checker、断言满分且非夹具（按 oracle-sha256.json 中 `22ddc640…` 夹具哈希排除），结果并入 `results.json["lcb389g_oracle"]`；同时把新 oracle 的 SHA-256 增补进 `SHA_MANIFEST` 并刷新快照日期。

两阶段落地的公共约定：负例/夹具证据只读、运行走临时副本、任何新固定资产随修随刷 `SHA_MANIFEST`。

## 边界

- 本脚本校验「判卷器自测绿 + 审计收据未被改动」，不证明判卷器语义一般正确，也不替代产品运行审计。
- `--selftest` 会执行 checker 内置的负例/oracle 构造（内部使用临时目录），不写 `2-用例/` 与 `4-打分细则/` 既有文件；本目录只写 `results.json` 与新收据。
- 收据文件（`run-*.stdout.txt`）与 `results.json` 本身不进 `SHA_MANIFEST`，避免自指；若要把某次收据本身固化为证据，再按扩展点约定补清单。
