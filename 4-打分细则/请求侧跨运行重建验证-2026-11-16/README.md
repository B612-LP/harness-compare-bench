# 请求侧跨运行重建验证（2026-11-16，R-A 执行报告）

本页是 [请求侧跨运行预注册](<../请求侧跨运行预注册-2026-11-16/README.md>)（v3 冻结，未执行状态发布于提交 6eec2ac）的**执行后派生报告**：预注册中声明的 R-A（同任务跨运行重建）在获得用户逐次授权后实际执行一次，本页冻结其结果与复算入口。预注册页不再改写；执行事实以本页为准。

## 授权与运行

- 授权：用户 2026-11-16T22:24:46+08:00 明确解除测试额度限制并要求继续推进（逐次授权，仅限本次运行）。
- 运行：2026-11-16T22:32:55–22:33:00+08:00，`capture-r2` profile（克隆自 capture-1 的 `capture-r1`，功能配置唯一预期 diff=本地捕获代理端口 8791→8793），同一 workspace 路径 `/Users/b612-lp/bench-workspaces/capture-r1`，同一 214B 任务提示词，同 model（glm-5.3-flash），exit 0，3 请求全部 HTTP 200。
- workspace 执行前核对：TASK.md 与 dominoes.py SHA 与 capture-1 基线一致（同路径重建为 no-op，私有归档留证）。
- capture-1（对比基准）见 [DSH请求侧最小捕获](<../DSH请求侧最小捕获-2026-11-16/README.md>)。

## 主要终点（预注册 H-stable 三分结局）

| 请求 | run1 SHA-256 | run2 SHA-256 | 判定 |
|---|---|---|---|
| req1（首主任务请求） | `92220699…120ac10` | 同左 | **逐字节恒等 → 结局①（组装稳定）** |
| req2（标题辅助请求） | `9f2b6b3e…63e34e76` | 同左 | 逐字节恒等 |
| req3（追加两工具结果的续请求） | `19e98d96…06b8b4` | `e14ff634…77bf67` | 不同（预期：含 run 内生成内容） |

- **主要结局：req1 逐字节恒等**。在 33091 字节、5 条消息、22 个工具定义、含 workspace 绝对路径字面量的完整首请求上，第二次独立运行的组装结果与第一次完全一致：本次观测范围内未见动态环境字段、未见时间戳/ID 类字段混入首请求。
- req2（辅助标题请求，1042 字节）同样逐字节恒等。

## req3 差异的归因（d 类/ b 类证据）

JSON 规范化后，run1 与 run2 的 req3 差异叶路径**恰 4 处**，全部为 provider 生成 ID 及其镜像引用：

- `messages[5].tool_calls[0].id` 与 `messages[6].tool_call_id`（call A）
- `messages[5].tool_calls[1].id` 与 `messages[7].tool_call_id`（call B）

assistant 消息的 tool_calls `name`/`arguments`、两条 tool result 字符串（dominoes 链执行输出）跨 run 相同；req3 总字节数两次运行同为 34107（两 call_id 等长）。→ req3 判定：**组装稳定但含请求时生成字段**（b 类证据：provider call_id 即为生成路径引用）；非截断、非重组、非环境状态字段。响应体（模型生成文本）不恒等属预期，不在本页终点内。

## Q1/Q2/Q4（run2 内，同预注册）

- Q1：req1 是 req3 内容级严格前缀（`req3.messages[:5] == req1.messages`），追加 3 条消息（assistant content=null + 2×tool），正文级字节 delta 1016（与 run1 相同）。
- Q2：追加式结构，无截断/重组标记。
- Q4：req1 跨 run 恒等 → system prompt（2593B）结构跨 run 恒等自动成立。

## 诚实披露

- 预注册要求"比对脚本执行前冻结 SHA"。实际时序：运行完成后先用 shell `shasum`/`cmp` 一行命令完成主要终点的逐字节比较（命令已 verbatim 记录于私有回执，可独立复算），随后经内联探查得到 req3 差异叶分类；本页打包的 `verify.py` 在**其首次执行前**冻结，`evidence.json`/`result.json` 只由该脚本产出并重算上述全部终点。主要终点本身是单命令 SHA 比较，不存在脚本选择空间。
- 预注册允许 0 请求失败同授权重试：本次运行一次成功（3/3 请求 200），无失败重试；运行前经 mock 上游 dry-run（0 真实调用）验证链路。
- n=1 对：结论仅适用于"该任务、该 workspace、该 profile 链、该模型"在两次运行中的组装稳定性，不外推到其他任务/模型/provider 行为；bytes 非 token；不认证 provider 服务端内部行为。
- "读→读→答"任务设计意图与 capture-1 相同；本页不新增模型行为结论。

## 复算

`verify.py`（stdlib，`python3 -I -S verify.py --root <仓库根> --run1-root <capture-1私档> --run2-root <run2私档> --build-evidence evidence.json --output result.json`）：重核两 run 全部请求字节 SHA、JSON 规范化差异叶分类、run2 内前缀恒等与追加结构，并对照本页与 capture 包、预注册页的固定 SHA。公开重放（`--evidence evidence.json`）不需私档，复核封印、算术与已发布的恒等事实（SHA 值本身可公开，正文内容仍不公开）。完整原文仍只在私有归档，公开证据不含消息正文、路径字面量与完整请求体。
