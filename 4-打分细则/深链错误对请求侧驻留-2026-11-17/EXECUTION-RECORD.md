# 执行记录：深链错误对请求侧驻留（t3 两 run，0 新运行）

## 问题
v1.58 §4.51 在事件层确立 r1 bash 缺参错误对跨 13 比较对持续驻留；环17（响应侧工具参数源头）已对该错误对做 W/L/H 三层定源（SSE→本地调用→最早后续请求），但只覆盖第一条后续请求。本包把「请求侧驻留」扩展到 t3 两 run 的全链逐请求放置轨迹、逐字节形态一致、跨 run 分类与事件层一致计数（0 新运行，全部复用既有捕获档）。

## 对象与冻结
- 数据面：loop8/t3-r1（16 请求）与 loop8/t3-r2（15 请求）requests/*.request.bin + event-layer-t3-r{1,2}/session.v4.jsonl.zstd（build 模式经系统 zstd CLI 多帧解包；公开重放不读私档）。
- 冻结页 README.md 含两次修订（均在任何 evidence 生成前）：修订一（t2 无错误对，锚不得用 t2）、修订二（loop1/loop5 亦无错误对；最终锚=loop8/t3 两 run；环17 先验 H=首后续请求）。t2 负结果保留为 D0 登记。冻结 SHA 见 SELF-ACCEPT。

## 结果摘要（verdict=wire_pair_persistent_r1_only_byte_stable）
- D1 放置：r1 首个含错误对请求=003；003–016 全部 14 条后续主请求均含，位置恒定（assistant[5]/tool[6]）；r2 全部 15 请求无错误对。
- D2 字节一致：r1 错误对两要素在全部出现处逐字节相同（assistant 项 sha=c06bff59…（id）/40e14c2a…（args）各 14 次；61B 错误文本 sha=1613fe63… 14 次）。
- D3 跨 run：PRESENT_IN_ONE_RUN（仅 r1 出现）。
- D4 事件层一致：r1 事件层恰 1 次坏调用 + 1 次错误结果且 sha 与请求侧相同；r2 事件层 0/0。环17 的 L 层（事件 seq18/19）与本包 D4 一致。
- 诚实定位：放置恒定性是追加式历史组装（跨 run 重建环已证）的可推出特例；本包新增测量 = 全链持久性计数、跨 run 行为差异（同一任务第二 run 未再犯错）被 Harness 逐字节如实携带。

## 实现与迭代（如实）
- verify.py（stdlib 公开重放；build 模式额外依赖系统 zstd CLI）：sha 锚定定位（id/args/错误文本三者 sha256），不用参数名启发式。实现中三次方向性修正：①事件层 tool/result 文本在 data.message.content[].text 而非 data.output；②result 的 evidence_sha256 改为落盘 evidence.json 字节计（与重放口径一致）；③误用 no_duplicate_pairs 于行去重（改行内 seen 集），并以 FROZEN_REQUEST_ROWS=31 区分冻结形状重建强制比对与合成形状跳过。
- 探索先验披露：冻结前探查（07:49–07:53）用「缺 command 参数」启发式扫 t2/loop1/loop5/loop8；冻结后实现中一度把 t3-r1 合法 t3 调用（参数名非 command）误读为「4 次坏调用」，随即改 sha 锚定纠正为真实图景（1 次坏调用；D3 从预想的 COUNT_DIFFERS 修正为 PRESENT_IN_ONE_RUN）。全部先验与本修正已在冻结页修订与 SELF-ACCEPT 载明。
- test_verify.py 18 用例：合成树全管线（进程内 main 驱动；子进程不继承 monkeypatch）、12 类篡改全 rc2（行值/空放置/schema/baseline/readme-pin/锚/重复行/层计数/r2 层非空/缺行/越界/bool 位置）、CLI fail-closed 4 类（缺 flags/双 flags/缺文件/输出冲突且原字节保留）、行级合法但终点不可翻转（严格冻结放置）、真档重放 e2e（DEEPPAIR_ARCHIVE_ROOT 门控，无 env skip=1）。四档全绿：普通/-O × 有/无 env。

## 验证
- 四路逐字节一致：build(普通/-O) 与 replay(普通/-O) 的 result 全等；build evidence 与已发布 evidence.json 全等（冻结形状强制比对）。
- 时间线（FS stat，birth|mtime）：README 07:49:32|07:53:32（冻结+两修订）；verify.py 08:02:15|08:02:42；evidence.json 07:57:25|07:57:25；result.json 07:58:52|07:58:52；test_verify.py 07:59:44|08:02:53。evidence 生成早于 verify 后续两次实现修正，但其字节与终版 verify 重建逐字节一致（cmp 通过），修正不改变科学输出。

## 已知限制
- 单任务（t3）、两 run、单模型通道；不外推其他任务/Harness/模型。
- 全部为 product-archived byte 观测；不认证模型内部/provider/HTTP 服务端。
- 公开重放不重建事件层（无 zstd 依赖）；事件层数值在 evidence 中为 build 侧见证，由真档 e2e（独审可复跑）与封印链兜底。
- 错误对两要素以 sha 锚定；公开档不含原始 id/参数文本/错误文本/任务正文/路径值。

## 独审
非作者独审：pending（见 SELF-ACCEPT.json）。

## 独审 delta（2026-11-17 08:13–08:15，非作者独审 PASS 后的两项低危闭环）
- L1（描述性字段未冻结）：verify.py 新增 FROZEN_N_MESSAGES（run,seq→n 全 31 值）并在公开重放逐行强制相等（校验 `n-pin`）；test_verify.py 新增 test_02b_row_tamper_n_messages（单行 n+1 → rc2）。n_messages 从「仅 int 正数」升级为逐值冻结；不进入任何终点计算的性质不变，但现在公开重放也能发现该字段被改。
- L2（公开测试文件含原始锚字面量）：test_verify.py 的 PAIR_ID/ARGS/ERR 三个常量改为片段重建（运行时字节与封印 sha 逐字节一致，已断言等价）；公开源码不再含连续 call id、工作区路径或错误文本原文。README/verify 的隐私声明本就只约束 evidence，此修订把同一口径延伸到测试源码。
- 修订后验证：四路（build/replay × 普通/-O）与公开 evidence/result 仍逐字节一致；19 用例四档全绿（env 普通/-O OK；无 env OK skipped=1）。evidence.json/result.json 未改动。
- 前一版字节归档：loop19/pre-delta/（MANIFEST.txt 含 verify 35f0a400…/test 28e6c1ee…/EXEC c91eea7e…/SELF 0f13b75f…）。
