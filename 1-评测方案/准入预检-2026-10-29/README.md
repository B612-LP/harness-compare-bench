# 准入预检（2026-10-29，零模型调用）

目的：在冻结规则 `freeze-20261029-v2` 下确定首批正式 A 组批次（formal-a1）的产品构成。结论先行：

- **Codex CLI / DSH CLI**：可进入正式批次。版本（codex-cli 0.163.0 / DSH 0.2.0-rc.2）、隔离配置、官方路由出处（Codex 隔离 CODEX_HOME `base_url=https://api.deepseek.com`；DSH `bench-cli` profile `provider: deepseek-official`，其官方 host 由同 profile 同 provider 的机制实验 12 次真实请求传输记录佐证，见 [r20261029-mechanism](<../../3-表现现场/r20261029-mechanism/>)）均可打包。预检收据：[cli-preflight.json](<../../3-表现现场/r1030-formal-a1/preflight/cli-preflight.json>)。
- **WorkBuddy 桌面端**：**不可进入首批正式表**。可披露产品版本/模型标签/工具/时间戳，但**没有任何请求级上游主机证据**（仓内现场无 `api.deepseek.com` 字样），且模型 id 字符串（`deepseek-v4.1-flash`）与统一 alias（`deepseek-flash`）不等价、无请求级佐证。两项均按老师要求④登记为受管未知（影响/下一步/停止条件/reopen 条件齐备）。结构化结论与来源：[wb-preflight.json](<wb-preflight.json>)。

## 边界

- 本预检是证据可得性预检，不是产品能力评价；「未准入」≠「产品差」，只是同模型同路由事实不可证明。
- WorkBuddy 继续保留在历史 25 格观察与后续桌面批次轨道；不因预检结论改写任何历史记录。
- 私有目录（`~/.workbuddy`）内容一律不打包、不作为公开源；其观察仅以叙述披露。

## r2 增补（2026-10-29，包C 请求级补证；用户直接指令触发 REA 方法升级）

预注册：[自动循环L1 包C](<../自动循环L1-2026-10-29/PREREGISTRATION.md>)。≤3 机制预算内完成（M1 应用内代理+env 注入+本地 tap 监听、M2 `--proxy-server` 进程标志、M3 进程内观察钩子+调用栈采样+REA 静态定位），证据与裁定：[wb-preflight-r2.json](<wb-preflight-r2.json>)，证据目录 [evidence-r2/](<evidence-r2/>)。

结论变化（证据如实更新，探针会话级观察、不外推全量行为）：

1. **wb-upstream-route-host-undisclosed → 已回答**：桌面会话模型面为**直连 `https://www.workbuddy.cn`（腾讯 EdgeOne）**——全部探针会话模型窗口内直连 IP 集合 `{119.147.114.214, 113.108.215.157}` 与同时段系统 resolver 的 www.workbuddy.cn A 记录集合精确匹配，`api.deepseek.com` 被同期 DNS 集合排除；静态目录（app.asar `main/common.js`）中唯一 DeepSeek 直连端点条目是 `deepseek-flash→api.deepseek.com`，会话所用 `deepseek-v4.1-flash` 无该条目。诚实边界：TLS 未破坏、SNI 未直读（IP 集合匹配 + 时序对齐 + 服务面同主机 SNI 钩子互证）；网关服务端上游本机不可观测。
2. **wb-model-alias-equivalence → 路由级不等价成立**：统一 alias `deepseek-flash`（= api.deepseek.com 直连）与桌面 `deepseek-v4.1-flash`（WB 网关计费条目）不同路；请求体级 model 字段未捕获（模型面绕过全部代理向量 + TLS 端到端，按纪律未采用行为有损取证）。
3. **裁定维持** `not_admitted_to_formal_a1`：阻断理由从「路由证据缺口」升级为「请求级证据表明路由不同」。WB 是否进 A 组留给未来正式批次，本循环不做。
4. **r1 证据解读修正**：r1030 在 WB 私有日志看到的 `NO_PROXY`（含 api.deepseek.com）名单，经 r2 验证为本机 harness/launchd 环境变量继承，非 WB 产品自述。
5. 过程记录：WB 在探针期内 5.8.3 自动更新至 5.9.3（更新器接管一次），模型面行为跨版本一致；对产品本体零改动（app.asar 仅只读哈希与仓外解包分析），系统代理/hosts/keychain/settings.json 全部还原（[还原证明](<evidence-r2/environment-snapshot/post-state-restore-proof.txt>)）。探针工具链与原始未脱敏捕获留存仓外 `~/bench-workspaces/_probe/wb-r2/`。
