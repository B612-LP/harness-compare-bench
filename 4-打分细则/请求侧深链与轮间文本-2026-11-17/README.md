# 请求侧深链与轮间文本（R-A4，2026-11-17）——预注册增补协议（先冻结后执行）

本页是[请求侧跨运行预注册 v3](<../请求侧跨运行预注册-2026-11-16/README.md>)授权范围内的第二次增补协议，遵循其观测边界（请求/响应原文只私档、公开层仅形状/哈希/计数、结论范围=本任务观测 run 对）。相对 R-A3（[多轮链捕获](<../请求侧多轮链捕获-2026-11-16/README.md>)，6 请求链、逐轮纯 tool_calls），本协议把链深推到约 13 主请求，并强制轮间文本输出。

## 任务 t3（冻结）

工作区 `/Users/b612-lp/bench-workspaces/capture-t3/`（仓外），仅含：

- `TASK.md` SHA `6eeedb62e63f24d82222a5a7e68ad475294c8e9c10784108ab087cead39e0060`：按序读 m01–m12；每读一个、在读下一个前，输出恰一行 `STEP <k>: <token>`；最后输出恰一行 `DONE`；不改文件。
- `inputs/sequence/m01.txt`…`m12.txt`（文件 SHA 冻结于执行记录页；内容为序号+token 行，token 形如 `TOKkK-`+3–7 个 z）。
- 13 文件（TASK.md+m01–m12）聚合 SHA `88e9c81b56febd7352ccf496a0e3e761373caf8927e7312c3f16878514aa9e0c`（聚合口径冻结：对按裸文件名排序的每个文件（`TASK.md`、`m01.txt`…`m12.txt`，不含目录前缀）取 `裸名 + 该文件SHA256` 串接后整体 SHA256；执行记录按同口径复核）。

提示词（60B，SHA `e7fea6df7f205a8c1542bbae3ada653a8e2a8fb09a27efa92547c2e3864153d4`）："Read TASK.md and follow it exactly. Do not modify any files."

## 预注册终点（全部描述性）

- P1（运行内前缀性）：每 run 捕获的请求序列中，除辅助标题请求外，主链每一步满足内容级前缀性（下一主请求消息数组以当前主请求全部消息为严格前缀+仅追加）。
- P2（追加形状登记）：每步追加的 assistant 消息 content 是否为 null（纯 tool_calls）或含 text 块，逐段登记；轮间文本为任务规定格式（`STEP k: …`）时可与 run 内确定性 token 对比。
- P3（跨 run）：首主请求与标题请求逐字节恒等；其余主请求在归一 call_id 形态子串（`call_[0-9a-f]{24}`）后 canonical 全等的比例；轮间文本行跨 run 是否逐字节相同（token 确定性 → 预期相同，若不同如实登记）。
- P4（无见证断言）：全链无任何截断/摘要/重组 marker；前缀性本身蕴含仅追加。

## 执行边界

- 两次真实运行（t3-r1/t3-r2），同 capture profile 链（新 profile capture-r5，唯一功能 diff=端口 8796）；先 mock 干跑（0 真实请求）。
- 运行后工作区聚合 SHA 与冻结值一致（rebuild no-op）。
- 非 `call_[0-9a-f]{24}` 形态或任何 UNEXPLAINED 差异 → 该对记 UNSTABLE 停，不追加凑恒等；同授权失败可重试一次。

## 限制（继承 v3）

n=2 run 对、单任务、单模型、同日；链长约 13 仍有限；bytes 非 token；响应体（模型输出）不在终点（轮间文本行按 P2/P3 仅登记与对比）；不认证 provider 服务端内部。
