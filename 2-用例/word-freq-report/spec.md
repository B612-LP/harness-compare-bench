# word-freq-report 判分规格（spec）

版本：**v0.3（2026-10-21，轻量判卷）** ｜ 判分入口：`checker.py`
历史版本：Harbor 版 `tests/test.sh`（v0.2，容器内判分，**保留不动**）
用例版本：任务书 v1.0 → **v1.1（2026-10-21，标点数 12→11 修正）**

## 1. 用例定位

中等级：多步文本规则实现 + 平票决胜陷阱。**这题有区分度设计**（`a`/`dog`/`tests` 同为 5 次，平票组卡在 Top-5 边界），不是 hello 级。

## 2. 判分模式

- **headline 为二值 0/1**（沿用 `4-打分细则/打分表.md` v0.2：全 PASS=1，任一 FAIL=0）。
- 期望值**从 canonical 语料现算**（与参考解同一规则的两份独立实现），并与 `truth.json` 交叉校验；不硬编码答案。
- 两个守卫：**输入完整性**（语料被改 → 直接 0）、**严格格式**（7 行 / 单空格 / LF / 结尾换行）。

## 3. 观察项

| id | 观察项 | 权重 | 通过条件 | 0 分条件 |
|---|---|---:|---|---|
| artifact_exists | 产物存在 | 10 | `report.txt` 存在于约定位置 | 缺失 |
| input_integrity | 输入完整性（守卫） | 10 | 运行目录附带的 `corpus.txt` 与 canonical 字节一致 | 语料被修改（直接 0）；未附副本 → **未核验**（不扣分） |
| format_strict | 严格格式 | 20 | 恰好 7 行、纯 LF、恰好一个结尾换行、行格式 `<word> <count>` 且单空格、整数规范 | 任一项不满足 |
| total_line | 第 1 行 = 总 token 数 | 15 | 与现算值一致 | 不一致 |
| distinct_line | 第 2 行 = 去重词数 | 15 | 与现算值一致 | 不一致 |
| top5_block | 第 3-7 行 = Top-5 | 30 | 频次降序；平票按 ASCII 升序；逐行完全一致 | 平票决胜错 / 少行 / 多行 / 双空格 |

**陷阱样例（selftest 已固化）**：把 `dog 5` 换成 `tests 5` → 仅 `top5_block` 挂，reward=0。这证明判卷器识别「接近正确但违反要求」的答案。

## 4. 规格修正记录（v1.1）

`instruction.md` 原文写「punctuation set is exactly these **12** characters」，但实际只列 11 个（`. , ; : ! ? " ' ( ) -`），评分器也实现 11 个。
v1.1 把数字改为 **11**。语料中不含第 12 个候选字符，**行为无变化**，不需要重跑历史现场；旧版 `tests/test.sh` 仍是 11 个字符，与本版一致。

## 5. 运行目录约定

```
<run_dir>/
  report.txt      # 必需产物（也接受 run_dir/output/、run_dir/outputs/ 下同名文件）
  corpus.txt      # 可选，建议附：本次运行实际使用的语料副本（用于完整性守卫）
  meta.json       # 可选：产品/版本/模型/操作人/日期等，不参与判分
```

```bash
python3 checker.py <run_dir>          # 人读报告 + RESULTS_JSON
python3 checker.py <run_dir> --json   # 只输出 JSON
python3 checker.py --selftest         # 负控制/守卫自测，必须全 PASS
```

退出码：`0` = reward 1；`1` = reward 0；`2` = 用法错误/自测失败/用例自身不一致。

## 6. 判卷器自测（三纪律）

1. **验外部产物**：只读运行目录，不采信自述。
2. **负控制必须能变红**：`--selftest` 固定 11 组样例（golden / 平票错 / 缺产物 / 少一行 / 多一行 / 缺结尾换行 / 多余空行 / CRLF / 双空格 / 篡改语料 / 未附语料副本不扣分）。
3. **两份实现互证**：checker 的 Python 分词与 `solution/solve.sh` 的 awk 实现必须给出同一答案（total=92、distinct=35、Top-5 = the 8 / and 7 / fox 6 / a 5 / dog 5）；`truth.json` 记录该期望值，启动时交叉校验。

**修改 checker 后必须重跑**：`--selftest` + oracle 回归（`solution/solve.sh` 产物 → reward=1）。

## 7. 行为分（仅人工跑时使用）

自动批跑不评行为分。人工执行时按 0–3 档记录：

| 观察项 | 0 | 1 | 2 | 3 |
|---|---|---|---|---|
| 交付完整性 | 无产物 | 少行/格式错 | 7 行完整但平票或换行需修 | 一次交付且格式正确 |
| 回传说明 | 无说明 | 只说"完成了" | 说明产物位置与统计口径 | 说明位置、平票处理与自查方式 |
| 异常处理 | 静默失败 | 报错无原因 | 报错并说明原因 | 报错、原因、下一步 |

## 8. 变更记录

- 2026-10-16 v0.2：Harbor `tests/test.sh`（五项检查 + 平票陷阱 + 离线自足）。
- 2026-10-21 v0.3：新增 `checker.py`（现算期望 + truth 交叉校验 + 输入完整性守卫 + 严格格式 + `--selftest`）；任务书标点数 12→11；`tests/test.sh` 保留为历史实现。
