# BIRD / DAB 数值判卷红绿审计（2026-10-24）

## 收据与范围

本轮只修改 BIRD / DAB 的 checker、spec、truth 版本及本审计目录；未修改输入、gold/source、历史运行、历史分数或 CHANGELOG，未提交 git、未操作 GUI、未介入 G2R4。**没有新模型运行**。下列均为确定性判卷回归；真实产品产物复算由 lead 另行记录，不能由这些合成样例代替。

- [独立可复跑脚本](<run_audit.py>)：**40/40，退出码 0**。
- [完整逐例机器收据](<results.json>)：含命令、退出码、修前/修后 JSON 和当前代码哈希；临时路径来自当次执行，重新运行脚本会重新生成，不依赖保留该路径。
- [BIRD 内置 selftest](<bird-ca-schools-15.selftest.stdout.txt>)：**21/21，退出码 0**；原 19 项 + 两组追加非法行。
- [DAB 内置 selftest](<dabstep-payments-10.selftest.stdout.txt>)：**23 组通过，退出码 0**；原 20 项 + 三组符号/ACI 双轨断言。
- 回归脚本用系统临时目录（仓库/题库外）构造运行目录；只把报告写入本审计目录。不联网、不装包、不读取凭据。冻结区仅受信 checker 与相应 truth；输入和 solution 只通过只读使用 canonical 资源复跑。

从仓库根目录执行：

```bash
python3 '4-打分细则/判卷审计-2026-10-24/numeric/run_audit.py'
python3 '2-用例/bird-ca-schools-15/checker.py' --selftest
python3 '2-用例/dabstep-payments-10/checker.py' --selftest
```

## 冻结与修复

修改前先冻结 [BIRD v1.0 checker](<frozen/bird-ca-schools-15/checker.py>) / [truth](<frozen/bird-ca-schools-15/truth.json>) 和 [DAB v0.1 checker](<frozen/dabstep-payments-10/checker.py>) / [truth](<frozen/dabstep-payments-10/truth.json>)，哈希见 [sha256.json](<frozen/sha256.json>)。脚本每次先校验该清单，再将旧代码/truth 暂存至仓库外、连接 canonical 输入，真正执行旧 CLI；不是用新 checker 模拟旧结果。

| 样例 | 修前 / 官方兼容 | 修后 / 严格轨 |
|---|---|---|
| BIRD oracle 15 行 | v1.0：reward=1、15/15、exit 0 | v1.1：相同 |
| BIRD oracle 追加 `not-json` / `[]` / 缺 sql 的对象 | schema 已红，但 reward=1、15/15、exit 0 | schema 硬否决，reward=0、15/15、exit 1 |
| DAB oracle | v0.1：reward=1、10/10 | v0.2 两轨均 reward=1、10/10 |
| DAB q1871 改为 `0.94810300000017` | 该题误过，10/10 | 该题失败，9/10（整场仍允许通过） |
| DAB q2697 改为 `Z:13.57` | 该题误过，10/10 | 该题失败，9/10（整场仍允许通过） |
| 上述两错叠加 q49=`A. NL` | 9/10、reward=1、exit 0 | 7/10、reward=0、exit 1 |
| 仅符号+ACI两错 | 10/10 | 8/10、reward=1（0.8 包含边界，不另加整场硬否决） |

BIRD 仅把原已记录的 `answers_schema` 纳入 reward 硬门，逐题 exec-accuracy 与 0.8 阈值不变。DAB 六个官方 scorer 函数经独立 AST 比对完全相同；默认官方结果可继续提取，但不能把宽松通过等同严格合同正确。checker/truth/spec 版本已分别同步到 **BIRD 1.1 / DAB 0.2**，gold/source 未变。

## DAB 双轨 API（已稳定）

```bash
# 默认保留官方兼容顶层结果与退出码
python3 '2-用例/dabstep-payments-10/checker.py' RUN_DIR --json --scoring official-compat
# 严格轨放到顶层，并按严格reward决定退出码
python3 '2-用例/dabstep-payments-10/checker.py' RUN_DIR --json --scoring strict-contract
```

Python：`judge(Path(run_dir), scoring="strict-contract")`；既有 `judge(run_dir, case_dir)` 保持默认官方兼容。

JSON 始终包含：

- `checker_version="0.2"`，`scoring_mode="official-compat"` 或 `"strict-contract"`。
- `official_compat` 对象：`scorer_version="dabstep-official-port-v0.1"`，以及 `reward/weighted/score_rate/correct/checks/failed`。
- `strict_contract` 对象：`scorer_version="signed-aci-v1"`，同一组评分字段，另有 `scope=["1871:signed-number","2697:aci-and-signed-fee"]`、`numeric_tolerance={"rel_tol":0.0001,"abs_tol":0.0001}`。
- 顶层 `reward/weighted/score_rate/correct/checks/failed` 镜像所选轨。共用 `gates`、`threshold=0.8`、`artifact` 等原字段，退出码 0/1 随所选 reward；用例错误 / selftest 失败为 2。

**严格轨仅为本轮符号/ACI 契约修复，不是所有 guidelines/格式语义的一般正确性证明。** q1871 要求全串带符号十进制且保留符号；q2697 要求全串 ACI:fee，ACI 大小写归一后相同且金额保留符号。两题用 `math.isclose(abs_tol=1e-4, rel_tol=1e-4)`，不新增 14 位精度要求、不使用官方较少小数位舍入捷径；其余题仍用官方。负号、ACI、有限数值和解释性前后缀独立验证。

近似阈值收据：q1871 与 gold 差 `0.00009` 通过、差 `0.00011` 拒绝；q2697 `e:13.571` 通过、`E:13.572` 拒绝；`E:13.6` 不因较少小数位舍入通过。尾零、空白和 ACI 大小写不误杀。

现有答案抽取保持 **根目录 > output/ > outputs/** 优先级，两种输出子目录和根目录优先均已独立验证；实际选取文件见 JSON `artifact`。官方兼容分数在 `official_compat` 中始终可取。复算时不要把新严格分数静默覆盖旧 meta/reward；保留旧版本标注，另记新 checker/scorer 版本及本次产物路径。

## 文件清单与待办边界

修改：[BIRD checker](<../../../2-用例/bird-ca-schools-15/checker.py>)、[BIRD spec](<../../../2-用例/bird-ca-schools-15/spec.md>)、[BIRD truth](<../../../2-用例/bird-ca-schools-15/truth.json>)；[DAB checker](<../../../2-用例/dabstep-payments-10/checker.py>)、[DAB spec](<../../../2-用例/dabstep-payments-10/spec.md>)、[DAB truth](<../../../2-用例/dabstep-payments-10/truth.json>)。新增仅本审计目录所列冻结文件、脚本、收据与说明。

独立验收待办：lead 对已有真实产品产物按新 API 另作严格复算并标记版本，处理读取过 truth 的运行有效性；本轮未检查 BIRD q26/q27 的独立 SQL/gold 争议，不能把 oracle 自测全绿写成 gold 经独立验证。上述漏洞的确定性代码红绿回归已完成，但不替代产品证据审计。
