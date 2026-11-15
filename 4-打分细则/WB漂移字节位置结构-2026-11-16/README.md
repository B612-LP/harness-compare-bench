# WB 漂移字节位置结构（r1109 bw-retest W1 残差定位）— 预注册 v1

- 冻结：2026-11-16T06:00+08:00（任何 result 计算前）。离线纯算法；0 新运行；不改分数/门/25 格；不改既有发布文件。执行记录进包内 EXECUTION-RECORD.md。
- 勘察注记（冻结前事实，可被包内复算推翻）：WB重复槽输入与交互量结构 result.json 的 W1 逐对偏移显示信封外差异集中在两 case 相同相对位置（信封闭合后 +93…+97B 的 5 字节簇）加一个孤立字节，三 rep 两两互异。本包把该结构从「勘察印象」升级为冻结裁定。

## 1. 问题
WB 复测槽首条用户消息的字节漂移（W1 登记 33 处：dab 三对 6/7/7、tb 7/7/6）在结构上是什么：固定位置的逐运行变量 token（模板注入位）、逐对随机散布，还是块移位/重排？

## 2. 冻结判据（内容无关：偏移、长度、SHA、计数；不读任何字节值）
- 数据源：bw-retest 归档六槽首条用户消息文本（与 W1 同源、同信封 span）；全部 33 处差异逐处登记 {case, pair, offset, envelope 相对位置 = offset − 信封闭合}。
- 逐差异局部上下文：取 ±16B 窗（不足取边界），窗内剔除差异字节后其余字节聚合 SHA（context_sha）；三 rep 同位置两两窗比对：context 相同（仅漂移字节异）⇒ 孤立替换；context 不同 ⇒ 块移位/重排候选。
- 变量区两两互异性：对每 case 的 +93…+97 簇与孤立位，断言三 rep 两两字节不同（pairwise-distinct）；任一对相同 ⇒ 记非逐运行唯一。
- 信封内差异（dab 2/2/2、tb 2/2/3）同样登记偏移与复现结构。
- 相对位置规律：两 case 簇的相对位置区间按冻结登记（勘察值 +93…+97 仅为勘察，非钉定；以复算为准）。
- 与 W1 硬等：逐 case 逐对 diff_offsets、envelope span 必须与 WB重复槽输入与交互量结构 result.json 完全一致，漂移 exit 2。

## 3. 分支
- B-FIXED-POSITION-TOKEN：≥两 case 的信封外差异 ≥80% 落在相对位置一致（跨 case 相对区间重叠）的窄簇（≤8B 宽），簇内三 rep 两两互异、context_sha 同位置三 rep 一致（孤立替换），孤立字节同理 ⇒ 漂移=固定位置逐运行变量 token，非任务文本语义重写；§4.36 语义未知 caveat 缩窄为「token 语义未知、位置结构已定」。
- B-SCATTERED：不满足簇条件（散布/移位为主）⇒ W1 字节面漂移维持原判、不缩窄。
- 数据不足或与 W1 硬等失败 ⇒ B-INDETERMINATE / exit 2。

## 4. 交付
verify.py（--root 与 --archive-root 必填，后者指向 bw-retest/workbuddy；stdout 摘要；--output 独占创建；双档 stdout 一致；fail-closed exit 2）+ test_verify.py（≥14 双档全绿；真档案 env WB_DRIFT_ARCHIVE_ROOT 门控拒绝静默跳过；合成用例：固定簇/散布/块移位分类、context_sha 剔除差异字节、与 W1 硬等防篡改、--output 拒绝覆盖）+ result.json（schema wb-drift-loc-v1，含 prereg sha256、baseline_commit、内容无关声明）+ EXECUTION-RECORD.md。

## 5. 解释边界
内容无关纪律：token 语义（nonce/时间戳/会话 id 等）不判；孤立字节与簇的字节值不上库；相对位置规律不外推其他产品或批次；不构成分数/门修改。
