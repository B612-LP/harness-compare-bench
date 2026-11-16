# 首条产品计数等值复核：探索后固定协议（2026-11-16）

## 研究问题与事后边界

回应[第四周反馈](<../../反馈/2026-11-11-第四轮/README.md>)：请求bytes与产品usage分列，实际思考/cache不能等控时保留混杂。在既有r1109的15个Codex主档里，首条product-reported input计数组内相等时，cache与reasoning计数是否也精确等值？只讨论这些产品记录，不把它认证成供应商原始usage、真实思考量、实际HTTP请求或服务端缓存行为。

这是**看过全部候选结果后固定的探索性复算协议**，不是盲前预注册、独立新样本或新产品运行。已知先验为五组首条input相等、cache/reason各0/5等值；406条usage及重复视图；11/15公开meta带其他槽前缀。冻结规则用于限制后续取值、失败分支及独立复算，不将发现伪装成确认性检验。旧累计/单次语义与日志无法认证发送切点的结论不是本次创新；不回填正式25格、旧门、分数或原件。

## 固定来源、单位与三个需求

- [SOURCES.json](<SOURCES.json>) SHA256 **09efcb05cd8fa8ba9fc7c3880f44c7f348ac0c9f06668b5f57bae39b178b6c72**：固定5题×r1/r2/r3共15槽。主档定位只用已钉定[v1.1投影](<../机制重复口径澄清-2026-11-12/evidence.json>)的同名槽identity，不另挑文件或读子代理档；其SHA为925470d3b55b4226d70f5749d45d0c65a161703c4053fa21028ce0516fcd6b5c。另固定15个CLI事件流SHA及15份公开meta路径/SHA，CLI是此次只读快照，不冒充历史封印。
- **需求1：可比单位与来源。** 原档逐事件四列投影/v1.1全部公开依赖硬等；本槽usage、token_count镜像、CLI终态逐项闭合；公开meta仅做作用域核查，不取其首行/总量冒充本槽。406记录与406镜像是同一记录的两种表示，不计812次模型调用，更不是独立trial数。
- **需求2：实际数值等值。** 每槽严格取原档次序第一条`token_usage_record.usage`，不取meta.per_call[0]、CLI终态或最大/最小值。主要两个终点为每组首条cached_input_tokens三元组是否全相等、reasoning_output_tokens三元组是否全相等；first input三元组等值并列描述。无容差、阈值调优、显著性、成本模型或预热因果。
- **需求3：未知与复核。** 身份、缺值、累计或终态任一关键门失败则相应组不可裁定（或整体硬失败），不能记为“不等值0/5”的有效分母；不排槽、不从别槽补值。公开只复算安全投影算术/封印；原档重建与独立实现才检查实际字段和作用域，仍不认证历史真实性。

## 六字段与固定检查

字段为`input_tokens`、`cached_input_tokens`、`cache_write_input_tokens`、`output_tokens`、`reasoning_output_tokens`、`total_tokens`。每条及原生累计必须显式包含全部六字段，值为非负int、拒bool/null/缺失/额外键；`total=input+output`、`cached≤input`、`reasoning≤output`。不将cached额外加到input或reasoning额外加到output，不将缺失补0；明确0与未知分列。JSON拒重复键及非有限数值。

1. 各槽原始response_id不能重复；turn_id与thread_id分别单一（身份仅私有逐值比较/安全hash与计数，不发原值）。按记录顺序各字段前缀和必须同时等于该记录turn_token_usage与thread_token_usage；若发现重置/多thread/算术冲突，不拼合修复。
2. 按原档次序把token_usage_record与event_msg/token_count一一配对，数量相同且后者行号在前者之后；last_token_usage逐字段等于本条usage，total_token_usage等于本槽累计。不能将镜像作为独立provider回执或完整请求清单。
3. 末条usage之后不得再有response_item；最后镜像之后必须有对应task_complete。每个CLI的唯一turn.completed必须在其末行，五个已有usage字段逐字段等于主档终态（CLI该面没有total，记录为不提供而非0）。这些门只检查已记录范围，不普查未记录重试。
4. 对两类usage事件完整根对象及嵌套schema报告source/origin/provider/estimated相关字段的出现路径（只结构键），不因未标估算断言非估算；也不因model_context_window数值认证真实服务端窗口。若出现来源字段，仅原样报告可观察字段，不据此认证供应商。

## 公开meta作用域（诊断，不修旧数据）

固定公共字段映射：cached_input_tokens对应cache_read_tokens，cache_write_input_tokens对应cache_creation_tokens，其余同名；不采用`or 0`或补默认。逐槽检查本槽六字段序列及response_id是否是meta.per_call精确后缀；cumulative_thread_final是否等于本槽终态；requests及汇总是否对应整个per_call列表。meta的聚合字段与本槽主档终态分开，不要求已知污染汇总假装本槽通过。

若有多列前缀，只在其**完整六字段序列和response_id均与某一其他固定槽精确相同且唯一**时标为已知槽前缀；否则UNKNOWN，不按近似计数猜身份。公开只发槽标签、布尔/hash、数值差和数量，不发ID。当前已知11份多列不改成15份纯净，也不覆盖旧meta；“meta列数”不计新trial/调用。仅定点说明本次实际检查到的报告/消费代码，代码本身不作历史执行证明，不扩大为全库结论受影响。

## 分支、分账与交付

- **支持不等值分支**：正确主档及所有关键门有效后，按两个首条三元组精确判等，若复核确认为0/5与0/5，可将本批边界细化为“产品记录中已观察到cache/reason计数不等值”；仍不能说实际thinking/cache已受控、provider已认证，或差异由模型/Harness/预热造成。
- **反对分支**：正确来源复算后等值，则撤回相应先验发现，保留来源错误/修订留痕；不更改规则迎合探索数值。
- **无法判断分支**：SHA/身份/字段/累计/终态硬门失败，相应等值终点未知而不是0；保留失败收据，不以更换槽或复制其他批次通过。
- **分账**：R3新增日志payload bytes、product-reported六字段计数、同槽真实请求bytes（当前未知）分别列示。首条input数值相同不证明消息字节/文本/服务端上下文同一；末态长度受执行路径混杂，只作覆盖描述，不与别批provider usage拼因果。

交付本协议/固定来源清单、内容脱敏evidence/result、只读verify.py、反例测试与实际EXECUTION-RECORD；完整JSON用`--output <独占新路径>`，stdout只摘要；原档重建用`--archive-root <r1109归档根>`。不执行任何归档命令或新产品调用，不泄露正文/cwd/ID/time/凭据/私有路径；路径逃根、修改封印与覆盖既有输出必须拒绝。作者自验与非作者独立实现、普通/-O、实际失败及公档能力边界分开记录。
