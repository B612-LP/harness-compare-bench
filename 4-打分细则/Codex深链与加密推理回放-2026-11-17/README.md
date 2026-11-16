# Codex 深链与加密推理回放（2026-11-17）

## 问题

环14（请求侧最小捕获）已证 Codex 首请求跨 run 差异恰 11 叶全 id 类、归一恒等，会话状态机制为「全量重发+加密推理回放」（`store=false`、`include=["reasoning.encrypted_content"]`）。本环把同一协议延伸到深链：同一 12 文件按序读任务（与 DSH §4.56 同任务面）真实运行两次，回答四个最小对照问题——

- **P1 运行内**：请求链是否严格前缀扩展、逐请求 usage 形状（无）；追加形状含 reasoning 回放项的分布。
- **P2 跨 run**：首请求 diff 叶分类（预期仍全 id 类）；主链逐对 diff 分类。
- **P3 加密推理回放稳定性**（本环新问题）：同链位 reasoning 项的 `encrypted_content` 跨 run 是否恒等——若恒等，说明 provider 加密对该 Harness 确定性输入是确定性的；若互异，则加密推理回放属逐请求生成物（与 id 同类），会话状态在字节面不可跨 run 复现。
- **P4 链尺寸**：请求数、尺寸增长、`prompt_cache_key`/`thread_id` 稳定性。

## 授权与预算

- 用户 2026-11-16 22:24 口头授权测试额度自由使用（「随便测试」）；goal objective 明确点名 Codex 侧捕获在范围内。预算：2 次计划真实运行 + 同授权失败重试 ≤2 次；0 次失败不补跑。
- 观测设置与环14完全一致：隔离 `CODEX_HOME=~/.codex-capture-loop14`（同一 config，base_url 指本地 capture proxy 8800 → https://api.deepseek.com，wire_api responses，model deepseek-flash，effort low，skills 关）；proxy 每次重启换捕获目录（loop15/codex-t3-{r1,r2}/requests|responses）。
- 任务面：workspace `/Users/b612-lp/bench-workspaces/capture-t3`（TASK.md + inputs/sequence/m01–m12，13 文件），prompt 文件 60B（SHA `e7fea6df…53d4`）与 DSH §4.56 同任务不同措辞（Codex 版为通用跟随指令）；workspace 聚合（规则=sha256(sorted("relpath:filesha\n"))，UTF-8）= `282e86ec…1329`，运行前后须一致（rebuild no-op）。

## 终点与判定（先冻结后执行）

1. P1：每 run 内请求 i+1 的 input 以请求 i 的 input 为严格前缀；逐请求追加形状登记。
2. P2：两 run 首请求逐叶 diff 全部分类到 id 桶（client_metadata/input id/prompt_cache_key）或 reasoning-encrypted 桶；归一（id→NORMALIZED、encrypted_content→NORMALIZED）后 canonical 相等记 `chain_stable_normalized`。
3. P3：主链同位 reasoning 项 encrypted_content 跨 run 恒等数/对数——恒等记 `encrypted_deterministic (observed)`，互异记 `encrypted_per_run (observed)`；只描述本 run 对，不外推、不认证加密语义。
4. P4：请求数/字节数登记；`prompt_cache_key==thread_id` 逐请求核验。
5. 响应侧（模型输出/final 文案/tokens）不入任何终点。

## 复算与边界

- verify.py（stdlib）两模式：build 从私档请求原文重算全部终点（前缀性/分类/归一恒等/P3 逐位比较）；replay 只核封印一致性。公开层不重放任何请求原文；私档真实性不经公开层认证。
- 单任务、单模型（deepseek-flash 官方 API id，与桌面账号路由不同面）、n=2 run 对；不外推。id/加密归一均为比较定义，非 provider 认证。
- 深链执行分步跨 run 可能不同（模型自由度），追加形状差异属响应侧自由度，不构成组装不稳定证据。
