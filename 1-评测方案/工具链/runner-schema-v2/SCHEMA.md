# runner-schema-v2：runner 产物 meta 规范（L2 包C 交付，L3 包B 修订）

> **公开引用说明（2026-10-30）**：下述 L2/L3 预注册链接现在指去除内部协调内容的公开摘要，非原件，也不继承原封印；原件不在当前工作树，不能仅凭摘要独立校验；既有 Git 历史是否公开原件须另行确认。原有章节引用和历史提交号仍指原件，不能视为摘要的校验信息。历史收据及其他依赖不能据此声称在当前工作树重新通过。本说明改变了此规范文件字节；历史收据对旧版的绑定不自动转移，核验应以各自原清单为准。

- 版本：v2.1-l3（L3 修订见文首「L3 变更框」；lab.py 实跑集成不在本包，见文末 unknown）
- 历史绑定：原预注册 §五（封印 commit `ae36f67`，分支 `loop2-2026-10-29`），原件不可公开核验；[相关公开依据摘要](../../评测依据-判卷回放与运行元数据-2026-10-29/PREREGISTRATION.md)并非原件或原章节。
- L3 历史修订绑定：原预注册 §三包B（封印 commit `72edb519`，分支 `loop3-2026-10-29`），原件不可公开核验；[相关公开依据摘要](../../评测依据-机读约束与证据工具-2026-10-29/PREREGISTRATION.md)并非原件或原章节；历史审计原件不公开，其结果可参考[判卷回放与证据说明](../../../5-评测报告/判卷回放与证据说明-2026-10-30.md)，摘要不替代原审计。
- 落盘时刻：2026-10-29 16:00:57 +0800（实钟，L2 初版）；L3 修订时刻以本框与收据脚本生成为准
- 基线：r1031 codex 侧 `runs/*/meta.json` 字段集逐项对齐（参照 `3-表现现场/r1031-variance-n3/codex/runs/*/meta.json` 与 `tools-codex/lab.py`，两者本包只读）
- 缺陷动机：**D1** 全批无 `registered_at`，注册先于运行只能锚点级间接佐证（历史记录未回填，本字段列为后续运行器必备）；**D2** codex 收据 `reported` 2 位小数 vs r1030 口径 8 位；**D5** dsh meta 缺 `selection/attempts/stdout_bytes` 等、`transport_retries` 列表型 vs codex 整型
- 配套校验器：[validate_runner_meta.py](validate_runner_meta.py)（stdlib-only；`--spec` 对 [fixtures/](fixtures/) 自检，`--retro` 对 runs 目录只读产出兼容矩阵，`--reconcile` 做 registered_at ↔ 封印提交时刻离线对账）

> **历史变更说明（2026-10-29；原审计和预注册不公开，不能仅凭本页核验其时序或封印）**
> 1. **B1** `status` 值域定死为 `{ok, timeout, error, transport-error}`（§一原行 `status∈{ok,timeout,error,transport-error,…}` 的「…」移除）；validator 自 v2.1 起按 enum 强制，越值 → `fail:enum`。
> 2. **B2** `integrity_verdict` 值域 `{clean, benign-reviewed, violation}`；`benign-reviewed` 必须伴随**非空 `corrections`**，否则 → `fail:companion`。
> 3. **B3** `selection` 为 null 必须伴随**非空 `diagnostic`**，否则 → `fail:companion`。
> 4. **B4** seal 校验响亮化：未提供 `--seal-at` 时 `classify` **永不返回裸 `pass`**——返回 `fail:unsealed`（`--spec` 由此非零退出，fail-closed）；显式 opt-in `--allow-unsealed` **仅限 `--retro` 披露模式**（`--spec` 传它即 exit 2），矩阵带 `seal.unsealed=true` 与 `seal.policy` 标记；判定值 `pass:unsealed` 本身带 unsealed 标记、不可被消费为裸 pass。
> 4b. **修复轮（2026-10-29，DF-B1/D-L3-1，裁定=修代码就预注册字面）**：`--retro` 无 `--seal-at` 且无 `--allow-unsealed` ⇒ **exit 3 不落盘任何矩阵**（非零退出落实预注册 B4 字面）；`--allow-unsealed` ⇒ exit 0 出矩阵并带 `seal.unsealed=true`/`seal.policy` 标记。`--reconcile`：`--git` 模式 src 字符串改字符串拼接（`%cI` 为 git 占位符，曾与 Python %-format 冲突致 TypeError 被吞）；verdict 语义对齐——任何步骤假 ⇒ verdict 不得为 ok（`error`=非比较步骤假 / `violation`=仅比较步骤假 / `ok`=全部真且比较通过），回归 T7–T9（历史记录称 `--git` 用例以只读 git 执行，`L3_ALLOW_GIT=1`）。
> 5. **B5** fixtures 6 → **10**（新增 B1/B2/B3 反例 ×3 + benign-reviewed 带 corrections 正例 ×1）；spec-selftest 收据改出新路径 `spec-selftest-receipt-l3-20261029.json`，原收据（`5c6177fd…`）与 `receipt-overwrite-evidence-20261029.json` 字节不动。
> 6. **B6** C-1 非破坏化：`--spec` 收据只写显式 `--out`；目标已存在即拒绝（exit 2、原字节不动）；缺 `--out` 不落盘（结果仍打印）。回归 `cli-selftest-l3.py` T1 机械复现 16:11:16 覆盖模式（二写失败且首文件字节不变）。
> 7. **B7** ⑦溯源：§三.4 显式披露「顺序检查必要非充分」；新增 §三.5 `--reconcile` 离线对账；L3 仅合成对账（fixtures/reconcile/，L3 封印提交 `72edb519` 口径），**真实批次对账留 L4（§五 U1）**。

