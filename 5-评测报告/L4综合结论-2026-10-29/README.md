# L4 综合结论（2026-10-29 批次）

- 撰写：judge（独立验收方）；写界仅本文件。时间一律读自收据/程序生成数据，非手写。
- 数据基座：observations-final.json（program 生成于 2026-10-30T00:25:55+08:00）；judge 终验 17 行收据（judge-final-ebbbb696cc2fbd70f410fae184d6bd5f274db0cabaa809214ee78b9fd2cfc061.json，sha256_16 ebbbb696cc2fbd70）；auditor 对抗性盲审 AUDIT.md；reviewer task10 六槽报告。全部引用文件撰写前经程序存在性校验。

## 一、观察

计划产品槽 17：**执行 16、未执行 1**（counts 见 observations-final.json）；canonical formal **0/17**；probe HTTP 记录 18、fresh-repeat pair **6**。未执行槽 = WB bird-ca-schools-15-r1（notexecuted.json 记录 at 2026-10-29T23:35:14，reason=startup-render-not-ready：CDP 9332 已起但 page target 未就绪，发送前失败，零会话/trace/usage）。执行 16 槽 canonical accounting 全 partial；producer 侧 formal_eligible 局部 flag 不构成准入。observed 分数：codex dab 70.0×3、cargo 70.37037037×3；DSH dab 70/80/70、cargo 70.37037037/74.07407407/74.07407407；WB dab 50.0、exercism 100.0、lcb 100.0、cargo 70.37（raw 两位精度，canonical 19/27=70.37037037 数值一致）。三产品别名/型号证据：WB 四槽 DB 实证 deepseek-v4.1-flash，上游 actual_request_model 缺省（managed unknown）。

## 二、证据

全部行级证据见 judge-final-ebbbb696cc2fbd70f410fae184d6bd5f274db0cabaa809214ee78b9fd2cfc061.json（source-snapshots 快照内嵌）与 observations-final.json（17 product_records 各含 canonical_fails 原文、contract_denominator、judge payload 计数）。要点：
1. **缓存 6 对**（18 probe 全 200、每槽恰 1 次 HTTP、write-once intent；逐字节同体、nonce=sha256(D:proto:block)[:16] 确定性、间隔 6–7s≥5s）：三 wire×2 repeat 的 read 阳性均为 2048——responses=usage.input_tokens_details.cached_tokens（fresh/control=0）、messages=cache_read_input_tokens（creation 显式 0×6）、chat=prompt_cache_hit_tokens≡prompt_tokens_details.cached_tokens 双别名（miss 互补自洽）。限定：bare_model_probe 非 product_run；fresh≠冷启动证明、repeat≠必然热命中；raw creation 仅 messages 显式 0，responses/chat 缺键≠无写；chat 双别名禁止重复求和。
2. **DSH 归档缺陷**：capture marker（双 dsh）与真实 session 目录（单 dsh）不匹配 → 原始 archive 空/usage null 一体六槽（dab-r1 integrity vacuous violation）。原档保留 + recoveries/ 8 zstd 晚补档独立成卷；reviewer task10 六行报告（final-six-summary-01.json，生成 2026-10-30T00:18:41.613895+08:00）：恰 6 去重/8 副本、6 身份结构支持、5 collected_at 明确晚于结束、cargo-r3 采集起点 unknown（仅独立 stat+重 hash）、160 项 159 过 1 unknown、93 输入并集复 hash 零漂移、receipt-check all_ok=true。**补档不自动改 formal**；DSH 线 usage 维度本轮不可作结论（AUDIT AUD-D3）。
3. **WB 独立路由未知**：alias 双证（driver 参数+会话库 model 字段）=deepseek-v4.1-flash；上游 actual_request_model=null 不可观测（managed unknown 登记）；app_asar before==after 无漂移（AUDIT AUD-O1）。
4. **双归档仅局部且 score not_evaluated**：master 原始流 write-once 落盘+legacy/current 双投影仅 codex/DSH 侧实现；WB 未走双归档；cargo 等 raw checker 两位精度与 8 位规范化差异即产物（score not_evaluated，不重算不回填）。
5. **污染裁定**：codex 机械命中 10 处分布 cargo-r1(3)/r3(3)=cat ws/meta.json 回显（runner 主动放置、冻结时排除的脚手架）、dab-r2(2)/cargo-r2(2)=Reasoning 文本提及（无命令无读取）；六槽**实际越界 0、oracle 内容 0**（auditor X6 全槽扫描独立证实；cargo-r2 模型推理后主动不读）。原 integrity violation 保留 → formal=false 维持；sidecar pollution-adjudication-cargo-r1.json。
6. **cache 报告层 erratum**（offline-recompute-erratum.json，producer dated erratum 2 于 23:33:34；AUDIT AUD-D1 同判）：raw/usage.raw/layer_raw_inventory 全含嵌套 cached_tokens；layer_mapping 预设平铺键 missing 系 coverage limitation；REPORT「6/6 missing=协议未返」为报告错误已纠。

