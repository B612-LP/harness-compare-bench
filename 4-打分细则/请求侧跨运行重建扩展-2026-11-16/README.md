# 请求侧跨运行重建扩展：同一任务连续五次真实运行（2026-11-16）

状态：**已执行**（预注册 [请求侧跨运行预注册](<../请求侧跨运行预注册-2026-11-16/README.md>) v3 覆盖「截至当前全部运行对」；第 3–5 次运行在用户 2026-11-16T22:24+08 明确解除测试额度限制的同一授权下执行）。本页是[请求侧跨运行重建验证](<../请求侧跨运行重建验证-2026-11-16/README.md>)（前两 run）的扩展：同一 workspace、同一 214B 提示词、同模型、同 profile 链（代理端口 8794），连续 5 次真实运行（r1=18:33、r2=22:32、r3=23:06:16、r4=23:06:44、r5=23:07:02，均 exit 0，3/3 请求上游 200）。

## 五 run 请求字节表（SHA-256，字节本身不入公开档）

| 请求 | 五 run SHA | 判定 |
| --- | --- | --- |
| req1（首主任务请求，33091B） | 五 run 全部 `92220699f215bbdfe0faa392587b8fc43ad6793f10da6baf8b7541518120ac10` | 10/10 run 对逐字节恒等 |
| req2（标题辅助，1042B） | 五 run 全部 `9f2b6b3e9b76dde704dd763efc1e60992ec2c798c987ae577c784ddd63e34e76` | 10/10 run 对逐字节恒等 |
| req3（续请求，34107B） | 五 run 各不相同（`19e98d96…`/`e14ff634…`/`24732b1d…`/`76ed5f58…`/`9b990320…`） | 每对 JSON 规范化差异叶恰 4、全为 provider 生成 call_id 及其 tool_call_id 镜像 |

主要终点：**组装稳定性 10/10 run 对**（任两 run 的 req1 与 req2 均逐字节恒等）；d 类残差为零：把 4 个 call_id 值归一后，任一对 req3 的 JSON 规范化表示逐字节恒等。每个 run 内 req1 都是 req3 的内容级严格前缀（追加 3 条消息：assistant content=null + 2×tool 结果），正文级追加 delta 各 run 均 1016B。每 run 执行前后 workspace 两文件 SHA 与基线一致（同路径重建为 no-op）；r3–r5 事件层副本留私档。

## 解释与限制

- 首请求组装的确定性从单对（n=1）升级为同任务连续 5 run / 10 对一致；仍限于单任务、单模型（glm-5.3-flash）、同日、同 workspace 与适配器链，不外推其他任务/模型。
- 续请求的逐 run 差异仍全部由 provider 生成 call_id 承载；父包独审已在 wire 侧确认该生成性（id 先见于同 run provider 响应流再回显、两 run id 集不相交）。本页不重复该证据，只统计全对一致。
- bytes 非 token/成本；响应体（模型输出）不恒等属预期且不在终点内；不认证 provider 服务端内部行为或私档历史真实性。
- 公开证据不含请求/响应正文、路径字面量与完整 call_id 值（id 以 SHA/计数表达）。

## 复算

`verify.py`（stdlib）：私有档构建 `python3 -I -S verify.py --root <仓库根> --archive-base <until14私档根> --build-evidence evidence.json --output result.json`；公开重放 `python3 -I -S verify.py --root <仓库根> --evidence evidence.json --output result.json`（不需私档，复核封印、覆盖与全部已发布算术）。私有归档根含 `loop1/capture`、`loop5/capture-r2`、`loop6/capture-r{3,4,5}` 五个 run 目录（requests/ + responses/）。