## 一、必备字段集（v2 meta.json，逐字段动机锚点）

### 身份与注册

| 字段 | 类型 | 约束 | 动机锚点 |
|---|---|---|---|
| `batch` | string | 非空 | 基线：批次归属，审计链分组键 |
| `rule_version` | string | 非空 | 基线：判卷合同版本，准入比对键 |
| `preregistration_commit` | string | `^[0-9a-f]{7,40}$` | **D1**：封印哈希逐场落盘，使「注册先于运行」有逐场机器可查锚点 |
| `registered_at` | string ISO8601 带时区 | 见 §三时序校验 | **D1（新增必备）**：值=预注册封印提交时间戳的引用；消除 D1 的逐场注册时序不可验证缺口 |
| `rep` | int | ≥1 | 基线：重复性研究 rep 槽位 |
| `product` / `case` / `form` | string | 非空 | 基线：运行身份三元组 |
| `run_id` / `event_id` | string | 非空，全场唯一 | 基线：证据链引用键 |
| `selection` | object 或 null | **null 时必须伴随非空 `diagnostic`**（v2.1 validator 强制，违反 → `fail:companion`） | **D5**：dsh 补齐；计划槽位（plan_id/slot_id/order/kind）；运行级失败记 null+诊断（L1 总则2 口径） |

### 运行环境（基线沿用，无新增缺陷动机）

| 字段 | 类型 | 动机锚点 |
|---|---|---|
| `workspace` | string | 基线：仓库外工作区路径，隔离断言对象 |
| `model` / `reasoning_effort` / `product_version` | string | 基线：模型与产品版本（老师要求①） |
| `route` | object（host/provider_id/wire_protocol/endpoint） | 基线：路由证据 |
| `tools` / `soft_constraints` | list | 基线：工具与软约束清单（老师要求①） |
| `permissions` / `skills` / `web_search` | string | 基线：权限/技能状态（老师要求①） |
| `prompt_sha256` | string `^[0-9a-f]{64}$` | 基线：题面哈希 |
| `isolation` | object（含 `ok`: bool） | 基线：工作区隔离断言 |
| `inputs` | list（path/sha256/bytes） | 基线：输入副本清单 |

### 时序（D1 关联）

| 字段 | 类型 | 约束 | 动机锚点 |
|---|---|---|---|
| `created_at` / `started_at` / `finished_at` | string ISO8601 带时区 | `started_at`/`finished_at` 为运行实测 | 基线 + **D1**：`started_at` 参与 `registered_at < started_at` 校验 |
| `duration_s` | number | ≥0 | 基线：耗时 |

### 执行明细

| 字段 | 类型 | 约束 | 动机锚点 |
|---|---|---|---|
| `status` / `exit_code` | string / int 或 null | **status ∈ {ok, timeout, error, transport-error}**（v2.1 封闭值域，validator 强制，越值 → `fail:enum`） | 基线：运行结局 |
| `attempts` | list | 每元素含 n/started_at/duration_s/exit_code/outcome | **D5**：dsh 补齐；逐尝试留档，重试证据不丢 |
| `transport_retries` | **int**（≥0） | 同一逻辑运行内传输层重试计数 | **D5**：统一整型（r1031 dsh 为列表型、codex 为整型） |
| `transport_retry_events` | list（可选） | 逐次退避明细（n/at/backoff_s/outcome） | **D5**：明细与计数分离，计数恒为整型 |
| `stdout_bytes` / `stderr_bytes` | int ≥0 | 完整流字节数 | **D5**：dsh 补齐；工程项 a 的落盘完整性证据（回应 stdout 8192 截断未知登记） |
| `stdout_sha256` / `stderr_sha256` | string `^[0-9a-f]{64}$` | 完整流哈希 | **D5**：与 bytes 组成可复核完整性对 |
| `archived_stdout` | object（**可选，dsh 特有映射字段**） | 见 §四映射 | **D5**：保留 dsh 现有投影统计字段并声明映射；不豁免四个 canonical `stdout_*/stderr_*` 字段 |

