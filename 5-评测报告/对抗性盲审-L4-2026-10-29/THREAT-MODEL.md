# L4 独立威胁模型与最终审计清单（auditor / task-9 阶段 I）

- 生成：脚本实钟 2026-10-29（见文末证据行）；作者：auditor（敌意审计，第三轮连任）。
- 铁律：零模型/零真实请求阶段；只写本目录；git 只读；不语义读 truth/solution；不读 secret-context；凭据仅按批准 refs.DEEPSEEK_API_KEY（ASCII 精确名）进入内存。
- 状态语义：本文所有「检查」分三态——**READY**（当前即可机械执行）、**PENDING-E**（等 E 封印/真实证据）、**PENDING-FINAL**（等全量数据+lead 释放终审）。

## 1. 资产与对手/失效模式

| 资产 | 主要威胁（本审计负责面） |
|---|---|
| 凭据（DEEPSEEK_API_KEY） | 泄漏进 L4 任一批次产物、收据、转录、zstd 会话、路径名；扫描器/收据自身回显凭据 |
| 35 固定槽位（17 product + 18 probe） | 槽位重复/缺位/自造 rep；未执行虚填 0 或折满；事故/预检冒充槽位 |
| E 封印 | E 前暗中发请求；E 源码闭包逃逸（软链/空 manifest 类，已知 draft 缺陷归 reviewer，不复述）；registered_at 与 E 时刻不等值 |
| 缓存探针结论 | absence→解释为无写入；miss→解释为无 cache creation；跨 wire 盲目求和 usage；n=1 命中差宣称等效 |
| 双归档重放 | 把等价模拟冒充原 pipeline 复现；测量效应宣称成代际因果；母本被副本流程污染 |
| WB 批次 | declared_alias 冒充 actual_request_model；网关历史结论填成本批事实；预检干扰用户会话 |
| 事故证据 | 以无 usage/哨兵覆盖推断「零请求」；手转哈希当实算；reconstruction 伪原件 |

## 2. 证据等级规则（从事故固化的审计判据）

1. 「无 usage」⇏「无模型请求」；Python socket 哨兵 **不覆盖原生子进程**——两者都不得作为禁网证据。
2. 手转哈希/转录片段 = **unverified fragment**；长度不符（如 52 位"SHA"）即作废；原件灭失 → 证据等级 incomplete，不重建伪原件、不补齐、不猜值。
3. 「零模型/零 API」主张必须绑定具体证据面（哪个进程树、哪个哨兵、哪个日志），不做全队笼统声明。
4. 任何凭据泄漏、污染、E 漂移 → 停相关执行/主张并归档，不静默重跑（PREREG §6）。

## 3. 凭据泄漏扫描（已实现，阶段 I 交付）

- 工具：`tools/credential_scan.py`（同目录）。唯一凭据源=批准 refs（ASCII `DEEPSEEK_API_KEY`，逐字符复刻 lab.py::load_api_key 解析）或 `--key-stdin` 外部已解析值；绝不遍历其他 secret。
- 覆盖：全文件类型逐字节精确匹配（压缩/明文载荷）；`.zst/.zstd` 魔数嗅探+**内存解压**后再检；generic（sk-/Bearer/api_key 赋值/私钥块）只记类型+次数+行号；凭据**名字**引用单列 env_name_refs 不当泄漏；路径含完整 key 才 redact（部分前缀不属泄漏，自检 T7 对照）。
- 报告纪律：真实 key 命中只输出定位+次数（无值/无片段/无值 hash）；收据零凭据材料（自检 T9 机械断言：报告字节无 key 的 ≥12 连续子串及其 sha256）；`--out` 原子拒写；`live_doc_drift: []`；exit 4=发现命中（告警态）。
- 自检：11/11（`selftest-receipt-credential-scan-r1.json`，全合成 key，真实凭据未参与）。
- **基线扫描（pre-E，r1）**：六目录 212 文件，**真实 key 精确命中 0**（exit 0）；generic 4 项全部人工归类的 benign：本扫描器自检 fixture（synthetic-stub）×2、DSH runner 自带 desensitize_text 自检字符串（`sk-`+x 占位，unclassified→人工判定 benign）。env_name_refs 全部为配置/代码对凭据**名字**的引用 ✓。
- **PENDING-E**：E 释放后对三批次真实证据（含 stdout/stderr 转录、zstd 会话、双归档副本、评审/验收新产物）重跑精确扫描；generic unclassified 项逐条人工归类（基线已示范流程）。

