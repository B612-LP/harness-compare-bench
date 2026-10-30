#!/usr/bin/env python3
"""New concise index to raw test diagnostics. Not an equivalence rewrite of raw receipt.
Retain intentionally invalid test strings and old/new verifier failure diagnostics in raw.
"""
import hashlib,importlib.util,json
from pathlib import Path
from datetime import datetime
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
raw=OUT/'round-02/offline-work-receipt-01.json';obj=json.loads(raw.read_text())
index={'kind':'offline-execution-index-not-full-diagnostic-replacement','at':datetime.now().astimezone().isoformat(timespec='seconds'),'raw_receipt':{'path':str(raw.relative_to(ROOT)),'sha256':hashlib.sha256(raw.read_bytes()).hexdigest(),'bytes':raw.stat().st_size},'counts':obj['counts'],'checks':[{'name':c['name'],'pass':c['pass']} for c in obj['checks']],'gate_negative_count':len(obj['gate_negatives']),'gate_negative_rejected':sum(c['rejected'] for c in obj['gate_negatives']),'real_score_recompute':obj['real_score_recompute'],'raw_kept_unchanged':True,'not_full_equivalence_claim':True,'omitted_detail_groups':['intentional bad-hex test fixture excerpts','historical old/new check_doc diagnostics (including nested live_doc_drift report objects)','full raw pre/post checker output objects and operation list'],'all_omitted_details_accessible_in_raw':True,'live_doc_drift':[]}
with (OUT/'offline-work-index.json').open('x',encoding='utf-8') as f:json.dump(index,f,ensure_ascii=False,indent=2);f.write('\n')
spec=importlib.util.spec_from_file_location('ek',ROOT/'1-评测方案/工具链/evidence-kit/evidence_line.py');ek=importlib.util.module_from_spec(spec);spec.loader.exec_module(ek)
rows=ek.gather([str(OUT/'offline-work-index.json'),str(raw),str(OUT/'receipt-check-01.json')],ROOT,ek.now_local())
text='''# 测试诊断载体规范说明（不改原件）

主 [README](<5-评测报告/L6独立复核-2026-10-30/README.md>)、[receipt](<5-评测报告/L6独立复核-2026-10-30/receipt.json>)、[binding收据](<5-评测报告/L6独立复核-2026-10-30/binding-check-01.json>) 已通过当前原版 receipt_check。

对完整 [offline-work 原始收据](<5-评测报告/L6独立复核-2026-10-30/round-02/offline-work-receipt-01.json>) 直接递归做格式检查，首次 [receipt-check](<5-评测报告/L6独立复核-2026-10-30/receipt-check-01.json>) 明示失败，保留不重写：37 个标记来自嵌入的自测故意坏 hex 示例、历史检查器违规报告中的被截断 hex/UUID 片段，以及四个 check_doc 的诊断字段 live_doc_drift 是字典而非业务状态数组。它们是测试诊断原文，不是本轮状态声明的格式放宽许可，也不影响实跑断言本身。

新增 [offline-work-index](<5-评测报告/L6独立复核-2026-10-30/offline-work-index.json>) 只汇总129条判断、计数和原始收据完整SHA指针；**不是完整JSON等价视图，明确省略详细测试片段，但不删除或改写原载体**。全部细节仍可按链接重查；不借unicode转义、键重命名或修改helper去假装原诊断全格式通过。主报告所称零未解决差异限定于655个功能/证据核验谓词，不宣称故意坏示例的原载体通过格式检查。

```text
'''+ '\n'.join(r['line'] for r in rows)+'''\n```

live_doc_drift=[]
'''
with (OUT/'diagnostic-format-note.md').open('x',encoding='utf-8') as f:f.write(text)
print(json.dumps({'index_checks':len(index['checks']),'raw_unchanged':True},ensure_ascii=False))
