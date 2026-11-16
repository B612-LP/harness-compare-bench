# 执行记录：捕获会话事件层与请求层溯源（2026-11-16）

## 范围与授权

对既有唯一授权捕获（[DSH请求侧最小捕获-2026-11-16](<../DSH请求侧最小捕获-2026-11-16/README.md>)）的同一会话，做本地事件层（session 日志）与 wire 请求层的逐消息溯源映射。零新产品/模型运行；只读既有私档副本与公开包。会话日志副本在分析前固定：`session.v4.jsonl.zstd`（18395B，SHA `5c2bf4d4840525c0df59932b705f44615d9ae3888c4d66b3347b19670e339ba4`），与采集时点一致。

## 方法

- 会话日志为**逐行独立 zstd 帧**拼接（11 帧 / 29 事件，解压后 49278B）。验证器以帧序列化解码（单帧 decompress 只会得到 197B 的 session 头，这是探索期踩过并写进实现的坑）。
- wire 侧三个请求体 SHA 与 capture 包 evidence 的 `request_sha256` 逐字节绑定后再解析。
- 映射规则（冻结于本包 README）：循环消息要求「恰单 text 块且逐字节恒等」；assistant 要求「tool-call 块的 id/name/arguments 与 wire tool_calls 精确相等且 wire content=null」；tool 声明要求「本地 {name,description,parameters} 与 openai function 包装逐字段相等」；标题请求要求「固定前缀 + compact separators JSON 嵌入事件文本」。
- 公开档只存布尔/字节量/序号/描述符，不存任何正文；证据内含内容黑名单自检。

## 观察事实（n=1，全部描述性）

- P1：8/8 循环消息内容精确（system=事件7、user×4=事件8–11、assistant=事件17、tool×2=事件20/21）。
- P2：assistant 2/2 块精确转换，wire content=null，tool_call_id 链接 2/2。
- P3：22/22 工具声明逐字段精确（config.model/maxTokens 亦精确；contextWindow=1,000,000 仅存在于事件层）。
- P4：标题请求 system/user/maxTokens/route 全精确；user 为固定前缀 + 事件8文本的 compact JSON 嵌入。
- P5：wire 顶层 `stream/stream_options/thinking/tool_stream` 不在事件流，保持适配器层 unknown。
- 事件29 条：0–2 permission/sandbox/approval、3/5 spliced（3=插入任务提示→user 事件8，5=drain removedCount1）、4 turn/start、6/23 step/start、7 system、8–11 user、12 header、13 context、14–16 title、17 assistant、18/19 tool/call、20/21 tool/result、22/25 step/end、24 assistant、26 turn/end、27 end-seed。
- 注入 user 消息（9–11）在事件层有 source 元数据，但文本在请求时生成——不能当作更早的历史事件。

## 验证与自验

- `test_verify.py`：22 反例（合成多帧 zstd 会话全管线、同形异内容漂移、assistant/tool/registry 漂移、标题分隔符错误、公开校验的 sources/行数/字节/端点/绑定篡改、CLI 拒绝与错误泛化），普通/-O 各 OK。
- raw 重建与公开 evidence 模式重放 result 逐字节一致（双路收敛）；打包 evidence/result 与首建逐字节一致。
- 私档布局：`--raw-root` = `session.v4.jsonl.zstd` + `requests/001..003.request.bin`（副本 SHA 与采集绑定）。
- 非作者独审：待定（fresh provenance-auditor，结论以私有审计记录为准，PASS 后方可整合发布）。

## 已知限制

n=1 单 run 单 provider；内容精确性在私档字节上计算，公开只封印算术；assistant 只验结构恒等不判语义；P5 适配器字段 unknown；注入消息的生成时序不可从事件流证明；本包不认证 provider 缓存语义或实际思考量。公开校验（`-I -S`）只重新推导 P1/P2 端点并核对封印；P3/P4/P5 端点与 `cross_binding` 布尔只存在于 result.json，公开重放不重derive它们——result 侧篡改不被公开校验发现（封印仅覆盖 evidence.json），evidence 侧篡改必在封印核对处被拒。

## 整改记录（I1，2026-11-16 独审后）

非作者独审发现 `cross_binding.req3_appended_roles_match_capture_evidence=false` 为实现错位（取 appended 第2项与 assistant 行比较，off-by-one）造成的假阴性绑定布尔；已改为按三角色 zip 全等对齐，重新生成 result.json（新 SHA `105fa57fc27c0a878234e2924cc1e69973a45fa27a2a59047fef868f4053b2b6`，值=true），verify.py 同步更新（新 SHA `19b336a5eefc680709bda1f30dd9343f9da0ad1a0a9e8f684f056c9e2775449d`），evidence 不变。旧字节归档于私有 loop3/pre-i1-delta/（含旧 result.json 与不变 evidence；旧 verify.py 字节另存 verify-old-6de3d025.py）。
