# 测试诊断载体规范说明（不改原件）

主 [README](<5-评测报告/L6独立复核-2026-10-30/README.md>)、[receipt](<5-评测报告/L6独立复核-2026-10-30/receipt.json>)、[binding收据](<5-评测报告/L6独立复核-2026-10-30/binding-check-01.json>) 已通过当前原版 receipt_check。

对完整 [offline-work 原始收据](<5-评测报告/L6独立复核-2026-10-30/round-02/offline-work-receipt-01.json>) 直接递归做格式检查，首次 [receipt-check](<5-评测报告/L6独立复核-2026-10-30/receipt-check-01.json>) 明示失败，保留不重写：37 个标记来自嵌入的自测故意坏 hex 示例、历史检查器违规报告中的被截断 hex/UUID 片段，以及四个 check_doc 的诊断字段 live_doc_drift 是字典而非业务状态数组。它们是测试诊断原文，不是本轮状态声明的格式放宽许可，也不影响实跑断言本身。

新增 [offline-work-index](<5-评测报告/L6独立复核-2026-10-30/offline-work-index.json>) 只汇总129条判断、计数和原始收据完整SHA指针；**不是完整JSON等价视图，明确省略详细测试片段，但不删除或改写原载体**。全部细节仍可按链接重查；不借unicode转义、键重命名或修改helper去假装原诊断全格式通过。主报告所称零未解决差异限定于655个功能/证据核验谓词，不宣称故意坏示例的原载体通过格式检查。

```text
5-评测报告/L6独立复核-2026-10-30/offline-work-index.json · f3894aaf · 11787B · 2026-10-30T12:39:20+08:00
5-评测报告/L6独立复核-2026-10-30/round-02/offline-work-receipt-01.json · 3ea6dc74 · 68629B · 2026-10-30T12:39:20+08:00
5-评测报告/L6独立复核-2026-10-30/receipt-check-01.json · f26d5103 · 23649B · 2026-10-30T12:39:20+08:00
```

live_doc_drift=[]