## 三、解释

formal 0/17 的构成是**证据完备性/发射缺口 + 保守污染策略**，不是能力判定：三产品共同的 gate 必需字段（meta.inputs_verification、meta.judge.checker_sha256、guards_used）在 raw 层均有等价事实（inputs 实测在位、绑定存在于 score-receipt/score 块、guards 可由 contract guards 集合+raw checks 重算），但 runner 未发射到 gate 读取的顶层字段；污染槽按「原 violation 保留、sidecar 不入 gate」纪律维持 partial。DSH usage null 归因 capture marker 缺陷而非无用量（晚补档身份链已独立支持，但本轮不用其补 HTTP 分母）。分数 observed 保持原始精度（70.37 与 70.37037037 为同值不同精度，按各线 raw 记录陈述）。以上均为机制性解释，**不构成 runner 生成效应、母体方差或跨产品因果/排名结论**。

## 四、未排除因素

1. 被测产品可感知自身被评（产品交付态固有），度量卫生限制随 managed unknowns 登记，无法完全排除其影响（AUDIT AUD-O1 注记）。
2. responses/chat 的 creation 缺键语义（协议不返 vs 未触发写）本轮无法区分；不排除服务端存在未命名缓存写入。
3. DSH 补档的采集起点：cargo-r3 unknown；其余 5 槽 collected_at 晚于结束 854s 量级，补档与原 run 之间的时间窗内状态不可完全复原。
4. 上游 actual_request_model 不可观测 →「路由独立」仅到 alias/DB 层，不能排除网关侧模型代换。
5. prepare 时刻输入一致性：runner 未落 inputs_verification，事后只能对真实运行目录 SHA 复核（dab 3 rep 全 match；cargo 3 个可修改 .py 为任务内修改后状态），无法机械复原派发瞬间。
6. 事故 INCIDENT-20261029-mock-real-codex-launch 证据等级 incomplete（stdout 52 位 fragment 作废、stderr 转录 unverified、DeepSeek provider unknown），不并入六账。

## 五、可复现实验

全部命令级复现路径与指纹：judge 终验 judge-final-ebbbb696cc2fbd70f410fae184d6bd5f274db0cabaa809214ee78b9fd2cfc061.json（sha256_16 ebbbb696cc2fbd70）；缓存 erratum offline-recompute-erratum.json；污染 sidecar pollution-adjudication-cargo-r1.json；mechanical sweep 与 canonical gate 输出在 L4独立验收-2026-10-29/realdata-product/（codex6/dsh6-mechanical-sweep.json、gate-admission-*.json、U1-product-admission-rows.json）；恢复档六行 final-six-summary-01.json（sha256_16 deaeea32e882bbda）+ receipt-check all_ok=true。复算约束：零模型调用；truth/solution 不语义阅读；checker 仅机械执行；canonical gate 以冻结源 1-评测方案/工具链/l4-execution/gate.py（E seal 5674de65 所封同版）复跑即得同表；审计独立性另见 AUDIT.md（本报告 formal/fails 全部来自该独立复跑，非 producer 自述）。

## L5 问题池（影响 / 下一步 / 停止条件）

