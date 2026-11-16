# 捕获会话事件层与请求层溯源（2026-11-16，探索后冻结）

目的：把「同 run 内」本地 I 事件层与会话标题辅助请求的 wire 消息逐条对齐，回答每条请求消息来自哪个事件、经过什么变换。这是请求侧直接捕获（§4.50）的溯源深化：不只证明请求间前缀恒等，还证明请求内容可由本地事件流确定性重建。纯离线，0 新运行。

先验曝光（如实）：作者探索时已接触私档原文与全部对应关系；非盲前预注册。

## 固定数据源
- 私档：捕获会话日志副本 `session.v4.jsonl.zstd`（SHA256 `5c2bf4d4840525c0df59932b705f44615d9ae3888c4d66b3347b19670e339ba4`，29 事件）与 3 个 wire 请求原文（`001/002/003.request.bin`，SHA 等于捕获包已登记的 request_sha256）。
- 公开 pin：[捕获 evidence](<../DSH请求侧最小捕获-2026-11-16/evidence.json>) `f3e4fab3cd0d742ce4840f1e3b57423b62094c4cd8b7a939b3b347658b4aeaa1`、[捕获 result](<../DSH请求侧最小捕获-2026-11-16/result.json>) `3de57557fe7f3c74e6abc041e5181fc415595299b9678ed59d271f8abe596357`、[捕获 README](<../DSH请求侧最小捕获-2026-11-16/README.md>) `a26c7ec7df5dc052ce708434a3cbfa2b50deca2745effa1b91a5877f279c04e7`、本 README。

## 冻结判定（exact = 私档内容字符串逐字节相等；公开只发布布尔与形状描述符）
- P1 循环消息内容同一：8/8（req1 system↔事件7；user×4↔事件8–11 各单 text 块；req3 tool×2↔事件20/21 块文本）。
- P2 assistant 变换：事件17 tool-call 块 {id,name,arguments} → wire {content:null,tool_calls:[{id,type:function,function:{name,arguments}}]}，id/name/arguments 字符串逐字节相等 2/2；wire tool 消息 tool_call_id ↔ 事件 toolCallId 2/2。
- P3 工具声明：header 事件12 的 22 个 {name,description,parameters} → wire {type:function,function:{…}} 名称与三字段逐字段相等 22/22。
- P4 请求级字段：model/max_tokens 来自事件12 config（glm-5.3-flash/128000）逐值相等；标题请求（事件15）：system 逐字节相等、user = 固定前缀 + 事件8 文本的 compact-JSON 嵌入（messageSeqs=[8]）、maxTokens 4096/route 的 provider+model 逐值相等。
- P5 适配器层未识别字段：wire 顶层 stream/stream_options/thinking/tool_stream 不在会话事件流内（provider 适配器层），记 unknown，不以事件流外推。

## 边界
n=1、单 provider、v4 日志代；assistant 语义等价不判（只结构）；内容值全部不入公开档（映射表只含 seq 对、字节、布尔、形状描述符如「单 text 块恒等」「tool-call 块改名嵌套」「compact-JSON 嵌入」「`<path>/<type>/<content>/N: 行` 读渲染」）；spliced 事件 3/5（插入任务提示/排出 1 条）与请求时生成注入（AGENTS/runtime-context/skill-catalog，source 元数据在事件内）如实分列；不推其他 run/provider/产品。

## 验收
verify.py 私档模式由上述私有源重建映射并写证据；公开模式校验封印、算术内部一致性与捕获 pin 绑定（不含内容重放）；测试含 pin 篡改/映射错位/变换反例；非作者独审后整合。
