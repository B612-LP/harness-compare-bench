# 判卷器可信度协议 v1 —— 多 judge 交叉 κ 与 judge–human 一致率（L38 预注册）

- 状态：协议已按 PREREG 封存（私档环目录预注册文件，sha256 540fa07f…）；**发射阶段（judge 实跑）待用户放行，未放行前协议不执行**。
- 零发射声明：本协议设计与 κ 工具自测（合成数据）零模型调用；本文不含判卷发射实测数字（§八的语料盘点统计是语料清单盘点，发射阶段未执行）。
- 老师反馈对照：直接服务反馈⑤（判卷器修订五要素之上的可信度度量层）与反馈④（一致率只作弱命题解读）。

## 一、测什么、不测什么

- **测**：人工判定事件（既有语料）与机械 checker 判定作为参照时，独立 judge 模型通道对同一测项给出相同判定的程度（一致性，κ 族指标）。
- **不测**：checker 的正确性证明（κ 高≠checker 对）；judge 的「智能水平」；跨产品能力比较（本协议结论不得入正式表）。
- 弱命题口径：一致≠正确；在金标本身不可唯一复现的测项（q2697 类）上，低一致为预期结果，单独分层解读，不并入总分。

## 二、测项集（封闭构造规则）

1. 池=L38 主项 D 语料盘点 `availability=direct_test_item` 的全部条目；按 type 分层抽样（裁定/修订正例/近似错误例/更正链/终审排除/replay 金标各类保持池内配比），目标 60 测项；池不足 60 如实缩减并披露，不凑数。
2. 测项形态三元组：{题面关键信息（题面原文或摘要，含完成条件）、产物摘要（轨迹结论性内容，非全文）、待判断言（该测项的判定问题）}。judge 输入**不含**：checker 判定结果、其他 judge 输出、L37 机制分类标签、裁定结论文本（裁定类测项以「裁定前」视角出题）。
3. 封闭选项集：`pass / fail / uncertain`（三选一，禁其他输出；输出不合集=invalid 计数披露）。

## 三、judge 集与盲态

| rater | 通道 | 角色 |
|---|---|---|
| checker | 机械（零模型） | 机械参照 rater，判定取既有 score-receipt 断言明细，零成本 |
| judge-DS | deepseek-flash（裸模型单轮） | 独立 judge 通道 1 |
| judge-GLM | GLM-5.3（裸模型单轮） | 独立 judge 通道 2 |
| human | 既有语料人工标签 | 金标参照（本环不新增人工标注任务；标注扩充留待后续提案） |

- 盲态硬规则：三 judge 输入互不可见；judge 不可见 checker 与 human 标签；发射阶段逐测项独立会话，无记忆延续。
- 已知重叠披露：judge-DS 与 A 组/裸底数模型同家族（DeepSeek），家族内偏置作为未排除因素登记；judge-GLM 无产品重叠。

## 四、指标与判读（预注册阈值）

- Cohen's κ（逐对：judge–checker、judge–human、judge–judge）+ Fleiss' κ（全体）+ 百分一致率 + 逐对混淆矩阵 + 按 L37 词表 F1–F8 机制类分层（分层仅对 checker 可机械分层的断言级测项适用）。
- 判读（Landis–Koch 惯例）：κ≥0.8 强一致；0.6–0.8 中度；0.4–0.6 中等偏弱；<0.4 弱。预注册锚点为三档（≥0.8/0.6–0.8/<0.6），0.4 界为预注册后细化披露（验收 judge 建议注记）。**结论表述只到「在测项集上的一致性水平」**，不得外推为「判卷器正确/错误率」。
- invalid 处理：不合选项集输出记 invalid，逐 rater 计数披露，不折算不补测；单 judge 通道发射阶段 3 次重试仍失效则该通道退出并如实登记（停止条件）。

## 五、发射阶段规模与放行边界（本环不执行）

- 预计调用：60 测项 × 2 judge × 1 轮 = **120 次判卷调用**（+glm-5.3-flash 敏感臂 60 次为可选项，默认不开）；单测项上下文≈2–4K tokens。
- 发射须用户另行放行后按单发协议执行；产物只入私档与分析账，不入正式表，不改历史分数。

## 六、工具与自测（已完成，零发射）

- [tools-judge-agreement.py](<tools-judge-agreement.py>) v1.1（sha256 ab64b47ea463c715d768b2dd32503dd26ab3d0099b275184c33345dfcbff7c87；v1=L38 `49974dae…`→docstring 修正 `b4ab33ed…`，修订史见私档 RESULTS）：Cohen/Fleiss/百分一致/混淆矩阵/invalid 披露；write-once content-addressed 收据；退出码 0/1/2/3（PREREG 记 0/1/2，3=收据已存在拒写为实现加性补充，从严不减）。**v1.1（L39）：validate() 强制每条 item 非空字符串 item_id，缺失/空→校验错误拒算（修 L38 验收 issue 5 静默剔除路径，修订五要素见私档 RESULTS-L39）；自测扩至 T1–T8 14 断言。**
- **v1.2=现行（2026-11-07）：write-once 收据新增 `tool_version`/`tool_sha256` 自哈希字段、docstring 增版本史注；SCHEMA 与判定逻辑零变更，合成自测 T1–T8 14/14。** 提交 `4ef1d952de8000a1af94c51d9543cec82195b066`；现行 sha256=`fdf46ea0dbf592e58e66c8a631e01e08ad24fa2bea9de254773a9f5931c2c96b`（核验台账 ledger.json 该文件条目同值）。上行 `ab64b47e…` 为 2026-11-07 上午整改时点历史值；[盲态可判性审计](<../盲态可判性审计-2026-11-04/README.md>) manifest.json 与核验台账 role 串中的旧版本串为对应时点历史记录，按「已发布历史记录不改写」原则保留不改写。
- 自测：合成解析解套件 v1.1 起为 T1–T8 共 14 断言全过（κ=1.0、κ=0、κ=−0.6、三 rater Fleiss=−1/3、invalid 剔除、空表拒绝、非法标签拒绝、缺 item_id 拒绝）；v1 期首跑 T6 缺陷（空表未拒绝）已修复，首跑收据 VOIDED 留档（judge-agreement-selftest-v1.json.v1-buggy-T6-VOIDED）。

