# Codex responses 流观测口径：冻结样本校准（试行 0.2）

## 问题

[第五周反馈第 1 条](<../../反馈/2026-11-18-第五轮/验收条款-公开版.md>)要求先有唯一观测规范，反例达预期后才冻结。[DSH 口径试行 0.2](<../DSH观测口径校准-2026-11-19/README.md>)已明示不能套用到其他流式格式；本页给出 Codex CLI（0.163.0，`/v1/responses`，model deepseek-flash，reasoning effort low）responses 流的试行口径，用一组冻结原始样本（12 请求+12 响应+12 元数据、5 个运行会话，均为既有存档，无新运行）检验。**只验收下述已知样本，不冻结通用规范**；不把离线派生当新运行，不改正式 25 格与历史分数。

## 观测与判定口径

| 层 | 输入与输出 | 准入与未知 |
|---|---|---|
| L0 原件 | 请求/响应/元数据原始字节与 SHA-256。本样本响应为明文 SSE（无压缩原件），元数据含双方正文摘要与响应头（含模型、effort、代理转写标记 `response_framing=rechunked`） | 文件、长度或摘要不符则原件身份不可核；派生副本不能沿用原件承诺 |
| L1 事件账 | SSE 帧须为 `event:`+`data:` 两行、以空行 dispatch；末帧未 dispatch 拒；事件名限 13 种 `response.*` 且与 `data.type` 一致；`[DONE]` 仅允许为尾段（本样本未出现，该门由合成种子覆盖） | 空段、名单外事件名、类型不一致、截断流、首尾空段均拒；不在物理字节层面排序或删帧 |
| S1 信封与条目门 | `response.created` 首、`response.completed` 末、`response.in_progress` 恰一次；三阶段帧信封身份键（`id`、`model`、`object`、`created_at`）一致，`in_progress` 状态不得改写，`completed.status=completed` 且无错误；非阶段帧禁携 response 信封。条目 `output_item.added→done` 不重复不反向；三族 delta 累计==done 值；`completed.output`==done 条目序列 | 任何一门不满足即该流不可核，不猜补；异名帧携外 ID 信封按错绑拒 |
| S2 分组与承接 | 无 `previous_response_id`、`store=false`，续请求历史在 `input` 内承接（reasoning+function_call+function_call_output）。分组用 call_id 连通分量与 session-id/thread-id 前缀两法交叉，一致才收 | 交叉不一致即分组不可核；工具声明投影按名称/描述/参数定义核对，不要求对象恒等 |
| D 逐包绑定 | 每包请求与响应正文各自对照元数据登记摘要（双 SHA），先拒来源不一致再解析 | 摘要不符整包不可核；元数据不能单独认领正文内容 |
| G↔W 本地会话 | `session.jsonl` 只取 `item.completed` 条目；`item.started` 计入会双重计数。wire item id 与本地 id 不同体系，按内容值绑定：agent_message 逐字节比 `output_text`；command 按声明适配（wire `arguments` 键为 `cmd`，本地串形如 `/bin/zsh -c/-lc '<cmd>'`）比对；cmd 含单引号时引号形态不可证 → `quoting 不可证`，不冒充匹配 | 无对应 wire 调用的本地条目如实计 `无对应`；条目数两侧分账，不互凑 |

0.2 起字母映射 v1 落地（[冻结门清单](<../观测规范冻结门清单-2026-11-23/README.md>)）：旧层名 L2/W/H→S1/S2/D，证据节链字母 A/B/C/H→V-group/V-meta/V-stream/D-persha，工具声明门落地为单列 V-tool-decl 键（映射表中「并入 V-stream 佐证」的显式登记偏差）；L0/L1 与 G↔W 维持。

