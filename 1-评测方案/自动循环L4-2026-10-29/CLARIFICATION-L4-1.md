# L4 首请求前澄清 1：准入真值表、WB未知与调度/失败规则

- 生成时刻（脚本实钟）：2026-10-29T20:06:03+08:00。
- 权威关系：补充设计封印 D 的歧义，原 PREREGISTRATION/plan/contract 字节不改；本文件须提交并纳入 E。来源：independent-reviewer 对 D 的首请求前评审 R1–R4。无真实模型/API请求已执行，非事后豁免。

## R1：全集记账与正式准入是两种判定

每个 product slot 恰有一条 slot-accounting 记录：`executed`、`partial`、`not_executed`。三者皆须含计划 slot/run/event 身份、D/E引用、理由及相关证据定位；accounting_complete 只判全集/唯一性/声明真实性，不等于 formal_admission。

| 执行状态 | 必要证据 | 分数 | formal_admission |
|---|---|---|---|
| not_executed（从未外发） | 身份/封印/原因/停止来源；可无 started_at、session、usage、score | null，不虚填0 | false；诊断记录完整仍可 accounting_complete=true |
| infrastructure error / transport-error | 首次启动/请求及可得原始流、错误诊断，失败部分不可虚构；若session未建立须明确 | checker如可运行可记录诊断性分数，但不作正式产品分数 | false，不按能力失败记零 |
| timeout（真实开始，达到事先题目时限） | 原始启动/停止时钟、完整已发生trace/流、prompt/input/配置、隔离、冻结checker完整分母评分及独立无污染裁定 | 可判的限时产物真实分数，未完成任务按冻结checker处理，不另行折算 | 仅在全部证据/语义门通过时可 true，明确 timed_out=true；不与基础设施中断混同 |
| status=ok（含产品正常结束但题目未做好） | 全执行证据+原始文件 SHA/bytes+冻结全分母收据+独立无污染裁定+字段/注册/配置检查 | checker原值 | 以上门全部通过才 true；能力低分不是拒收理由 |
| 污染/配置漂移/证据缺失/无法管理的未知 | 首次证据和诊断保留 | 如有评分仅列diagnostic | false，不删槽/替换 |

L3 validate_meta 不支持 not_executed/某些不完整诊断记录，故只对已执行、字段有真值的 meta 走该组件。组件失败须保留诊断，不制造空流或假的起止时刻填齐。contract.admission.required_original_evidence 解释为正式准入的必要证据集合，不要求未执行槽位虚造。

严格准入门真值：`formal_admission = executed_or_genuine_timeout AND field_compliance AND seal_plan_integrity AND source_hash_integrity AND allowed_actual_configuration AND evidence_complete AND contamination_cleared AND full_denominator_score_valid`。完整记账另算。两者必须在合成fixture覆盖：17/17有记录但0正式准入，以及真实超时可评分/证据缺失超时拒收。

## R2：WB 产品交付态允许的未知（首请求前固定）

- 表的层名仍为 plan.stratum=`wb_gateway_delivery`，展示全称必须是“WB 产品交付态（历史证据指向网关；本批路由状态单列）”。这不是本批网关已验证或同权重声明。
- 正式 WB 行必须有本批 app版本/asar哈希、当前产品原生可观察的 `declared_alias=deepseek-v4.1-flash` 选择证据（如原生会话模型字段/驱动模型列表与选择回执，指向具体原始记录），以及首次执行trace。alias不可观察、选择失败或变成其他alias：停该slot，只有诊断，不用旧r2字段冒充本批选择。不得把declared_alias写成actual_request_model。
- 本批 `actual_gateway` 可为 unknown（非干扰取证无法观察时），必须附 `route_verification=current_not_observed` 与 r2 历史依据路径；若有本批网络证据则如实列观察方法及边界。contract.strata.gateway=www.workbuddy.cn 是历史预期/佐证，不自动成为本批事实。
- 可管理且不阻断“产品交付态”描述准入的未知白名单：网关服务端上游模型权重/供应商、本批无法被动观察的网关主机、effort具体档位、产品不可见的内部工具/skills开关。每项逐场/批次列影响、下一步、停止条件；不能因此参与同模型或同路由因果比较。
- 不允许豁免：当前产品build未知、declared_alias未知或错、workspace/输入不明、无原始trace、无法裁定污染、评分分母不完整、E代码配置漂移。可见工具行为仍以trace审计，不把内部不可见当作越界无须审计。

## R3：序号与并行

product_slots.order 是计划身份序；执行时每个产品保持其投影子序列，Codex/DSH/WB 可跨产品并行。cache probes 按 probe_slots.order 全局串行，且每槽最多一次外发。实际跨产品重叠时刻需保留；共享机器/账号缓存竞争是限制，不宣称随机化或完全控制。运行开始前每个独立slot的调用登记必须先持久保存，避免进程故障后因无结果文件而补发。

## R4：探针失败分类（优先级固定）

1. 每槽最多一次HTTP请求；不自动跟随redirect，不换endpoint/body/effort再试，不借其他slot额度补跑。
2. 401/403：凭据/权限问题，停止全部cache探针，余槽not_executed；立即通知其他产品执行者停止尚未启动的新官方API槽位并保留已运行证据，不换key补跑。
3. 其他4xx（含429）、3xx、请求/响应格式错误、协议不支持：立即停该协议，其后槽位not_executed；429不另按service连续计数，避免两种规则冲突。
4. 5xx、socket/TLS/timeout：该槽消费并记失败；连续两次真实外发的网络/服务失败停该协议，不在本槽重试。成功外发响应清连续计数。
5. fresh没有成功原始响应时，同block repeat因依赖失败标not_executed（不发）；nonce-control仍可在该协议未触发停止时执行，但不标paired warmness对照。不可用的pair不得进入缓存命中变化比较。
6. 生成器固定synthetic ASCII prefix目标约8192字符，上限16384 UTF-8字节，首nonce取D完整hash+protocol+block的确定性哈希；fresh/repeat正文逐字节一致，control仅换首nonce。wire body与low/256映射和源码 SHA 全纳入 E；不保证对应token数或缓存状态。

## E 与母本附加锚

双归档投影锁定历史源文件路径、完整源commit、SHA、适配diff与母本输入映射；模拟必须标 equivalent_simulation，不能冒充精确复现。release/binding 是 E 后按源码可重建的不可覆盖新收据，含完整 E ID/真实git时刻、D/E blob等值与祖先关系；不以自引用不可能为由省略校验。git时刻不是外部可信时间戳。
