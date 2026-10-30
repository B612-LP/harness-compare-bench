# M3 — 进程内观察（NODE_OPTIONS 钩子 + 调用栈采样）+ 主机归属判定（2026-10-29）

> 事后链接修订说明：本页已事后修正链接及说明，不是原封印字节；历史结果不代表本次开展了新的验证。

用户直接指令触发的 M3 内方法升级：停止试错式探针，引入 REA 静态分析定位 + 进程内观察钩子（只观察、不篡改请求内容；产品本体零改动，见 [../rea-static-analysis/README.md](../rea-static-analysis/README.md) 的完整性声明）。

## 方法

1. **观察钩子 v2**（仓外 `~/bench-workspaces/_probe/wb-r2/wbhook.js`）：经 `NODE_OPTIONS=--require` 注入 WB 进程树，包装 `dns.lookup / net.connect / tls.connect / http2.connect / http(s).request` 并包装 `worker_threads.Worker`（worker 先装观察补丁再加载原入口）；只记录主机名/SNI 元数据，不改写任何连接参数（[m3-hook.redacted.jsonl](<m3-hook.redacted.jsonl>)）。
2. **macOS `sample` 调用栈采样**：模型调用窗口对 daemon 进程采样，判别模型客户端运行层级。
3. **DNS 归属对照**：系统 resolver（与 WB 同视角）对候选主机做 A 记录解析，与直连观测 IP 对集。
4. 驱动方式同 r1029 口径：CDP 9332 + `window.wb.invoke`（原驱动位于仓外 bench-automation，未公开；本页不提供公开链接，静态分析文档不是原驱动），探针任务一题一句，模型 deepseek-v4.1-flash / low。

## 关键发现（时序）

1. **模型客户端定位**：`sample` 采样（探针会话 7d55d5d5，14:10:24–31）在模型窗口内捕获 `node::TCPWrap::AfterConnect` → `node::crypto::TLSWrap` → JIT JS 帧的 Node 层 TLS 连接栈——模型请求是 **daemon 进程（daemon-app-server-entry.js 子进程）内的 Node TLS 连接**；主 realm 补丁（服务面全部可见）从未截获它 → 模型客户端运行在**钩子未覆盖的 realm**（worker 线程经 eval 直通，见 worker-passthrough 记录，或更深层的独立 realm）。
2. **代理旁路机理确认**：daemon 主 realm 的 axios（服务面）被 `http.proxy`/env 捕获（钩子可见 `net.connect→127.0.0.1:8888` + `tls.connect sn=www.workbuddy.cn`）；模型面的连接完全绕开全部代理向量（env HTTPS_PROXY、应用内 http.proxy、`--proxy-server`、NO_PROXY 重写均无效）。
3. **主机归属判定（①的答案）**：
   - 全部探针会话中，模型窗口内的直连 443 只出现过两个 IP：`119.147.114.214`（5.8.3 与 5.9.3 的多个会话）与 `113.108.215.157`（14:25 会话）；每次 3–4 条新连接，与 sendPrompt→assistant message 时序对齐（[m3d-lsof-chain.redacted.txt](<m3d-lsof-chain.redacted.txt>)）。
   - **系统 resolver 在同一时段解析 `www.workbuddy.cn`（CNAME `www.workbuddy.cn.eo.dnse5.com`，腾讯 EdgeOne）的 A 记录恰为 `{119.147.114.214, 113.108.215.157}`**——两个观测 IP 全部命中该集合（2/2），且跨会话交替命中两个 POP。
   - 同期 `api.deepseek.com`（CNAME `api.deepseek.com.eo.dnse1.com`）的 A 记录为 `{14.29.51.120, 14.116.174.67}`（223.5.5.5 视角历史值 `{211.97.84.77, 221.11.190.218}`）——与观测 IP 无交集；`opencode.ai`（Cloudflare 172.65.x）与 `token-plan.*.maas.aliyuncs.com`（阿里云 39.106.x）同样无交集。
   - 服务面同主机（www.workbuddy.cn）经代理路径的 TLS SNI 由钩子独立读得（`sn=www.workbuddy.cn`），与直连目标 IP 集互证。
   - **结论：桌面会话的模型面出站为「直连 `www.workbuddy.cn`（腾讯 EdgeOne）」，即 WorkBuddy 自家网关，而非 api.deepseek.com。** 诚实边界：TLS 端到端未破坏，SNI 未从线路层直接读得；归属基于「同解析时段 A 记录集合精确匹配（两 POP 双命中）+ 时序对齐 + 服务面同主机 SNI 互证」，非 SNI 直读。
4. **静态目录印证**（[../rea-static-analysis/README.md](../rea-static-analysis/README.md)）：WB 内置 provider 目录中，`deepseek-flash` → `https://api.deepseek.com`（与统一 alias 同名的目录条目），而会话所用模型 id `deepseek-v4.1-flash` 的三个内置条目分别指向 opencode.ai（Cloudflare）/ 阿里云 MaaS，均与观测 IP 矛盾；spill 的运行时产品目录（私有目录，仅叙述性观察）显示 `deepseek-v4.1-flash` 为 vendor 计费目录条目（credits 计费），与「网关代计费」架构一致。

## 对两个受管未知的更新含义（裁定详见 [../wb-preflight-r2.json](<../../wb-preflight-r2.json>)）

- **wb-upstream-route-host-undisclosed**：已由「未披露」升级为「请求级出站证据在案」：模型面直连 WB 自家网关（www.workbuddy.cn / EdgeOne），api.deepseek.com 被同期 A 记录集合排除。
- **wb-model-alias-equivalence**：路由级已可判定**不等价**——统一 alias `deepseek-flash` 在 WB 自身目录中映射 `api.deepseek.com`（直连路由），而桌面会话的 `deepseek-v4.1-flash` 走 WB 网关路由；请求体级模型字段仍未观测（TLS），但 A 组「同模型同路由」要求下路由级不等价已足以下判。

## 未排除因素（预登记）

- 全部动态观测在「探针会话 × WB 5.8.3/5.9.3 × 本机网络环境（Clash 出口）」条件下取得，不外推全量行为。
- IP 归属基于 DNS A 记录集合匹配（EdgeOne POP 动态调度，匹配限于同时段），SNI 未直读；若产品方披露网关后端上游，可进一步闭环到最终推理服务商。
- 请求体模型字段（②的线路级形态）与响应头（③）未捕获：模型面绕过全部代理向量 + TLS 端到端 + 观察钩子不重定向连接（纪律约束）；按 lead 两轮 CA 纪律，未采用行为有损取证。
- 钩子只覆盖 main realm 与部分 worker；模型所在 realm 未能插桩（worker 经 eval 直通），不影响上述 IP 级归属判定。

## 探针工具侧「自动化修复」沉淀（应用户要求）

- 可复用工具链（仓外 `~/bench-workspaces/_probe/wb-r2/`）：`launch_wb.sh`（进程级 env 注入启动）、`wbhook.js`（观察钩子 v2，worker 包装）、`capture.js`（tap/mitm 双模监听器，上游链回 Clash）、`run_probe.py`（CDP 驱动探针任务）。
- r1029 CDP+RPC 驱动在 5.9.3 上验证仍完好（4 个探针会话全部正常完成）。
- 捕获自动化的边界结论：WB 桌面端模型面对代理全旁路 + TLS 端到端，**不改产品本体、不做行为有损重定向的前提下，线路级解密不可得**；请求级证据以「进程归属 + 直连 IP + DNS 集合匹配 + 静态目录」组合为准。