规范 JSON 计 UTF-8 字节：键按码点排序、无额外空白、数组保序、不做 Unicode 归一化、不删字段与 [DSH 页](<../DSH观测口径校准-2026-11-19/README.md>)共享；**数字子口径不称相同**——本页既有投影规范 SHA 系臂 JSON 浮点渲染所得，不可与[数字口径定版候选 v1](<../数字口径定版候选-2026-11-23/README.md>)直接比较；自 0.2 起后续重算采用 v1 profile（前瞻采用，既有 SHA 不重算；本页受检面输入侧样本请求零浮点，工具声明投影与逐包绑定结论不受渲染差异影响，见[对齐审读](<../观测口径试行对齐-2026-11-23/README.md>)发现 F3）。LF/CRLF、键序、等值转义或 gzip 重分帧可改物理字节，不应改受检值。等值 JSON 重编码只保留值相同，不沿用原捕获字节承诺。

## 证据与结论（12 包 / 5 运行）

- **V-group（分组与承接）**：5 组 [[1,2,3],[4,5,6],[7,8],[9,10],[11,12]] 与 5 个会话一一对应，两法交叉一致；12 包请求顶层键同集（`client_metadata,include,input,model,parallel_tool_calls,prompt_cache_key,reasoning,store,stream,tool_choice,tools`）；运行内 call_id 承接链共 7 条全部成立（后续请求承接本运行既有 function_call）。
- **V-meta（元数据）**：12/12 为 model deepseek-flash、effort low、`response_framing=rechunked`（代理转写——正文以代理可见分帧为原件，服务端原分帧不可核）。
- **V-stream（流内部一致）**：12 流信封门与条目门全过；12 个 response id 全异、5 个运行的响应记录互异、同运行内 `input` 逐包增长。
- **D-persha（逐包双 SHA，L0 级绑定）**：12/12 全绑定。
- **V-tool-decl（工具声明，S2 层）**：12 请求的 tools 投影（名称+参数定义规范 SHA）同集，共 9 条声明；跨包不一致即拒（一致性门）。
- **G↔W 绑定**：agent_message 6/6 逐字节匹配；本地 command 完成条目 7 对 wire function_call 7（两侧平衡）；适配匹配 5，2 条 cmd 含单引号（正则模式串）→ quoting 不可证，无对应 0。

## 反例与待验

- **等价表示不翻判（合成种子）**：同一 SSE 换 CRLF 行尾、JSON 值规范重编码（键排序+非 ASCII 直出）、gzip 重帧，裁定不变；尾部多一个空行（未 dispatch 的空尾帧）拒。
- **真改不被等长掩盖**：本线（Codex）深链运行对旧样本已证明参数文本等值重编码（255→277 B）与真实改值可以区分（统一协议 0.2 候选对照节载结论，见[对齐审读](<../观测口径试行对齐-2026-11-23/README.md>)发现 F4；原始对照在私档，本页只登记结论不重算）；DSH 线另有同尺寸真改使选定命中 8→7 的公开对照可跨线参考。本页合成种子集尚无同尺寸真改负控，列入待补。
- **错绑与缺失不冒充（合成种子）**：名单外事件名（如 `response.queued`）携外 ID 信封帧拒；`in_progress` 对象 status 改 `completed` 拒；末帧缺空行 dispatch 拒；截断流拒；跨运行 call_id 错绑拒；元数据正文摘要不符拒；请求顶层键出现异集 → 标 `unknown`，不静默收下。
- **样本缺口（如实登记，不补造）**：本样本无 `[DONE]` 尾段原件、无日志层变体原件、无独立捕获的第二来源——相应门只由合成种子覆盖或只作声明（rechunked 标记），不充当已验证；未做单变量干预，不估 Harness 效果。

## 复核与外推边界

实现与全部中间记录在私档；公开证据为派生汇总（[evidence.json](<evidence.json>)，按运行聚合，不含会话标识与原件路径），`python3 verify.py --self-test` 可核对公开字段与分母的一致性，不是隐私检测器，也没有原件不能重做身份绑定。内部非作者独审情况见私档记录；老师要求的受控第三方原件核验尚未完成。S2 分组与承接面不是服务端实际摄入，不等于 token 数或费用。本口径只覆盖 Codex responses 流该冻结样本；messages 线与其他产品不适用。试行 0.2 不冻结（0.1→0.2 升版=字母映射落地、数字口径分账改述、跨线参考条目与承诺句补齐，见[冻结门清单](<../观测规范冻结门清单-2026-11-23/README.md>)）；新增近错或真实变体需另版重验后才可升版。
