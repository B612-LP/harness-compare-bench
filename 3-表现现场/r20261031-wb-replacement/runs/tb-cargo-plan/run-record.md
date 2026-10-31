# WorkBuddy · tb-cargo-plan · 唯一替代场级记录

本场有明确首批判废前承；非无前承首次样本。TASK原字节和提示修订绑定见证据。原分与准入独立。

```json
{
  "schema_version": 2,
  "run_id": "r20261031-wb-replacement:workbuddy:tb-cargo-plan:a3202743-0604-47b7-ae54-2791939fca0e",
  "case": "tb-cargo-plan",
  "spec_version": "tb-cargo-plan@sha256:fa0165237440b614ec13bd196ae03135fdd43fecb2d40ab90442fe91a340a5c5",
  "case_version": "tb-cargo-plan@sha256:fa0165237440b614ec13bd196ae03135fdd43fecb2d40ab90442fe91a340a5c5",
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
    "started_at": "2026-10-31T20:35:48+08:00",
    "duration_s": 285.0
  },
  "evidence_grade": "explicit-public-derived-trajectory+byte-identical-submissions;private-original-hash-bound",
  "status": "valid",
  "verdict_basis": "运行负责方及独立证据复核确认：41工具调用及真实dispatcher/aircraft/navigation完整代码审查，无可见协议越界或主动联网调用；baseline仅输入大小/mtime，无答案。原冻结checker经代码审查后OS隔离实测20/27、74.07407407（checker74.07）、reward0，低分照录且不补跑。125行原派生链、原字节产物/冻结manifest、实际TASK/proof及37task+1aux本场route和完整工具菜单捕获均核对通过。",
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
