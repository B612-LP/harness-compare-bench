# l4-execution：L4 共同闸门与离线重放工具（builder-dsh 交付；共享接口）

预注册：`1-评测方案/自动循环L4-2026-10-29/PREREGISTRATION.md`；澄清：同目录 `CLARIFICATION-L4-1.md`（R1–R4）。
封印/绑定生成：lead 的 `execution_seal.py`（本目录工具只读复用其 `validate_manifest`/`required_files`，不改 lead 文件）。

## 1. gate.py —— 共同 gate（CLI + 可 import）

### verify_execution(binding_path, ...) → 证据 dict｜raise `GateError`

```python
import importlib.util
spec = importlib.util.spec_from_file_location(
    "l4_gate", "<repo>/1-评测方案/工具链/l4-execution/gate.py")
gate = importlib.util.module_from_spec(spec); spec.loader.exec_module(gate)

ev = gate.verify_execution("<repo>/1-评测方案/自动循环L4-2026-10-29/runtime-binding.json",
                           require_release=True)   # 真实消费者必须显式 require_release=True（默认即 True）
```

- 核验链：binding 键/格式 → release 闸（require_release=True 时 `released_for_model_calls=false` 直接 raise）
  → plan/contract 磁盘 sha == binding → D/E 提交内 plan/contract blob 三方一致
  → `registered_at` == E 提交时刻（只读 git `%cI`）→ E ≤ 核验时刻 → 只读 `merge-base --is-ancestor`
  证明 D↤E、E↤HEAD（时钟序必要非充分）→ manifest 取 E blob：sha 对 binding；
  `files` 逐项 = 仓内安全相对路径 + E blob sha == manifest sha + 磁盘 sha 一致；
  `external_files`（绝对路径→sha，含 `~/.dsh/profiles/bench-cli/{cordis.patch.yml,package.json}`
  与 `~/.dsh/AGENTS.md`）逐项实算；必需成员集复用 lead `validate_manifest`（防漏封 helper/runner 入口）。
- 注入点（合成测试零 git 写）：`git_reader/git_time/git_ancestor/now/required_set/plan_dir/repo`。
- git 只读，仅限本工具内部执行；人工 git 写命令仍全禁。

### gate_admission(binding_path, product, ...) → 报告 dict

`product ∈ {dsh, codex, workbuddy}`；内部**先** `verify_execution(require_release=True)`，
binding 未放行或任一核验失败即 raise（fail-closed，不接受裸 load_binding）。

R1 真值表已实现：每 slot 恰一条记账（`executed`/`partial`/`not_executed`）；
`not_executed` 只认 `evidence_dir/notexecuted.json`（身份+preregistration_commit+非空
reason/stop_source；目录内出现其他文件=疑似虚造证据，fail），**不要求也不允许 meta/空流**；
真实 timeout（`timed_out=true` + 全套原始证据 + 冻结全分母收据 + 无污染）可 formal_admission=true；
基础设施 `error/transport-error` 恒 partial、不折满。formal 公式八门逐场布尔分层输出。
slot_id/run_id/event_id **各自**唯一（部分重号即 raise）。summary 中
`accounting_complete`（全集记账真）与 `all_formal_admitted`（全槽准入）**互不混同**。

各产品 runner 的 meta 须满足（gate 实核项，都是 v2 必备字段之外的对齐项）：
`slot_id/run_id/event_id/case/rep/order/stratum` 与 plan 逐项相等；`registered_at` 与 binding
**严格等值**；`preregistration_commit`==binding；`registered_at < started_at`；`attempts` 恰 1 元素、
`transport_retries` int；`selection.slot_id`（ok/timeout）或 `selection=null`+非空 `diagnostic`；
`route.host=="api.deepseek.com"`、model/effort==strata（cli 层）；isolation.ok true（空 dict 不作事实）；
canonical `prompt/stdout/stderr` sha256+bytes=原始文件实算；`archived_stdout.full_*` 另列字段独立实算
（full 流绝不冒称原始流）；`judge` 含计数对（`correct`/`n_tasks` 等）+`checker_sha256`；
`score-receipt.json` 的 `score.reported`（8dp）与分母对 `contract.denominators`。
WB 层追加（R2）：`declared_alias` 本批选择证据（`route.alias_evidence` 指向存在的原始记录）、
`actual_gateway=unknown` 须 `route_verification=current_not_observed`+`r2_history_ref`、
`product_version` 与 `app_asar_sha256` 必填、白名单未知逐条 impact/next_step/stop_condition。

### CLI

```
python3 gate.py --verify-execution --binding <...> [--no-require-release] [--plan-dir <dir>] [--out <receipt>]
python3 gate.py --admission --binding <...> --product dsh [--out <receipt>]
python3 gate.py --selftest
```

退出码 0=过 / 1=判定未过（GateError 也会打印 JSON）/ 2=用法或拒写。`--out` O_EXCL|O_NOFOLLOW
拒写已存在/软链；所有新收据内嵌 `live_doc_drift`（list）。

## 2. replay_dual.py —— 双归档离线反事实重放（offline_recompute；零模型）

- `--run <evidence_dir> --case <case> --out <report.json>`：母本只读（前后 sha 对账入报告），
  两 sandbox 副本分别按 r1030 语义（rmtree 序缺陷在副本内复现→raw 丢失/vacuous 扫描/无 cache 拆分）
  与 r1031/L4 语义（staging 先行/完整流重建/逐调用 cache 拆分）重放后处理，diff 报告。
- **equivalent_simulation=true 是身份**：等价模拟≠旧/新完整 pipeline 原样复现；仅 raw-vs-full
  对比不得声称双 pipeline 已复现。`--selftest` 8/8（合成会话，非模型数据）。

## 3. 收据纪律（本目录工具产出的收据全部过 evidence-kit receipt_check）

- `live_doc_drift` 恒 list；哈希/时刻脚本生成禁手打；hex 记号须小写且长度 ∈ {7,8,40,64}
  （截断前缀用 8 位）；收据只写新路径，已存在/软链即拒。

## 4. 现行状态

- gate 自测 25/25（receipts/gate-selftest.json，r1 留痕）；dual-replay 自测 8/8。
- 真实批次准入：等 E 封印 + lead release 后 `--admission --product <p>`。
- DSH runner：`3-表现现场/l4-20261029-cli/dsh/tools/lab.py`（plan 驱动 6 槽；whole-CLI 重启=0；
  原始流 O_EXCL 永不覆盖；每槽派发前快核 external_files，漂移即停）。
