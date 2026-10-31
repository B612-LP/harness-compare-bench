# WorkBuddy 独立网关产品轨冻结合同

规则 ID：`freeze-20261031-wb-v1`。本合同继任[第六代合同](<../可信冻结-2026-10-29-v6/README.md>)，仅登记 `W_gateway` 下 WorkBuddy 的五个新题槽位，不重评历史、不抬分、不重写原合同，不与 A/B 混排名。

## 评价范围

- `A_same_model`、`B_native` 的模型/官方路由限制与既有选择、分母、证据、污染、时间和准入规则不变。本代没有 A/B 新槽位。
- W 组仅允许 `workbuddy`。UI 选择事实固定为 `{"ui_label":"DeepSeek V4.1-Flash","ui_model_id":"deepseek-v4.1-flash","reasoning_effort":"low","attribution_scope":"ui_selection_only"}`；事实须有哈希与 JSON pointer 支持，不把 UI 标签当后端身份证明。
- 路由仍须披露 host/provider_id/wire_protocol/endpoint 且内部一致，非官方路由不直接阻止 W 产品整体评价。不得据此声称同模型控制成立。
- 每个 W 产品事件必须披露 `backend-model-unverified` 问题，`knowledge_status=unknown`、`confound_status=not_excluded`、`attribution_scope=same_model_attribution`、`unknown_fields=[]`，并保留影响、下一步、停止/重开条件及可复核引用。该精确问题仅限制同模型、后端身份与参数映射归因，不单独阻止产品轨。其他未排除因素仍阻止准入；不能以该 scope 豁免任何 FACT unknown、证据、污染或其他闸门。
- DAB2697 仍不得支持能力归因。未知不是零、不折算满分，缺失运行不是产品失败。

## 预注册与冻结

[批次计划](<../../1-评测方案/正式批次-2026-10-31-WB/registration-plan.json>) 的 `registrations` 必须包含且只包含五题的首次登记；每项精确字段为 `event_id,plan_id,slot_id,order,kind,parent_id,reason,registered_at`。`plan_id=r20261031-wb-formal`，`event_id=r20261031-wb-formal:workbuddy:<case>`，`slot_id=workbuddy|<case>`；`order=1,kind=first,parent_id=null,reason=fixed_first`。登记时间必须为实际带时区时间并早于产品开始时间。

事件沿用[事件 schema](<import-schema.json>)。`selection` 在计划条目基础上去掉 event_id、加上 `plan_source` 与 `plan_pointer=/registrations/N`，引用已封印计划。任何导入的正式产品批次须完整包含五条登记，不能只导入高分或成功结果；重复/重试/替代的既有队列校验仍保留，本计划不预授额外尝试。

[配置](<config.json>) 保存冻结时五题当前字节快照（固定题面、spec、case、truth、checker、可选 trusted_runner 与 inputs 全树）、实际冻结时钟、计划 SHA 和恰好五个 W canonical slots；不是历史题目版本证明。[锁文件](<freeze.lock.json>) 的 contract pins 绑定本代机制、schema、测试、说明、配置、计划、五题文件及所有本地实际读取依赖。锁本身不是独立可信时间戳，不能证明原始证据真实性，人工仍须审查来源语义和污染。

## 复核调用

在仓库根目录执行（仅离线校验，不运行模型、桌面或 checker）：

```bash
python3 -B -m unittest discover -s '4-打分细则/可信冻结-20261031-wb-v1' -p 'test*.py'
python3 -B '4-打分细则/可信冻结-20261031-wb-v1/freeze.py' build
python3 -B '4-打分细则/可信冻结-20261031-wb-v1/freeze.py' verify
# 实际产品证据完整后，build 与 verify 均显式传同一完整 --imports <公开相对路径>。
```

无 imports 的构建仅显示等待运行的空 W 表，绝不是五题已运行、已通过或已完成评分。生成物只允许写入本代[报告目录](<../../5-评测报告/可信冻结-20261031-wb-v1/summary.md>)，禁止 source-map。旧代产物不覆盖。测试使用合成证据，测试次数不得计作产品运行数。
