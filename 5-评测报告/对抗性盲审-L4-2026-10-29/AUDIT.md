# 对抗性盲审报告（L4 终版）——全 17 槽终态 F3–F11，2026-10-30

- 审计角色：敌意审计（task-9 最终全量）。预注册/CLARIFICATION/EXECUTION-RULINGS 为基准；producer/judge 陈述作待证主张。
- 方法与铁律：零模型调用；只写本目录；git 只读（blob 等值/时刻提取）；truth/solution 未语义阅读（仅文件名字节校验）；凭据仅批准 refs.DEEPSEEK_API_KEY（ASCII）内存比对；PII needle 运行时内存提取；全部收据原子拒写、`live_doc_drift` 内嵌、时间/哈希脚本生成。
- 时点：主审执行 2026-10-29T19:0x – 2026-10-30T00:4x +08:00（分阶段，各收据内实钟）。

**live_doc_drift: none（0 项）**

## 0. 总判定

**安全/交付 blocking：0。** 全量 key 扫描（cache18+codex6+DSH6+recoveries 8 zstd 内存解压+WB 全部+报告目录，累计 1000+ 文件次）**真实凭据精确命中 0**；PII 已由 producer 脱敏并经独立复扫放行；答案类内容（truth/solution/checker 逻辑）无越过被测边界的证据。

**真实缺陷如实列示，不以 0-blocking 掩盖**：本环试验目标未达标/机读缺口共 4 项 defect、2 项 observation、1 项事故单列（§1）。要点：cache 报告层 missing 误报（已 dated erratum 2 纠正，C10 转 PASS）、归一化映射 coverage limitation（C5c 在案）、codex ws 元数据暴露（runner 设计缺口→L5）、DSH marker 缺陷致 usage 观测缺失（原档保留+recoveries 补档，DSH 线 usage 维度本轮不可作结论）、独立 gate inputs_verification 发射缺口、judge 汇总 upsert 掉行（已修+17 集合核）。

分级计数：**blocking 0 / defect 5（含 AUD-D5 本审计自身文档缺陷）/ observation 2 / 事故 1（单列）**。

## 1. 发现清单

### AUD-D1【defect·已纠】cache 报告层把预设键 missing 误推为「协议未回传缓存字段」
- 三层精确定位（final-audit-stage-cache-r3.json，C4/C4b/C5/C5b/C5c/C10）：raw 响应体、usage.raw.json、layer_raw_inventory 全部含 `input_tokens_details.cached_tokens`（responses repeat=**positive 2048**，fresh/control=0）；`layer_mapping.cache_read_tokens` 选 `wire_key=cached_input_tokens`（wire 不存在的平铺键）→ missing；REPORT.md:64 由此误写「6/6 missing」。producer dated erratum 2（23:33:34）承认嵌套字段存在、归因 USAGE_FIELDS 预设路径遗漏、保留原句为缺陷记录；C10 已按「原句保留+dated erratum」纪律转 PASS。
- 分类：**报告层 defect（已纠）+ 映射层 coverage limitation**（密封源 mapping_note 自述「仅作归一化对照，不得互相替代」；responses 键集未含实际键 vs 键写错的设计意图判定归 lead/judge）。chat hit/miss 别名未双计；anthropic creation 显式 0；三 wire×2 repeat 读数均为 2048（与本审计独立重提一致）。
- 影响：原表述抹掉 responses 阳性命中观测；erratum 后四态表（C4b）为最终口径。

