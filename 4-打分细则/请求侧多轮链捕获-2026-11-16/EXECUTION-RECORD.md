# 执行记录：请求侧多轮链捕获（R-A3，2026-11-16）

授权与范围：承接[请求侧跨运行预注册 v3](<../请求侧跨运行预注册-2026-11-16/README.md>)的授权边界与本目录 README 的增补协议（先冻结后执行）。两次真实运行（t2-r1、t2-r2）经本机 DSH capture profile 链执行，上游 glm-5.3-flash；请求/响应原文只存私有归档，公开层仅形状/哈希/计数。

## 时间线（Asia/Shanghai 2026-11-16 晚）

- 23:35 冻结增补协议（README.md，SHA `8ad7e80cf7ca2821641c68c04fd2f78b74ee19cb30a85c74ec14a65adf81627f`），工作区 `capture-t2/` 五文件与提示词哈希在冻结页固定。
- 23:35:xx mock 干跑（proxy 8795→127.0.0.1:8799，0 真实请求，exit0，2 请求）。
- 23:35 proxy 8795 切真实上游 open.bigmodel.cn:443；工作区基线核对（五文件聚合 SHA `ed365b0731782c7bab3a6042b8142e00e3e1a6456c958bc1e5ab467e51f94096`）。
- t2-r1 23:34:14–23:34:33（墙钟约 19s）exit0，session-c7cf8b8e…，7 请求全 200，答案一行（响应侧，不在终点）。
- t2-r2 23:34:47–23:35:11（约 24s）exit0，session-9413d691…，7 请求全 200。
- 运行后工作区五文件聚合 SHA 与基线一致（rebuild no-op）。

## 观测结果（与 evidence.json/result.json 一致）

- 每 run 7 请求：1 主请求 + 1 辅助标题请求（941B）+ 5 主续请求；主链 6 请求。
- P1（运行内前缀性）：两 run 全部 5 步 `prefix_ok=true`；每步追加恰为 [assistant(tool_calls, content null) + tool(结果字符串)]。
- 追加字节 delta 两 run 逐段相同：[876, 519, 548, 497, 315]。
- P2：链上无任何截断/摘要/重组见证（前缀性蕴含，另无截断类 marker）。
- P3（跨 run）：req1 与标题请求逐字节恒等；5 个主续请求在归一 call_id 形态子串后 canonical 全等（5/5）。
- P4：模型逐轮只产 tool_calls（content null），轮间无自由文本；工具结果均为确定性文件内容/脚本输出。

## 验证与自验

- verify.py（stdlib；脚本目录锚定协议 pin；`--archive-base` 私档重建，`--evidence` 公开重放，输出独占）。
- test_verify.py 17 反例（合成同构链：happy/prefix 破坏/delta·形状·canon SHA 篡改/归一 ID 格式/请求计数/pin/严格 JSON/描述符/独占/CLI），普通与 -O 双档全绿。
- 四路一致性：公开重放（普通/-O）与私档重建的 result 及 evidence 逐字节同（REPLAY-N/O-IDENTICAL、RAW-EVIDENCE/RESULT-IDENTICAL）。
- 非作者独审另行执行，结论见其独立收据；本页不自认证。

## 限制

- n=2 run 对、单任务 t2、单模型、同日；链长 6 仍有限，不外推更长会话。
- bytes 非 token/成本；响应体（模型输出）不在终点；不认证 provider 服务端内部。
- 归一仅消除 `call_[0-9a-f]{24}` 形态子串；不证明其余字节之外的等价性。
- 公开重放只核封印/算术/schema；真档重建需私有 run 归档。
