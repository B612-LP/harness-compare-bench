# 原生请求先导：声明子集外的真实响应与停止现场

**交付日期：2026-11-04；本研究目录与事件日期保留2026-11-03。状态：技术停止，`direct_observation_incomplete`。** 本现场不是成功的两请求配对，不产生正式分数、产品能力失败判定或 Codex/DSH 排名。条件确认没有启动；已有正式 25 行与此前 DSH 六对观察不变。方案见[技术门](<../../1-评测方案/原生请求技术门-2026-11-03/README.md>)，结论见[先导报告](<../../5-评测报告/原生先导-2026-11-03/README.md>)。

## 1. 真实请求顺序与守卫决定

Codex 0.163.0，alias `deepseek-flash`、low；一次真实先导，2026-11-03 15:47:02.688123Z 至 15:47:04.650198Z（进程观测 1.962056959 秒，exit 1，未超时）。

| 项 | Req1 | Req2 |
|---|---|---|
| 客户端请求实体 | 27,345 B | 40,170 B |
| 守卫 | 转发前批准；响应检查批准 | `second_suffix_invalid`，转发前拒绝 |
| 上游尝试 | **1** | **0** |
| 客户端 HTTP | 200 | 409（本地拒绝，不是模型错误） |
| 响应证据 | 33,961 B 首 SSE，完成标志有效 | 无上游响应；不得补作模型回答 |

首请求后 fixture 真实调用。第二请求前四项与实际首请求逐项同型同值，追加 `[reasoning,function_call,function_call_output]`，输入项数4→7。声明的仪器子集只接受两项 call+return suffix，因此在第二次上游转发之前拒绝。不是 prefix 漂移，不是没有 fixture，也不能把额外 `reasoning` 删除后当本批通过。

派生请求/首 SSE、逐请求 metadata、原 gate 和终止输出均随[公开清单](<publication-manifest.json>)列出；字段改写与原件/派生哈希关系见[映射](<projection-map.json>)。原件来源哈希不等于派生件哈希，遮盖派生件不冒充完整原始会话。

## 2. 早退计数陷阱：为什么真实合计是 1，而不是 gate 的 0

原 `session-gate.json` 在捕获文件数量/形态未满足完整两请求条件时早退，保留 `upstream_attempts=0` 默认值；这是**尚未完成计数**，不是实测零上游。其 `ok=false`、`primary_valid=false`、`capture_file_count_invalid` 和 `guard_reason=second_suffix_invalid` 均原样保留，不修改原收据消除矛盾。

计数权威链是 Req1 capture metadata 的1、Req2的0，与完成收据和机器账对齐，见[校正对账](<reconciled-accounting.json>)及[逐事件账](<batch-events.json>)。产品会话数、客户端请求数、上游尝试数与有效比较数必须分列：**1 / 2 / 1 / 0**。首请求 usage 的自报 input5628、cached3584、output64、reasoning35、total5692 仅辅助，不反推实际思考档控制、独立 cache 控制或计费。

## 3. 可以复算的字节，不能声称的效果

| Codex 客户端字段 | Req1 | Req2（拒绝转发） | 差 |
|---|---:|---:|---:|
| selected input（input+tools） | 25,873 | 38,698 | 12,825 B |
| input 分量 | 18,999 | 31,824 | 12,825 B |
| tools 分量 | 6,855 | 6,855 | 0 |
| wire body | 27,345 | 40,170 | 12,825 B |

fixture 源文件35,767 B，真实工具返回解码文本12,021 B。**12,825 B 是客户端已构造、但未上游转发的第二输入与第一输入的字节差**；不是两次模型输入 token 的差，也不是一个合格 Codex/DSH 对照的机制效应。对象自身序列化开销使分量和不必等于整体字段字节。实际 reasoning、cache、服务端最终输入与 Codex 输出 cap 仍未控制/未知。

分析分支为 `direct_observation_incomplete`：有效块0，块差数组空，中位差/范围 null。此前 DSH 六对观察不因这次无效先导改变，也不和本行拼成新效应量。两条严格 mock 的双键答案只校准仪器，不能替代这里缺失的真实最终回答。

## 4. 全阶段分账与未执行槽

| 事件类别 | 数量 | 上游尝试 | 正式准入 |
|---|---:|---:|---:|
| Codex 真实先导 product_run | 1 | 1 | 0 |
| 本地 native probe ×2 + 严格 CLI mock ×2 | 4 non_product_reference | 0 | 0 |
| WorkBuddy 直接二进制启动探测 | 1 interface_preflight | 产品网络 not_observed | 0 |
| 合计 | 6 events | 可确认模型上游 1 | 0 |

预算8 live/16上游未用满，不代表应补满。DSH 桥接先导1槽未尝试；有条件的六会话确认未启动（分析中 `confirmation_planned=0`，不是最初没有预留），三个条件预留块均未启动、有效块0，**不是三次真实失败**。不重试、不补样、不放宽此批合同。

WorkBuddy 5.9.3 的启动探测 exit -6/SIGABRT、0.28141 秒、无stdout/stderr；已见主进程、未见 helper，原因未知。模型任务0，产品文件操作分母0，TP/FN/FP/TN及率均 null。它不证明真实 GUI 路径、fixture读取或产品隔离；controller无网络不等于产品网络实测0。十二项 synthetic预检包含 hardlink/preopened-FD 两种成功内容旁路，不能写“隔离12/12通过”。详见[隔离可行性](<workbuddy-isolation/isolation-feasibility.json>)。

## 5. 公开复核与尚未覆盖

公开材料提供离线 `verify_scene.py`，以[清单](<publication-manifest.json>)和[派生映射](<projection-map.json>)核对文件、字段与字节口径。复制到独立目录后可运行：

```sh
python3 3-表现现场/r20261103-native-input-gated/verify_scene.py
```

复核器验的只是该公开派生现场及对账不变量；不能恢复私有原件、补齐第二次上游响应、验证模型身份、把 opaque token 解码成思考、证明第三方参与或完整 OS 审计。复核器哈希以清单为准，执行结果以实际退出状态为准；不能凭文件存在推断远端已推送、原件封印通过或真人已核验。

真实未参与项目的核验人、外部首读、身份/时间/签名仍 pending/null；准备检查不等于真人复核。历史5份原始压缩会话缺失、40条公开重复尝试逐run版本未知也未由本现场补齐。参见[未知登记 r6](<../../5-评测报告/未知登记-2026-11-03-r6.json>)。
