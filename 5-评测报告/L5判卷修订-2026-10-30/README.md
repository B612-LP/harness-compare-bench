# L5 判卷工具修订档案（grading_regression；R4 gate v2 + R5 cache mapping v2）

- 修订纪律（老师要求）：修前代码、修后代码、正例、近似错误例、独立验收、历史复算影响，逐项留档。
- 两个修订的历史记录为「新增版本化文件」，当时未改冻结版本、未调用模型或网络。本页现已修正公开链接并去除内部分工，是事后整理页，不是旧封印原文；所述自测及复算通过均为历史记录，不表示当前公开工作树已重新验证。部分计划、绑定与复核原件不公开，相关历史重跑可能失败。

## gate v2（R4，池 L5-8）

- 修前：[1-评测方案/工具链/l4-execution/gate.py](../../1-评测方案/工具链/l4-execution/gate.py)（冻结，SHA 见 [gate-v2/archive-meta.json](gate-v2/archive-meta.json)）
- 修后：[1-评测方案/工具链/l5-execution/gate.py](../../1-评测方案/工具链/l5-execution/gate.py)（sha256_16 38b42a87c30c87d2）
- diff：[gate-v2/diff-l4-to-l5.patch](gate-v2/diff-l4-to-l5.patch)（唯一语义改动=not_executed 白名单放行恰名 `registrations` + 收据字段 whitelisted_entries）
- 正例/近似错误例：[gate-v2-notexec-acceptance.py](gate-v2-notexec-acceptance.py) → [gate-v2-acceptance-receipt.json](gate-v2-acceptance-receipt.json)（8/8：正例无 fail+record_valid True+清单 2 项 SHA；拼写变体/并存/虚造均仍 fail；冻结 v4 对照行为保持）
- 回归：v2 内置 selftest 全过（GATE_SELFTEST: PASS）
- 历史复算影响：[gate-v2-history-recompute.py](gate-v2-history-recompute.py) → [gate-v2-history-recompute-receipt.json](gate-v2-history-recompute-receipt.json)（17/17 槽全覆盖；唯一差异=bird 白名单 fail 消失+record_valid True；bird formal 仍 false；**L4 formal 0/17 不变**）
- 独立验收：[历史公开摘要](<../L5独立复核-2026-10-30/README.md>)；原独立复核执行材料不公开，不能据摘要完整核验原件。

## cache mapping v2（R5，池 L5-5）

- 修前：[3-表现现场/l4-20261029-cache/tools/cache_probe.py](../../3-表现现场/l4-20261029-cache/tools/cache_probe.py) USAGE_FIELDS 预设（responses 缺嵌套路径；原勘误收据不公开，见[L4 公开复核摘要](<../L4独立验收-2026-10-29/README.md>)；摘要不能替代原件）
- 修后：[1-评测方案/工具链/l5-execution/cache_mapping_v2.py](../../1-评测方案/工具链/l5-execution/cache_mapping_v2.py)（wire_key 键控+嵌套 `input_tokens_details.cached_tokens`+normalized 不求和）
- 正例/近似错误例：内嵌 unit selftest 6 例（parent_missing/parent_non_object/child_missing/zero/positive/别名不求和）
- 一致性复算：L4 18 probe raw 只读重算，28 断言全过 + erratum responses 6 槽逐值一致 → [cache-mapping-v2/recompute-receipt.json](cache-mapping-v2/recompute-receipt.json)
- finding 撤销：「responses 协议缺 cache 字段」自 mapping v2 起撤（raw 一直完整，系映射覆盖缺口）
- 独立验收：预留同上。

live_doc_drift=[]
