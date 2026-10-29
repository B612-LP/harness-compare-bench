# evidence-kit：证据机械化工具包（L3 包C）

- 绑定：[自动循环L3-2026-10-29 PREREGISTRATION §三包C](../../自动循环L3-2026-10-29/PREREGISTRATION.md)（封印 commit `72edb519`，分支 `loop3-2026-10-29`）；池项 ⑥（哈希/时刻脚本化）+ ⑧b（live_doc 报告制三条件之 b）
- 执行：builder-dsh；范围 `1-评测方案/工具链/evidence-kit/`；零模型调用

## 铁律（C3）

**叙述文档（README/收据/审计/周报式文本）中的哈希与时刻必须引用脚本输出——粘贴 evidence_line.py / validate_runner_meta.py / freeze.py 等工具的打印结果，禁止手打。**

- 手打哈希/时刻是 L1–L2 全部哈希类差错（误报、误标、模糊时刻）的共同成因（AUDIT-L2 O-4「收据准确性模式评估」）。
- 判断基准：能被 [receipt_check.py](receipt_check.py) 机械复算的证据行才算数（claimed vs recomputed）；大写/怪长 hex 记号会被逐条记 violation。
- 本轮 judge / auditor / lead 实际试用并留痕（试用登记由使用者本人入活台账；工具侧提供 `--selftest` 证据）。

## 工具

### C1 证据行生成器 [evidence_line.py](evidence_line.py)

```bash
python3 evidence_line.py <path> [<path> ...] [--root <repo-root>] [--json]
python3 evidence_line.py --selftest
```

输出报告标准证据行：`<相对路径> · <sha256 前 8 位> · <字节数>B · <生成时刻 ISO8601+tz>`。
多文件按命令行顺序；任一文件不可读即整批失败（不产半截行）；时刻脚本生成。

### C2 收据规范检查器 [receipt_check.py](receipt_check.py)（⑧b）

```bash
python3 receipt_check.py <doc> [<doc> ...] [--root <repo-root>] [--out <report.json>] [--no-drift-require]
python3 receipt_check.py --selftest
```

机械核验（**只读，绝不回改输入**）：

1. `live_doc_drift` 状态行：文本行含 `live_doc_drift` 且带状态记号（none/空/非空/N 项/[]）；JSON 递归查键（值须 null 或 list）；缺 → fail（`--no-drift-require` 只查哈希行）。
2. 哈希行合规：hex 记号须小写且长度 ∈ {7,8,40,64}；违规逐条记（行号+token）。
3. 证据行复算：匹配 C1 标准格式的行按 `--root` 解析并**重算** sha8/字节数；不符 → fail；不可达文件如实记 unverified（不计 pass）。

报告写 `--out`（目标已存在即拒绝，C-1 同款纪律）；退出码 0/1/2。

### 联合自测 [kit_selftest.py](kit_selftest.py)

```bash
python3 kit_selftest.py [--out selftest-receipt-l3-20261029.json]
```

机械运行 C1/C2 `--selftest`（子进程），汇总计数与退出码为一份收据（哈希/时刻脚本生成；写 `--out` 同款拒绝已存在纪律）。

## L3 交付状态（C4）

- evidence_line.py `--selftest`：11/11 PASS
- receipt_check.py `--selftest`：10/10 PASS
- kit_selftest.py：以落盘收据为准（见本目录收据文件）

## 边界

- 本包不触碰 v3 与 runner-schema-v2（分写界）；不回改任何历史收据；退出码语义 0=过 / 1=核验未过 / 2=用法或拒绝写入。
