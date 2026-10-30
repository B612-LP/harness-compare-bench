# 证据核验工具

> 本说明经整理，字节与历史运行封印时的版本不同；不能据此声称历史封印在当前工作树仍通过。原始内部记录不公开，历史验收不能仅凭本页独立核验。

## 证据记录原则

记录文件指纹和生成时刻时应使用程序输出，避免手动转写错误。能被 [receipt_check.py](receipt_check.py) 读取的证据行可按路径核对声明值与实测值；未取得原件时，应如实标记未验证。

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
