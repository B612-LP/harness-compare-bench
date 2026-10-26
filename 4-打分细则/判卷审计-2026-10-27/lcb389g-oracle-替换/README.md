# lcb389g-oracle-替换：重放夹具 → 独立参考解（受控替换收据）

日期：2026-10-27 ｜ 执行：lcb389g-oracle（teammate） ｜ 授权：Lead（BIRD v1.2 q26 并入同款纪律）
前置事实：候选解已于 2026-10-26 验收通过（`4-打分细则/判卷审计-2026-10-26/lcb389g-oracle/`）。

## 1. 替换点与挂接方式（先读 checker.py 得出）

「重放夹具」不是 checker 内部数据，而是**外部文件 `2-用例/lcb-recent-hard-4/solution/abc389_g.py`**。
checker.py 通过 `_oracle_text(pid)`（L244-245）读 `HERE/solution/<pid>.py` 作为 oracle 源文本，
仅用于 `--selftest`（判分路径 `judge()` 只读 run_dir 产物 + truth.json，完全不读 solution/）：

| selftest 项 | 用法 |
|---|---|
| 第 2 项「oracle（solution/ 四题）」 | put_oracle 写入临时 run_dir 后 judge，期望 reward=1、4/4 |
| 负例 6「输出格式多空格」 | `_format_mangle_text`（L261-275）以 `runpy.run_path` 绝对路径跑夹具再弄乱输出，要求 fail_kind=wrong |
| 负例 7「输入副本被篡改」 | 四题 oracle 全过（passed=4）但 integrity 变红 → reward 压 0 |

（第 3、4 项边界/负例只用前两题/第一题 oracle，不涉及 abc389_g。）

## 2. 替换内容

- **动作**：以验收候选 `4-打分细则/判卷审计-2026-10-26/lcb389g-oracle/solution_abc389_g.py`
  （层级 DP + 生成函数 y=1+x 代换，editorial-converged 标注见候选 README）
  就地覆盖 `2-用例/lcb-recent-hard-4/solution/abc389_g.py`，字节级一致（SHA 复核见 §4）。
- **留档**：旧夹具副本存本目录 `abc389_g.replay-fixture.bak.py`（替换前字节拷贝，SHA 与替换前夹具一致）。
- **不改动**：checker.py、truth.json、inputs/problems.json、instruction.md、task.toml、case.json、
  其余三题夹具、`4-打分细则/判卷回归/run_regression.py` —— SHA 均与替换前一致（checker/truth 见 §4 对照）。

## 3. selftest 对照（真实运行，Python 3.9.6）

| 时点 | 命令 | 退出码 | 结果 | 存档 |
|---|---|---|---|---|
| 替换前 | `python3 checker.py --selftest` | 0 | **11/11 全绿**（正例 2、负例 8、守卫 1） | `selftest.before.stdout.txt` |
| 替换后 | 同上 | 0 | **11/11 全绿**（同上；oracle 项 passed=4 weighted=100.0） | `selftest.after.stdout.txt` |

替换后耗时 29.3s（新 oracle 43 组 4.7s，与旧夹具 4.75s 同量级）。无任何一项变红，未触发回滚。

## 4. SHA-256 对照

| 文件 | 替换前 | 替换后 |
|---|---|---|
| `2-用例/lcb-recent-hard-4/solution/abc389_g.py`（重放夹具→参考解） | `0c61e2bc5304eae8baa6d95ef9691d30e2f2180bbb7f8c31dec617d06df34cba` | `1755f0b590159d15a7237ae82122d156024650d5fc4e38cb9d1f3fc7934a7b55` |
| `2-用例/lcb-recent-hard-4/checker.py` | `e07654d42450468c1c33e65044b91339b60cf2b31252a9dc40b82f059a381791` | 同前（未动） |
| `2-用例/lcb-recent-hard-4/truth.json` | `8a9ae6deb4d088b011348d5245d18697f5df5b8b65390c7679c6a8d539c90d14` | 同前（未动） |
| `2-用例/lcb-recent-hard-4/inputs/problems.json` | — | `0ce2f9c1eee0039fa9cfc7cd9969d99118d3fba4ac41571c49d9f5289592a673`（与 truth 守卫值一致，未动） |
| 本目录 `abc389_g.replay-fixture.bak.py` | — | `0c61e2bc…`（= 替换前夹具，字节级留档） |

替换前后清单全文见 `sha256-before.txt` / `sha256-after.txt`。

## 5. 历史分数影响 = 0 的论证

1. **判分数据源不变**：真提交评分走 `judge(run_dir)`，其 gold 输出全部来自 `truth.json`
  （tests_sha256 三重守卫闭环），`solution/` 不在判分读取路径上；本次 truth.json 字节未动。
2. **checker 未动**：判分口径、守卫、常量全部不变（SHA 对照 §4）。
3. **oracle 只进自测管路**：被替换文件仅被 `--selftest` 的 3 个用例读作「正确解样例」，
   替换后 11/11 行为与替换前完全一致（期望值与实际值逐项相同）。
4. **结论**：任何历史/未来批次的正式评分结果均不受本替换影响；改变的只是
   「checker 自测所用的 oracle 是否为经独立验证的真解」（由重放夹具 → 独立参考解）。

## 6. 文件清单与复现

| 文件 | 说明 |
|---|---|
| `README.md` | 本收据 |
| `selftest.before.stdout.txt` / `selftest.after.stdout.txt` | 替换前后 selftest 完整 stdout |
| `abc389_g.replay-fixture.bak.py` | 旧重放夹具留档（字节级） |
| `sha256-before.txt` / `sha256-after.txt` | 替换前后 SHA 清单 |

复现：
```bash
cd 2-用例/lcb-recent-hard-4 && python3 checker.py --selftest   # 应 11/11 全绿，exit 0
sha256sum solution/abc389_g.py   # 应为 1755f0b590159d15a7237ae82122d156024650d5fc4e38cb9d1f3fc7934a7b55
```

## 7. 边界遵守

未动 `CHANGELOG.md`；未动 `truth.json` / `inputs/` / `instruction.md`；未动
`4-打分细则/判卷回归/run_regression.py`；未 git add/commit；写范围 =
`2-用例/lcb-recent-hard-4/solution/abc389_g.py`（Lead 授权的受控替换点）+ 本目录。
