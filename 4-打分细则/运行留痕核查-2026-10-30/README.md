# 运行留痕十字段核查（2026-10-30，L10-C）

> 依据：老师 2026-10-28 反馈第①条——每次运行保留唯一 ID、题目版本、产品版本、模型、工具、权限、技能状态、运行时间、证据等级和最终裁定。
> 本核查只读检查既有批次原件，不回填、不改写任何历史 meta；结论面向未来运行的模板升级（同日生效，见 §3）。

## 1. 十字段 × 批次符合性矩阵

图例：✅ 实测达标（场级原件直读）｜📄 披露覆盖（值不在场级 meta，但有明确承载位置）｜❌ 场级缺口（本核查登记，见 §4）｜🔍 未逐场抽查（范围声明见 §5）

| 留痕字段 | r1030-formal-a1（CLI×10） | r1031-variance-n3（CLI n=3） | r20261027-yuanbao-4cases（桌面×5） | r20261027-wb-lcb-sandbox（桌面×1） | r1026 / r1029 历史桌面 |
|---|---|---|---|---|---|
| 唯一 ID | ✅ `run_id` | ✅ 同族 schema（抽查） | ✅ 机器账行 `run_id`（batch/case 组合） | ✅ 机器账行 | ✅ 机器账行 |
| 题目版本 | ✅ `judge.checker_version` + `rule_version` | ✅ 同族 | ✅ `judge.checker_version`（如 1.2-q26-frpm） | 📄 TASK.md + 冻结版本引用 | 📄 判卷审计链 |
| 产品版本 | ✅ `product_version` | ✅ 同族 | 📄 `product: yuanbao-expert-web`；精确 build 无公开出处（产品封闭） | 📄 `preflight_receipt.json` 版本字段 | 📄 同左 |
| 模型 | ✅ `model`（deepseek-flash 等 alias） | ✅ 同族 | 📄 封闭模型：`internet_search_protocol`/`disclosure` 批级披露，模型 id 不可证 | 📄 同左（WB 准入预检两受管未知在案） | 📄 同左 |
| 工具 | ✅ `tools` | ✅ 同族 | 📄 产品不可配置：批级 `disclosure` | ✅ 沙盒 profile + 代理白名单即工具面证据 | 📄 批级配置留档 |
| 权限 | ✅ `permissions` | ✅ 同族 | 📄 产品封闭：批级披露 + 联网三档实测 | ✅ `sandbox-exec` profile（deny network-outbound）+ Clash 剔除记录 | 📄 批级 |
| 技能状态 | ✅ `skills` | ✅ 同族 | 📄 产品封闭：批级披露 | 📄 批级 | 📄 批级 |
| 运行时间 | ✅ `duration_s` | ✅ 同族 | ❌ 场级无 `duration_s`（trace 含会话时间戳，未结构化） | ❌ 同左（launch/console log 有时间线） | ❌ 同左 |
| 证据等级 | ✅ `integrity.evidence`（如 original-contemporaneous-full） | ✅ 同族 | ✅ 机器账行 `evidence_grade`（conversation-api-dumps-and-artifacts） | ✅ 机器账行（archived-events-and-artifacts） | ✅ 机器账行 |
| 最终裁定 | ✅ `integrity_verdict` + 机器账 `adjudication` | ✅ 同族 | ✅ 机器账 `adjudication`（V，含检索轴实证 clean 说明） | ✅ 机器账（V，1/100.0） | ✅ 机器账（V/X 各在案） |

**总评**：CLI 赛道（r1030/r1031）十字段场级全达标；桌面赛道 ID/题目版本/证据等级/最终裁定四项达标或行级承载，模型/工具/权限/技能四项因产品封闭只能披露覆盖，**运行时间两项存在真实场级缺口**（时间线散在 trace/log，未结构化为 `duration_s`）。

## 2. 修订记录（运行记录模板 v1 → v2）

- 修前存档：[修前-20261030/](<修前-20261030/>)——`运行记录模板.md`（SHA-256 `239ef71f…`）、`validate_run.py`（SHA-256 `6c963c6d…`），逐字节副本。
- 修后：模板 §5.1 升为 schema v2，新增 `case_version`、`provenance.{model_resolved, tools, permissions, skills, started_at, duration_s}`、`evidence_grade`、`verdict_basis`；纪律为「实测值或 披露：<承载位置>」，禁止裸写「未知」。校验器同步支持 v1/v2 双版本：v1 记录原样有效（历史不回填），v2 新记录十字段强制。
- 正例 / 近似错误例：校验器内置自测——v2 正例 1（十字段全）、v1 历史正例 1（向后兼容）、负例 12（缺证据等级/缺裁定依据/运行时间非数值/裸写「未知」/缺技能状态/缺题目版本等）；**2026-10-30 实跑 14/14 PASS**（退出码 0）。
- 语义选择声明：取「披露值合法化 + 缺失即拒」而非「一律要求实测」——桌面产品封闭字段无法实测，强迫实测会诱导编造；披露值必须指明承载位置，可复核性不降级。
- 影响面：`4-打分细则/轻量判卷/` 两文件；零判卷器（checker）修订、零分数影响；v2 自 2026-10-30 起对新运行生效。

## 3. 生效与边界

- v2 生效日起的新运行（含下一环 B 组正式准入批）一律 schema v2 记录；既有批次原件与机器账不回填、不重写。
- 本核查不改变任何 N/V/F/X 计数与既有裁定；桌面场级时间线缺口按 §4 管控。

## 4. 未知登记（三件套）

| 未知项 | 影响 | 下一步 | 停止条件 |
|---|---|---|---|
| 桌面赛道场级留痕薄弱（运行时间无结构化 `duration_s`；模型/工具/权限/技能仅披露覆盖） | 场级自足取证弱于 CLI，单场复核需组合机器账行级 + 批级披露 | 自 v2 模板生效批起场级显式化；B 组正式准入批按 v2 执行并在预注册中声明 | 模板执行批的场级记录通过 `validate_run.py` v2 校验且独立验收通过，即视为该缺口收口 |

## 5. 核查范围声明

- 逐场直读：r1030 全部 10 场 meta 字段名级核查 + r20261027-yuanbao run_meta 全文直读 + wb-lcb-sandbox 目录清单级核查。
- r1031 标记「同族 schema」依据同一 runner 族与文档在案的 corrections 机制，未逐场展开；r1026/r1029 历史桌面仅核机器账行级承载，未逐场展开。此两格为 🔍 未逐场抽查，不据此声称「全档案达标」。
- 私有台账（L9-B 交付入口）2026-10-30 以当前参数复跑：`verified_checked_scope=true`，`all_archive_narrative_references_verified=false`（既有披露限制，未改写）。
