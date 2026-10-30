# 运维卫生规程（Operations Hygiene）

版本：2026-10-30（L7-B 建立；源事件=L5 期 `ps` 命令误印 Bearer——零入库实证见
[对抗性盲审-L5 AUDIT](<../../5-评测报告/对抗性盲审-L5-2026-10-30/AUDIT.md>)，本规程将该
教训条目化为硬规则）。

## 1. 敏感命令行卫生（硬规则）

1. **凭据不得出现在命令行参数中**：token / Bearer / API key / 密码 / cookie 一律经
   环境变量或文件（0600）传递；禁止 `curl -H "Authorization: Bearer xxx"` 这类把值写进
   argv 的形态（argv 对同机所有用户经 `ps`/`/proc` 可见）。
2. 需要在命令里带凭据时，用 `--header @file`（curl 7.55+）、`--netrc`、配置文件或
   环境变量注入；脚本内拼装后也不得 `set -x` / echo 回显。
3. 进程标题/包装器（如 `setsid`、`env`、包装脚本）不得把凭据复制进可见 argv。

## 2. 日志与收据

1. 日志、trace、meta、收据正文落盘前不含凭据字面量；确需记录凭据形态时只存
   尾号/前 8 位标识符。
2. 巡检口径：对现场与工具链目录定期执行凭据字面量扫描（Bearer/sk-/key= 等 pattern），
   结果出收据；本规程随附的首查收据见同目录。
3. 凭据意外落盘即按「事故」处理：立即轮换该凭据，再清理落盘物（顺序不可反），
   并在活台账登记 incident。

## 3. 仓内约束

- 凭据绝不入库（既有 AGENTS.md 级规则重申）；secret 走 secret-context，不入任何
  仓库文件。
- 评测现场 runner/驱动新增任何外部调用前，自查本规程第 1 条。

## 4. 本规程的验证

- L7-B 交付时执行了一次全量扫描（L6 现场 + 工具链目录 + L7 新增文件），
  收据：`bearer-scan-receipt-l7.json`（同目录，零命中为过）。

live_doc_drift: none（0 项）
