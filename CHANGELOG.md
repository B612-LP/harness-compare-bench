# Changelog

本仓库所有重要变更记录在此。周报（邮件发出版）以 Markdown 形式存档于 [`6-周报/`](6-周报/)。

## [2026-10-20]

- 新增项目级 `AGENTS.md` 规则：维护 Changelog 与周报存档。

- 新增 `CHANGELOG.md`，开始维护变更记录。
- README 状态表更新为当前进度，并链接本文件。
- 按公告要求收敛仓库结构：`5-学习笔记/` 不再入库（本地保留，加入 `.gitignore`），目录与公告五件交付物 + 周报存档一一对应。

## [2026-10-19]

- 入库 2026-10-16 两批 CLI 赛道表现现场（Codex / DSH / bare-model 对照，含空跑与参考解两组准入检查）。
- 入库自建用例 `int-sum-sort`、`word-freq-report`（Harbor 规范：environment / instruction / solution / tests）。
- 入库评测工具链（`1-评测方案/工具链/`：跑批脚本、代理 overlay、bare-model 与 DSH 适配器）。
- 旧调研档案仓更名为 `harness-compare-bench-old`，同步工具链 BENCH 路径与文档引用。

## [2026-10-16]

- 初始化仓库：目录结构与公告五件交付物一一对应，写入归因定责定调（模型 / SKILL / Harness 三层）与用例、表现现场模板。
- 统一 LF，防止 Windows checkout 转 CRLF。

## 周报存档

| 期数 | 日期 | 状态 | 链接 |
|---|---|---|---|
| 第 1 期 | 2026-10-17 | 已发（18:37，收件人四位） | [6-周报/2026-10-17-第1期.md](6-周报/2026-10-17-第1期.md) |
