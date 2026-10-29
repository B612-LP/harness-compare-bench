# 对抗性盲审 L4（auditor / task-9）——阶段 I 交付索引

- 角色：敌意审计（零模型/零真实请求阶段）。写界仅本目录；git 只读；不读 truth/solution；不读 secret-context。
- 阶段 I（2026-10-29，E 封印前）：凭据泄漏扫描器+合成自检+pre-E 基线扫描、独立威胁模型、最终审计脚本骨架（F1/F2 已机械通过，余 9 项显式 PENDING-E）。
- 事故口径基线：Codex mock 误启真实 CLI 已单列 incident（不占 35 槽/不评分/不计合成 pass/证据 incomplete）；「无 usage/Python 哨兵」不作为原生子进程禁网证据；手转哈希=unverified。详见 THREAT-MODEL.md §2。

## 产物

| 文件 | 说明 |
|---|---|
| [THREAT-MODEL.md](<THREAT-MODEL.md>) | 独立威胁模型 + F1–F11 终审清单（三态：READY/PENDING-E/PENDING-FINAL）+ 证据等级规则 |
| [tools/credential_scan.py](<tools/credential_scan.py>) | 凭据泄漏扫描器：唯一批准 refs.DEEPSEEK_API_KEY（ASCII），zstd 内存解压，报告零凭据材料，原子拒写 |
| [selftest-receipt-credential-scan-r1.json](<selftest-receipt-credential-scan-r1.json>) | 合成自检 11/11（真实凭据未参与） |
| [scan-report-baseline-preE-r1.json](<scan-report-baseline-preE-r1.json>) | pre-E 基线扫描：六目录 212 文件，真实 key 精确命中 **0**（exit 0）；generic 4 项人工归类全 benign |
| [tools/final_audit.py](<tools/final_audit.py>) | 终审机械检查：plan/contract 全集 **17 PASS / 0 FAIL**（17=6+6+5、18 probe 3×2×3、身份唯一、timeout 冻结、contract.plan_sha256==plan 字节），F3–F11 显式 PENDING-E |
| [final-audit-stage-report-plan-r1.json](<final-audit-stage-report-plan-r1.json>) | 上行报告收据 |
| [tools/pii_min_check.py](<tools/pii_min_check.py>) | 发布前 PII 最小化检查（needle 运行时取自全局 AGENTS 内存提取，报告只含定位/计数，自检 6/6） |
| [pii-min-check-report-l4new-r1.json](<pii-min-check-report-l4new-r1.json>) | L4 新批次/新报告 PII 扫描（8 目录 312 文件，exit 4）：**真实命中 1 文件** = dsh `config-baseline/config-snapshot/AGENTS.md:33`（三类标识齐现，已报 lead 由 producer 脱敏公开派生快照）；其余为本工具自身 label 词自匹配，无值 |
| [pii-min-check-report-l4new-r2-release.json](<pii-min-check-report-l4new-r2-release.json>) | 提交前放行 PII 复扫（360 文件）：**exact 类命中 0**（producer 脱敏独立验证：公开快照 5786a0ef、真实全局 d343bcc3 未动）；余 10 处均本工具 label 词自匹配 |
| [scan-report-baseline-preE-r2-release.json](<scan-report-baseline-preE-r2-release.json>) | 提交前放行凭据复扫（336 文件，批准 key 内存比对）：**真实 key 精确命中 0**；generic 4 项同 r1 已知 benign 集（含 lab.py desensitize 自检串移位至 :1868） |
| [pre-commit-safety-release-r1.json](<pre-commit-safety-release-r1.json>) | **提交前安全放行裁定：PASS**（发现即停条款未触发；F3–F11 仍待 E 后） |

## 自证

- 本目录 JSON 收据内嵌 `live_doc_drift: []`；[THREAT-MODEL.md](<THREAT-MODEL.md>) 含 5 条脚本生成证据行并经 `receipt_check.py` 回验 exit 0（/tmp/l4-audit/threat-model-check-r1.json）。
- E 封印/真实数据到位后：F3–F11 逐项执行 + `credential_scan.py` 精确轮重扫（含 stdout/stderr 转录与 DSH zstd 会话）。

证据行（`evidence_line.py` 生成，22:30:33 与 23:06:32+08:00 两批）：

```
5-评测报告/对抗性盲审-L4-2026-10-29/tools/pii_min_check.py · 9935c1cf · 7906B · 2026-10-29T22:30:33+08:00
5-评测报告/对抗性盲审-L4-2026-10-29/pii-min-check-report-l4new-r1.json · 3480bf6f · 1879B · 2026-10-29T22:30:33+08:00
5-评测报告/对抗性盲审-L4-2026-10-29/pii-min-check-report-l4new-r2-release.json · bbef2e63 · 1033B · 2026-10-29T23:06:32+08:00
5-评测报告/对抗性盲审-L4-2026-10-29/scan-report-baseline-preE-r2-release.json · 7ce8012d · 88842B · 2026-10-29T23:06:32+08:00
5-评测报告/对抗性盲审-L4-2026-10-29/pre-commit-safety-release-r1.json · a2d554ee · 1741B · 2026-10-29T23:06:32+08:00
```

**live_doc_drift: none（0 项）**
