# REA 静态分析 — 端点目录定位（2026-10-29，用户直接指令触发的方法升级）

- 触发：用户 2026-10-29 14:17 前后直接指示「调用 rea 工具吧，把 workbuddy 的自动化修好」，经 lead 批准作为 M3 的静态定位手段，边界为**只读分析 + 只改探针工具侧**。
- 工具：`rea-agents@6.8.0`（REA CLI 路线，无需 MCP 注册）。对 app.asar 的整树分析两次受阻（unpacked 原生库 `pty.node` 声明完整性不符——Electron 打包常态；`--integrity-policy record-and-continue` 重跑后分析器 `execution_failure`），改用 `@electron/asar` 将 app.asar **解包副本**至仓外 `~/bench-workspaces/_probe/wb-r2/rea/wb-asar-extracted/` 后做定向检索与条目级复核。
- 产物身份：分析对象 = WB **5.9.3** `app.asar` sha256 `12a2be53ec7db2943a9958f6986d7807adcf083bd79b307d26706d83750effa7`；关键文件 `main/common.js` sha256 `990716146c900b0aa67e4f9ae19b2e0b2280aa51ac332d84ac2acbdfa773eac5`（bundle 为单行压缩，以下以**字节偏移**定位，可用 `python3 -c "s=open('main/common.js','rb').read(); print(s[<offset>:<offset+N>])"` 复核）。

## 静态证据条目（file: offset + 原文摘录）

1. **provider `deepseek` 目录条目（统一 alias 同名 id）** — `main/common.js` offset ≈ 620867：
   > `"deepseek":{"deepseek-flash":{"id":"deepseek-flash","name":"DeepSeek V4.1 Flash","api":"openai-completions","baseUrl":"https://api.deepseek.com","provider":"deepseek",...}`

   WB 自身目录中 id `deepseek-flash`（与本项目统一 alias 同名）映射 **`https://api.deepseek.com`**（直连路由）。同表相邻条目 `deepseek-v4-pro` 同 baseUrl。
2. **会话模型 id `deepseek-v4.1-flash` 的全部内置条目**（无一条指向 api.deepseek.com）：
   - offset 789836：`provider:"opencode-go"` → `"baseUrl":"https://opencode.ai/zen/go/v1"`（Cloudflare 172.65.x）
   - offset 986308：`provider:"qwen-token-plan"` → `"baseUrl":"https://token-plan.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1"`（阿里云）
   - offset 996117：`provider:"qwen-token-plan-cn"` → `"baseUrl":"https://token-plan.cn-beijing.maas.aliyuncs.com/compatible-mode/v1"`（阿里云）
   - offset 831072：`"deepseek/deepseek-v4.1-flash"` → `"baseUrl":"https://openrouter.ai/…"`（openrouter）
3. **`https://api.deepseek.com` 在 `main/common.js` 全文仅 2 次出现**，均在上述 provider `deepseek` 目录内；主目录其余 140+ 主机字面量中模型面相关者已全量列举比对（详见分析过程，含 anthropic/openai/moonshot/minimax 等同表条目）。
4. 运行时 spill 产品目录 `~/.workbuddy/cache/conversation-product-spill/acc-product-config-v3-*.json`（**私有目录，仅叙述性观察、不入库**）中 `deepseek-v4.1-flash` 为计费目录条目（`"credits":"x0.11"`、`"vendor":"f"`、积分折扣徽章），不含路由 baseUrl——路由决策在 daemon 进程内的模型配置合并逻辑（ModelConfigDiag，多 provider 目录 smartMerge），合并后的有效 baseUrl 未在可打包工件中落盘。

## 与动态证据的拼接（双向印证）

- 动态（M1/M2/M3，5.8.3 与 5.9.3）：模型面直连 `{119.147.114.214, 113.108.215.157}`，两 IP 恰为同时段系统 resolver 下 `www.workbuddy.cn`（EdgeOne）A 记录集合，与 `api.deepseek.com` 同期 A 记录集合无交集。
- 静态：WB 自身目录将 `deepseek-flash` 映射 `api.deepseek.com`，将 `deepseek-v4.1-flash` 置于网关计费目录（无直连 DeepSeek baseUrl）。
- 合并结论：桌面会话 `deepseek-v4.1-flash` 的请求级路由 = **WB 自家网关（www.workbuddy.cn / EdgeOne）**，与统一 alias `deepseek-flash` 的 `api.deepseek.com` 直连路由**不同路**。

## 产品完整性声明

- 对 `/Applications/WorkBuddy.app` 仅做只读读取（hash、解包复制到仓外、检索）；无任何写入、无补丁、无重签名。探针期所有可逆改动仅限：`~/.workbuddy/settings.json`（已字节级还原，sha256 前后一致）与 WB 进程级 env/启动参数（进程已退出即消失）。
- keychain 未添加任何 CA；系统代理（scutil/networksetup → Clash 7897）、/etc/hosts、DNS 设置全程未动；还原核验见 [../environment-snapshot/post-state-restore-proof.txt](../environment-snapshot/post-state-restore-proof.txt)。

## 残留未知

- WB 网关的服务端上游（网关之后最终调用哪家推理服务）属服务端行为，本机不可观测；需产品方披露方可闭环。
- 请求体级模型字段与响应头未捕获（TLS 端到端 + 模型面绕过全部代理向量 + 观察钩子不重定向）。