### AUD-D2【defect】codex ws 元数据暴露超「只 inputs+TASK」设计边界（→L5 池）
- runner 向每个 codex workspace 写 meta.json（TASK.md 不提及）：暴露评估框架（model/effort/route/endpoint/product_version/timeout）、D/E commit 身份、checker_sha256、**活仓库绝对路径**（config_ref；codex danger-full-access 下技术可达）、约束自曝（stay-in-workspace/no-oracle-hunt/offline）与 inputs 清单。跨 6 槽一致（含 dab-r2）。
- 逐槽越界核（crossing-verification-cargo-r1-r1.json + X6 全槽扫描）：**实际越界 0、oracle 泄漏 0**——46+46+… shell 事件逐条扫，truth/solution 0 次；cargo-r1/r3 为 cat meta 回显；**cargo-r2 模型推理「可能无 solution，无必要」后未读**（拒绝使用元数据的直接证据）。作者「未读 truth/solution」独立证实。
- 机械命中口径澄清：3 词全目录扫描总量 116 处，其中模型轨迹侧仅 5 处（cargo-r1/r3 各 2 rollout + agent.jsonl 回显 1 类），其余全为 runner 自写 meta 家族（meta.json/projections/meta.partial）——机械扫描须分层归因，不得把 runner 工件命中记为模型越界。
- 处置：lead 已入 L5 池；raw meta verdict=violation 保守 fail-closed 合理保留；19/27 等原分为诊断分口径交 judge 主裁；sidecar 不改原 meta、不重跑。

### AUD-D3【defect】DSH marker 缺陷：原始 capture 空/usage null/dab-r1 vacuous integrity=violation
- 原档如实保留（D3）：6 槽 usage.requests=None 未被填 0/虚构；dab-r1 integrity=violation 为 vacuous（formal 判定归 judge/reviewer）；gate formal=0。
- recoveries：6 槽 8 个 session.v4.jsonl.zstd 晚补档，独立于 runs/ 原档（D4 无写回）；reviewer task10 首槽身份/完整性 36/36 通过、余 5 在审；补档≠自动 formal。
- 影响：**DSH 线 usage 维度本轮不可作任何结论**（含 cache 观测）——试验目标未达标项，原分 dab 70/80/70、cargo 70.37037037/74.07407407/74.07407407 照实保留（D2 机械吻合）。

### AUD-D4【defect】独立 gate inputs_verification 发射缺口 + judge 两处已纠正误读
- meta.inputs_verification 字段发射缺失（真实存在缺口）；judge 曾据归档 snapshot 误读「无 inputs 目录」（实际 workspace/inputs 7 文件，lead glob 证实）→ judge dated 纠正；judge 汇总 WB-dab 行被 codex6 sweep 覆盖（upsert 掉行）→ 已修 slot_id upsert 并做 17 集合核。本审计 coverage F0 双向集合核独立通过（17/17 一一映射、无跨产品混排）。

### AUD-O1【observation】WB 语义核：清洁，附度量卫生注记
- 4 执行槽同严格度语义核（非仅机械）：**零网络动作动词**（navigate/fetch/curl/wget/urllib/requests.get/web_search 全 0）；atcoder/github URL 均为任务输入文本（lcb problems.json 自带题目 url 与 statement_zh；exercism 测试文件头注释），非导航事件；solution×368 为任务规定的输出文件名约定（`solutions/<problem_id>.py`）；cargo 的 checker/truth 命中为模型对判分的**推理措辞**（「Could the checker intended feasible=true?」），无任何访问动作。
- alias：driver 创建参数「DeepSeek V4.1-Flash」+ 会话库 model 字段双证（nativeDB 证实）；actual_request_model=null（不可观测，managed unknown）；app_asar before==after 无漂移；inputs_verification 机械比对 ok。
- 注记：模型可感知自身被评（产品交付态固有），度量卫生限制随 managed unknowns 登记；WB cargo 两位 70.37 与 8 位 norm 差别、earned=0 语义、guards 顶层缺漏交 judge 核（未改原物）。

### AUD-O2【observation】WB bird=not_executed（基础设施 startup-render-not-ready）
- 首鸟槽冷启动 CDP page 未就绪（open-g 后 9332 起但 _page_ws_url 无 page）；只有 registration+仓外 workspace，无本批 session/trace/score；bird-startup-failure-proof.json 在案。按 R1 真值表：score=null 不虚填、formal=false、诊断记录完整可 accounting_complete；非能力 0，不允许按已评 4 项折算或拼五题总分；L5 池非生成就绪等待。

