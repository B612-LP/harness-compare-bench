# 工具输出保留预算：真实上下文机制闭环

研究诊断，非正式产品排名。DSH CLI 0.2.0-rc.2，既有官方路由 deepseek-flash（本机catalog名称DeepSeek-V41-Flash），low。2026-10-29 01:06–01:10 Asia/Shanghai，实际6场/12次HTTP200；输入总量含缓存46081 tokens；6场均正确提取两端观测值。

## 观察

单改原生 `spill-policy.maxInlineTokens`，12500→512；固定工具、prompt、权限、model/low和输出。大输出原文35767字节，bounded场实际下一请求仅保留1981字节两端与恢复路径。full场保留全文。所有首请求完整JSON一致。

|固定顺序|规模/臂|第二调用input_tokens|cache_read_input_tokens|总输入（含缓存）|原始SSE|
|---|---|---:|---:|---:|---|
|1|large/full|19313|384|19697|缺失；持久化stream补证|
|2|large/bounded|1125|384|1509|有|
|3|large/bounded|724|768|1492|有|
|4|large/full|241|19456|19697|有|
|5|small/full|248|256|504|有|
|6|small/bounded|140|384|524|有|

cache_creation_input_tokens均0。总输入=input_tokens+cache_read_input_tokens+cache_creation_input_tokens，保持原字段分列；这里不把未缓存量误作全部输入，不推导货币成本。

## 证据

- [原始证据与离线分析](<../../3-表现现场/r20261029-mechanism/analysis.json>)：六场独立ID/时间、实际request、HTTP状态、raw SSE或标明降级的durable stream、完整stdout/stderr、退出码、原始工具输出与hash、每场profile、source freeze校验。
- [预注册](<PREREGISTRATION.md>)和[初始化修正v2](<AMENDMENT-v2.md>)、[零网络验收v3](<AMENDMENT-v3.md>)、[仅修流取证v4](<AMENDMENT-v4.md>)均在各自后续调用之前冻结。v1、v2在真实发送前失败/拦截，0 API；原源码与原收据不改。v3首场真实完成但observer未flush，原始SSE丢失，保留不重跑，v4只续原计划5场。全部4版冻结源码hash仍匹配。
- [恢复文件事后收据](<../../3-表现现场/r20261029-mechanism/spill-recovery-posthoc.json>)：从两bounded场真实request定位原生系统临时文件，事后仍存在、可读，公有完整副本35767字节，SHA-256均为`fed57592028c9d8a9180c2b97f74a3cd5e0daa841aab244cf4aad78fe44626a2`，与原始工具输出相同。原runner只查home/spill而漏系统tmp，故原meta空数组不代表没spill；不改写原meta，另收据补录。

## 解释

第二交叉对（第3/4场）最强：实际第一请求相同；实际第二请求在只归一动态tool ID/signature后，唯一差异是tool_result文本。对应总输入19697→1492，减少18205 tokens。完整输出不变、原生预算配置改变、原生spill标记和完整恢复文件同hash、实际服务端usage共同构成干预链；不是历史总账算术拆分，也不是mock模型比较。

第一对19697→1509（差18188）同时有首调thinking文本差异与raw SSE缺口，不能把全部差值逐token都归因spill。小输出负对照工具结果完全相同、不spill，第二请求只差模型自行生成的thinking，总输入504→524（差−20）；它排除了“改阈值会无条件改工具内容”的解释，也展示了独立发射的随机性。六场均保留，没有按最好pair选样。

## 未排除因素

- n=2大输出配对+1小输出负对照，只支持本固定输入的机制存在性，不支持通用任务质量提升或产品优劣。题目故意把目标放头尾，正确率相同不是对中间信息任务的保证。
- 独立首调的thinking/signature与cache命中不同。pair1和small不是逐字单变量prefix；pair2仅在声明的动态字段归一后匹配。不能推断相同比例金钱节省。
- 首场无原始SSE，response model由adapter持久化来源补证，证据等级低于其余5场；不伪造或重跑填齐。实际响应仅给模型别名，不能据此证明后端权重build完全不变。
- 共同只提供fixture_output，没有read/bash；原生spill文件存在不等于模型已恢复读取，更不能说DSH天然恢复能力下降。恢复文件验证是事后补录，不是原预注册的during-run观测。
- 请求只截body，不截任何headers；HOME/workspace路径脱敏；保留原生opaque系统临时文件路径与模型thinking signature以审计，不含凭据值。未读取或复制认证文件、未改登录态/全局配置、未使用browser、未向agent暴露truth/solution。

停止条件已满足：原计划六场全部完成，没有继续追加API。以上局限只能由新证据重开：原始首场SSE、能恢复随机prefix的预注册反事实试验、更大独立任务样本、或原生read可用的恢复实验；不能把未知默认为失败或满分。

## 可复现实验

[原创全新六场复现入口](<run_reproduction.py>)是后验整理的干净入口，未再发API；使用逐chunk observer，与实际v4请求前后逻辑相同，不包含私有自动化驱动。原始实际版本均保留，不用复现入口冒充历史冻结源。

```bash
python3 '1-评测方案/机制实验-2026-10-29/run_reproduction.py' \
  --workspace "$HOME/bench-workspaces/r20261029-mechanism-new" \
  --evidence '3-表现现场/r20261029-mechanism-new' \
  --credential-store "$HOME/.dsh/.credentials.yaml"
# 上一命令是真实API，需预配认证；--preflight-only只做零API配置预检。
python3 '1-评测方案/机制实验-2026-10-29/analyze.py' --verify
# 或 --output /tmp/mechanism-analysis-new.json：新文件独占写入，不覆盖原分析收据。
```

[离线分析器](<analyze.py>)不发API，直接复算历史六场；[事后恢复检查器](<recover_spill.py>)只检查request明确给出的本实验spill文件，文件消失即报告缺失，不搜索其他临时文件。纯接口预检与真实模型产品运行分账；全部研究运行排除正式比较表。
