# WorkBuddy · lcb-recent-hard-4 · 唯一替代场级记录

本场有明确首批判废前承；非无前承首次样本。TASK原字节和提示修订绑定见证据。原分与准入独立。

```json
{
  "schema_version": 2,
  "run_id": "r20261031-wb-replacement:workbuddy:lcb-recent-hard-4:b0f3ee40-f050-42c8-a940-c20ffacbe968",
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
    "started_at": "2026-10-31T20:27:17+08:00",
    "duration_s": 510.0
  },
  "evidence_grade": "explicit-public-derived-trajectory+byte-identical-submissions;private-original-hash-bound",
  "status": "valid",
  "verdict_basis": "运行负责方及独立证据复核确认：26工具调用与实际四份代码完整审查，冻结checker经代码安全审阅后在OS隔离实测4/4、100、reward1。原发送提示绑定、工作区封存、每行原派生与产物原字节、27task+1aux当前请求route链均通过，完整可用菜单来自本场捕获而非父场复用。原L89末尾git status/dev/null及L90无git状态或外部评测资产内容的结构性限制已披露：不把潜在祖先探测猜成实际越界，也不宣称系统调用级隔离/零隐性外读。 原L89 git status重定向至/dev/null，L90无git状态或外部评测资产内容；潜在祖先探测未被证明为实际越界，也不能据此宣称系统调用级隔离或零隐性外读。见adjudication.json extra_observations。",
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
