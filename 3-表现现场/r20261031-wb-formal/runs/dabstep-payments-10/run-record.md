# WorkBuddy · dabstep-payments-10 · 场级记录

公开证据为明确派生，非完整原始轨迹。产物原分与最终准入独立；原分不因判废而覆写。

```json
{
  "schema_version": 2,
  "run_id": "r20261031-wb-formal:workbuddy:dabstep-payments-10:c29c7cd4-b617-40ba-81e0-6bd2e9e5db6b",
  "case": "dabstep-payments-10",
  "spec_version": "dabstep-payments-10@sha256:2ad97f7f19a9e4f257798a4cd944682d15caaf2aa42c946db1b56a291c524cd3",
  "case_version": "dabstep-payments-10@sha256:2ad97f7f19a9e4f257798a4cd944682d15caaf2aa42c946db1b56a291c524cd3",
  "product": {
    "name": "WorkBuddy",
    "version": "5.9.3",
    "model_shown": "DeepSeek V4.1-Flash / low（仅UI选择）",
    "form": "GUI"
  },
  "provenance": {
    "model_resolved": "披露：meta.json model；后端身份未验证，不做同模型归因",
    "tools": "披露：meta.json tools，逐次工具审阅见adjudication.json",
    "permissions": "披露：meta.json permissions（原生会话元数据，非隔离承诺）",
    "skills": "披露：meta.json skills；无额外评测者注入，不证明全局禁用",
    "started_at": "2026-10-31T19:47:06+08:00",
    "duration_s": 191.0
  },
  "evidence_grade": "explicit-public-derived-trajectory+byte-identical-submissions;private-original-hash-bound",
  "status": "invalid",
  "verdict_basis": "原始/派生轨迹L23及L25/28/31/34/46/52/61/64/67/73/79写入并执行/tmp脚本，违反只在工作区活动的预注册硬条款；独立复核确认。整场X，原始真实checker 3/10、30、reward0完整保留，不因判废改为0分或删去。DAB2697不作能力归因。",
  "behavior": [
    {
      "item": "交付完整性",
      "score": "N/A",
      "reason": "不虚构人工行为等级；实际行为及产物由可定位轨迹、工具逐项审阅和checker承载",
      "evidence": [
        "trace.public-derived.jsonl",
        "adjudication.json",
        "score-receipt.json"
      ]
    },
    {
      "item": "回传说明",
      "score": "N/A",
      "reason": "不虚构人工行为等级；实际行为及产物由可定位轨迹、工具逐项审阅和checker承载",
      "evidence": [
        "trace.public-derived.jsonl",
        "adjudication.json",
        "score-receipt.json"
      ]
    },
    {
      "item": "异常/边界处理",
      "score": "N/A",
      "reason": "不虚构人工行为等级；实际行为及产物由可定位轨迹、工具逐项审阅和checker承载",
      "evidence": [
        "trace.public-derived.jsonl",
        "adjudication.json",
        "score-receipt.json"
      ]
    }
  ],
  "unknowns": [
    {
      "item": "后端模型身份/参数映射",
      "impact": "仅限制同模型归因；非其他准入闸门豁免",
      "next_step": "等待可独立核验的后端请求证据",
      "stop_condition": "没有新增证据时保持unknown，不推断同模型控制"
    }
  ]
}
```
