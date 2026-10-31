# WorkBuddy · bird-ca-schools-15 · 场级记录

公开证据为明确派生，非完整原始轨迹。产物原分与最终准入独立；原分不因判废而覆写。

```json
{
  "schema_version": 2,
  "run_id": "r20261031-wb-formal:workbuddy:bird-ca-schools-15:c386cc34-c206-4496-92f4-2069ec5b8c52",
  "case": "bird-ca-schools-15",
  "spec_version": "bird-ca-schools-15@sha256:4ea5ee92db986ba556ff876f9646310e9d7a1659bcc96ce10b9e04c6e35bdf8c",
  "case_version": "bird-ca-schools-15@sha256:4ea5ee92db986ba556ff876f9646310e9d7a1659bcc96ce10b9e04c6e35bdf8c",
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
    "started_at": "2026-10-31T19:45:14+08:00",
    "duration_s": 92.0
  },
  "evidence_grade": "explicit-public-derived-trajectory+byte-identical-submissions;private-original-hash-bound",
  "status": "valid",
  "verdict_basis": "逐条审阅10次工具调用及返回均局限工作区；.baseline.json仅输入大小/mtime不含答案。冻结产物与输入哈希核验、真实隔离checker 15/15、reward1。独立来源复核确认可见行为有效；原生推理自述回忆gold完整保留，不证明外读，预训练记忆仍不能排除，不作泛化因果归因。",
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
