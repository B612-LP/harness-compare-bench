# 第三周可信冻结：可复跑档案与准入合同

> 公开隐私派生资料说明：本页标注的公开隐私派生 JSON 仅供公开阅读，不能替代原件封印验证；原件字段、SHA 与历史核验表述仍按原件及当时版本理解，不适用于派生文件。本次仅修订链接与隐私边界说明，不改变分数或历史裁定。

只读旧现场、旧账和题库；不调用模型、不执行历史提交、不读 home 私有目录、不改 Changelog。Python 3.9+，仅标准库。新机制实验可用同一入口导入，但研究变体不进入官方产品比较。

## 入口

在仓库根目录：

```sh
python3 -B 4-打分细则/可信冻结-2026-10-29/freeze.py verify
python3 -B 4-打分细则/可信冻结-2026-10-29/freeze.py build
python3 -B 4-打分细则/可信冻结-2026-10-29/test_freeze.py
# 可在纯公开 fresh copy 中重建到新目录：
python3 -B 4-打分细则/可信冻结-2026-10-29/freeze.py build --output-dir 5-评测报告/可信冻结-2026-10-29/rebuilt
# 导入真实新事件，不自动发现/重跑现场：
python3 -B 4-打分细则/可信冻结-2026-10-29/freeze.py build --imports PATH_TO_PUBLIC_IMPORT.json
```

`verify` 按产物中的构建配方自动重用导入列表，核导入文件 SHA、原账 SHA、每项公开源 SHA、事实 pointer 与原值、全部题目资产树以及确定性产物；退出码 0 才是成功，任何不符退出 2。不使用私有目录 fallback。`validate-import` 走同一套输入验证但不写产物。自测的断言数不是产品运行数。

当前原账基线为 HEAD `827988e557ec48da0fcfef28a2631aed7beaf66f`，96 条原行、326 条源引用；242 条公开源核对一致，84 条是 `bench-automation/` 私有来源引用，**不是“文件不存在”，也不是“公开证据已可复核”**。最新 WB sandbox 原 V/clean 与原 100 分完整保留，不回退为旧 suspect；但不能用其历史有效性替代新版所有准入字段。

## 产物

- [统一档案（公开隐私派生资料）](<../../5-评测报告/可信冻结-2026-10-29/archive.public-derived.json>)：96 行原件字段完整保留，归一事实与原始字段并列；原时间与收集时间分开。
- [逐字段／源审计（公开隐私派生资料）](<../../5-评测报告/可信冻结-2026-10-29/field-source-audit.public-derived.json>)：每行所有原字段叶子、原账 pointer、每条 supplied source 的原 SHA、实核 SHA、状态。未从批次名猜日期，不把缺失历史版本补成今天版本。
- [六类分账（公开隐私派生资料）](<../../5-评测报告/可信冻结-2026-10-29/six-ledgers.public-derived.json>)、[汇总与覆盖](<../../5-评测报告/可信冻结-2026-10-29/summary.json>)。
- [正式主表](<../../5-评测报告/可信冻结-2026-10-29/official-main-table.json>)：A/B 分区，无跨组排名，逐场拒绝理由；目前两组均 0。这是新标准证据不足，不是产品 0 分或历史数据损坏。
- [25格有限历史观察](<../../5-评测报告/可信冻结-2026-10-29/historical-25-cells.md>)及[机器明细](<../../5-评测报告/可信冻结-2026-10-29/historical-25-cells.json>)：全候选、不选最好；原分、归档版本复算、当前未执行复算分别列。完整原规则字段与评分收据 SHA 在机器明细；原 `main_table_eligible` 不作为新版裁定。
- [未知／局限登记](<../../5-评测报告/可信冻结-2026-10-29/unknown-limitations.json>)：知识状态、调查状态、混杂状态三轴独立。
- [构建配方](<../../5-评测报告/可信冻结-2026-10-29/build-recipe.json>)和[产物指纹](<../../5-评测报告/可信冻结-2026-10-29/output-manifest.json>)。

## 正式准入：缺任何一项即拒绝

1. **冻结规则**：精确规则版本、当前冻结后运行时间、唯一官方格的预注册计划／槽位／计划源 SHA，不能事后改 plan 再首跑。
2. **题面有效**：有出处的独立有效性裁定；题面／spec／case 元数据／完整 inputs／checker／truth／trusted runner 全部进入 canonical manifest；新增、删除、修改任何输入均导致漂移。题目版本是 `case_id@sha256:<manifest>`，不是随便填一个已知字符串。
3. **可复核评分**：有原始评分收据 SHA、精确 rule_version/checker SHA；必须完整评估；分母始终为全部约定项目，未知不能按已评部分折满或补二值裁定。
4. **有效证据**：有出处的证据有效性裁定，不等同路径存在或 JSON 能解析。
5. **无污染**：有出处的独立污染裁定；未扫描、扫描无命中、原 V/clean 都不自动升级。机器只检查来源和值绑定，**不替人证明语义无污染或因果已识别**。

全部 15 个事实槽：题目版本、产品版本、模型、路由、工具、权限、技能、开始／结束时间、证据等级、最终裁定、规则版本、checker SHA、truth SHA、完整题目 manifest SHA。历史原件中缺失的保持 unknown；当前配置 hash 只能说明本次收集／重建配置，不能证明历史使用了此配置。

