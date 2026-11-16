# Codex 深链与加密推理回放 — 执行记录

- 日期：2026-11-17（Asia/Shanghai）；窗口 2026-11-16 22:24 起至 2026-11-17 12:00（授权同环14：goal objective 点名 Codex 侧捕获、额度「随便测试」）。
- 真实运行预算：本环 2 次 Codex 真实运行（各 1 次，无失败无重试）；另有 1 次 `DEEPSEEK_API_KEY` 未注入的即时失败（exit 1、0 请求、不计预算）。
- 基线：公开仓 0f3eef0（v1.72 发布后）；冻结页 README 于运行前写好（SHA `bdc74881…8336`）。

## 问题

环14 证得 Codex 首请求跨 run 差异恰 11 叶全 id 类、会话状态=全量重发+加密推理回放。本环把协议延伸到深链（12 文件按序读任务，与 DSH §4.56 同任务面），新增一个环14 没有的机制问题：**同链位 reasoning 项的 `encrypted_content` 跨 run 是否恒等**——恒等则加密层对确定性输入是确定性的；互异则加密推理回放属逐请求生成物，会话状态在字节面不可跨 run 复现。

## 方法

- 与环14 完全一致的观测设置：隔离 `CODEX_HOME=~/.codex-capture-loop14`、capture proxy 8800 → https://api.deepseek.com（每 run 重启换捕获目录 loop15/codex-t3-{r1,r2}）、wire_api responses、model deepseek-flash、effort low。
- 任务：workspace `/Users/b612-lp/bench-workspaces/capture-t3`（13 文件），prompt 60B（`e7fea6df…53d4`，与 DSH §4.56 同任务通用措辞）；workspace 聚合（规则=sha256(sorted("relpath:filesha\n"))，UTF-8）运行前后均 `282e86ec…1329`（rebuild no-op）。

## 主要观察（证据文件承载，此处仅摘要）

- **P1 运行内**：两 run 请求链均严格前缀扩展（r1 4→7→10、r2 4→10→13）；追加形状 r1 逐步 [reasoning,fc,output]×2、r2 步1 [reasoning,message,fc,fc,output,output]（一步含 message+两调用）+步2 [reasoning,fc,output]——执行分步跨 run 不同（模型自由度），追加性成立。
- **P2 跨 run**：首请求 diff 恰 11 叶全 id 类（client_metadata 6+条目 id 4+prompt_cache_key 1），归一后 canonical 恒等（SHA pin `1dadb193…48b5a`）；req2/req3 的跨 run 差异=id 类+执行分步形状差（len），登记不计分。
- **P3（新问题）加密推理回放稳定性**：同链位（第1、第2个 reasoning 项）`encrypted_content` 跨 run 全部互异，`summary` 全部恒等 → **encrypted_per_run (observed)**：加密推理回放属逐请求生成物，会话状态在加密层不可跨 run 复现；明文 summary 层恒等（两侧 summary 均为空列表——「恒等」仅为空对空观测，无区分度）。
- **P4**：`prompt_cache_key==thread_id`、`store=false`、`include=["reasoning.encrypted_content"]` 全部 6 请求成立。

## 验证器与套件

- `verify.py`（stdlib）：build 从私档 6 个请求原文重建（前缀性/lens/shapes/deltas pin、状态机制逐请求、req1 11 叶分类+归一恒等、加密稳定性按链序配对、任务面 60B pin）；replay 只核封印一致性；泄漏扫描拒 /Users 与凭据形状。
- `test_verify.py`：11 用例四档（普通/-O × 有/无 `CXCHAIN_ARCHIVE_BASE`）全 OK——合成两 run 全管线（含加密互异/summary 恒等构造）、前缀篡改、dup key/1e999/浮点拒绝、公档篡改 rc2、独占写 rc2、缺参 rc2、真档公开重放逐字节比较、env 门控真档端到端（build→replay 与包内件逐字节同）。
- 四路一致性（真档）：私档重建（普通/-O）与包内 evidence/result 逐字节相同；公开重放（普通/-O）与 result 逐字节相同。

## 时间线（按文件系统 birth/mtime 订正，Asia/Shanghai）

- 05:24 冻结页写入；proxy 就绪；首次 r1 尝试失败（`DEEPSEEK_API_KEY` 未注入，exit 1、0 请求——0 请求无捕获物，文件系统不可验，按披露接受）；注入后 r1 成功（3 请求 bin 出生 05:24:20–23，全 200）；proxy 换 r2 目录后 r2 成功（3 请求 bin 出生 05:24:35–40，全 200）；05:24:44 运行后聚合核对一致；05:25:04 chain-analysis.json；05:27:26 verify.py 终稿；05:27:37 evidence/result 生成（早于套件定稿——顺序如实登记）；05:28:38–05:29:20 test_verify.py 修复至四档全绿；05:29:54 本记录初稿；05:30:03 SELF-ACCEPT 封印。
- **记录订正披露（task-40 独审发现，2026-11-17 05:52 归档初稿后订正）**：本记录初稿的时间线为事后按印象补写，与文件系统系统性不符（初稿叙述 05:26–05:58，实际全部事件发生在 05:24–05:30；且初稿叙述了写入时尚未发生的事件）。初稿字节已归档（`until14/loop15/pre-delta/EXECUTION-RECORD.md`，SHA `b9b49cac…079f6`）；本节按 FS birth/mtime 重写。技术工件与全部终点不受影响（独审①–⑥独立复现全过）。
- 实现修正披露（两项，均发生在 evidence 生成前）：①req2 期望行补 `summary_equal` 键；②加密配对从绝对 input 下标改为链序——r2 执行分步使同序 reasoning 项位于不同绝对下标（req3 侧 r1 [4,7] vs r2 [4,10]），绝对下标配对是设计错误，链序配对才是「同链位」的正确语义（独审以实际下标实证）。
- 套件修复史（合成 fixture 与真档口径差）：items 键错位、构造器名遮蔽、合成段重写、thread_id/pck 对齐、变量顺序——逐一修复后四档全绿，中间态未单独留存。

## 已知限制与诚实披露

- 单任务、单模型（deepseek-flash 官方 API id）、n=2 run 对；不外推。
- `encrypted_per_run` 是**观测**结论（两 run 对内互异），不认证 provider 加密语义或随机性来源；`summary` 恒等为空对空观测（两侧均为空列表），无区分度。
- 执行分步差异（r2 一步 message+两调用）属模型自由度；本环链较短（每 run 3 请求即完成任务——Codex 单命令批量读取），DSH 同任务 15 请求的分步行为不可比，链长比较不构成 Harness 优劣证据。
- 公开重放无法证伪私档整体伪造；非作者独审（task-40）从原始 bin 独立重算补证。
