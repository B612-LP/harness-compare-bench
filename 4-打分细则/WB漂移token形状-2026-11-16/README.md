# WB 复测漂移 token 的字节形状 — 预注册 v1

- 冻结：2026-11-16T07:21+08:00（任何 result 计算前）。离线纯算法；0 新运行；不改分数/门/25 格；不改既有发布文件。执行记录进包内 EXECUTION-RECORD.md；值无关纪律：只登记长度、边界、字节类（digit/alpha/other），不读任何字节值。
- 勘察注记（冻结前事实，可被复算推翻）：环 11 已裁定 40 处漂移为固定位置逐运行数字 token；本包把其形状收窄。勘察：信封外簇 offsets 构成两组长度 2 的数字 run、中间隔恰 1 个非数字字节（dab [6423,6425)+[6426,6428)、tb [6379,6381)+[6382,6384)），两 case 形状同构、绝对位置不同；三 rep 的 run 边界逐字节一致；信封内 3 孤立位（dab 181/5558/6660、tb 175/5540/6604）均为字母邻接的单个数字。

## 1. 问题
环 11 登记「数字类 token 的语义（会话 id/时间戳/随机数等）不判」。token 的字节形状（run 边界、长度、邻接类）在跨 rep 与跨 case 上是否固定？固定形状可排除长度可变 id 类候选、支持定长时钟类候选——不读值、只形状。

## 2. 冻结判据（值无关）
- 数据源：与环 6/11 同一 W1 提取（WB bw-retest 六槽首条 user 消息 input_text 块 UTF-8 字节）；漂移 offsets 硬等环 11 result.json case_analysis.events.positions_offset 全集（漂移即 exit2）。
- 逐 offset、逐 rep：包含它的极大数字 run 的 [起,止)、长度、漂移字节在 run 内 index、run 左邻字节类（digit/alpha/other）。
- 结构断言：S1 信封外簇恰为两组 run、各长 2、中间隔恰 1 个非数字字节（DD?DD），两 case 同构；S2 全部漂移 run 的边界在三 rep 间逐字节一致（起点/止点/长度三 rep 相等）；S3 信封内孤立位 run 长=1、左邻=alpha。
- 簇内分隔字节只登记字节类，不登记值；不比对分隔字节跨 rep 是否同值（值无关纪律边界）。

## 3. 分支
- B-DIGIT-RUN-FIXED-SHAPE：S1∧S2∧S3 全过 ⇒ 外部 token 为定长 DD?DD 形状、跨 rep 跨 case 边界不变；排除变长 id 类；与秒/分时钟类相容性仅在字节类层面登记（? 为 other 类——冒号类分隔与该形状相容，不判定语义）。
- B-SHAPE-VARIABLE：任一 S 断言在任一 rep/case 破 ⇒ 形状可变，登记差异明细。
- 数据不足或硬等失败 ⇒ exit2 / B-INDETERMINATE。

## 4. 交付
verify.py（--root 与 --archive-root 必填，后者=bw-retest/workbuddy；stdout 摘要；--output 独占创建；双档 stdout 逐字节一致；fail-closed exit2）+ test_verify.py（≥12 双档全绿；真档案 env WB_TOKEN_SHAPE_ARCHIVE_ROOT 门控拒绝静默跳过；合成用例：DD?DD 判定、run 边界跨 rep 一致性、字母邻接孤立位、漂移 offsets 与环 11 硬等防篡改、--output 拒绝覆盖）+ result.json（schema wb-token-shape-v1，含 prereg sha256、baseline_commit、值无关声明）+ EXECUTION-RECORD.md。

## 5. 解释边界
形状不等于语义：DD?DD 与时钟、序号、编码片段等均可能相容，本包只排除「跨 rep 长度可变」类；分隔字节与漂移字节值一律不读；n=3×2 case；不改环 11 裁定、分数、门与 25 格。
