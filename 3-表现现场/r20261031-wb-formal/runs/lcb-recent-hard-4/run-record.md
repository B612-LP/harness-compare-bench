# WorkBuddy · lcb-recent-hard-4 · 场级记录

公开证据为明确派生，非完整原始轨迹。产物原分与最终准入独立；原分不因判废而覆写。

```json
{
  "schema_version": 2,
  "run_id": "r20261031-wb-formal:workbuddy:lcb-recent-hard-4:ae719f44-7334-4e7c-beb1-5b0d4613a022",
  "case": "lcb-recent-hard-4",
  "spec_version": "lcb-recent-hard-4@sha256:d53d6e9e318c7a84d2103c3c75828a25be67aac645ab027a7b11624941b14a65",
  "case_version": "lcb-recent-hard-4@sha256:d53d6e9e318c7a84d2103c3c75828a25be67aac645ab027a7b11624941b14a65",
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
    "started_at": "2026-10-31T19:52:59+08:00",
    "duration_s": 568.0
  },
  "evidence_grade": "explicit-public-derived-trajectory+byte-identical-submissions;private-original-hash-bound",
  "status": "invalid",
  "verdict_basis": "原始/派生L50写并读取/tmp/t387.txt、L51返回成功；L53删除外部文件、L54返回成功，独立复核确认。后续改用工作区_scratch不抵消违规，整场X。四份实际冻结代码审查后真实隔离checker 4/4、100、reward1原分保留，不准入。",
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
