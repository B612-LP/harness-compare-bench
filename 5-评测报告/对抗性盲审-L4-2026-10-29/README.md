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
| [final-audit-stage-u1-r1.json](<final-audit-stage-u1-r1.json>) | F4-lite 实测 **8/8 PASS**：registered_at==E git 时刻；plan/contract blob D=E=现行=binding；manifest 42+17 逐条实算（含 WB asar/全局 AGENTS 外部哈希） |
| [final-audit-stage-cache-r2.json](<final-audit-stage-cache-r2.json>) | cache 实测 14 PASS + **1 FAIL=C10 erratum 钉**。**两路径分别表述**（lead 精准化）：①raw/raw_inventory 层完整忠实——递归独立重提 18/18，`input_tokens_details.cached_tokens` repeat=positive 2048 在案；②**预设归一化映射层未覆盖实际嵌套字段**——responses 的 `layer_mapping.cache_read_tokens` 选 `wire_key=cached_input_tokens` 而 missing（C5c），anthropic/chat 映射覆盖各自字段、chat hit/miss 别名未入映射表。REPORT.md:64 把预设键 missing 误推为「协议未回传缓存字段」=确定报告层缺陷；映射层分类候选=coverage limitation（密封源 mapping_note 自述「仅作归一化对照，不得互相替代」），非 instrument raw loss |
| [scan-report-actualE-cache-r3.json](<scan-report-actualE-cache-r3.json>) | actual 输出精确 key 扫描（369 文件）：**0 真实 key 命中**；transport 仅 header 名单、请求体无鉴权字段 |
| [crossing-verification-cargo-r1-r1.json](<crossing-verification-cargo-r1-r1.json>) | cargo-r1 越界独立核（供 judge 主裁）：**实际越界无、oracle 泄漏无**（46 shell 事件逐条扫，truth/solution 0 次）；暴露面=runner 向全部 codex ws 写评估框架元数据+活仓库路径（runner 设计缺口→L5）；19/27 诊断分保留 |

## 自证

- 本目录 JSON 收据内嵌 `live_doc_drift: []`；[THREAT-MODEL.md](<THREAT-MODEL.md>) 含 5 条脚本生成证据行并经 `receipt_check.py` 回验 exit 0（/tmp/l4-audit/threat-model-check-r1.json）。
- E 封印/真实数据到位后：F3–F11 逐项执行 + `credential_scan.py` 精确轮重扫（含 stdout/stderr 转录与 DSH zstd 会话）。

证据行（`evidence_line.py` 生成，22:30:33 / 23:06:32 / 23:40:46 / 23:44:25+08:00 四批）：

```
5-评测报告/对抗性盲审-L4-2026-10-29/tools/pii_min_check.py · 9935c1cf · 7906B · 2026-10-29T22:30:33+08:00
5-评测报告/对抗性盲审-L4-2026-10-29/pii-min-check-report-l4new-r1.json · 3480bf6f · 1879B · 2026-10-29T22:30:33+08:00
5-评测报告/对抗性盲审-L4-2026-10-29/pii-min-check-report-l4new-r2-release.json · bbef2e63 · 1033B · 2026-10-29T23:06:32+08:00
5-评测报告/对抗性盲审-L4-2026-10-29/scan-report-baseline-preE-r2-release.json · 7ce8012d · 88842B · 2026-10-29T23:06:32+08:00
5-评测报告/对抗性盲审-L4-2026-10-29/pre-commit-safety-release-r1.json · a2d554ee · 1741B · 2026-10-29T23:06:32+08:00
5-评测报告/对抗性盲审-L4-2026-10-29/tools/final_audit.py · 644317bc · 26039B · 2026-10-29T23:48:45+08:00
5-评测报告/对抗性盲审-L4-2026-10-29/final-audit-stage-u1-r1.json · e3fa7acc · 1263B · 2026-10-29T23:40:46+08:00
5-评测报告/对抗性盲审-L4-2026-10-29/final-audit-stage-cache-r2.json · 2d9aaa9e · 3952B · 2026-10-29T23:48:45+08:00
5-评测报告/对抗性盲审-L4-2026-10-29/scan-report-actualE-cache-r3.json · 177cd2c1 · 98077B · 2026-10-29T23:40:46+08:00
5-评测报告/对抗性盲审-L4-2026-10-29/crossing-verification-cargo-r1-r1.json · a5ddab1f · 3077B · 2026-10-29T23:44:25+08:00
```

**live_doc_drift: none（0 项）**