| # | 问题 | 影响 | 下一步 | 停止条件 |
|---|---|---|---|---|
| L5-1 | WB/DSH gate 必需字段发射缺口（inputs_verification/meta.judge.checker_sha256/guards_used；WB receipt.earned 镜像 reward） | 全部产品槽 canonical formal=false 的主因 | runner 按 gate 契约补发射；judge 以同一 canonical gate 复验 | 全 17 行 gate fails 清零且 formal 判定复跑一致；未清零前 formal 维持 false |
| L5-2 | WB renderer 就绪 wait 缺口（bird 冷启动失败） | 首槽 not_executed，损失 1 计划样本 | driver 增加就绪等待+超时降级；新批次重排 bird | 同类失败复现即停该槽记 not_executed，不重试兜跑 |
| L5-3 | ws 元数据暴露面（codex/DSH runner 向模型可见 ws 写 meta.json） | 框架信息/checker_sha256/仓库绝对路径暴露；触发机械扫描命中 | meta.json 移出模型可见域或脱敏 config_ref | 扫描命中归因仍需逐条轨迹核验；未整改前 violation 保守保留 |
| L5-4 | DSH capture marker 不匹配（双 dsh vs 单 dsh） | usage 维度整线不可作结论 | collector marker 修正+下批先 dry 验证 capture 非空 | 修后首批真实槽 capture 非空且身份链过验才恢复 usage 结论 |
| L5-5 | gate 归一化映射 coverage（responses 嵌套 cached_tokens 路径） | mapping 层 missing 与 raw 阳性并存，易再生报告错误 | mapping 增加 nested 路径或改为 raw-inventory 驱动 | erratum 表与 mapping 输出一致方撤 finding |
| L5-6 | setsid 脱组写者覆盖边界（组确认≠全停） | 组级 confirmed≠产物冻结成立 | producer 显式 residual 限制披露+停后 ws 双采样常态化 | 双采样检出→partial 纪律持续；披露文案随实现更新 |
| L5-7 | 分数精度双口径（raw 2dp vs 规范 8dp） | 跨层比较易生「数值不同」误判 | 统一以 raw 记录陈述+canonical 重算并列表述 | 两口径并陈纪律写入报告模板 |
| L5-8 | gate not_executed 白名单误报（bird registrations/ 被判『疑似虚造』；dated sidecar：realdata-product/gate-falsepositive-bird-registration-sidecar.json，2026-10-30T00:35:24+08:00） | R3 强制先持久登记与 gate 白名单冲突，canonical fail 伪命中（accounting_complete 不受影响） | 下版 gate 白名单放行 R3 登记目录；冻结版不改 | 修复版 gate 对 bird 槽复判该 fail 消失、其余判定不变 |

## 账目边界

事故单列不并六账（interface_preflight ×1 accidental CLI start：chatgpt.com plugin-warm 401 证实 1 次、DeepSeek provider unknown、证据 incomplete）；AUDIT 自身 AUD-D5 手写数值违纪已 dated 在案。本报告不出现五题总分、不按已评折算、不归一化缺失、不做金额/成本推论。


## Dated 勘误 v2（2026-10-30T00:30:44+08:00，脚本生成；初审 lead 九点，原表述保留为历史，本节为修正口径）

