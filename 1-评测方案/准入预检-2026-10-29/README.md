# 准入预检（2026-10-29，零模型调用）

目的：在冻结规则 `freeze-20261029-v2` 下确定首批正式 A 组批次（formal-a1）的产品构成。结论先行：

- **Codex CLI / DSH CLI**：可进入正式批次。版本（codex-cli 0.163.0 / DSH 0.2.0-rc.2）、隔离配置、官方路由出处（Codex 隔离 CODEX_HOME `base_url=https://api.deepseek.com`；DSH `bench-cli` profile `provider: deepseek-official`，其官方 host 由同 profile 同 provider 的机制实验 12 次真实请求传输记录佐证，见 [r20261029-mechanism](<../../3-表现现场/r20261029-mechanism/>)）均可打包。预检收据：[cli-preflight.json](<../../3-表现现场/r1030-formal-a1/preflight/cli-preflight.json>)。
- **WorkBuddy 桌面端**：**不可进入首批正式表**。可披露产品版本/模型标签/工具/时间戳，但**没有任何请求级上游主机证据**（仓内现场无 `api.deepseek.com` 字样），且模型 id 字符串（`deepseek-v4.1-flash`）与统一 alias（`deepseek-flash`）不等价、无请求级佐证。两项均按老师要求④登记为受管未知（影响/下一步/停止条件/reopen 条件齐备）。结构化结论与来源：[wb-preflight.json](<wb-preflight.json>)。

## 边界

- 本预检是证据可得性预检，不是产品能力评价；「未准入」≠「产品差」，只是同模型同路由事实不可证明。
- WorkBuddy 继续保留在历史 25 格观察与后续桌面批次轨道；不因预检结论改写任何历史记录。
- 私有目录（`~/.workbuddy`）内容一律不打包、不作为公开源；其观察仅以叙述披露。
