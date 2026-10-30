# r1031-variance-n3：n=3 可重复性批次现场（2026-10-29）

> 本说明经隐私整理，字节与历史版本不同；不因此改变原始运行产物或历史判定，原文件哈希不适用于本版。

[公开方法整理](<../../1-评测方案/评测依据-重复性与预检-2026-10-29/PREREGISTRATION.md>)与[勘误整理](<../../1-评测方案/评测依据-重复性与预检-2026-10-29/AMENDMENT-1.md>)是事后非敏感整理版，不是预注册或修正案原件、认证摘录或重封。原件不公开，历史 hash、提交与时间不能为整理版背书，原预注册先于运行的时序无法公开核验。**验收结论见 [RESULTS.md](<../../5-评测报告/可重复性-n3-2026-10-29/RESULTS.md>)（独立复核记录）。**

## 结果矩阵（n=3/格，headline = 全对题数）

| 产品 | rep1(=r1030) | rep2 | rep3 | spread | headline 序列 |
|---|---|---|---|---|---|
| codex | 444.81 | 440.37 | 461.48 | **21.11** | 3,3,4（dab rep3 翻绿） |
| dsh | 444.07 | 440.37 | 444.07 | **3.70** | 3,3,3 |

历史比较口径（gap₀=0.74）：两产品 spread ≥ 0.74；历史报告称「r1030 产品差与重复性方差不可区分」，这只是小样本描述，并非统计显著性或等效性证明。敏感性对照（30.74）：比值 1.46 / 8.31。n=3 不排名。

## 运行器与工程项

- `tools-dsh/`、`tools-codex/`（各自自 r1030 最小适配，差异见各自 README；event id `var-n3-<product>-<case>-r<rep>`；工作区 `~/bench-workspaces/r1031/<product>/<rep>/<case>/`）。
- 工程项 a（stdout 截断）：codex 侧完整落盘（`stdout_bytes` 125,526–620,069）；dsh 侧实证 8192/32KB 为 dsh-headless 0.2.0-rc.2 **硬编码不可覆盖**，采用「raw CLI 流 + 会话轨迹重建无截断完整流」双落盘缓解——未知登记「stdout 8192 截断」据此推进/缓解。
- 工程项 b（usage）：20 场逐调用 usage（含 cache 字段）入 `meta.usage.per_call`；`cache_creation` 全 0、`cache_read` 合计 19,159,168 tokens——responses 路由「只读不写」语义未经请求级验证，入未排除因素。

## 缺陷与异常披露（全部不静默）

1. **r1031#1**：第 1 场（dsh bird r2）raw stdout/stderr 丢失——继承自 r1030 archiver 缺陷（`rmtree` 先于 staging 移动，r1030 侧当时为会话内手工补救、代码级修复未生效）。运行本身完好，完整流由会话轨迹无损重建为 `agent.jsonl.full`，`meta.corrections` 显式披露。runner 已结构性根除（日志落笔即在 staging），第 2 场起 raw 流完整。r1030 README「tools/lab.py 已修」声明不准确 → 问题池留下一轮修正。
2. **codex cargo r2 integrity 事件**：4 条 `reference/` 机械命中，经证据复核裁定 benign-reviewed（prose-echo：推理散文复述纪律原文，0 条在 function_call 载荷；独立行级复核无矛盾）。翻案经 `meta.corrections` 落盘，原判定保留。
3. **D1**：全批 meta 无 `registered_at` 字段（schema 偏差）。历史裁定不回填；提交字段与运行时间只提供间接记录，原预注册先于运行无法通过公开原件核验，字段列为下一轮 runner 必备。
4. **D2/D4/D5**（observation）：codex 收据 `reported` 精度 2dp（算术一致）；freeze.lock 1 pin 漂移（准入预检 README 后续增补，评分关键 pins 当时记录完好）；dsh meta 无 `stdout_bytes` 字段。

## 六类分账（本批）

product_run 20（`codex/runs/`、`dsh/runs/`，全部 `preregistration_commit=be39fc2`）；self_test：runner 自测（`dsh/selftest/`、`tools-codex/README.md` 记录）+ 验收工具 r1030 自检；interface_preflight：2（`codex/preflight/`、`dsh/preflight/`，WB 预检另账在 [准入预检 r2](<../../1-评测方案/准入预检-2026-10-29/wb-preflight-r2.json>)）；离线复算/判卷回归/裸模型探针：本批无新增（如实为空）。证据等级 `original-contemporaneous-full`（bird r2 stdout 重建已披露）。