### 计分与证据

| 字段 | 类型 | 约束 | 动机锚点 |
|---|---|---|---|
| `usage` | object（含 `per_call` 明细） | 逐调用含 cache_read/cache_creation | 基线（工程项 b）：provider-cache 语义观察数据层 |
| `reward` | int 或 null | checker 原值 | 基线 |
| `weighted` | number，**唯一精度 8 位小数** | 见 §五精度规范 | **D2**：机读加权分统一 8dp，消除 2dp/8dp 双口径 |
| `failed` | list | 失败项 id | 基线 |
| `judge` | object | checker 原始输出 | 基线：判分双源之一 |
| `integrity` / `integrity_verdict` | object / string | **verdict ∈ {clean, benign-reviewed, violation}**（v2.1 validator 强制）；`benign-reviewed` 必须伴随**非空 `corrections`**（否则 → `fail:companion`） | 基线（L1 两级裁定先例） |

## 二、逐场收据（score-receipt.json）

| 字段 | 类型 | 约束 | 动机锚点 |
|---|---|---|---|
| `score.reported` | number，**唯一精度 8 位小数** | 算术=round(earned/possible×100, 8) | **D2**：本字段的 2dp 偏差即 D2 本体；v2 统一为 8dp 机读唯一精度 |
| `score.reward` / `score.rule_version` / `score.checker_sha256` / `raw_checker_output` | 同 r1030 口径 | — | 基线：收据双源结构沿用 |

## 三、`registered_at` 时序校验（D1 专条）

1. **格式**：ISO8601 且必须带时区（naive 时间戳判类型错误）。
2. **先注册后运行**：`registered_at < started_at`，违反记 `temporal-error(order)`。
3. **不早于封印**：`registered_at ≥ 预注册封印提交时刻`（校验器经 `--seal-at` 提供封印时刻，如 r1031 为 `2026-10-29T13:22:39+08:00`），违反记 `temporal-error(seal)`。
   **B4（v2.1，修复轮按预注册字面收紧）**：未提供 `--seal-at` 时本条**不可静默跳过**——`--spec` 面 `classify` 返回 `fail:unsealed`（非裸 pass，非零退出）；`--retro` 面无 `--seal-at` 且无 `--allow-unsealed` ⇒ **exit 3、不落盘矩阵**；`--allow-unsealed` 为唯一披露出口（矩阵带 `seal.unsealed=true`/`seal.policy` 标记）。
4. 值语义：预注册封印提交时间戳的**引用**——runner 启动时从批次预注册登记读取，不得事手写未来时刻（L2 总则5）。
   **⑦/O-1 披露（v2.1 显式化）**：第 2/3 条的顺序检查是**必要非充分**——它们只能验证格式与时序自洽，不能验证 `registered_at` 确实来自封印提交时刻；「可查真」依赖 §三.5 的离线对账。

### §三.5 `--reconcile`：registered_at ↔ 封印提交时刻离线对账（⑦/O-1，v2.1 新增）

```bash
python3 validate_runner_meta.py --reconcile \
    --ledger <预注册台账路径> (--pointer /registered_at | --line-regex <含时刻的行>) \
    --commit <封印提交哈希> \
    (--commit-time <ISO8601+tz> | --commit-time-file <含 git log 输出的文件> | --git) \
    --out <对账收据路径>
```

- 机械步骤：台账可读 → 字段位置提取 → ISO8601+tz 格式 → 提交哈希格式 → 提交时刻来源解析 → `registered_at ≥ commit_time`（记 delta_seconds）；每步落盘、任何一步失败即 `ok=false` 非零退出。
- **verdict 语义（D-L3-1 对齐）**：任何步骤假 ⇒ verdict 不得为 ok——`error`=非比较步骤假（来源/格式/提取失败）、`violation`=仅比较步骤假（registered_at < commit_time）、`ok`=全部步骤真且比较通过、`inconclusive`=防御保留。
- **commit_time 来源三模式**：`--commit-time`（显式值）/ `--commit-time-file`（文件内首个 ISO8601+tz 记号；审计侧可粘贴 `git log -1 --format=%cI <hash>` 输出）/ `--git`（脚本直接读取 git）。**L3 未行使 `--git`**（当时测试范围未覆盖），该模式代码路径在 L3 无行使记录，如实披露；**真实批次对账为正式闭项条件（§五 U1，留 L4）**。
- L3 自检证据（合成对账，self_test）：[reconciliation-synthetic-l3-20261029.json](reconciliation-synthetic-l3-20261029.json)（正例 verdict=ok，delta=0）与 [reconciliation-synthetic-early-l3-20261029.json](reconciliation-synthetic-early-l3-20261029.json)（负例 verdict=violation，exit 1），样本在 [fixtures/reconcile/](fixtures/reconcile/)。

