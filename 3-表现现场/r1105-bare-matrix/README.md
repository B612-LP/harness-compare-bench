# r1105-bare-matrix —— 现行五题 × 裸模型探针矩阵（2026-11-01）

> **定位**：C 组裸模型底数（现行定案五题版）。单轮 `/responses`、无系统提示、无工具、prompt = instruction.md 原文 + 声明内联输入包 + 交付约定；模型 `deepseek-flash`（官方端点），arm `inline-low` 钉 `reasoning.effort=low`（[预检收据](<preflight-reasoning-pin.md>)），arm `inline-default` 默认档敏感性对照。**本批不入正式表；不改变报告 v1.2 任何数字。**（2026-11-03 注：本句写作时现行报告为 v1.2，现已演进至 v1.3；本批不入正式表的事实状态不变。）
> 命名沿用 r1030–r1104 的流水号延续（README 索引声明的日期制自 r1030 起被事实延续所覆盖，如实注记）。

- **结果**：[RESULTS.md](<RESULTS.md>)（五段结构 4 条结论）——bare headline 3/5，达标/未达标题集与 A 组双 CLI 正式账重合；同题分数与失败断言集互异（tb 裸 70.37/19 项对正式账 codex 81.48、dsh 74.07；bird 同分不同错题），不构成「同构」——详见结论一/四的修正口径。
- **逐场证据**：runs/<arm>/<case>__r<rep>/ 内 bare-request.json（prompt 原文+SHA）、bare-response.json（原文）、**被判分产物（answers/solutions/修复后 app 文件）与 inputs 副本**、RESULTS_JSON/result.json（原字节 checker 判分，本机路径已占位脱敏）、meta.json（十字段+内联清单+抽取映射；其中 7 场事故运行的 meta 为事故后重建，duration_s/started_at 如实置 unknown、逐场含 postmortem）。
- **分账**：[bare-matrix-events.json](<bare-matrix-events.json>)（17 场，category=bare_model_probe）+ [six-accounts.json](<six-accounts.json>)（产品运行 0、裸探针 17、预检 1——与产品运行严格分账）。
- **执行期如实披露**：首轮 7 场 JSONL 题因抽取器签名 bug 未落产物，API 响应原样在案、零重发，修复后离线重抽取（[run1 存档](<batch-results.run1-extractor-bug.json>)；该 7 场重建 meta 逐场含 postmortem，duration/started 不可恢复如实置 unknown）；buggy 版脚本未留版本副本（第二次违反版本化纪律，已在 RESULTS 如实披露）。[预检收据](<preflight-reasoning-pin.md>)曾误写 key 前缀，已更正为尾号形态并在此勘误。
- **工作区纪律**：发射工作区在仓外 `~/bench-workspaces/r1105-bare-matrix/`；本目录只收证据集，不含 23MB 级原始输入拷贝。