1. **精度表述**：70.37 不是与 70.37037037「数值一致/同值」——前者是后者四舍五入至两位的**近似值**。WB cargo 原发射 2dp（raw checker 70.37、receipt reported 70.37、meta weighted 70.37），canonical 重算为 8dp 70.37037037（19/27）；两口径必须区分陈述，不得写「同值」。
2. **L22『三产品共同 meta.inputs_verification 等均缺』不准确**：按 canonical gate 逐槽实际——codex 6 槽 fails 含 inputs_verification.ok 非真（meta 顶层未发射）；**WB 执行 4 槽 inputs_verification.ok=true（已发射且机械比对通过）**；DSH 6 槽 gate fails 为 capture/usage 相关与发射类字段组合、无 inputs_verification 项。不得从单产品槽推广到三产品。
3. **L5-1 停止条件更正**：本批冻结旧行**不补写、不追认、formal=0 永久不变**；验收对象改为——新封印下的合成正/负例 + 下批次正确发射后的真实槽 canonical gate 复验。历史 17 行 fails 不作为清零目标。
4. **事故账口径**：interface_preflight ×1 归 interface_preflight 账、单列呈现、不并 35 槽总账；DeepSeek provider requests=unknown 维持。
5. **双归档与精度脱钩**：双归档本轮仅局部实现且 score not_evaluated；cargo raw 2dp / 规范 8dp 的差异是 **runner/receipt 发射层差异的证据**，不构成「双归档对分数差异」的证据。
6. **补档时间逐行更正（不作量级泛化）**：854s 仅首槽 dab-r1；实际逐行 collected_after_finished_seconds——dab-r1 854.0、cargo-r1 1362.0、cargo-r2 1082.0、dab-r2 489.0、dab-r3 122.0、**cargo-r3 unknown（collection_time=unknown；at 为作者称 copy 后构造，reviewer 仅独立 stat APFS birthtime/mtime 并重 hash）**。
7. **复现限定**：「复跑即得同表」改为——E 条件（封印/绑定/外部件路径与内容）满足时复验可得同表；外部 17 pin 可能随环境漂移，**无永久重放保证**。
8. **WB frame 覆盖补充**：app frame 覆盖已恢复、before/after 两版均为空态记录；渲染就绪等待缺口在 L5 池待修（wb-probe 正写 sidecar）。
9. **数据源指针**：首次 observations.json（sha16 377d8f419c7e7b81）已过期；最终以 immutable snapshot **observations-final.json（sha16 5f717c44281b64e6，generated_at 2026-10-30T00:25:55+08:00）为准**。以下改用可点击相对链接：[observations-final.json](observations-final.json) ｜ [judge 终验 17 行快照](source-snapshots/judge-final-ebbbb696cc2fbd70f410fae184d6bd5f274db0cabaa809214ee78b9fd2cfc061.json) ｜ [AUDIT.md](../对抗性盲审-L4-2026-10-29/AUDIT.md) ｜ [reviewer 六行 summary](../L4首请求前评审-2026-10-29/late-archive-verification/final-six-summary-01.json) ｜ [cache erratum](../L4独立验收-2026-10-29/realdata-cache/offline-recompute-erratum.json) ｜ [污染 sidecar](../L4独立验收-2026-10-29/realdata-product/pollution-adjudication-cargo-r1.json) ｜ [U1 rows](../L4独立验收-2026-10-29/realdata-product/U1-product-admission-rows.json)。


## Dated 勘误 v3（2026-10-30T00:33:33+08:00，脚本生成；数据基座切换至 observations-final-v2）

- 事实：独立 reviewer 发现 v1 汇总（observations-final.json，sha16 5f717c44281b64e6）**遗漏部分 canonical block_reason（含 codex-tb-cargo-plan-r1：v1 canonical_fails 误为空数组）**，且脚本把当次 2048 观测写成硬断言（不再把观测结果断言为预注册规则）。lead 已修脚本并生成 **observations-final-v2.json（sha16 7a1fd8ab738a9f0e，generated_at 2026-10-30T00:32:54+08:00）**；v1 原样保留为旧快照。
- v2 语义：cargo-r1 的 canonical_fails 置 null（不再伪造空=无 fail）并与原 block_reason 分别保留；counts 不变（17/16/1、formal 0、probe 18、pairs 6）；snapshot 与 v1 相同。
- 本报告数据基座自此**以 observations-final-v2.json 为准**；[observations-final-v2.json](observations-final-v2.json) ｜ 旧快照（历史保留）：[observations-final.json](observations-final.json)。
- 宏观结论不变：16 执行+1 未执行、formal 0/17、缓存 6 对及其限定、各产品 observed 分数与发射缺口/污染裁定口径均维持（judge 侧 canonical 判定出自独立 17 行收据，不依赖该汇总脚本）。


## Dated 勘误 v4（2026-10-30T00:41:05+08:00，脚本生成）

- **git diff --check 口径说明**：暂存前 `git diff --check` 恰 3 项 whitespace 告警，全部来自 WB dab `workspace/inputs/manual.md` 第 53/76/97 三行行尾空格（程序复核：该文件 sha256_16 bb7f4ca6fdc759af 与冻结 contract 输入完全一致，行尾空格为**原始输入自带格式**）。原输入字节不可改动——保留原始字节导致全量 diff --check 告警；**排除该精确文件后 diff --check 通过**。此为原输入格式问题而非源码样式问题，**不声称全量 diff --check 干净**。
