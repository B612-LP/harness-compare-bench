# Codex 请求侧最小捕获 — 执行记录

- 日期：2026-11-17（Asia/Shanghai）；窗口 2026-11-16 22:24 起至 2026-11-17 12:00（用户口头授权"随便测试"，goal-round6 objective 明确点名 Codex 侧捕获在范围内）。
- 真实运行预算：本环 2 次 Codex 真实运行（计划内，各 1 次；无重试）；此前窗口累计 12 次（GLM r1–r6、t2×2、t3×2、DS×2）。
- 基线：公开仓 10230d5a（v1.71 发布后）；冻结页 README 于首次真实运行前写好（SHA `dccc9e01…`，mtime 04:10 前后）。

## 问题

请求侧直接证据此前只覆盖 DSH（§4.50–4.61）。Codex（同一评测 A 组另一 CLI）的请求组装是否同族稳定、任务载荷是否与 DSH 相同、会话状态机制是什么——老师归因定责问题在第二个 Harness 上的直接检验。

## 方法

- 隔离 `CODEX_HOME=~/.codex-capture-loop14`，config.toml 与 r1109 正式批快照同构（model deepseek-flash、provider deepseek、base_url 换成本地 capture proxy、wire_api responses、effort low、approval never、sandbox danger-full-access、skills 关闭）。
- capture proxy 8800 → https://api.deepseek.com，逐字节记录全部请求/响应；mock 干跑一次验证 wiring（0 真实请求；mock 不能产 responses SSE，codex 5 次重连后 exit1，属预期）。
- 任务与工作区与 DSH 捕获环一致（capture-r1 工作区：`TASK.md` `68599aec…`、`inputs/exercises/dominoes/dominoes.py` `89f1fede…`，两 run 前后逐文件 SHA 与 DSH 基线一致，rebuild no-op）。聚合规则=`sha256(sorted("relpath:filesha256\n"))`（UTF-8），值 `46f98067…` 可由 evidence.workspace.files 复算；初版 evidence 曾含一个不可复算的聚合值 `c6b1797b…` 与「13 文件」表述，均在发布前订正（pre-delta 归档在案）。

## 主要观察（证据文件承载，此处仅摘要）

- **P1 跨 run**：req1 非字节恒等，但 diff 恰 11 叶、全部 id 类（client_metadata 6 + input 条目 id 4 + prompt_cache_key 1）；id 归一后 canonical 恒等（SHA pin `351bc938…`）→ verdict `codex_assembly_stable_ids_generated`，与 DSH §4.54 的组装稳定+逐请求 id 同族（差异：Codex 的 id 在 message 层而非 call 层）。
- **P2 run 内**：两 run 的 input 均严格前缀扩展（r1 4→7→10、r2 4→9）；追加形状随模型执行分步不同（r1 逐步 [reasoning,function_call,output]×2；r2 一步 [reasoning,fc,fc,output,output]），delta [1534,882]/[1855]——追加性成立、形状属响应侧自由度。
- **P3 跨 Harness 任务面**：Codex input[3] 任务消息 214B == prompt 文件 == DSH messages[1]（字节恒等）；Codex 自带 instructions（developer，17119B）+permissions（362B）+environment_context（410B，含 cwd）三层包裹，工具 8 个；DSH 为 system 2593B+22 工具+4 条 user 上下文消息。
- **P4 会话状态机制**：`store=false`、无 `previous_response_id`、`include=["reasoning.encrypted_content"]`、reasoning 项携带 encrypted_content 逐轮回放——全量重发+加密推理回放；`prompt_cache_key == thread_id`。
- 响应侧（模型输出/final 行/tokens）不入任何终点；两 run final 文案差异属响应自由度，已登记不入档。

## 验证器与套件

- `verify.py`（stdlib）：build 模式从私档 5 个请求原文逐字节重建（前缀性/状态机制/缓存键/P1 分类/P3 任务面/归一恒等），replay 模式只核封印一致性；泄漏扫描拒 /Users 与凭据形状。
- `test_verify.py`：21 用例四档（普通/-O × 有/无 `CX_ARCHIVE_BASE`）全 OK——合成两 run 全管线、13 类篡改、dup key/1e999 拒绝、真档公开重放与 result 逐字节比较、CLI 拒绝/独占/缺参、env 门控真档端到端。
- 四路一致性（真档）：私档重建（普通/-O）与包内 evidence/result 逐字节相同；公开重放（普通/-O）与 result 逐字节相同。

## 时间线（文件系统时间，Asia/Shanghai）

- 04:09–04:10 侦察与冻结页/私立题/profile；04:10 mock 干跑（0 真实）；04:11 真实 r1（04:11:13–19）、r2（04:11:44–48）；04:12–04:13 常量提取与 evidence-draft；04:14–04:17 verify.py 实现与构建；04:18–04:21 套件修复至四档全绿；04:22 本记录与 SELF-ACCEPT。
- 常量更正披露（重要）：evidence 构建过程中两次发现草稿常量与实测不符并即时订正——①任务文本 SHA 草稿值 `1ec2cc15…` 为误记，实测=7a7c57c7…（与 prompt 文件/DSH 消息同串）；②instructions SHA 草稿尾段凭记忆补全错误、instructions 字节数草稿 16979 为字符数（实测 UTF-8 17119B）。两处均在 build 首次成功前由构建器 pin 检查拦下并以实测值替换；最终 evidence 由实测常量构建并经四路一致性核验（教训重申：常量必须当场测量，构建器硬等 pin 是最后一道闸）。
- 套件首跑 5→16 errors 的根因（合成 fixture 与真档口径差）：文件字节含尾 `\n` 而快照 sha 未含、合成前缀未复用同一 id 对象、normalized/workspace/byte_equal 三个模块 pin 未随合成刷新、`cls.d, v = refresh(v)` 元组解包遮蔽模块名、dup-key 用例构造错误；逐一修复后四档全绿，中间态未单独留存。

## 已知限制与诚实披露

- 单任务、单模型（deepseek-flash 官方 API 模型 id，与桌面账号 `deepseek-flash` 路由不同面，结论不表述为同款模型对照）、n=2 run 对；不外推。
- id 归一是**比较定义**（替换后相等），不是 provider 认证；client_metadata/prompt_cache_key 的生成语义未在 provider 侧核证。
- delta 与追加形状跨 run 不同属模型执行分步自由度；终点只主张 run 内追加性与前缀性。
- 公开重放无法证伪私档整体伪造；非作者独审（task-39）从原始 bin 独立重算补证。
- 发布前订正披露：独审指出 README「两 Harness 同模型」措辞不准确（三环模型 id 各异）与 workspace 聚合不可复算两点后，README 两处、verify.py（README pin/工作区文件 pin+规则）、evidence/result 已按上文订正并重建（pre-delta 全套归档 `loop14/pre-delta/`，订正后四路一致性与 21×4 套件重验全绿）；独审对订正的复核记录见私档 SEAL delta_recheck。
