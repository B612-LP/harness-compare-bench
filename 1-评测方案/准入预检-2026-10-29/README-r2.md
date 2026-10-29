# WorkBuddy 准入预检 r2 增补（包C，2026-10-29）

> 本文件原为 [README.md](<README.md>) 的增补节；因 README.md 处于 freeze-20261029-v2 封印清单（增补导致 sealed file drift，v2 verify exit=2），按封印纪律迁出至本未封印文件。内容一字未改，裁定与证据链见 [wb-preflight-r2.json](<wb-preflight-r2.json>) 与 evidence-r2/。

## r2 增补（2026-10-29，包C 请求级补证；用户直接指令触发 REA 方法升级）

预注册：[自动循环L1 包C](<../自动循环L1-2026-10-29/PREREGISTRATION.md>)。≤3 机制预算内完成（M1 应用内代理+env 注入+本地 tap 监听、M2 `--proxy-server` 进程标志、M3 进程内观察钩子+调用栈采样+REA 静态定位），证据与裁定：[wb-preflight-r2.json](<wb-preflight-r2.json>)，证据目录 [evidence-r2/](<evidence-r2/>)。

结论变化（证据如实更新，探针会话级观察、不外推全量行为）：

1. **wb-upstream-route-host-undisclosed → 已回答**：桌面会话模型面为**直连 `https://www.workbuddy.cn`（腾讯 EdgeOne）**——全部探针会话模型窗口内直连 IP 集合 `{119.147.114.214, 113.108.215.157}` 与同时段系统 resolver 的 www.workbuddy.cn A 记录集合精确匹配，`api.deepseek.com` 被同期 DNS 集合排除；静态目录（app.asar `main/common.js`）中唯一 DeepSeek 直连端点条目是 `deepseek-flash→api.deepseek.com`，会话所用 `deepseek-v4.1-flash` 无该条目。诚实边界：TLS 未破坏、SNI 未直读（IP 集合匹配 + 时序对齐 + 服务面同主机 SNI 钩子互证）；网关服务端上游本机不可观测。
2. **wb-model-alias-equivalence → 路由级不等价成立**：统一 alias `deepseek-flash`（= api.deepseek.com 直连）与桌面 `deepseek-v4.1-flash`（WB 网关计费条目）不同路；请求体级 model 字段未捕获（模型面绕过全部代理向量 + TLS 端到端，按纪律未采用行为有损取证）。
3. **裁定维持** `not_admitted_to_formal_a1`：阻断理由从「路由证据缺口」升级为「请求级证据表明路由不同」。WB 是否进 A 组留给未来正式批次，本循环不做。
4. **r1 证据解读修正**：r1030 在 WB 私有日志看到的 `NO_PROXY`（含 api.deepseek.com）名单，经 r2 验证为本机 harness/launchd 环境变量继承，非 WB 产品自述。
5. 过程记录：WB 在探针期内 5.8.3 自动更新至 5.9.3（更新器接管一次），模型面行为跨版本一致；对产品本体零改动（app.asar 仅只读哈希与仓外解包分析），系统代理/hosts/keychain/settings.json 全部还原（[还原证明](<evidence-r2/environment-snapshot/post-state-restore-proof.txt>)）。探针工具链与原始未脱敏捕获留存仓外 `~/bench-workspaces/_probe/wb-r2/`。
