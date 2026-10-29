# L4 首请求前独立设计评审

**结论：设计方向认可；R1/R2设计歧义已由首请求前澄清解除。这不是E实现验收、真实API放行或最终产品验收。**

执行封印代码的首次阻断与原始失败链见末节；后来v3修复的局部解除依据见[seal-preflight](<seal-preflight.md>)，实际E候选仍待另行审查。task-7保持in_progress。仅本目录为写界，不改builder/历史/CHANGELOG，不提交真实仓库git。未执行模型/API，未语义读取题库truth/solution或历史答案；冻结verify只机械读取原件字节核hash，不运行判卷器。

live_doc_drift: []。依据本次[旧合同只读verify收据](<old-contract-verification.json>)：v2/v3均exit0，v3返回空drift列表。该状态不外推为尚未完成的E实现无漂移。

## 一、观察：三项设计纠正已吸收

### 1. runner代际不等于生成spread的因果干预

[L1 RESULTS:96–103](<../可重复性-n3-2026-10-29/RESULTS.md#L96-L103>)披露：历史rep1与rep2/3使用两代runner，n=3只描述，不能估计代际因果贡献。代码中模型执行前/中可能生效的变化包括绝对workspace路径（进入prompt）、重启/重试策略与不同运行环境；归档staging修复、stdout记录保全、DSH耐久session重建完整流、usage提取、8位精度、integrity重扫和收据字段均属执行后测量处理。stdout展示截断不等于模型上下文截断。

原始依据：[旧runner任务与调用](<../../3-表现现场/r1030-formal-a1/tools/lab.py#L138-L148>)、[旧归档顺序](<../../3-表现现场/r1030-formal-a1/tools/lab.py#L303-L365>)、[新Codex执行/重试](<../../3-表现现场/r1031-variance-n3/tools-codex/lab.py#L476-L575>)、[新DSH重建说明](<../../3-表现现场/r1031-variance-n3/tools-dsh/lab.py#L293-L301>)与[新DSH执行](<../../3-表现现场/r1031-variance-n3/tools-dsh/lab.py#L688-L747>)。旧、新调用意图一致不能代替实际request/config/profile/build一致性证据；实际零重试也不表示两代重试代码相同。

最低可识别研究是同一固定产物/trace的独立副本经过旧/新后处理，比较证据留存、可判定率、usage投影与评分差异；它只识别测量效应。若研究执行层生成差异，须先锁定可操作差异、统一后处理，同产品/同任务/同route与build分层随机AB/BA时间块，独立fresh会话、每臂相同且预先固定n。历史rep1不能当随机对照；极差依赖样本量，不是总体方差，不据n小无差主张统计等效或贡献百分比。

[L4预注册:13–15、29–37](<../../1-评测方案/自动循环L4-2026-10-29/PREREGISTRATION.md#L13-L37>)正确将本轮限定为同证据双副本归档重放；当前CLI重复仅作诊断性描述，不包装为旧/新生成质量随机对照。cache探针区分missing/null/0，fresh不等于冷缓存、repeat不保证命中，不跨协议盲目相加或由usage推货币成本。旧pipeline无法原样复现须标equivalent_simulation并列适配diff，不伪称精确复现。

### 2. WB网关层必须独立于旧同模型合同

[WB README-r2:11–15](<../../1-评测方案/准入预检-2026-10-29/README-r2.md#L11-L15>)支持探针窗口的IP/DNS/静态与钩子互证，不是完整模型HTTP请求、直读模型面SNI或网关上游权重证明。本批不可用历史网关字段冒充实际观测。

[v2 config:3–15](<../../4-打分细则/可信冻结-2026-10-29-v2/config.json#L3-L15>)及[v3 config:3–15](<../../4-打分细则/可信冻结-2026-10-29-v3/config.json#L3-L15>)锁定官方host与alias，既定official_slots仅Codex/DSH十格。既有引擎还要求canonical slot/plan、valid裁定、五门、case/评分SHA、rule/time和无未排除混杂；不是换alias/组名即可通过。[v3继任语义](<../../4-打分细则/可信冻结-2026-10-29-v3/README.md#L5-L18>)保留v2历史合同及v3既定输出恒空，不通过加旧slot/改原表给WB追溯准入。

[L4预注册:7–9、17、39–43](<../../1-评测方案/自动循环L4-2026-10-29/PREREGISTRATION.md#L7-L43>)与[独立合同strata](<../../1-评测方案/自动循环L4-2026-10-29/contract.json#L135-L155>)已正确使用新命名空间、独立WB产品交付态，不进入既有A_same_model/B_native，不产生跨路由排名。

### 3. L3组件通过不等于生产准入门已接通

[L3 ACCEPTANCE:8、44、49–51](<../../1-评测方案/自动循环L3-2026-10-29/ACCEPTANCE.md#L8-L51>)同时声称门已就绪又保留U1与retro消费者纪律未知。正确解释仅为候选组件具备，实际集成与真实批次尚待验证；[SCHEMA:147–152](<../../1-评测方案/工具链/runner-schema-v2/SCHEMA.md#L147-L152>)明确该界限。

- [validator retro实现](<../../1-评测方案/工具链/runner-schema-v2/validate_runner_meta.py#L329-L398>)最终直接return0，不调用classify；summary非全量语义issues。无meta目录被跳过，重复run_id可覆写dict；null伴随diagnostic等issues未完整投影。--spec exit0也仅表示正反fixture与预期一致。
- 合法status/integrity枚举可包含失败/污染；浅层route/isolation/usage对象类型、SHA格式不证明路由、隔离、原始文件内容与有效准入为真。
- [reconcile实现](<../../1-评测方案/工具链/runner-schema-v2/validate_runner_meta.py#L451-L523>)仅检registered_at≥commit_time，不证明它等于所引用封印时刻，不证明commit包含该计划/runner/配置，也不把git可编辑时钟变成可信外部时间戳。

[L4预注册:45–53](<../../1-评测方案/自动循环L4-2026-10-29/PREREGISTRATION.md#L45-L53>)正确新增生产消费者：全集/唯一性、源SHA/bytes实算、实际配置/路由、证据与污染裁定、完整分母、精确E注册引用及D/E blob对账；多维状态不得压成一个exit0。

## 二、证据：R1/R2解除依据与R3/R4

[首请求前澄清1](<../../1-评测方案/自动循环L4-2026-10-29/CLARIFICATION-L4-1.md>)保持D三文件原字节，要求本澄清自身进入E，不是看结果后放宽规则。

- **R1设计层解除**：8–20行拆分全集slot accounting与formal；not_executed可无真实不存在的started/session/usage/score，不填零、不造空流；infra/transport不formal；真实达到预定时限的timeout可判完整分母限时产物，但仅全部证据/语义门通过才formal；正常低分不是拒收理由。合同required_original_evidence只约束正式行，失败组件记录仍保留。17槽完整但0正式、真实超时正例及缺证超时拒收均要求fixture覆盖。
- **R2设计层解除**：24–28行明确展示全称为历史指向网关而本批路由单列。当前产品build与原生declared_alias选择证据不可豁免；alias未知/错误停槽，不能冒充actual_request_model。本批actual_gateway可unknown但须标current_not_observed；白名单允许不可见上游/effort/内部工具skills未知并管理，不允许未知扩张成无trace/无隔离/污染未清/错分母/代码漂移豁免，不参与同模型因果比较。
- R3：32行plan.order是身份序，执行保持各产品投影序，跨产品可并行；cache全局串行，每槽调用登记先持久保存，记录共享资源与缓存竞争限制。
- R4：36–41行每槽单HTTP、禁止redirect/换body重试；401/403停止全部探针并通知未启动官方槽；429依4xx立即停该wire；5xx/网络超时连续两次停wire；fresh失败依赖repeat不发，nonce-control可独立而不作为配对；ASCII前缀及nonce/长度/wire映射在E锁定。
- 附加E锚：45行要求历史源commit/SHA/适配diff、模拟标记、精确E与D/E相同blob/祖先关系、可重建且不可覆盖binding/release。

## 三、解释：仅认可设计，不替Lead释放E

R1/R2不再是设计歧义阻断；实现仍必须证实相同真值表，尤其WB白名单unknown不能被结构validator误收/误拒，status/exit_code矛盾不得进入formal，超时与基础设施中断不可混同。E候选完整源码、配置、manifest闭包、真实U1与Lead明确release未验完前，不得执行任何模型请求。

## 四、未排除因素与当前执行封印阻断

### 已固定被测版本的首失败（不覆盖）

Lead开始修复前，已将原封印工具/自测复制至独立tmp，路径与源SHA见[快照收据](<seal-source-snapshot-v1.json>)。对真实仓库不执行manifest/bind，只在每次新建的synthetic临时git提交D/E，不涉及凭据、模型或题库内容。

[作者六项自测收据](<author-seal-selftest-v1.json>)exit0；[原创反例](<seal_adversarial.py>)的[首失败收据](<seal-adversarial-v1.json>)4检查中正例通过、以下3个应拒攻击均未拒，整体exit1：

1. **files集合为空**：修改manifest.files={}再提交synthetic E，D/E三设计文件不变，bind仍写released=true；不验证必需成员/非空/schema，自身runner/config等绑定可被省略。
2. **封后source换symlink**：把已封regular runner换为指向仓外相同字节文件的symlink，内容SHA相同仍过bind；需在bind/每次实际执行前重做regular、safe relative path、symlink及路径闭包检查，而非仅内容hash。
3. **遗漏澄清**：澄清根本未存在/未列manifest，bind仍成功；D设计与补充澄清的required set不应由manifest.files自己声明证明。

这不是模型失败，属于独立self_test发现的source/manifest绑定逃逸。已实时通知Lead并由其承诺按release blockers修复；我不代改其代码。**首次裁定：仍阻断E放行，须修复后独立重测，不以原作者6/6替代。** 后续已经按固定v3快照复验通过，见[局部解除与新收据](<seal-preflight.md>)；保留本节原失败事实，不据此代替尚待完成的E代码预审。

### 仍需E审查的停止条件

源/config/contract/manifest/路由漂移、无授权真实请求、答案/凭据泄漏、错误准入立即停止相关执行/主张；保留首失败、不可静默补跑。若旧后处理只能模拟、缓存字段语义不明、WB当前route不可见，按已冻结限制降级，不能改名包装因果成功。样本小、诊断选题、固定顺序、跨产品并行与服务端权重未知仍限制泛化。

## 五、可复现实验与分账

所有已执行命令只用于只读git、旧冻结verify及synthetic git自测：

```bash
/usr/bin/python3 -B /private/tmp/l4-seal-reviewed-v1-lsjnzwu2/test_execution_seal.py
/usr/bin/python3 -B '5-评测报告/L4首请求前评审-2026-10-29/seal_adversarial.py' \
  --source /private/tmp/l4-seal-reviewed-v1-lsjnzwu2/execution_seal.py \
  --out '<新的独立review收据路径>'
```

首失败收据不可覆盖；复测必须固定新源码快照与新输出名。tmp可能清理，故仓内收据保存源码hash、测试代码与具体可重建攻击方式，不承诺临时路径永久存在。self_test：作者一命令六断言，独立一命令四检查；offline_recompute：v2/v3各一次只读verify。product_run/bare_model_probe/model API均0，不把断言数当运行数。

## 脚本生成证据行

以下逐行粘贴evidence-kit打印输出，完整hash见各机器收据；不手填时间或SHA。

```text
1-评测方案/自动循环L4-2026-10-29/PREREGISTRATION.md · 5977c6e1 · 9732B · 2026-10-29T20:15:37+08:00
1-评测方案/自动循环L4-2026-10-29/plan.json · e8dfb73f · 17003B · 2026-10-29T20:15:37+08:00
1-评测方案/自动循环L4-2026-10-29/contract.json · 3a8a45ac · 11960B · 2026-10-29T20:15:37+08:00
1-评测方案/自动循环L4-2026-10-29/CLARIFICATION-L4-1.md · bc8546e0 · 6629B · 2026-10-29T20:15:37+08:00
1-评测方案/工具链/runner-schema-v2/validate_runner_meta.py · 8e423de5 · 31452B · 2026-10-29T20:15:37+08:00
5-评测报告/L4首请求前评审-2026-10-29/seal_adversarial.py · 8f90f6e6 · 5278B · 2026-10-29T20:15:37+08:00
5-评测报告/L4首请求前评审-2026-10-29/seal-source-snapshot-v1.json · bafa927c · 584B · 2026-10-29T20:15:37+08:00
5-评测报告/L4首请求前评审-2026-10-29/seal-adversarial-v1.json · f1971859 · 7294B · 2026-10-29T20:15:37+08:00
5-评测报告/L4首请求前评审-2026-10-29/old-contract-verification.json · 74064468 · 7276B · 2026-10-29T20:15:37+08:00
```
