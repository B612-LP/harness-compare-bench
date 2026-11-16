# WB 复测漂移 token 的值语义检验 — 预注册 v1

- 冻结：2026-11-16T07:59+08:00（任何值读取前）。离线纯归档重分析；0 新运行；不改分数/门/25 格；不改既有发布文件；执行记录进包内 EXECUTION-RECORD.md。
- 上游：环 11（固定位置数字 token）、环 15（DD?DD 定长形状、分隔字节类=other、时钟类相容仅在字节类层面、语义不判）。本包读**漂移 token 与分隔字节的值**及同 run 轨迹自身时间戳，把相容性升为证实/否证；零任务正文读取与发布。

## 1. 问题
§4.41 登记的定长 DD?DD token 语义未知。若 token 值解析为合法 HH:MM 且与同 run 轨迹时间戳强相关 ⇒ 时钟类证实；若定长但非时钟 ⇒ 固定格式计数器/编码类；均不成立 ⇒ 登记 unknown。

## 2. 冻结判据（值面）
- 数据源：与环 6/11/15 同一 W1 提取（六槽首条 user 消息 input_text UTF-8 字节）；漂移 offsets 硬等环 11 result.json 全集（漂移即 exit2）；run 边界硬等环 15 result.json（DD?DD 结构漂移即 exit2）。
- 逐 rep×case 读：信封外窄簇的 5 字节 token（4 漂移数字 + 1 分隔字节，位置由环 15 run 边界给出）原值；同 run 轨迹 jsonl 内首个与末个消息时间戳字段（ISO-8601 字符串，元数据面）。
- 断言：V1 全部 6 token 匹配 ^([01]\d|2[0-3]):[0-5]\d$（分隔字节值同一）；V2 token 的 HH:MM 与该 run 首消息时间戳的 HH:MM 差 ≤1 分钟（逐 rep 登记，相关方向：token 时间 ∈ [首消息时间 −1min, +5min] 视为构建时刻一致）；V3 孤立位（信封内 2 + 信封外 1）单数字值逐 rep 登记、不判语义。
- 值发布边界：发布仅 token 5 字节、时间戳 HH:MM、数字孤立位单字节；字母/多字节/任务文本零读取零发布；私有字节类仍按环 15 纪律。

## 3. 分支
- B-CLOCK-CONFIRMED：V1∧V2 全过 ⇒ token 为构建时刻时钟注入；§4.36 语义未知面收窄为「产品输入构建器在信封中嵌当次时钟」。
- B-COUNTER-OTHER：V1 全过∧V2 破（定长非时钟，如递增计数）或 V1 破但 6 token 定长同格式 ⇒ 登记格式特征，时钟类否证。
- B-INDETERMINATE / 硬等失败 ⇒ exit2。

## 4. 交付
verify.py（--root 与 --archive-root=bw-retest/workbuddy 必填；stdout 摘要；--output 独占创建；双档一致；fail-closed exit2）+ test_verify.py（≥12 双档全绿；真档案 env WB_TOKEN_SEM_ARCHIVE_ROOT 双根门控；合成用例：HH:MM 判定正反、±1min 相关、计数器反例、offsets/run 边界双硬等防篡改、--output 拒绝覆盖、README SHA 防篡改）+ result.json（schema wb-token-sem-v1，含 prereg sha256、baseline_commit、值发布边界声明）+ EXECUTION-RECORD.md（零任务正文字样）。

## 5. 解释边界
时间戳相关≠因果（仍可能有共同上游如批处理启动时刻）；n=3×2 case；不改环 11/15 裁定、分数、门与 25 格；值发布仅限元数据面。
