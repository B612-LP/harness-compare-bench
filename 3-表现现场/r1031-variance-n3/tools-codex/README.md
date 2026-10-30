# tools-codex：r1031-variance-n3 Codex 侧运行器

> **事后脱敏摘要**：本文由原说明事后整理，移除内部协作分工和个人路径；不是原始封存文件，也不代表本次重新运行或复核。运行证据和代码未因本文整理而改变。

## 测试方法与运行限制

基于 [r1030 运行器](<../../r1030-formal-a1/tools/lab.py>) 最小适配，仅运行 Codex。隔离 `CODEX_HOME`，其配置与 r1030 config-snapshot 语义一致；调用方式为：

```bash
codex exec --json --skip-git-repo-check -C <ws> -m deepseek-flash -c model_reasoning_effort="low" -
```

stdin 提供 `TASK.md`，stdout/stderr 重定向落盘；环境包括 `CODEX_HOME`、`DEEPSEEK_API_KEY` 和 `RUST_LOG=warn`，密钥不打印、不入库。工具、权限和技能配置沿用 r1030 Codex，模型为 deepseek-flash，思考档 low。判卷使用 freeze-20261029-v2 冻结 checker，runner 执行 checker 并记录 SHA-256。

本批 rep 为 2、3，事件 ID 为 `var-n3-codex-<case>-r<rep>`，运行目录为 `codex/runs/codex__<case>__r<rep>`，meta 记 `preregistration_commit=be39fc2`。工作区输入为 inputs 和 `TASK.md`。

运行级失败不补跑，记 `selection=null`、`diagnostic` 与 `infrastructure_invalid`；仅 429、rate limit、断连等传输错误在同一逻辑运行内按 2/8/32 秒退避重试，最多三次，尝试流及耗时留档在 `meta.attempts`。超时按 `case.json` 的 `timeout_s` 截停，checker 评估已有产物，不重试。

`adjudication.json` / `adjudications.json` 为 `draft: true` 机械草案，语义裁定须另行复核；正式事件导入通过 `build_import` 和 v2 `validate-import`。本文脱敏不表示执行过这些操作。

## stdout 与 usage 归档

- runner 将 `codex exec --json` stdout 直接重定向归档，meta 记 stdout/stderr 字节数及 SHA-256，失败尝试流也保留。日志经 staging 移动进证据目录，避免 r1030#1 的目录删除连带日志缺陷；该描述是原说明所载，并非此次新复核。r1030 缺陷及勘误另见 [DSH 侧说明](<../tools-dsh/README.md>) 与 [r1030 记录](<../../r1030-formal-a1/README.md>)。
- Codex CLI 显示层对大工具输出约 8192 字符的前缀截断属于产品行为，runner 不能去除；完整工具输出由会话 rollout jsonl 佐证，meta `stdout_archive_note` 披露区别。完整归档 stdout 不意味着产品显示投影无截断。
- `meta.usage.per_call` 从 rollout `token_usage_record` 提取 response_id、turn_id、时间戳、输入/输出/reasoning/总 token；`cached_input_tokens` 映射 `cache_read_tokens`，`cache_write_input_tokens` 映射 `cache_creation_tokens`。保留兼容字段 `requests/input_tokens/output_tokens`。

## 用法

在批次目录执行（仅列出原说明中的方法，不代表本次执行）：

```bash
python3 tools-codex/lab.py preflight
python3 tools-codex/lab.py prepare <case> <rep>
python3 tools-codex/lab.py run <case> <rep>
python3 tools-codex/lab.py integrity <case> <rep>
python3 tools-codex/lab.py receipt <case> <rep>
python3 tools-codex/lab.py summary
python3 tools-codex/lab.py status
```

`preflight` 不调用模型；`integrity` 重扫会话轨迹和 stdout；`receipt` 重新生成收据和裁定草案，`summary` 生成批级汇总与草案，`status` 查看台账。实际行为以 [运行器代码](<lab.py>) 为准。case 为 `bird-ca-schools-15`、`dabstep-payments-10`、`exercism-py-6`、`lcb-recent-hard-4`、`tb-cargo-plan`。

- **代码公开整理版说明**：[程序](<lab.py>) 现为仅中立化内部角色文字的公开整理版；历史代码原件不公开，旧哈希不可用于核验此版字节或历史封印；此版新执行输出不是历史原件，不能冒充旧封印证据。本条独立说明本次代码整理，不改写上文所述此前文档整理的范围。
