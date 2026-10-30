# M1 — WB 应用内代理设置 + 进程级 env 注入 + 本地 tap 监听（2026-10-29）

机制：`~/.workbuddy/settings.json` 写入 `http.proxy=http://127.0.0.1:8888` + `http.proxySupport=override`（改前字节级快照，见 environment-snapshot/），WB 进程树注入 `HTTPS_PROXY/HTTP_PROXY=http://127.0.0.1:8888`、`NO_PROXY=localhost,127.0.0.1,::1`（重写掉本机环境原有的 api.deepseek.com 豁免项）、`NODE_EXTRA_CA_CERTS`、`SSLKEYLOGFILE`，直接 exec Electron 二进制带 `--remote-debugging-port=9332`。本地监听器为 tap 模式（记录 CONNECT 目标主机后纯 TCP 隧道，不做 TLS 中间人），**上游固定链回 Clash 127.0.0.1:7897**，出口路径与 WB 原生服务面一致。

探针会话：`797c56b6-0988-47ad-9621-515bc138715b`（13:45:04.9 发题 → 13:45:09.9 assistant message → 13:45:12 completed，模型 deepseek-v4.1-flash / low，工作区 `~/bench-workspaces/_probe/wb-r2/ws-m1`，题面「不要使用任何工具…WB-R2-PROBE-OK」）。

## 观察与证据

1. **链路验证通过**（lsof 0.8s 采样，[m1-lsof-chain.redacted.txt](<m1-lsof-chain.redacted.txt>)）：Electron 主进程 (pid 96993) → 127.0.0.1:8888（监听）→ 127.0.0.1:7897（Clash）逐进程可见；服务面全部经过监听。
2. **服务面主机清单**（[m1-connects.redacted.jsonl](<m1-connects.redacted.jsonl>)，75 CONNECT）：`www.workbuddy.cn`×53、`galileotelemetry.tencent.com`×13、`download.codebuddy.cn`×4、`workbuddy-extensions-…cos.ap-guangzhou.myqcloud.com`×2、`static.workbuddy.cn`×2、`tencent.sso.codebuddy.cn`×1。
3. **模型面负结果（可发布证据）**：模型请求**绕过全部代理向量直连**——任务窗口内 Electron 主进程存在且仅存在 4 条直连 `119.147.114.214:443`（本地端口 57495/57496/57497/57510，13:45:06–13:45:11），与 sendPrompt→assistant message 时序完全对齐；同窗口内其余直连 443（113.108.215.157、14.152.80.143）为全程存在的服务面长连接。该客户端不受 env 代理、应用内 http.proxy、NO_PROXY 重写任一影响，也非 Chromium 代理语义（Chromium 会走系统/会话代理）。
4. **IP ≠ 主机名**：119.147.114.214 无 PTR，属腾讯 EdgeOne POP 网段；`api.deepseek.com`（eo.dnse1.com）与 `www.workbuddy.cn`（eo.dnse5.com）均在 EdgeOne 平台且 A 记录随地域/时点变化，**不得将该 IP 等同于任何域名**。主机归属待 M3 客户端意图主机名/SNI。

## 未排除因素（预登记）

- 全部捕获在「WB → 本地监听 → Clash 7897」链下进行；服务面主机为客户端意图目标（CONNECT 行明文），出口由 Clash 规则决策。
- 模型面直连为探针会话单次观测（n=1 会话、4 条连接），不外推为全量行为。
- 本机 harness/launchd 环境变量 `NO_PROXY` 含 `api.deepseek.com` 豁免项——r1030 在 WB 私有日志看到的该名单应归属**本机环境继承**，非 WB 产品自述；r2 修正 r1030 证据解读。
- 未做 TLS 解密：tap 模式端到端 TLS 未破坏，请求体/响应头不可见（②③留待 M2/M3）。