## 4. 最终敌意审计清单（终审执行面）

| # | 检查 | 状态 | 机械工具 |
|---|---|---|---|
| F1 | plan/contract 槽位全集：17=12 CLI+5 WB、18 probe、身份三元组唯一、order/rep/timeout 与冻结一致、caps 不超 | **READY** | `final_audit.py --stage plan` |
| F2 | contract.plan_sha256 == plan.json 实际字节；denominators/strata/case 快照存在 | **READY** | 同上 |
| F3 | 全槽 slot-accounting：executed/partial/not_executed 三态全集+唯一+声明真实；not_executed 不虚填 0/不折满（R1 真值表） | PENDING-E | final_audit.py --stage accounting |
| F4 | U1：完整 E 提交 ID 下 plan/contract/manifest blob 等值+祖先；runtime-binding 精确时刻；meta.registered_at==E 时刻<started_at；L3 reconcile 仅作组件 | PENDING-E | final_audit.py --stage u1 |
| F5 | 文件 SHA/bytes 实算 vs 收据；证据写入非破坏（母本不可覆盖） | PENDING-E | --stage hashes |
| F6 | 缓存原字段：missing/null/0/正值四态保真；absence 不解释为无写入；usage 分母按协议原字段；不推成本 | PENDING-E | --stage cache |
| F7 | 双归档：两副本均 equivalent_simulation 标注；差异只归测量效应；母本输入映射锁定 | PENDING-E | --stage archive |
| F8 | WB：declared_alias≠actual_request_model、app 版本/asar 哈希入证据、actual_gateway=unknown 须附 route_verification=current_not_observed、白名单四项逐场管理、不进 A/同路由排名 | PENDING-E | --stage wb |
| F9 | 污染：被测 agent 不触仓库/checker/truth；prompt 规范化仅路径差；逐场独立无污染裁定 | PENDING-E | --stage pollution |
| F10 | 停止语义：R4 优先级逐槽对账（401/403 全停、4xx 停协议、5xx 连二停、fresh 失败 repeat 不发）；不挪额度补跑 | PENDING-E | --stage stops |
| F11 | 凭据扫描（E 后精确轮）+ 扫描器/收据自身零凭据 | PENDING-E | credential_scan.py |

## 5. 与 judge / independent-reviewer 的分工边界（不重复劳动）

- judge（task-8）：runner fake 全链、执行验收。reviewer（task-7）：E 候选源码闭包/封印逃逸、gate 与进程停止——其已知 draft 缺陷不重复申报。
- 本审计独占：凭据面（§3）、槽位记账全集对账、U1 等值链、缓存字段四态保真、双归档推断边界、WB 白名单纪律、以及把上述合成负例做**独立**（非 builder 自测）重放。
- 已知事实基线（不再当发现）：Codex 事故已单列 incident、不占槽/不评分/不计 pass、证据 incomplete；lead 已 dated 更正「零网络/零调用」口径。

## 6. 本目录产物

- `tools/credential_scan.py` · `selftest-receipt-credential-scan-r1.json`（11/11）· `scan-report-baseline-preE-r1.json`（0 命中/212 文件）· `final_audit.py`（F1/F2 READY，其余 PENDING 显式）· 本文件。

---

证据行（`evidence_line.py` 脚本生成，21:44:47+08:00）：

```
5-评测报告/对抗性盲审-L4-2026-10-29/tools/credential_scan.py · 4dbbff27 · 14842B · 2026-10-29T21:44:47+08:00
5-评测报告/对抗性盲审-L4-2026-10-29/tools/final_audit.py · 644317bc · 26039B · 2026-10-29T23:49:28+08:00
5-评测报告/对抗性盲审-L4-2026-10-29/selftest-receipt-credential-scan-r1.json · e17a13ed · 1654B · 2026-10-29T21:44:47+08:00
5-评测报告/对抗性盲审-L4-2026-10-29/scan-report-baseline-preE-r1.json · dd8ab265 · 56175B · 2026-10-29T21:44:47+08:00
5-评测报告/对抗性盲审-L4-2026-10-29/final-audit-stage-report-plan-r1.json · 2cfe5f4f · 3406B · 2026-10-29T21:44:47+08:00
```

**live_doc_drift: none（0 项）**——两份 JSON 收据均内嵌 `live_doc_drift: []`；本文件经 `receipt_check.py` 回验 exit 0（证据行 5/5 claimed=recomputed，报告 /tmp/l4-audit/threat-model-check-r1.json）。