路由事实 `route.value` 精确为 `{host,provider_id,wire_protocol,endpoint}` 对象；host 必须已知，后三项未知可为 null，已知 endpoint 必须 HTTPS 且 hostname 与 host 一致。A 组除模型 alias 以外必须有官方上游 host=`api.deepseek.com` 的出处；本地 provider_id 与 responses／Messages 协议路径完整披露但不要求相同。历史只有 endpoint 的保留为 raw partial，不冒认 provider／完整 route。**官方 host＋alias 仍不能证明服务端权重 build 一致**，这是明确未排除的服务端边界。

A 组只接受 Codex／DSH／WorkBuddy 的同模型事实，B 组元宝／豆包默认模型单独列；形态／权限等未同构不能跨组能力排序。`experiment=true`、research 分组、已知消融／GPT／skill／work01 来源均不能冒认官方产品。DAB2697 兼容分保留，**通过、失分及两轨差均不作能力归因**；[原裁定](<../裁定-2026-10-26-dab-q2697.md>)不重写。

## 固定选样，不按结果选

新正式格必须在冻结配置中绑定唯一 `group|product|case_id → {plan_id,slot_id,plan_sha256}`。本次 `official_slots` 为空：只建立新合同，**不倒填历史预注册，也不借本轮研究变体凑正式分**。

- 首跑：固定注册 order=1，不按分数排序。
- 替代：只允许前一个已明确 invalid/suspect、且理由为污染／题面无效／证据无效；下一注册事件明确 parent_id，整队最多替代 1 次，不能一直抽到成功。原行保留，不补 0，不把“分低”当替代理由。
- 重复：预先注册的全部事件必须导入，保留每场；不选最高分，也不替首跑。
- 异常重试：仅前一场已裁定 infrastructure_invalid，理由限 transport/startup/tool infrastructure，整个注册队列最多 1 次；重试仅诊断，不入 primary。
- 注册文档的同一计划 registrations 列表必须完整导入。漏掉已注册失败／重试、编号缺口、重复编号、跨产品／处理臂／用例队列均拒绝。技术预检尚未到模型阶段的事件必须记接口预检，不因计划最初写 product_run 就计产品运行。

## Schema 与后续导入

[导入 Schema](<import-schema.json>)与[配置 Schema](<config-schema.json>)为可读合同，**语义检查以验证器为准**；[完整例子](<import-example.json>)引用[合成示例源](<example-source.json>)，明确不是实际运行，默认不导入、不计数。事实包装：

```json
{"state":"known","value":"an exact JSON value","refs":[{"source":0,"pointer":"/path/in/public/source"}]}
```

- `known`：原来源中可读事实；并不表示当场已冻结。
- `supplemented`：事后补录来源；不得冒认当场快照。
- `unknown`：严格 null 与空 refs；必须被 issue 的 `unknown_fields` 数组逐路径覆盖（如 `facts.permissions`、`gates.rules_frozen`、`score`），否则导入即拒绝。可聚合管理，不必每槽一条。原字段仍在原件区保留，不改成 0、clean、成功。
- `identity` 也是事实：绑定 event_id、原始 run_id、category、product、group、experiment、case_id；不能只改顶层换产品／改研究身份，同一原始 run_id 不能换 event_id 再计一次。
- 已知事实的每个 pointer 必须解析，类型和值都必须与源相等；来源只允许仓内相对路径、禁止越界／符号链接出仓；不接受 hash 伪格式、重复 JSON key、NaN/Infinity。
- `score.value` 为 earned/possible/assessed/reported/reward/rule_version/checker_sha256；`reported=100×earned/possible`，评估不完整时 reward 必须 null。
- 每个 issue 必须有 impact、next_step、stop_condition、**reopen_condition**与 refs。`knowledge_status`=unknown/accepted_limitation/resolved；`investigation_status`=open/stopped/closed；`confound_status`=not_excluded/excluded/not_applicable。停止调查≠问题已解决，接受局限≠排除混杂；pointer 存在仅证明可定位，不证明论断成立。

## 六账口径与可信边界

产品运行／自测／离线复算／判卷回归／裸模型探针／接口预检互斥分账。原 96 行中 91 是带产品工具的执行（含探索／无效／研究），5 是裸模型基线；`exploratory-probe` 不是裸模型。历史工作账只登记 [registry](<work-registry.json>)列出的可定位调用／批次收据；一个五题回归是一件事，不是五个产品运行，31 行复算不是 31 新模型场。历史覆盖不完整，不能把全仓断言、文件数、脚本存在计运行。覆盖截止以后独立复核及再跑自测不循环回灌为“冻结前完整总数”。首轮路径规范化自测失败另补录，后续成功保留独立 raw 收据，未隐藏失败。

[冻结封条](<freeze.lock.json>)绑定代码、配置、schema、registry和政策来源；正式交付时须把封条 SHA 发布到外部可信收据。**SHA 封条不是数字签名**：若攻击者能同时改代码、配置、所有来源和封条，必须有独立保留的可信 SHA 才能识别，不能宣称本地可写 hash 文件能抗任意篡改。事实与语义审查、可信证据作者及人工裁定仍是明确的信任边界。
