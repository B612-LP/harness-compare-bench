# int-sum-sort 判分规格（spec）

版本：**v0.3（2026-10-21，轻量判卷）** ｜ 判分入口：`checker.py`
历史版本：Harbor 版 `tests/test.sh`（v0.2，二值 + 容器内 `/app` 判分，**保留不动**，作为 CLI 自动批跑的历史实现）

## 1. 用例定位

hello 级流水线验证：读 `/app/input.txt`（6 个整数）→ 产出 `/app/output.txt`（总和 / 个数 / 升序整数）。
**这不是区分度题**：任何 Harness 都应该过；过不了说明「读文件 → 写文件」执行链路有问题，这本身就是结论。

## 2. 判分模式

- **headline 为二值 0/1**（沿用 `4-打分细则/打分表.md` v0.2：全 PASS=1，任一 FAIL=0）。
- 逐项权重只用于复核定位与报告中的加权参考，**不改变二值口径**。
- 三个守卫：**输入完整性**（输入被改 → 直接 0）、**严格格式**、**值比对**。

## 3. 观察项

| id | 观察项 | 权重 | 通过条件 | 0 分条件 |
|---|---|---:|---|---|
| artifact_exists | 产物存在 | 10 | `output.txt` 存在于约定位置 | 缺失 |
| input_integrity | 输入完整性（守卫） | 10 | 运行目录附带的 `input.txt` 与 canonical 字节一致 | 输入被修改（直接 0）；未附副本 → **未核验**（不扣分） |
| format_strict | 严格格式 | 20 | 恰好 8 行、纯 LF、恰好一个结尾换行、每行一个规范十进制整数、无首尾空白/空行 | 任一项不满足 |
| sum_line | 第 1 行 = 总和 | 20 | 与 canonical 输入现算值一致 | 不一致 |
| count_line | 第 2 行 = 个数 | 20 | 同上 | 不一致 |
| sorted_block | 其余行 = 升序整数 | 20 | 6 行升序、每行一个 | 折叠成一行 / 缺行 / 乱序 / 空行 |

> v0.2 的 Harbor `test.sh` 存在三个已复现缺口：排序块折叠成一行可过、插空行可过、篡改输入后可自洽作答拿满分。v0.3 用 `format_strict` + `input_integrity` 把这三条堵住（见 `--selftest` 负例）。

## 4. 运行目录约定

```
<run_dir>/
  output.txt      # 必需产物（也接受 run_dir/output/、run_dir/outputs/ 下同名文件）
  input.txt       # 可选，建议附：本次运行实际使用的输入副本（用于完整性守卫）
  meta.json       # 可选：产品/版本/模型/操作人/日期等，不参与判分
```

```bash
python3 checker.py <run_dir>          # 人读报告 + RESULTS_JSON
python3 checker.py <run_dir> --json   # 只输出 JSON（供脚本聚合）
python3 checker.py --selftest         # 负控制/守卫自测，必须全 PASS 才可用于正式评分
```

退出码：`0` = reward 1；`1` = reward 0；`2` = 用法错误/自测失败。

## 5. 判卷器自测（三纪律）

1. **验外部产物**：只读运行目录里的文件，不采信产品自述、不读仓库内真值进产品目录。
2. **负控制必须能变红**：`--selftest` 固定跑 11 组样例——1 组 golden 必须 1 分，10 组违规（缺产物 / 折叠 / 空行 / 缺结尾换行 / 多空行 / CRLF / 行首空格 / 多一行 / 篡改输入 / 未附输入副本不扣分）必须 0 分或 1 分符合预期。
3. **用例自身一致性**：`truth.json` 记录 canonical 输入 SHA-256 与期望值；checker 启动时校验，canonical 与期望值任何一方被改动都会报 `ERROR`。

**修改 checker 后必须重跑**：`--selftest` + 用 `solution/solve.sh` 产物跑一遍 oracle 回归（必须 reward=1）。

## 6. oracle 回归

```bash
# 用参考解生成产物，再交给 checker（两条独立实现互证）
awk '{s+=$1} END {print s}' input.txt > output.txt
awk 'END {print NR}' input.txt >> output.txt
sort -n input.txt >> output.txt
python3 checker.py <run_dir>   # 须 reward=1
```

## 7. 行为分（仅人工跑时使用）

自动批跑（CLI）没有过程观察，行为分记 N/A，不计入。若人工执行，按 0–3 档打分并写入运行记录：

| 观察项 | 0 | 1 | 2 | 3 |
|---|---|---|---|---|
| 交付完整性 | 无产物 | 产物缺行/格式错 | 产物完整但需一次返工 | 一次交付且格式正确 |
| 回传说明 | 无说明 | 只说"完成了" | 说明产物位置与内容 | 说明产物位置、内容与自查方式 |
| 异常处理 | 静默失败 | 报错但无原因 | 报错并给出原因 | 报错、原因、下一步 |

## 8. 变更记录

- 2026-10-16 v0.2：Harbor `tests/test.sh`（二值；容器内判分；nop/oracle 闸门）。
- 2026-10-21 v0.3：新增 `checker.py`（产物目录判分 + 输入完整性守卫 + 严格格式 + `--selftest`）；`environment/input.txt` 落盘（字节与旧 Dockerfile `printf` 完全一致）；`tests/test.sh` 保留为历史实现。