### 事故单列（不并六账/35 槽）
interface_preflight ×1 accidental CLI start（INCIDENT-20261029-mock-real-codex-launch）：chatgpt.com plugin-warm 401 证实 1 次；DeepSeek provider requests **unknown**；原始日志灭失、52 位"SHA"已作废为 unverified fragment、stderr 64 位 hand-transcribed unverified；证据等级 incomplete；不重建伪原件。全队「零模型/零调用」口径不得笼统声明。

### AUD-D5【defect·本审计自身】activity-index 候选 r2 手写数值违纪（lead 程序核对指出；dated 2026-10-30T00:19:54+08:00）
- r2 存在：at 为**手写未来时刻**、groups 合计手写 23（程序实算 **18**）、WB executed 写 4/6（应 4/5）、product.groups 未随终态更新、codex selftest test_case_n 手写 60（落盘收据现版本 73）。
- 处置：r2 保留不覆盖并加 dated erratum；程序化 **r3**（tools/activity_index_gen.py，零手写数值：at=now、终态逐槽读 meta、合计=数组实长=18、source refs 存在校验全过）为现行候选；本文件原「六类 23 组」表述按此更正为 **18 组**。分类：实证审计文档缺陷，不以 0-blocking 遮盖；不影响产品原记录。另：WB bird E provenance 旁挂（bird-notexec-preregE-provenance.json）已纳入 r3 refs 与安全扫描索引——acc_not_executed 内存 dict + 首次 O_EXCL 写前填 canonical E，persist_not_executed 从未调用、None 未物化；born==mtime 同秒仅佐证。

## 2. F3–F11 逐项结果（机器收据为本目录 final-audit-stage-*.json）

| 项 | 结果 | 收据/依据 |
|---|---|---|
| F1 计划全集 35（17+18） | PASS（plan 阶段 17/17 检查） | final-audit-stage-report-plan-r1.json |
| F2 contract 绑定 | PASS（plan_sha256==plan 字节） | 同上 |
| F3 全槽记账 | **候选已备**（activity-index-proposal **r3 程序化**：六类 **18** 组【r2 手写 23 已 erratum，见 AUD-D5】；产品 executed=16/17+bird not_exec）+coverage F0 双向 17/17 | activity-index-proposal-r3 + stage-coverage-r2 |
| F4 U1/E 注册 | PASS 8/8：registered_at==E git 时刻；plan/contract blob D=E=现行；manifest 42+17 逐条实算（含 WB asar、全局 AGENTS d343bcc3） | final-audit-stage-u1-r1.json |
| F5 文件哈希 | PASS（manifest 42 仓内+17 外部全对；codex prompt/agent/stderr 链 X4；cache 请求哈希 C2） | u1/cache/codex 三收据 |
| F6 cache 四态 | PASS 15（C4 独立重提 18/18；C4b 四态表；C5/C5b/C5c 两路径披露；C10 erratum PASS） | final-audit-stage-cache-r3.json |
| F7 双归档 | codex 6 槽投影在案（legacy/current+ADAPTATION+status）；**逐槽 equivalent_simulation 完备性=留 judge 终审**（本审计未逐字核 ADAPTATION 语义） | 目录核 |
| F8 WB 路由纪律 | PASS（语义核 §AUD-O1）：declared_alias≠actual_request_model、nativeDB 双证、asar 无漂移、route not observed=managed unknown、不进同路由排名 | 本文件 §AUD-O1 |
| F9 污染 | PASS（codex X6 逐槽 truth/solution=0、无 ws 外命令；WB 语义核零网络动作、零 oracle 访问；唯一 ws 外字符串=config_ref 回显=AUD-D2 暴露面） | codex-r1 + crossing 收据 |
| F10 停止/预算语义 | cache：18/18 每槽恰 1 外发、时序非降、pair 间隔≥5s、无重试（C2/C7/C7b/C8）；intent→HTTP 计数=18/18 | final-audit-stage-cache-r3.json |
| F11 凭据/PII | PASS：全量扫描 0 真实 key 命中（含 8 个 recovery zstd 内存解压、WB native）；PII 0（codex/DSH 槽）；coverage/skips 见 §3 | scan-report-*-r3/r4/r5 + pii-*-r3/r4 |

