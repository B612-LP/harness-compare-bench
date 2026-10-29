# tools-codex：r1031-variance-n3 Codex 侧运行器

自 [`r1030-formal-a1/tools/lab.py`](../../r1030-formal-a1/tools/lab.py) **最小改动适配**。r1030 的调用方式逐字保留：

- 隔离 `CODEX_HOME`（`~/bench-workspaces/r1031/codex/_codex-home`），`config.toml` 与 r1030 config-snapshot 语义一致（仅头注释标注本批）；
- 调用命令逐字同 r1030：`codex exec --json --skip-git-repo-check -C <ws> -m deepseek-flash -c model_reasoning_effort="low" -`（stdin 喂 TASK.md，stdout/stderr 重定向落盘）；
- 环境变量：`CODEX_HOME` + `DEEPSEEK_API_KEY`（取自 `~/.dsh/.credentials.yaml` refs 段，不打印不入库）+ `RUST_LOG=warn`；
- 工具/权限/技能 TOOL_FACTS 与 r1030 Codex 完全一致；模型 deepseek-flash，思考档 low；
- 判卷只用 `2-用例/<case>/checker.py` 冻结版（freeze-20261029-v2），runner 不读其内容，只执行并记录 sha256。

## 适配差异（r1030 → r1031 codex 侧）

| 项 | r1030 | r1031（本 runner） |
|---|---|---|
| 批次/事件 | `r1030-formal-a1`，event id `formal-a1-codex-<case>-01` | `r1031-variance-n3`，event id **`var-n3-codex-<case>-r<rep>`** |
| rep 维度 | 无（r1030 各场记 rep 1） | rep ∈ {2,3}；run 目录 `codex/runs/codex__<case>__r<rep>` |
| workspace | `~/bench-workspaces/r1030/codex/<case>/` | `~/bench-workspaces/r1031/codex/<rep>/<case>/`（仅 inputs+TASK.md） |
| meta 预注册 | 无此字段 | 每场 `preregistration_commit="be39fc2"` |
| 产品范围 | codex+dsh | 仅 codex（dsh 侧由 tools-dsh 并行负责，本 runner 不触碰） |

## 随批工程项（预注册包A，在本批内验证）

- **a. stdout 归档去除 8192 截断**：runner 把 `codex exec --json` 的完整 stdout 事件流直接重定向落盘（无任何 8192 截断路径），meta 记 `stdout_bytes`/`stderr_bytes` + `stdout_sha256`/`stderr_sha256`；传输重试的失败尝试流也整体保留（`agent.failed-attempt<n>.jsonl`）。日志经 staging 移动进证据目录，修复 r1030#1「rmtree 连带删除 agent.jsonl」缺陷，本轮不存在日志丢失路径。注：CLI 显示层对大工具输出的约 8192 字符前缀截断是产品行为（未知登记 `cli-stdout-display-truncation`），runner 无法去除；完整工具输出由会话轨迹（rollout jsonl）佐证，meta `stdout_archive_note` 已披露该区分。
- **b. 逐调用 usage 入库**：meta.usage 从 Codex 会话 rollout 的 `token_usage_record` 逐条提取 `per_call`（response_id/turn_id/时间戳/input/output/reasoning/total），并映射 `cached_input_tokens→cache_read_tokens`、`cache_write_input_tokens→cache_creation_tokens`；保留 r1030 兼容字段 `requests/input_tokens/output_tokens`（本轮为真实值，非 0 占位）。

## 纪律实现（预注册总则2）

- 运行级失败（非传输层错误、超时之外的失败）：**不补跑**，meta/裁定草案记 `selection=null` + `diagnostic`，该 rep 记 `infrastructure_invalid`，继续下一场；
- 仅传输层错误（stderr 命中 429/rate limit/断连等模式）：同一逻辑运行内指数退避 2/8/32s 重试，**≤3 次**；每次尝试的流与耗时全量留档（meta.attempts）；
- 超时：按 case.json timeout_s 合同截停，checker 对现有产物全量评估（同 r1030 口径），不重试。

## 裁定边界

`adjudication.json` / `adjudications.json` 由本 runner 产出的均为 **`draft: true` 机械草案**（映射规则同 r1030 gen_adjudications.py），`adjudicator` 字段显式声明语义裁定权在 lead；lead 复核后翻转 `draft` 并定稿。正式事件导入（`build_import` + v2 `validate-import`）由 lead 执行。

## 用法

```bash
python3 tools-codex/lab.py preflight                 # 零模型调用
python3 tools-codex/lab.py prepare <case> <rep>
python3 tools-codex/lab.py run <case> <rep>          # 跑+判分+归档+inline 重扫+receipt
python3 tools-codex/lab.py integrity <case> <rep>    # 幂等重扫（会话轨迹+stdout）
python3 tools-codex/lab.py receipt <case> <rep>      # 重出 score-receipt/adjudication 草案
python3 tools-codex/lab.py summary                   # 批级 integrity 汇总 + adjudications 草案
python3 tools-codex/lab.py status                    # 运行台账（run-log.jsonl）
```

case 全名：`bird-ca-schools-15` `dabstep-payments-10` `exercism-py-6` `lcb-recent-hard-4` `tb-cargo-plan`。

## 写界

仅 `3-表现现场/r1031-variance-n3/codex/**`、`tools-codex/**`、`~/bench-workspaces/r1031/codex/**`。
