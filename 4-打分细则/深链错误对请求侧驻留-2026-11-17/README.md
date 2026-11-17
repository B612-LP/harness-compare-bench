# 深链错误对请求侧驻留（t2 两 run，0 新运行）——冻结口径（事后探索，先验披露）

状态：冻结于实现前（作者已先读 t2-r1/t2-r2 捕获档与环17/18 产物——先验已发生，如实披露，不冒充盲前预注册）。

## 对象与锚
- 数据面：loop7/t2-r1 与 t2-r2 的 responses/NNN.response.bin + meta.json（与环18 同档，14 响应）。
- 错误对锚：r1 run 的 SSE 错误对（环17 环节：001.response.bin 内 assistant tool_calls（无 command）→此后本地 error 61B；此处扩展到 t2 run 的请求侧）。
- 精确定义：在 t2-r1/t2-r2 各自首个主请求 messages 起，逐请求递归检索错误对两要素文本（assistant 工具调用 id 与 61B 错误文本）在 messages 数组中的 item 序号与字节量。

## 终点（全部描述性，无通过/失败门）
- D1 起始位与存在性轨迹：每 run 首个包含错误对的请求序号；此后每请求存在/缺席。
- D2 形态一致性：错误对 item 的 role 与字节数，与 session L 层对应值一致的条数。
- D3 跨 run 分类：IDENTICAL_PLACEMENT（两 run 位置逐请求一致）/ POSITION_DRIFT / ABSENT_IN_ONE / OTHER（如实）。
- D4 登记项：与环7 chain_prefix_ok 的关系说明（驻留是否为前缀传递可推出的特例）。



## 修订二（仍在任何 evidence 生成前）
修订一的改锚（loop1/loop5）同样被数据否定：loop1/capture 与 loop5/capture-r2 各 3 请求均为「读→读→答」干净链，无缺参错误对。最终锚改为**存在错误对的既有捕获**：loop8/t3-r1（16 请求）与 loop8/t3-r2（15 请求），同一 t3 任务两次真实运行（2026-11-16/17 捕获档，0 新运行）。先验披露：环17 已对该错误对做过 W（SSE）/L（本地调用）/H（最早后续请求=003 的 messages[5]/[6]）三层定源（SOURCE_MISSING_PRESERVED）；本包扩展为全链逐请求放置轨迹、形态逐字节一致性、跨 run 放置分类与事件层一致性。修订一所述 t2 负结果保留为 D0 登记。

## 修订一（冻结后、任何 evidence 生成前，如实记录）
冻结后初步探查（loop19/probe_t2.py）：t2 两 run 各 7 请求（共 14）messages 中均不存在缺参 bash 错误对（无 assistant tool_calls 缺 command 的 bash/shell 调用，亦无 tool 角色错误文本命中）——冻结页原锚「扩展到 t2 run」前提被数据否定。本修订把锚改回**存在错误对的既有捕获**：loop1（r1 run 3 请求）与 loop5 capture-r2（r2 run 3 请求）；t2 负结果保留为 D0 登记项（该深链任务未复现缺参形态，如实登记，不解释原因）。D1–D4 定义不变，对象改为 loop1/loop5 两 run 全部 6 请求。

## 已知限制（冻结时点）
- 单任务（t2）、单 run-pair、单模型通道（glm-5.3-flash 代理），不外推其他任务/Harness/模型。
- 全部为 product-archived byte 观测，不认证模型内部/provider 行为。
- 字节量按 UTF-8 编码计；字符串定位按精确子串匹配，不做规范化。

## 公开面
公开 evidence 仅含：位置序号、存在布尔、role、字节数、分类标签、各请求 messages 总项数；不含任何任务正文/错误文本原文/路径值。复算入口 verify.py --evidence --output（公开档）与 --archive-root --build-evidence（私档重建）；独审与集成发布按 until14 窗口既有流程。
