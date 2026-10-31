# WorkBuddy · dabstep-payments-10 · 唯一替代场级记录

本场有明确首批判废前承；非无前承首次样本。TASK原字节和提示修订绑定见证据。原分与准入独立。

```json
{
  "schema_version": 2,
  "run_id": "r20261031-wb-replacement:workbuddy:dabstep-payments-10:f4d812a3-7714-4ff9-8977-6163f2e7a02d",
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
    "started_at": "2026-10-31T20:24:29+08:00",
    "duration_s": 167.0
  },
  "evidence_grade": "explicit-public-derived-trajectory+byte-identical-submissions;private-original-hash-bound",
  "status": "valid",
  "verdict_basis": "运行负责方及独立证据复核确认：23调用完整审查，无可见协议越界或主动联网请求；输入完整且原冻结checker实测6/10、60、reward0，低分照录且无追加尝试。原字节TASK与发送proof/公开预注册prompt一致，默认私人identity注入逐字哈希及结构已核。完整可用工具菜单未捕获，仅限制精确工具控制归因，不拿父名单填补；实际调用仍完整。q2697的字段/覆盖/聚合三重歧义未解、金标未唯一复现；not_applicable仅针对能否按冻结official-compat契约记录描述性产品原分，不代表能力有效或排除混杂；完整10题分母及双轨分照录、禁止q2697能力归因。",
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
    },
    {
      "item": "完整可用工具菜单未捕获",
      "impact": "仅限制完整菜单精确控制及其因果归因；不影响已完整保留的实际工具调用事实与冻结checker量尺计算。available_tool_names=null、capture_status=not_captured，不称已排除。",
      "next_step": "仅检查同一会话现有日志或既有产品导出，不用父场名单回填，不为此新发探针或改产品设置。",
      "stop_condition": "本批没有新增现有证据即保持未捕获；不得通过新探针或猜测凑齐菜单。"
    }
  ]
}
```