## 3. 安全扫描 coverage/skips 明示

- 覆盖：l4-20261029-cache（369 文件）、codex（316+316 双扫）、DSH 含 recoveries（171 文件，zstd 内存解压 8 份）、WB runs（含 native zstd 若有，走同一魔数嗅探路径）、l4-execution、L4 plan/selftest、三个报告目录。收据：scan-report-{baseline-preE-r1/r2-release, actualE-cache-r3, codex6-r4, dsh6-recoveries-r5, wb-final-r6}.json、pii-min-check-{l4new-r1/r2-release, codex6-r3, dsh6-r4, wb-final-r5}.json。WB 终扫含 bird provenance 旁挂（199 文件 0 命中；1 处 sk-token 为 payments.csv 任务输入数据值，unclassified→人工归类 benign，真实 key 精确比对 0 为权威口径）。
- skips/边界：~/.dsh/sessions 历史会话（非本批产物）未扫——事故溯源属 lead/judge 线，扫描器能力已具备（zstd 内存解压实测）；secret-context 与其他任何 ref 从未读取；2-用例 truth/solution 未语义阅读。
- 输出纪律：零值/零片段/零值 hash；命中仅定位+计数；路径含 key 即 redact（自检 T7/T9 机械断言）。

## 4. 未知登记（影响/下一步/停止条件摘要）

| 未知 | 影响 | 下一步 | 停止条件 |
|---|---|---|---|
| WB actual_request_model/actual_gateway=null | 不能同路由归因 | L4 内保持 managed unknown；网关取证另立 | 出现按 unknown 填已知值即违规 |
| DSH usage 维度缺失（marker 缺陷） | DSH 线 usage/cache 观测本轮不可结论 | recoveries+reviewer 身份核收尾 | 补档被用于 formal 而身份核未过即违规 |
| 事故 provider requests unknown | 不能声明全队零调用 | 保持 incident 单列 incomplete | 以无 usage 反证零请求即违规 |
| layer_mapping coverage（responses 键集） | 归一化对照层不完整 | producer 决定 dated 补映射或明示对照范围 | 用 mapping missing 反推协议缺失即违规（已由 erratum 纠正） |
| codex ws meta 暴露面 | 度量卫生+潜在路径可达 | L5 修 runner 写出面 | 模型实际访问引用路径即升级 |

## 5. 移交与边界

- judge 主裁：formal_admission 逐槽（gate 发射缺口、DSH vacuous violation、codex meta 暴露对准入的权重、WB cargo 两位 70.37/earned=0/guards 顶层缺漏）；producer：cache REPORT erratum 已落地、DSH recoveries 补档、L5 池（meta 暴露面、WB 就绪等待、来源泄露缺口）；lead：最终六账/总结（本审计出候选 activity-index r2 + coverage F0 供其串行登记，登记后由我复核事实一致性）。
- 本审计未做：不新跑任何 checker 回归（grading_regression=0/不适用）；不改 raw/layers/任何源码；不对未落地项冒充完成。

## 6. 复现命令要点

1. `final_audit.py --stage plan|u1|cache|codex|dsh|coverage|pending --out <新路径>`（各 stage 收据即本文件引用）。
2. `credential_scan.py --scan <目录> --out <新路径>`（zstd 内存解压；0 命中 exit 0）；`pii_min_check.py --scan ... --out ...`。
3. C 系证据：`probes/<slot>/usage.raw.json` 递归枚举 vs `response.body.raw` 重提（C4）；layers 两路径 L10-12 vs L36-38（C5c）。
4. crossing：`crossing-verification-cargo-r1-r1.json` + X6 per-slot 计数。

## 7. 本文件自证

- 机器收据集：final-audit-stage-{report-plan-r1,u1-r1,cache-r3,codex-r1,dsh-r1,coverage-r2}.json（全部原子拒写、内嵌 live_doc_drift:[]）。
- 证据行（§8）由 evidence_line.py 生成并经 receipt_check 回验（见文末回验行）。

