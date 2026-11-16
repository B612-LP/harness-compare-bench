# WB 复测漂移 token 的 mm:ss 时钟同一性确认 — 预注册 v1

- 冻结：2026-11-16T08:34+08:00（本包内任何新计算前）。离线纯归档重分析；0 新运行；不改分数/门/25 格；不改既有发布文件；执行记录进包内 EXECUTION-RECORD.md。
- **事后假设声明（诚实披露）**：本包假设源于环 17 Lead 验证期观察（token 前 2 位=首消息「分」6/6、全 token=「分:秒」4/6 精确、2/6 秒位差 1），非独立预测；本包将其转为显式冻结判据并在同一归档上确认/否证，证据等级=事后确认，弱于事前预测，登记照实。

## 1. 问题
环 17 以 HH:MM 时钟判据否证时钟类（B-COUNTER-OTHER），但 Lead 观察指示 token 实为「分:秒」格式（冻结正则 ^([01]\d|2[0-3]):[0-5]\d$ 把合法 mm:ss 误判非法，如 25:55=25分55秒）。token 是否=输入信封构建时刻的 mm:ss？

## 2. 冻结判据
- 数据源：与环 6/11/15/17 同一 W1 提取；offsets 硬等环 11 全集、run 边界硬等环 15（漂移即 exit2）；时间戳=同 run 轨迹 timestamp（epoch 毫秒，UTC+08）。
- 逐 rep×case 读：窄簇 5 字节 token 原值（位置由环 15 边界）；首消息时间戳。
- 断言：V1′ 全部 6 token 匹配 ^([0-5]\d):([0-5]\d)$（两位:两位、两字段均 ≤59）；V2′ |token(mm:ss) − 首消息时刻(mm:ss)| ≤ 1 秒全 6 处成立（逐处登记精确秒差，含 ±1s 边界归属）；V3′ token 前 2 位=首消息「分」6/6（同前，冗余核验）。
- 发布边界：token 5 字节、秒差整数、HH:MM:SS 首末消息时刻（元数据面）；零任务正文。

## 3. 分支
- B-MMSS-CONFIRMED-POSTHOC：V1′∧V2′∧V3′ 全过 ⇒ 环 15/16「数字 token」语义收口：输入信封嵌入构建时刻 mm:ss（逐运行变化、位置固定）；环 17 B-COUNTER-OTHER 保持不动（其冻结判据字面结果不改写），本包登记语义层修正。
- B-MMSS-PARTIAL：V1′ 全过∧V2′ 4–5/6 ⇒ 登记秒差明细，判定「与首消息时刻一致但存在秒级偏差源未定位」。
- B-MMSS-REFUTED / 硬等失败 ⇒ exit2 / 登记 unknown。

## 4. 交付
verify.py（--root 与 --archive-root=bw-retest/workbuddy 必填；stdout 摘要；--output 独占；双档一致；fail-closed exit2）+ test_verify.py（≥12 双档全绿；env WB_TOKEN_CLOCK_ARCHIVE_ROOT 双根门控；合成用例：mm:ss 正反、±1s 边界、V1′ 拒绝 HH:MM 旧口径误判（25:55 应过）、双硬等防篡改、--output 拒绝覆盖、README SHA 防篡改）+ result.json（schema wb-token-clock-v1，含 prereg sha256、baseline_commit、posthoc 声明）+ EXECUTION-RECORD.md。

## 5. 解释边界
事后确认证据等级；±1s 偏差源（发送时戳 vs 构建时刻取整）不判；n=3×2 case；不改环 11/15/17 任何冻结判定文字；正式 25 格与历史分不回写。
