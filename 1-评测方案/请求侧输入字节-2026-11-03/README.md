# 请求侧输入字节实验：条件、冻结与判定

> 2026-11-03 的新增机制研究，不是 A/B/W 正式产品复测；正式仍为 **25 行、每产品每题 n=1**。本页公开研究合同及修订事实，不包含私人运行器、内部计划或调用凭据。

## 研究问题与可答范围

在 DSH 的同一版本、模型、提示、唯一夹具工具和输出上限下，只改变工具结果外溢阈值，客户端组装的下一次输入大小是否稳定下降，且一个预先指定的双键端点是否仍正确？这是 **同 Harness 的局部干预**。不是五产品排名、跨产品成本比较、通用压缩保真、服务端最终输入测量或原生传输时延实验。

## 条件合同

| 项目 | 冻结条件 |
|---|---|
| 产品 / 系统 | DSH 0.2.0-rc.2；Node v24.22.0；macOS 26.6 arm64 |
| 模型 / 来源 | 官方 DeepSeek，`deepseek-flash` |
| 思考与输出 | `thinking enabled`、`effort low`、`max_tokens=1024`；只固定设置，不声称控制了实际 reasoning tokens |
| 输入 | 同一提示、同一 system、仅一个 fixture 工具及相同 schema；停用其余工具和技能 |
| 输入夹具 | 35,767 UTF-8 bytes；SHA-256 `fed57592028c9d8a9180c2b97f74a3cd5e0daa841aab244cf4aad78fe44626a2` |
| 提示 SHA-256 | `82f49e6223aad78640e412663d7f96dae4c14c3619d1af8ce292298e7ef75042` |
| inline 条件 | `maxInlineTokens=1000000`，本夹具完整内联 |
| bounded 条件 | `maxInlineTokens=512`，原生外溢策略保留首尾片段及引用 |
| 请求侧仪器 | 相同进程内转送＋loopback relay；固定官方 HTTPS 上游，不改变请求 JSON body；规范化 `Accept-Encoding: identity`，全缓冲响应 |
| 会话边界 | 每场新配置、独立进程/会话；每场最多 2 次模型请求、1 次夹具调用、240 秒、零自动重试 |

原提示：

```text
Call fixture_output exactly once. Then return only a JSON object with HEAD_KEY and TAIL_KEY containing the two observed values. Ignore checksum noise. Do not call any additional tool.
```

## 指标与预设分支

主指标为 `B_input = UTF8_bytes(canonical_JSON({system,messages,tools}))`。canonical JSON 为 key 排序、紧凑分隔、不转义 Unicode；角色、工具调用参数、工具返回和 schema 保留在相应组件内。辅助报告原请求 body 字节、各组件大小、序列化包络差及解码后工具文本字节。不要拿漂亮打印的 JSON 文件大小代替请求 body。

每场 `ΔB = B_input_after_tool − B_input_before_tool`；每个独立配对块 `R = ΔB_inline − ΔB_bounded`。冻结 **6 对 / 12 场**，块内顺序交替，见[冻结槽表](<../../3-表现现场/r20261103-input-bytes/freeze.json>)。固定样本，不根据中间答案或显著性扩样；失败不追加替代。两次 pilot 和所有 mock 均不算确认样本。

- 6 对都有效、每个 `R>0` 且中位数 `R≥16384 bytes`：重复支持该局部方向；再依据双键端点分成 retained / impaired。
- 任一方向条件不满足：unstable / different；有效配对不足 6：incomplete。
- 技术有效性与答案正确性分开：必须两次完整请求、真实且唯一夹具调用、35767 bytes 与固定哈希、调用 ID 串联、模型/low/schema 条件相符、完整 SSE 与正常退出。**错误答案本身不被筛掉或重跑。**
- 语义端点仅为最终 JSON 的 `HEAD_KEY=AMBER-731` 和 `TAIL_KEY=COBALT-492`；不测试中间噪声保留，不等于全部内容无损。
- 中位数、范围、逐对差值为主要描述；Wilson 区间及双侧符号量仅作本批描述，不证明总体概率、等效或通用机制。

## 失败、修订与分母

初始计划上限 20 live 会话 / 40 请求，包括最多两场 pilot。首场 pilot 只发出 1 请求：上游 HTTP 200、715 response bytes，但仪器拒绝不支持的编码，客户端收到 502，场次失败；原响应头未留存，**编码算法 unknown**。该失败保留，未改判、未替代、未计入确认。

在确认批启动之前，单独记录仪器 v2：规范化请求编码头但不改变 body；仍拒绝压缩响应，不做不受限解压。旧源哈希快照和旧失败留存。未使用的第二 pilot 槽改用于 DSH v2 技术验证，**取消本批 Codex live reference**，不增加 pilot；总上限收紧为 **14 live 会话 / 27 请求**。v2 pilot 技术有效后才冻结 6 对。冻结时间为 2026-11-03 20:13:44.493647 +08:00；12 确认场随后依次执行。

实际为 **14 live / 27 上游请求**：失败 pilot 1/1、有效 pilot 1/2、确认 12/24；另有 8 场 mock CLI 校准、0 模型调用。逐场见[分账](<../../3-表现现场/r20261103-input-bytes/batch-events.json>)。Codex 的当前原生 namespace/MCP 菜单只做了 mock 兼容校准，**live 未发、直接跨产品证据 incomplete**；不能拿模拟答案充作产品结果。

## 停止纪律及其机械保证边界

预设模型、schema、夹具或控制项漂移应停止余槽。本批所有 24 个确认请求已逐项复核，无实际漂移。执行器实时门只覆盖正常退出、两次请求、夹具收据及首请求控制哈希，**没有在每槽继续前机械检查第二请求的全部条件**；因此不能宣称停止器完备。完整逐场复核支持本批有效性，不反向制造更强的实时保证。冻结源码未被事后修补；复用执行器前须先补全 fail-fast 门并重新冻结，当前批次不再发射。

## 不可控制项

low 档不等于 actual reasoning tokens 已控制；缓存和 reasoning token 没有完整独立观测，不能填 0。捕获的 usage 仅作[逐场辅助字段](<../../3-表现现场/r20261103-input-bytes/README.md#辅助用量与缓存>)。relay 全缓冲改变分块/时延，规范化编码头也使其不是原生透明观察。客户端字节不是 tokens、费用，也不是服务端经过重写/截断/追加后的最终模型输入。客户端量的重复方向仍是本批可复核结论。

[表现现场及公开复算](<../../3-表现现场/r20261103-input-bytes/README.md>) · [最新综合报告](<../../5-评测报告/竞品评测报告-v1.5.md>)
