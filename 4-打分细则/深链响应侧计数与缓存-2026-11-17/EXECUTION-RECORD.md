# 执行记录：深链响应侧计数与缓存（环18，0 新运行）

## 问题与预注册

- 问题：把环8「prompt 稳定/cache 波动」（单发 t1+DS）与环16（Codex t1/t3）的响应侧计量延伸到 DSH 深链 t2-r1/t2-r2（2026-11-16 深链两 run，7 请求 × 2 run = 14 响应，既有捕获）。
- 冻结：README SHA `849c96a45255e8831e124009526d9fa0fd3b0e19ba297af1fe0ad99d1685361a`（07:32:21 落盘）。**探索性事后**：作者 07:30:59 草探脚本（loop18/probe_usage.py）已读取全部 14 行 usage，07:31:38 私立题 loop18/DIRECTION.md 原样披露全部数值后才冻结；不伪装盲预测。

## 数据源与处理

- 私档 `loop7/t2-r{1,2}/responses/NNN.response.bin`（SSE 正文）+ `NNN.response.bin.meta.json`；每行绑定 raw SHA、meta `response_body_sha256`（与 raw 相等核验）、meta `request_body_sha256`、duration 分档（<2s/<8s/≥8s）、SSE data 帧数、末 finish_reason、usage 五键（含 details 子键）。
- 响应正文（任务文本/模型输出）不入公开档。

## 结果（product-reported）

- E1 prompt 跨 run 7/7 逐位置相等：7597/167/7816/7927/8034/8141/8174。
- E2 cached 跨 run 6/7 互异（r1 0/0/7552/7808/7872/8000/8128 vs r2 7552/128/7808/7872/8000/8128/8128，仅 pos7 相等）；r2 首请求 cached=7552>0 = 同前缀跨 run 缓存复用的响应侧见证（不认证服务端内部/命中路径/计费）。
- E3 每 run 主链（pos1、pos3–7）cached 单调不减；r2 pos2 辅助请求回落至 128。
- E4 schema 恒定：usage 顶层恰 5 键、prompt_tokens_details 恰 {cached_tokens}、completion_tokens_details 恰 {reasoning_tokens}（实测全 0）、每响应恰一次 usage chunk、finish∈{tool_calls,stop}、total=prompt+completion 恒等。

## 时间线（FS stat，Asia/Shanghai 2026-11-17）

- 07:30:59 草探 probe_usage.py（先验产生）；07:31:38 loop18/DIRECTION.md；07:32:21 README 冻结+FREEZE.json。
- 07:33:23 verify.py 初版；**三次构建失败（均 exit 2 无产物，07:33:30–07:34:10）**：①合成 schema 假设 completion detail 为空对象（实测恰 {reasoning_tokens:0}）②恒等式方向写反（GLM 语义 total=prompt+completion）③t2-r2 pos3 帧数常量 25（实测 27）；三处修复后 07:34:10 首建成功（evidence-first/result-first，-O 幂等同字节）。
- 07:34:53–07:35:54 test_verify.py 编写与修复两次（合成 usage 误加顶层 cached_tokens；合成 SSE 帧数 off-by-one；json 默认空格分隔符致字节替换未命中→改紧凑分隔符），终版 17 用例。
- 07:36:10 公开档 evidence.json（SHA `68056357b73cc031c088a0a052f6ed7a1602f33baddfde6691b71c9dc38cbef3`）/result.json（SHA `a2e64f29a0e554bb57d089288e62b5b9fcb486e32f2e541180f39a8021649ece`）安装（xb 拷贝自 first）；随后幂等重建与公档重放均与公开件逐字节相同；17×普通/-O 全绿（私 scratch 目录）。
- 非作者独审（task-45）：pending。

## 已知限制

- product-reported 计数；不认证 provider 内部、实际摄入、计费、KV 复用或缓存命中路径；r2 首请求 cached>0 只按响应侧见证表述。
- 探索性事后、先验全披露；复算只证明公开 evidence 与私档重算一致及终点算术成立，不证明冻结时点先后。
- duration 只发布分档不发布原值；request/response 正文只在私档；单任务单模型（glm-5.3-flash 捕获通道），不外推其它任务或通道。
