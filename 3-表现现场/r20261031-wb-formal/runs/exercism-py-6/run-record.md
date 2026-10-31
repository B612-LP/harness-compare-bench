# WorkBuddy · exercism-py-6 · 场级记录

公开证据为明确派生，非完整原始轨迹。产物原分与最终准入独立；原分不因判废而覆写。

```json
{
  "schema_version": 2,
  "run_id": "r20261031-wb-formal:workbuddy:exercism-py-6:e8cee56f-1072-4b73-8059-cb17e6e8ecdf",
  "case": "exercism-py-6",
  "spec_version": "exercism-py-6@sha256:7913a1ad769f1f9e002b5473375ea3ddf076bad152e2fed8f50c514ff3e2420c",
  "case_version": "exercism-py-6@sha256:7913a1ad769f1f9e002b5473375ea3ddf076bad152e2fed8f50c514ff3e2420c",
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
    "started_at": "2026-10-31T19:50:17+08:00",
    "duration_s": 162.0
  },
  "evidence_grade": "explicit-public-derived-trajectory+byte-identical-submissions;private-original-hash-bound",
  "status": "valid",
  "verdict_basis": "40次工具调用逐条审查均工作区内；六份实际冻结实现全文安全审查后在OS隔离执行原checker 6/6、100、reward1，官方测试未变。独立审查核对原-派生、manifest、score、route链相符；无本次外读或主动联网工具调用证据，不等于排除预训练记忆或全部底层网络。",
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