## 七、未排除因素（如实）

1. judge 与被评产物家族重叠（judge-DS vs DeepSeek 系产物）。
2. 测项三元组是有损压缩：产物摘要由人工构造，摘要偏差是新增一层人为变量（构造规则：只删不改，摘要后逐条对照原断言明细核保留语义；构造过程入私档环目录可查）。
3. human 金标有限：部分语料人工标签是「过程性裁定」而非「断言级对错」，此类只作 context_only 不入测项（主项 D 分级已区分）。
4. 单轮判卷无温度/多采样敏感性臂（默认关）；如需，另提案。

## 八、语料盘点结果（主项 D，2026-11-03 实测）

- 人工判定语料 **71 条**（预注册预期 40–80 内）：ruling 18、final_adjudication 19、correction_chain 13、replay_golden 9、other 4、selftest_positive 3、revision_fixture_near_miss 3、revision_fixture_positive 2。
- 可用性分布：**direct_test_item 17**（发射阶段测项池直接规模：r1101 十条完整性终审 + wb 五场终审 + 豆包额度改期两事件；HJ-069/HJ-006 发射期拆槽可再扩约 20）、needs_construction 48（发射前需按三元组构造）、context_only 6（不入选）。
- 即：直接池 17 项 < 预注册目标 60——按 §二.1 如实缩减并披露，或经拆槽至约 37；差额须以 needs_construction 构造补足，构造质量验收在发射提案中另行预注册，本环不凑数。
- 逐条机器账与人读版见 [human-judgment-corpus.json](<human-judgment-corpus.json>) 与 [human-judgment-corpus.md](<human-judgment-corpus.md>)（64 个证据路径全部存在、SHA-256 覆盖 71/71 条、ERRORS: NONE；7 项数据缺口如实登记于其局限段，含 L8证据链修订目录为空、r1101 原始 trajectory 不在公开仓等）。

## 九、收口路径

协议+语料盘点+工具自测收据公开登记（4-打分细则/判卷器可信度协议-2026-11-03/）；环末向用户提案发射阶段（L39 预案）；未放行则协议挂起登记，不作任何 judge 调用。

## 十、测项池（主项 B+C，L39 环 2026-11-03，零发射）

- 机器账与人读版：[judgment-test-pool.json](<judgment-test-pool.json>)（sha256 58e37b8fd2da8e74ac135f3a390aa98c9e2ee2ab4b4313bf7916e3aea04096cb）与 [judgment-test-pool.md](<judgment-test-pool.md>)（sha256 2cd42318659c94cbdf4a69facfdead7ad012e270e784a1e88e6e8994414a5cb1）。验收后窄修（auditor I-1/I-2 各补一条口径声明，修前版本 ecf1bfc2…/659da999… 经双验收全过，修订记录见私档 RESULTS-L39）。
- 池规模 **60 条**（P-001..P-060）= direct 17（HJ-049..063,070,071）+ 拆槽 21（HJ-069 十一槽逐槽 P-018..P-028、HJ-006 十探针逐探针 P-029..P-038，两源零缩减，gold=裁定内逐槽/逐探针判定原文）+ 构造 22（ruling×16+final_adjudication×1+correction_chain×5，裁定前视角三元组，结论只进 gold_provenance）。
- gold 分布：pass 47 / fail 13 / uncertain 0（既有人工裁定均为二值，无 uncertain 设计位，如实披露）。
- 池达 60 的实现路径与 §八预案一致（拆槽扩池+构造补足），构造条数 22 未超 PREREG 上限；不可忠实构造剔除 0、拆槽缩减 0；correction_chain 其余 8 条证据可构造但类型配额满未入池（宁少不凑，如实登记于 md）。
- 每条 evidence[].path 仓根相对且 SHA-256 实测覆盖 60/60；quote 逐字回溯与独立复核 17 项见 md 自检段；转写声明 3 条（P-004/P-057..060/P-016）。
- 判读力注记：HJ-069 逐槽 verdict 无成文判别口径、gold 全 pass（判别力弱，系忠实覆盖逐槽裁定的设计取舍）；本池发射阶段对这两项弱判别源保持披露。quote 分「行引逐字」与「声明转写」两类口径，发射组装 prompt 时转写类不得作逐字原文引用（口径判定见池 md §七）。
- 发射（judge-DS/judge-GLM×60 测项≈120 调用）仍待用户单独放行，本环零模型调用。
