# REPORT — L4 cache 裸模型探针（l4-20261029-cache）

- 执行者：builder-codex；阶段 I（实现+零模型预检/合成测试）完成时刻：2026-10-29T20:2x+08:00（实钟见收据）
- 设计封印 D：`bb14897a7d1ac26c06697bb80a15d94158cd8ae0`；CLARIFICATION-L4-1（R3/R4）已全文纳入实现
- 状态：**阶段 I 完成，停待 E 封印 + lead 释放**。真实模型调用 0 次。

## 文件清单

| 文件 | 说明 |
|---|---|
| `tools/cache_probe.py` | 18 槽探针主入口：selftest / dry-run [slot] / run [slot] |
| `config/probe-config.json` | E 候选配置快照（端点+出处、三协议请求形状、prefix/nonce 规范、失败规则、usage 纪律；无凭据） |
| `probes/<slot>/dry-run.json` | 18 槽零网络走查收据（executed=0） |
| `probe-receipt.json` | dry-run 批收据（slots=18, executed=0, not_executed=18） |

## 槽位与顺序（全部读自 plan.json）

18 槽 = responses / anthropic-messages / chat-completions × block{1,2} × {fresh, repeat, nonce-control}。block1 协议正序（responses→messages→chat，order 1–9），block2 反序（chat→messages→responses，order 10–18）。全局按 order 串行，每槽最多一次外发。

## 阶段 I 测试计数

`cache_probe.py selftest`：**32/32 PASS**（socket 哨兵禁网；`load_api_key` 全程未被调用）。
新增 fake-HTTP 端到端：全 200 十八槽（18/18 外发、repeat paired、raw inventory 嵌套路径）、401 全停仅 1 次外发、429 停协议不殃及其他协议（13 次外发=6+6+1）、5xx 连续 2 停协议且 fresh 败 repeat 不发（14 次=12+2）、重复 execute 零额外外发（write-once 即拒）；usage 双层（映射嵌套三态+无偏 inventory）。覆盖：prefix 规范（ASCII/8217 字符≤16384 字节）、nonce 确定性+协议×block 独立+control 差异、fresh/repeat 请求体逐字节一致、control 仅换首 nonce、usage 四态分类（missing/null/zero/positive）、失败分类优先级（401/403→stop-global；其他 4xx 含 429→stop-protocol；5xx/network→consume+连续 2 停协议；3xx 不跟随→stop-protocol）、gate fail-closed（binding 缺失）、plan 18 槽/串行 order 不变量。

## 零调用证明

1. dry-run 收据 `executed: 0`（18 槽全部 dry_run 状态，未发任何请求）；
2. `run` 命令实测（E 前）：exit 3，`{"fail_closed": true, "reason": "runtime-binding.json 不存在…"}`——gate 检查先于 `load_api_key()` 与 `http_post`；
3. selftest 全程 socket 哨兵；`load_api_key` 仅存在于 run 路径，selftest/dry-run 代码路径无引用。

## 命令接口（E manifest 入口）

- 主入口：`3-表现现场/l4-20261029-cache/tools/cache_probe.py`
- 子命令：`selftest` / `dry-run [slot]` / `run [slot]`
- runtime 源码与实际配置（须 E 封印覆盖）：`tools/cache_probe.py`（sha256_8=194a9cec）、`config/probe-config.json`（sha256_8=c2131e96）

## 执行语义（E 后，R3/R4 全文内建）

- 门：与 codex 侧同 binding 四重 fail-closed；
- 每槽外发前先持久化 `intent.json`（R3 崩溃安全）；不跟随 redirect（专用 opener）；
- 端点来自 contract.probe_endpoints（三端点均有出处：r1022 bare_run.py / r20261029-mechanism 01-transport.json / 官方 create-chat-completion 文档）；
- 请求体：synthetic prefix（8192 字符目标）+ 首行 `NONCE:<确定性十六进制>`；fresh/repeat 逐字节一致（发送前自校验，不一致 fail-closed）；control 仅换首 nonce；block 间 nonce 独立；repeat 与 fresh 间隔 ≥5s（实测计时）；
- 留证：`request.body.json`（synthetic 文本，无密钥）、`response.body.raw`、`transport.json`（status/时延/header 名单/response id/raw body 字节与 SHA）、`usage.raw.json` + `usage.presence.json`（缺失/null/0/正值四态）；auth 头与密钥绝不落盘；
- 失败状态机按 CLARIFICATION R4 优先级：401/403 全停+立即通告 lead（其他 CLI 停新官方 API 槽）；其他 4xx 含 429、3xx、格式错停该协议；5xx/网络连续 2 次停该协议（成功清零）；fresh 无成功原始响应 → 同 block repeat 不发记 not_executed；control 若协议未停可发但不作 paired 对照；
- 记账：每槽 executed/failed/not_executed 三态（R1），原始结果不填零；reason 全程留档。

## 已知限制与语义边界（预注册 §2A/§3A）

- fresh 只是新 nonce，不宣称真实冷缓存；repeat 不保证热命中；「本条件未观测命中」≠服务端无缓存。
- 不把 miss==creation；首次 hit≠由本实验建缓存；creation 字段缺失/0 的解释分 wire 分层（responses 为 CLI 侧同名字段语义待探针回答；messages 为 anthropic 线标准键；chat 线官方无 creation 字段——缺键即协议层缺键，不得解释为无写入）。
- usage 分母/是否含 cached 按各 wire 原字段说明，禁止跨 wire 求和。
- 探针与历史 rollout 非同请求，禁止逐调用对应；历史「creation=0」按产品/字段源层分开陈述（codex=r1031 提取层 `or 0` 合并 absent/null/0；dsh=session log 键存在且值 0）。
- anthropic 兼容官方出处：https://api-docs.deepseek.com/zh-cn/guides/anthropic_api（lead fetch：base /anthropic、version/thinking.budget_tokens/cache_control 忽略、output_config 仅 effort、max_tokens 全支持、content string 支持；Bearer 与官方 ANTHROPIC_AUTH_TOKEN 路径一致；**cache_control 忽略≠无缓存/成本结论，creation 与否以 18 探针 raw usage 为准**）
- low 映射官方出处：https://api-docs.deepseek.com/guides/thinking_mode/ （lead web_fetch）：responses=reasoning.effort low、chat=reasoning_effort low、messages=output_config.effort low——与 SHAPES 一致，无形状改动。responses reasoning 字段若仍 4xx 首败按 R4.3 停该协议不适配（契约纪律不变）。
