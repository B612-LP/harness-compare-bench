# 执行记录：请求侧跨日稳定性与凭据面归因（2026-11-17）

## 问题
同一 app 构建（app.asar mtime 2026-11-13 15:31:48、版本 0.2.2-rc.3）与同一 profile/工作区/prompt 下，今日真实运行 req1 是否与 2026-11-16 捕获（SHA 92220699…）逐字节一致；若不一致，漂移是否可归因到某一可操作的表面（构建/凭据/日期），为老师 P1①「外溢/截断/重组区分」提供请求侧端点。

## 方法
- 复用 loop1 stdlib 捕获代理（upstream https://open.bigmodel.cn:443，本地 127.0.0.1:8791，17:46:37 启动实例）。
- 运行前登记（公开冻结 README FS birth 17:41:40，初稿 SHA 455ba0b8…；FREEZE.json FS 17:41:53）：prompt=昨日 req1 messages[1].content 逐字提取 214B（SHA 7a7c57c7…）、工作区两文件 SHA 未变、tools 22、系统提示 2593B 等；先验=作者已读昨日全部事实，今日请求未读。
- attempt4（17:46:54，ZAI+DEEPSEEK 双 key）：3 请求全 200。
- attempt5（17:49:22，`env -u DEEPSEEK_API_KEY` 仅 ZAI key）：3 请求全 200。两次均同 profile/工作区/prompt/代理。

## 结果
- E1（跨日、双 key）：req1 34126B（昨日 33091B，+1035B）；tools 22→24（新增 `web_search`、`web_fetch`）；system +2 行内容（215B/150B web 指引）+2 空行；user 消息 1–4 逐字节相同；非消息参数全部相同。
- E1b（跨日、仅 ZAI）：req1=33091B SHA 92220699… == 昨日**逐字节相同**；aux=1042B SHA 9f2b6b3e… == 昨日逐字节相同；req3=34107B 同字节数异 SHA，差异恰 4 叶 id 类（tool_calls/0/id、tool_calls/1/id、tool_call_id×2——与环5 跨 run 分类同型）。
- 归因：预登记期望命中（req1(B)==92220699…），反证未触发 → 跨日漂移完全归因**凭据条件化的 web 工具注入面**（DEEPSEEK_API_KEY 在场→tools+system 注入；不在场→请求字节跨日稳定）。固定凭据面下跨日 runtime 稳定。
- 两 run 内前缀性均保持（req3=req1+3 条追加消息，非消息键相同，runA delta 恰 +1016B 与昨日同型）。

## 时间线（FS stat）
- 17:36 树态核对（HEAD 7b0353b2 clean）；17:42:27 代理首次起（8793，后因 profile 固定 8791 于 17:46:37 换 8791 重启，capture 目录重建）；FREEZE-AMENDMENT FS 17:45:39（先于任何成功请求）、FREEZE-AMENDMENT-2 FS 17:49:18（runA 后、runB 前 4 秒）；17:46:54 attempt4 成功；17:49:22 attempt5 成功。
- 17:54–17:58 verify.py 实现（初版 pinned 引用 NameError 一次、safe_path 拒绝跨根 prior 读取改 SHA 钉定直读一次、系统提示差异方向反转一次[added 应取 runA-only 行]、req3 比较误用 req1 体一次、pin 常量 216/151 系早期 difflib 探测把 '+' 前缀计入应为 215/150 一次、EXPECTED 叶路径补前导斜杠一次）；17:58:20 evidence/result 落盘并四路一致（build/replay×普通/-O 全 cmp 逐字节同，幂等重建同）。
- 17:59–18:04 test_verify.py 19 用例（合成两臂+对抗+CLI+env 门控真档重放）；修 parse_float 拒 1e999、synthetic prior 路径深度、drift 反例改 pin 翻转法（改文件会破坏 summary bytes 一致性，fail-closed 正确行为）；18:04:21 终版。18:05 四档全绿（真档 19 OK×2；无 env 18 OK skipped=1×2）。

## 预算与修订披露（经非作者独审订正，时间线以 FS stat 为准）
- 冻结页原预算=1 计划运行+≤1 零请求重试。实际：**3 次** 0 请求失败（attempt1 17:43:00 MISSING_CREDENTIAL：key 未导出；attempt2 17:44:33 包装器 `dsh headless --profile` 参数位置错误；attempt3 17:45:59 ECONNREFUSED 8791：代理端口与 profile 不符）+attempt4 成功+attempt5 归因对照。修订落盘真实顺序（FS）：FREEZE-AMENDMENT.json 17:45:39（先于任何成功请求）；FREEZE-AMENDMENT-2.json **17:49:18——runA 3 请求完成（17:47:02）之后、runB 首请求（17:49:22.109）之前 4 秒**，预登记期望/反证覆盖 runB 不覆盖 runA（初版 EXEC 写「均在任何成功请求之前」为假，已订正；声明时间戳 17:46:30/17:53:30 与 FS 不符，以 FS 为准，私档 FREEZE-AMENDMENT-TIMELINE-NOTE.json 为权威订正记录）；成功请求共 6 个（2 run×3）。

## 已知限制
- n=1/臂；同一任务面单模型；字节为传输层非 token；字节同一不证明模型行为不变；web 工具在场≠被使用（两 run 均未调用 web 工具，0 次 web 调用）。
- id 类差异（4 叶）仅证明逐 run 生成物，不构成任何行为/质量结论。
- 归因针对「捕获上游响应的请求字节面」；不认证模型内部或 provider 行为。
- 公开档不含任何请求正文值；公开重放只复核 pin 与结构，内容级比较在构建时由私档完成（result-only 字段不受 evidence 封印保护）。

## 发布前订正披露（非作者独审 F1–F9）
- F1–F4（时间线）：初版「两次修订均先于任何成功请求」「4 次失败」「冻结 17:49」与 FS 矛盾，已按 FS stat 订正（见上「预算与修订披露」与时间线行）；私档 FREEZE-AMENDMENT-TIMELINE-NOTE.json 为权威订正记录，原 amendment 文件不追改。
- F5：verify.py prior-SHA 不符时 prior_body 未定义致 NameError（rc1 traceback）→改为显式 Invalid（rc2 干净失败，missing/mismatch 均 fail-closed）。
- F9：build 先写 evidence 后校验，校验失败会残留无效文件→改为先 loads+validate_public 再落盘。
- 低危登记：F6（E4/E5 仅私档）、F7/F8/F10/F11 维持披露口径；订正后 evidence/result 幂等重建并四路复验。
