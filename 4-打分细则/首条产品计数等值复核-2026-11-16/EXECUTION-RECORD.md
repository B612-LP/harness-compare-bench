# 首条产品计数等值：实际探索后复算记录（2026-11-16）

## 身份、冻结与实际范围

按[冻结协议](<README.md>)与[固定来源](<SOURCES.json>)只读复建既有15个Codex主档、15个CLI事件流及15份公开meta；不执行轨迹命令、旧采集器或产品，不新增模型调用。全部候选数值及11份meta多槽前缀在冻结前已暴露，本次不是盲前预注册、独立新样本或因果试验。固定解释基线为`50c073c084006c0bfd5f8b79db3bc495e842847b`，不读取动态HEAD。

作者已实际运行普通/优化各109个测试，以及public/raw×普通/优化四路完整JSON输出；四个输出分别用真实`cmp`与本包[result.json](<result.json>)比较，均退出0。作者自验不是非作者独审，本页不宣称已发布或独审通过。内部执行位置不影响来源定位：执行时显式给`--root`；公开安装后的默认root为本文件同级Python文件的`Path(__file__).resolve().parents[2]`，测试可用测试专用环境变量显式选root。

## 需求1：本槽、重复视图与来源作用域

- 固定v1.1投影SHA为`925470d3b55b4226d70f5749d45d0c65a161703c4053fa21028ce0516fcd6b5c`，全部69个公开依赖硬等；15原档全文件SHA、主session身份及所有事件四列投影逐条硬等。没有从邻档、子代理档或另批补槽。
- **406条原生usage与406条token_count是同一记录的重复视图，不是812次调用，也不是406个独立trial。** 六字段逐条明确存在、非null、非负int（拒bool）；每条total=input+output、cached≤input、reasoning≤output；所有字段前缀和同时等于turn/thread累计，镜像last/total逐字段相等。每槽response身份不重复，turn/thread单一。
- 15槽最后usage之后均无response_item，最后镜像之后都有对应身份的task_complete。15个CLI唯一turn.completed均在末行，五个已有字段与原档终态相等；CLI的total为**不提供/null状态，不是0**。这些检查不普查未记录重试。
- 全406条的cache_write_input_tokens明确为0；其余五字段均406条非零。成功分母中缺失/null各0；缺失、null、bool等反例走硬失败，不静默补零。
- 两类usage事件的完整根对象和嵌套schema均已扫描source/origin/provider/estimated相关键路径，当前未观察到这些字段。只能称product-reported counters，不能据此认证非估算、provider来源或实际thinking/cache；model_context_window标签也不认证服务端窗口。

安全的逐事件行号、SHA、六字段、累计、两类事件schema与作用域投影见[evidence.json](<evidence.json>)；公开投影不含原ID、时间、cwd、原文或rollout路径。

### 公开meta不是本槽汇总

前置探索的初始同槽计数门实际失败为`ValueError: public usage count mismatch`，不能隐去或改称原15份汇总全部同槽通过。本次分别检查完整列表、本槽后缀与本槽终态：

- **4/15**份仅本槽，**11/15**份多列某一其他固定槽的完整前缀；702列中多列296，不能计新trial/调用。
- 15份本槽后缀均以**完整六字段序列与response_id原值**逐项相等；11个前缀也仅在这两者与唯一其他固定槽完整相等时识别，当前未知前缀0。公开仅输出ID的SHA、槽标签和布尔/数值；原值比较仅在原档重建时进行。
- 15份cumulative_thread_final等于本槽终态；各份requests/汇总等于其整个per_call列表。11份汇总因此不是单槽总量；没有覆盖或修补旧meta，也不从meta第一行取本次首条终点。

定点只读核查：[旧采集器:278–331](<../../3-表现现场/r1109-mech-n3/tools/lab-codex.py#L278-L331>)遍历目录JSONL并对缺失字段用`or 0`，其[572–619行](<../../3-表现现场/r1109-mech-n3/tools/lab-codex.py#L572-L619>)消费usage并输出摘要；没有执行它，代码本身不证明历史执行过程。另读[v1.1消费段:252–298](<../机制重复口径澄清-2026-11-12/verify.py#L252-L298>)及[R3来源分解:139–165](<../R3不稳定来源分解-2026-11-16/verify.py#L139-L165>)：所查段落的R3/R4来自原档投影/单档aggregate，不用上述meta usage汇总计算这些机制字节。本次不据此声称全库报告均未受影响，未改旧门/分数。

## 需求2：严格首条、两个等值终点

每槽只取本主档次序第一条token_usage_record.usage；以下向量按r1/r2/r3，单位都是产品记录计数。

| 题组 | first input | first cached input | first reasoning output |
|---|---|---|---|
| bird | 9567 / 9567 / 9567 | 3584 / 9344 / 9344 | 9 / 8 / 46 |
| dabstep | 9319 / 9319 / 9319 | 7808 / 9088 / 9088 | 15 / 31 / 42 |
| exercism | 8923 / 8923 / 8923 | 7808 / 8704 / 8704 | 53 / 97 / 68 |
| lcb | 9033 / 9033 / 9033 | 7808 / 8832 / 8832 | 40 / 9 / 51 |
| tb | 8809 / 8809 / 8809 | 7808 / 8576 / 8576 | 13 / 30 / 24 |

首条input等值为5/5；两个主要等值终点cache与reasoning均**0/5等值、5/5不等值、0未知**。这把本批边界细化为“产品记录中已观察到计数不等值”，不是只有“未证明等值”。不等值不能归因为模型、Harness、预热或成本；input计数相等也不证明字节、文本或后端上下文同一。

## 需求3：未知、分账与可复核能力

身份/字段/累计/终态硬门失败时整体退出2，不写成功终点；反例另验证无效组为UNKNOWN、从有效分母剔除但保留固定5组，不转成“不等值0/5”。原件来源或scope不能唯一确定时保留UNKNOWN，禁止近似匹配或换槽。

R3的1,578个response_item合计**4,325,070 B日志payload**、产品报告六字段、实际请求bytes三面分列；实际请求bytes为UNKNOWN/null，不能以bytes推token/成本。终态全程长度受路径混杂，只作覆盖，不替代首条终点。

公开算术复算（在本包目录，目标必须不存在）：

```sh
python3 -B verify.py --root ../.. --output ./replay-public-new.json
python3 -B -O verify.py --root ../.. --output ./replay-public-optimized-new.json
python3 -B test_verify.py
python3 -B -O test_verify.py
```

有原档时额外完整重建并与已封证据比较：

```sh
python3 -B verify.py --root ../.. --archive-root "${ARCHIVE_ROOT:?}" --output ./replay-raw-new.json
```

完整结果仅写`--output`，stdout只摘要；JSON重复键/非有限数值、bool计数、输入逃根、输出覆盖与符号链接逃逸均拒绝。109个测试覆盖缺失/null/零、累计重置、重复身份、镜像错配/缺漏、尾部遗漏、CLI缺字段、meta错误后缀/汇总、多槽前缀、未知分支、normal/-O与隐私白名单。原档复建核实际关系；公开复算仅核封印和安全投影算术；两者都不能认证历史真实性、供应商原始usage或实际HTTPattempt。
