# 机制复制实验预注册（2026-10-29，先于任何复制运行）

本文件在复制实验第一场运行之前定稿。目的：把「工具结果外溢(spill)→下一次调用输入骤降」的机制结论从**单一 Harness(DSH)单一夹具**扩展为**跨 Harness 对照**，并用一场**完整 raw SSE** 的新运行补上原 pair-1 的观测缺口（不重跑、不替代原六场）。

## 研究性质声明

- `experiment=true`、`group=research`：全部复制运行是研究诊断，**不进入官方产品比较**，无 truth/score。
- 夹具与原实验同源：`fixture-v1`（HEAD_KEY=AMBER-731 / TAIL_KEY=COBALT-492 + 420 行确定性噪声，large≈35.7KB）；提示词与原 PLAN 相同语义。
- 判分口径：exact HEAD/TAIL 观察 + 用量对照；无官方分。

## 注册的复制运行（共 3 场，全量报告，不选结果）

| # | 运行 | 产品 | 臂 | 预测（跑前登记，可证伪） |
|---|---|---|---|---|
| R1 | `repl-dsh-large-512-01` | DSH CLI 0.2.0-rc.2 | large / bounded / maxInlineTokens=512 | 2 次 HTTP 200；第 2 次调用总输入（含缓存）远小于第 1 次；**两段 raw SSE 完整**（v4 逐块追加 observer） |
| R2 | `repl-dsh-large-512-02` | 同上 | 同上 | 同 R1；两次独立运行重复性检查 |
| R3 | `repl-codex-large-01` | Codex CLI 0.163.0 | large / MCP 夹具 / 无 spill 策略 | Codex 无外溢机制：第 2 次调用输入**不出现** DSH 式骤降（近似维持 large 水平，或受其自身工具输出截断策略影响——两种结果都有信息量，如实记录） |

## 已知差异（披露，不掩盖）

1. Codex 侧夹具注册通道不同：DSH 用原生插件注入，Codex 用 MCP stdio server 返回**字节级相同**的夹具文本（同 SHA 校验）；工具名在 Codex 可能带 server 前缀，提示词语义不变。
2. Codex 侧无请求级抓取（无 preload observer）：用量取产品自报（agent.jsonl/会话 rollout），证据等级标注为 product-reported，不等同 DSH 侧 raw-SSE 级证据。
3. 每次 DSH 复制运行仍是 2 次调用语义（观察→回答）；若超时/失败按原样保留，不顺延补跑。

## 停止条件与重开条件

- 停止：3 场跑完即停；任何一场失败不触发替代重跑（与正式批次选样纪律一致）。
- 重开：仅当用户要求或夹具/模型 alias 变更需要重新对照。

## 结果落点

`RESULTS.md`（五段结构）+ 逐场原始收据于本目录；结论不外推为任何产品排名、通用节省率或金钱成本主张。
