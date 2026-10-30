# L5 CLI runner 修复报告（task-11，lead 代修；mechanism-engineer 通道启动失败未交付）

- 修复对象：L4 遗留池 L5-1/L5-3/L5-4；冻结 L4 文件零改动，全部落 `3-表现现场/l5-20261030-cli/` 新副本。
- 时间与 SHA 由脚本生成（见 receipts/selftest 内嵌 evidence）；E 未放行，零模型、零网络、零真实 CLI 调用。

## R1 发射修复（codex；池 L5-1）

- `cmd_prepare` 发射 `meta.inputs_verification={ok,checked,mismatches,unexpected,method}`：ws/inputs 逐文件 SHA256 对 contract `case_snapshots.files["inputs/*"]` 机械比对，集合等值才 ok。
- `meta.judge` 改为 gate 契约结构块（`judge_block`）：`{checker_sha256, guards_used, guards_candidates, guards_method, guards_conflict, correct, n_tasks, weighted(8dp), exit_code, raw_output_ref}`；raw checker 输出只留在 `checker.stdout` 与 `score-receipt.raw_checker_output`，不再整体并入 meta。
- `guards_used` 用「索引序字典序首个 reconciling 组合」机械推导（`derive_guards`）：k=len(checks)−possible，按原序 combinations 取首个满足 (scored==possible ∧ scored 通过数==earned) 的集合；记录候选总数；无解置 `guards_conflict=true` 让 gate 必 fail，不静默乱选。L4 实据验证：cargo→[input_integrity, code_rerun, plan_structure]（候选 1540）、dab→[answers_format, input_integrity]（候选 36）。
- `score-receipt.score.{checker_sha256, reported(8dp)}` 与 `meta.weighted(8dp)` 延续 L4 已达标行为；raw 2dp 字段保留（D2 双口径）。
- partial（停止未确认）路径 `meta.judge=null`（checker 0 调用），与 `partial_meta_score_null` 纪律一致。

## R2 ws 模型可见元数据移除（codex+DSH；池 L5-3）

- 删除 pre-run 写 `ws/meta.json`：codex 改写 `ev/meta.prepare.json`（run 时读回，缺席即 FailClosed）；DSH 改写 `ev/meta.prepare.json`（meta 全程内存持有，无回读）。
- 运行期 ws 仅含 `inputs/`+`TASK.md`；checker_sha256/config_ref/仓库绝对路径不再进入模型可见域（同时消除 L4 codex 机械扫描的 `cat ws/meta.json` 回显类命中的来源）。
- 归档排除表保留 `meta.json` 名（防御性，旧产物语义不变）。

## R3 DSH capture marker 修正（池 L5-4）

- `dsh_session_dirname(ws)`：按 DSH 真实编码推导会话目录名 `--` + 绝对路径去首 `/` 后 `/`→`-` + `--`，非 ASCII 按 `~XXXX~`（大写 4 位十六进制 UTF-16 码元）转义。
- `capture_session` 重写：精确名匹配优先，未命中退化按「内名以 `-{槽位ID}` 结尾」后缀匹配；返回收据 `{match_method: exact|suffix|mock|none, matched_dir, expected, copied}` 落 `meta.session_capture`；`none` 不静默（必披露并阻断 usage 结论）。
- 对照证据：新匹配器对 L4 六个真实会话目录名 6/6 命中；L4 旧 marker 构造同批回放 0/6（缺陷复现）。

## DSH 已达标项保留

- DSH `score_case` 已有 GUARDS 静态表 + 机械调和断言（len(scored)==分母、earned 与 checker weighted 一致）+ `meta.judge` 完整发射与 `inputs_verification`（L4 DSH gate fails 无发射类项）——保留原实现，仅加 R2/R3。与预注册 R1 文本的差异（静态表 vs 推导）为等价更强保证，特此披露。

## 自检（self_test 账；全部零模型）

| 收据 | 结果 |
|---|---|
| `codex/tools/selftest.py`（mock 全链，槽位适配 L5 r1） | SELFTEST: PASS |
| `dsh/tools/lab.py selftest`（L4 会话回放+脱敏） | 3/3 PASS |
| `selftest/l5-selftest.py`（R1/R2/R3 专项 11 例） | 11/11 PASS |

- R1 负例口径更正（本报告 dated）：`passed+1` 小篡改仍可被他调和集吸收（候选 1848）——推导保证内部一致性，不防篡改；防篡改由 gate 对 raw checks 独立重算承担。负例改为物理不可达计数（passed=25>22），conflict 必现。
- R3 负例：旧 marker 0/6 为缺陷复现证据，非新缺陷。

## 边界与未决

- mock prepare 的 inputs_verification 正例用 stub contract（1 文件）；真实派发对真实 contract 比对（7 文件 dab / 10 项 cargo 级）在 preflight 与首槽 run 中机械执行，失败即停槽。
- `guards_candidates` 数值大（1540/36）说明按计数调和存在多解——canonical 规则取索引序第一，跨产品一致性由同一规则保证；candidates 数逐场入收据备审。
- E 未放行：真实 2 槽（codex dab/cargo r1、dsh dab/cargo r1）待 lead 通知。

live_doc_drift=[]
