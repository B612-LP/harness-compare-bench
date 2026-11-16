# Codex 输入面元数据的值语义检验 — 预注册 v1

- 冻结：2026-11-16T09:07+08:00（任何值读取前）。离线纯归档重分析；0 新运行；不改分数/门/25 格；不改既有发布文件；执行记录进包内 EXECUTION-RECORD.md。
- 上游：环 7（Codex输入面残差定位）已把 15 槽全部 135 处输入面字节差定位到 3 条键路径：payload.id（元数据）、payload.internal_chat_message_metadata_passthrough.create_time / .turn_id（嵌套、保守归内容侧）；content[].text 15 槽逐字节零差异。本包读三键的**值**，判其是否为随会话构建变化的元数据（时间戳/序号/随机标识），收窄环 7 的保守口径未知面。
- 事后性声明：值语义假设由环 7 键路径定位自然引出（路径名即语义提示），但「create_time 是否≈该 rep 的 rollout 起始时刻、turn_id 是否跨 rep 递增」为本包首次检验，非验证期已见答案的确认；证据等级在 result.json 登记。

## 1. 问题
三键的值在 15 槽（5 case×3 rep）中呈什么语义：create_time 是否为时间戳且与该 rep rollout 首事件时刻强相关（有界差）？turn_id 是否为会话内序号（同槽内单调、跨 rep 重排）？payload.id 是否为带前缀随机标识（同槽三 rep 全异）？

## 2. 冻结判据（值面）
- 数据源：环 7 同一提取（r1109-mech-n3 15 槽 Codex rollout jsonl；--archive-root=launch-r1109 根）；漂移键路径硬等环 7 result.json（键路径集合漂移即 exit2）；content[].text 零差异复验（破即 exit2）。
- 读值范围：15 槽 developer+user 消息的 payload.id、internal_chat_message_metadata_passthrough.create_time、.turn_id 全值（漂移槽与稳定槽都读——稳定槽值作对照）；同 rollout 首事件 timestamp 字段。
- 断言：V1 create_time 全 45 值可解析为统一时间格式（登记格式与字段名）；V2 每 rep 的 create_time 与该 rep rollout 首事件时刻差有界（|Δ|≤120s，逐槽登记）；V3 turn_id 同槽内三值彼此关系登记（相等/递增/全异三选一），跨槽模式一致性登记；V4 payload.id 同槽三 rep 全异率登记（预期 100%，对照环 5 call_id 全异.namespace 结论）；V5 稳定槽（无漂移的槽）三键值仍逐 rep 互异 ⇒ 漂移检测以值差为准而非键路径（登记性断言，不破分支）。
- 发布边界：id/turn_id/create_time 原值与时间差为元数据面，可发布；content[].text 与消息正文零读取零发布；私有路径占位。

## 3. 分支
- B-METADATA-CONFIRMED：V1∧V2（≥14/15 槽）∧V4=100% ⇒ 三键=会话构建元数据（时间戳+序号+随机 id），环 7 保守口径的语义读法（会话元数据漂移）获值面支持；正式语义结论仍以双事实并列为准。
- B-MIXED：部分键不满足 ⇒ 登记逐键判定，语义收窄仅到满足键。
- B-REFUTED / 硬等失败 ⇒ exit2 / 登记 unknown。

## 4. 交付
verify.py（--root 与 --archive-root=launch-r1109 根必填；stdout 摘要；--output 独占创建；双档一致；fail-closed exit2）+ test_verify.py（≥12 双档全绿；真档案 env CODEX_META_SEM_ARCHIVE_ROOT 双根门控；合成用例：时间解析正反、有界差正反、id 全异率、turn_id 模式、键路径硬等防篡改、text 零差异防篡改、--output 拒绝覆盖、README SHA 防篡改）+ result.json（schema codex-meta-sem-v1，含 prereg sha256、baseline_commit、证据等级声明）+ EXECUTION-RECORD.md（零正文、零私档路径字样）。

## 5. 解释边界
值相关≠因果（构建时刻与 rollout 记录时刻的先后不判）；元数据发布不等于正文发布；n=15 槽；不改环 7 冻结判定文字与保守口径（其为本包上游登记）；正式 25 格与历史分不回写。
