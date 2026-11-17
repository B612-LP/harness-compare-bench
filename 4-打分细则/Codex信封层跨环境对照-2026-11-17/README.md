# 冻结协议：Codex 信封层跨捕获环境对照（含 DSH 跨会话控制）— 2026-11-17

状态：**预注册冻结（实现前）**。探索性事后（复用既有捕获档，0 新运行）；先验披露见文末。

## 问题
§4.62 在单一捕获环境（loop14 CODEX_HOME）内确认 Codex 把任务消息用 instructions（developer 层）+permissions+env_context 包裹、任务面与 DSH messages[1] 逐字节恒等。**未回答**：这些信封层里哪些字节是随捕获环境（CODEX_HOME/工作区/任务）变化的、哪些在同一环境跨 run 稳定——即「Harness 包裹层」自身的归因分解（binary/config 固定 vs 运行时生成）。DSH 侧已有跨 build 系统提示对照（§4.60），但缺**同 build 跨会话**的请求侧信封控制组。

## 数据面（全部既有捕获档，只读）
- Codex：loop14/capture-codex-r1（3 请求）/capture-codex-r2（2 请求）；loop15/codex-t3-r1（3）/codex-t3-r2（3）——两套不同 CODEX_HOME、同 codex 0.163.0。
- DSH 控制：loop1/capture（capture-r1，3 请求）；loop7/t2-r1（7）；loop8/t3-r1（16）——同 DSH build 时代跨会话/跨任务。
- 每请求取 req1（首个请求文件）；DSH 侧另取 messages[0] 与 tools。

## 层定义（实现前冻结，避免实现期猜结构）
- Codex 体（Responses 形，含顶层 `instructions` 与 `input`/`tools`）：
  - L-INS = `instructions` 字段字符串（存在才定义；缺失记 absent，不算差异面）。
  - L-INPUT-ENV = `input` 数组**除最后一项外**的逐项 (role, kind, bytes, sha256) 有序列表（末项按规则视为任务消息，不进信封层）。
  - L-TOOLS = `tools` 数组计数 + 逐项 canonical JSON sha256 的排序多集。
- DSH 体（chat 形，`messages` 数组）：
  - L-SYS = messages[0]（system）(bytes, sha256)。
  - L-TASK = messages[1]（按既有先验任务面位置）——只记录，不参与信封对照。
  - L-TOOLS = `tools` 计数 + canonical sha 多集。
- 比较单位=层；每层三态分类 {identical, differs, absent}。

## 终点（全部描述性）
- E1 清单：6 个 Codex req1 的 (n_input_items, roles 序列, L-INS sha, L-TOOLS 摘要) + 3 个 DSH req1 的 (L-SYS sha, L-TOOLS 摘要)。
- E2 Codex 跨环境：loop14-r1 vs loop15-t3-r1 逐层分类（L-INS/L-INPUT-ENV/L-TOOLS）。
- E3 Codex 同环境跨 run：loop14-r1 vs r2；loop15-r1 vs r2（逐层分类）。
- E4 DSH 跨会话控制：loop1-capture-r1 vs loop7-t2-r1 vs loop8-t3-r1 的 L-SYS/L-TOOLS 逐对分类。
- 主 verdict：`codex_inputenv_<a>_tools_<b>__dsh_sys_<c>_tools_<d>`（a–d∈{identical,mixed,differs}汇总为 stable/mixed/varying；实际观测 `codex_inputenv_mixed_tools_stable__dsh_sys_stable_tools_stable`）。顶层 `instructions` 字段在本数据面全部缺失，按冻结规则按 absent 处理、不进入 verdict 段（模板首版含 ins 段，实现修订后移除——独审 L1 订正，数据与终点未变）。

## 边界与不认证
- 全部为 product-archived wire bytes；不认证模型内部/provider/HTTP 服务端/二进制身份。
- 「stable」指字节恒等，不指语义恒定；「varying」不定位变化原因字段（env_context 内嵌 cwd/session 等只按字节差登记）。
- 任务消息排除规则（末项/第二项）是结构性约定，若实际布局不符由分类失败（absent/not_applicable）暴露，不得为凑分类改规则。
- 单任务面（capture-r1/t2/t3/capture-t3）+单模型通道；不外推其他任务/Harness 版本。
- 0 新运行；事后探索，先验披露：作者冻结前已知 loop14 层量（instructions/permissions 362B/env_context 410B/任务 214B/tools 8）与 DSH loop1 system 2593B、tools 22；**未读** loop15/loop7/loop8 的 req1 层载荷。

## 公开档
- verify.py（stdlib，双模式 fail-closed）：--archive-root（含 loop14/loop15/loop7/loop8/loop1 的窗口根）+--build-evidence（raw）｜--evidence（公开重放）+--output。
- test_verify.py、evidence.json、result.json、EXECUTION-RECORD.md（FS stat 时间线）。