## 四、dsh 侧补齐与 `archived_stdout` 映射（D5 专条）

dsh 现有 `archived_stdout` 保留为 **dsh 特有可选映射字段**，与 v2 canonical 字段映射关系：

| archived_stdout（dsh 现状） | v2 canonical（必备） | 说明 |
|---|---|---|
| `full_bytes` | `stdout_bytes` | 完整流字节数（`agent.jsonl.full`） |
| `full_file` | —（文件名引用） | 完整流落盘文件 |
| `full_lines` / `full_method` / `raw_bytes` / `raw_lines` / `raw_file` / `raw_truncation` / `raw_lost` / `raw_lost_reason` | —（dsh 特有留存） | CLI 投影统计（`maxStringBytes=8192` 等 cap 证据）与归档缺陷披露 |

规则：`archived_stdout` 的存在**不豁免** `stdout_bytes/stdout_sha256/stderr_bytes/stderr_sha256` 四个必备字段；stderr 侧 dsh 现状无对应投影字段，v2 直接要求 canonical 字段落盘。

## 五、机读精度规范（D2 专条）

1. **唯一机读精度 = 8 位小数**：`score-receipt.json: score.reported` 与 `meta.json: weighted` 的值必须等于 `round(earned/possible×100, 8)`（分母来源 judge 计数字段四组之一：`correct/n_questions`、`correct/n_tasks`、`passed_problems/total_problems`、`passed/total`）；计数不可导出时做表示性检查（`round(v,8)==v`）。
2. **展示层 2dp 另列**：如需两位小数展示，用显式命名的展示字段（建议 `score_display.reported_2dp` / `weighted_display_2dp`），不得复用机读字段名，也不得回写机读字段。
3. 判定分级：`ok`（值==8dp 期望）/ `precision-error`（值==2dp 粗化等）/ `representable-only`（不可导出期望，仅表示性检查通过）。

## 六、校验器用法

```bash
# --spec：对合成 fixtures 自检（manifest 期望全匹配则 exit 0；收据只写显式 --out，B6 C-1 非破坏化）
python3 validate_runner_meta.py --spec --out spec-selftest-receipt-l3-20261029.json
#   目标已存在 → 拒绝（exit 2，原字节不动）；缺 --out → 不落盘（结果仍打印）
#   --spec 不接受 --allow-unsealed（B4：固定 fail-closed；未提供 --seal-at 时 pass 期望必失败）
# --retro：runs 目录只读兼容矩阵（每场×每必备字段：有/缺/类型/精度）
python3 validate_runner_meta.py --retro <runs_dir> [--retro <runs_dir> ...] \
    --out retro-r1031-matrix.json [--seal-at 2026-10-29T13:22:39+08:00] \
    [--allow-unsealed]   # 仅限本披露模式；矩阵带 seal.unsealed / seal.policy 标记
# --reconcile：registered_at ↔ 封印提交时刻离线对账（§三.5，⑦/O-1）
python3 validate_runner_meta.py --reconcile --ledger <台账> --pointer /registered_at \
    --commit <hash> --commit-time-file <文件> --out <对账收据>
```

--retro 为**只读**操作；矩阵为披露性 delta 报告，不构成对历史批次的追溯判定（见矩阵文件首部声明）。
L3 收据路径（本包内）：`spec-selftest-receipt-l3-20261029.json`（--spec）、`cli-regression-receipt-l3-20261029.json`（[cli-selftest-l3.py](cli-selftest-l3.py) 机械回归：B6 覆盖模式 / B4 fail-closed 与 opt-in 界限 / B7 对账正负例 / 原收据字节守护）、`reconciliation-synthetic-l3-20261029.json` 与 `reconciliation-synthetic-early-l3-20261029.json`（B7 合成对账）。L2 原收据 `spec-selftest-receipt.json`（`5c6177fd…`）与 `receipt-overwrite-evidence-20261029.json` 字节不动。

## 七、显式 unknown（老师④格式）

**lab.py 实跑集成未验证**：本包交付规范+校验器+模板级合成 fixtures，`registered_at` 采集、8dp 写出、dsh canonical 字段补齐均未经真实 API 运行检验。
影响：schema 可能在真实批次暴露工程缺口（字段采集时点、序列化精度实现）。
下一步：L3 预注册时将 v2 集成进 codex/dsh 两侧 lab.py，并入首次真实批次验收。
停止条件：集成完成并通过一次真实批次全量校验，或 schema 被继任版本显式废弃。