## 8. 证据行（脚本生成，00:14:07 / 00:20:14 / 00:21:07+08:00 三批）

```
5-评测报告/对抗性盲审-L4-2026-10-29/tools/final_audit.py · 8393b423 · 35270B · 2026-10-30T00:14:07+08:00
5-评测报告/对抗性盲审-L4-2026-10-29/tools/credential_scan.py · 4dbbff27 · 14842B · 2026-10-30T00:14:07+08:00
5-评测报告/对抗性盲审-L4-2026-10-29/tools/pii_min_check.py · 9935c1cf · 7906B · 2026-10-30T00:14:07+08:00
5-评测报告/对抗性盲审-L4-2026-10-29/final-audit-stage-report-plan-r1.json · 2cfe5f4f · 3406B · 2026-10-30T00:14:07+08:00
5-评测报告/对抗性盲审-L4-2026-10-29/final-audit-stage-u1-r1.json · e3fa7acc · 1263B · 2026-10-30T00:14:07+08:00
5-评测报告/对抗性盲审-L4-2026-10-29/final-audit-stage-cache-r3.json · f0b498fc · 4051B · 2026-10-30T00:14:07+08:00
5-评测报告/对抗性盲审-L4-2026-10-29/final-audit-stage-codex-r1.json · 51cf6ecf · 3018B · 2026-10-30T00:14:07+08:00
5-评测报告/对抗性盲审-L4-2026-10-29/final-audit-stage-dsh-r1.json · a6fea5eb · 1742B · 2026-10-30T00:14:07+08:00
5-评测报告/对抗性盲审-L4-2026-10-29/final-audit-stage-coverage-r2.json · aa1cf8a9 · 1780B · 2026-10-30T00:14:07+08:00
5-评测报告/对抗性盲审-L4-2026-10-29/scan-report-actualE-cache-r3.json · 177cd2c1 · 98077B · 2026-10-30T00:14:07+08:00
5-评测报告/对抗性盲审-L4-2026-10-29/scan-report-codex6-r4.json · 24a98049 · 90664B · 2026-10-30T00:14:07+08:00
5-评测报告/对抗性盲审-L4-2026-10-29/scan-report-dsh6-recoveries-r5.json · afef2a65 · 45676B · 2026-10-30T00:14:07+08:00
5-评测报告/对抗性盲审-L4-2026-10-29/pii-min-check-report-codex6-r3.json · b72eb174 · 337B · 2026-10-30T00:14:07+08:00
5-评测报告/对抗性盲审-L4-2026-10-29/pii-min-check-report-dsh6-r4.json · 9272f573 · 335B · 2026-10-30T00:14:07+08:00
5-评测报告/对抗性盲审-L4-2026-10-29/crossing-verification-cargo-r1-r1.json · a5ddab1f · 3077B · 2026-10-30T00:14:07+08:00
5-评测报告/对抗性盲审-L4-2026-10-29/activity-index-proposal-r2.json · 1414fb9b · 9312B · 2026-10-30T00:20:14+08:00
5-评测报告/对抗性盲审-L4-2026-10-29/activity-index-proposal-r3.json · b6b33d4c · 10415B · 2026-10-30T00:20:14+08:00
5-评测报告/对抗性盲审-L4-2026-10-29/selftest-receipt-credential-scan-r1.json · e17a13ed · 1654B · 2026-10-30T00:14:07+08:00
5-评测报告/对抗性盲审-L4-2026-10-29/tools/activity_index_gen.py · 492945f4 · 11403B · 2026-10-30T00:21:07+08:00
5-评测报告/对抗性盲审-L4-2026-10-29/scan-report-wb-final-r6.json · 6cae40cd · 55879B · 2026-10-30T00:21:07+08:00
5-评测报告/对抗性盲审-L4-2026-10-29/pii-min-check-report-wb-final-r5.json · 3ce66680 · 338B · 2026-10-30T00:21:07+08:00
```
