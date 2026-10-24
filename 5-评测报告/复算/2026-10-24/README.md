# 2026-10-24：历史产物版本化只读复算

**这是已有提交的离线重新判卷，不是新跑模型。** 32 个选定观察槽＝31 次临时副本判卷＋1 个 WorkBuddy×LCB suspect 排除。该 suspect 的当前分为 `null`，不是 0；元宝 5 个未执行槽保持暂停，均不计运行次数。

## 1. 规则、输入与证据

- 冻结 checker：BIRD 1.1、DABstep 0.2、Exercism 1.1、Cargo 0.2；LCB 原 0.1。本次输出逐题记录实际 `checker_version`；checker／truth 的 SHA256 在 [results.json](results.json) 的 `versions`。
- DABstep 同时保留 `official_compat` 与 `strict_contract`。当前主表使用后者；其仅修复已知差额符号与 ACI 字母漏判，`abs_tol=rel_tol=1e-4`，不另加 14 位字面精度门槛、不宣称所有语义一般正确。
- 每项输出包含 `run_id / product / group / interface / model / task / source / historical / strict / checker_version / denominator`，并记录输入重建来源、原分变化及排除理由。
- 选定首跑的来源引用从旧数据快照读取，但所有当前分数重新执行 checker 生成；**不读取旧四维排名／均值作为成绩**。首跑来源包括已替换污染格的 r1027，重复来源为 r1028。
- 31 个产物仅在 `TemporaryDirectory` 中执行；Exercism 判卷器本身也在临时副本中恢复官方测试。原 32 个现场目录全部文件 SHA256 前后相同；当前文件还可由[独立验收](verify.py)再核对。

## 2. 首跑观察矩阵（修复轨；单元为 reward / weighted）

| 用例 | Codex CLI · A | DSH CLI · A | WorkBuddy GUI · A | 豆包 GUI · B |
|---|---|---|---|---|
| BIRD | 1 / 86.67 | 1 / 86.67 | 1 / 86.67 | 0 / 60.00 |
| Exercism | 1 / 100 | 1 / 100 | 1 / 100 | 1 / 100 |
| DABstep | 0 / 70 | **0 / 60**（官方兼容 70） | 0 / 70 | 0 / 70 |
| LCB | 1 / 100 | 1 / 100 | **排除：suspect，非 0** | 1 / 100 |
| Cargo | 0 / 70.37 | 0 / 70.37 | 0 / 70.37 | 0 / 81.48 |
| 达标／有分观察槽 | 3/5 | 3/5 | **2/4**，另 1 排除 | 2/5 |

不把 2/4 当成已证明优于／劣于 3/5；不比较缺一格产品的 weighted 总和；A/B 模型不同，不形成纯 Harness 强弱排名。原四维评分只是历史探索，不能用其总分替代本表。

### 真实变更

| 原始现场 | 官方兼容／历史 weighted | 严格复核 weighted | headline |
|---|---:|---:|---|
| [DSH×DABstep 首跑](../../../3-表现现场/r1027-isolated/runs/dsh__dabstep-payments-10/meta.json) | 70 | 60 | 0 → 0 |
| [DSH×DABstep 第三次](../../../3-表现现场/r1028-repeats/runs/dsh__dabstep-payments-10__r3/meta.json) | 60 | 50 | 0 → 0 |

两处均为 `q1871` 正数预测被旧 scorer 当作负数 gold 判对。严格修复后原始提交没有变化，仅派生分数变化。其余 29 次复核分数不变；DABstep 官方兼容轨与每个原场分数均保持一致。

CLI 三道重复题的本样本二值序列仍为 BIRD `1/1/1`、DABstep `0/0/0`、Cargo `0/0/0`，不据 n=3 宣称排除噪声。DSH DABstep 严格 weighted 现为 **60/50/50**；旧 70/50/60 不再作为当前严格成绩。

## 3. 缺失输入和源代码怎样处理

1. 归档输入存在时，原样叠入临时判卷目录；归档省略时从当前已校验 canonical 输入恢复。输出明确区分 `historical_inputs_present` 与 canonical 恢复，不能把恢复后的 hash 当成当时输入的直接证据。
2. r1027／r1028 中六个 Cargo 场原归档省略了 `inputs/app` 被测代码。本轮从原 `meta.workspace` 或 WorkBuddy `trace-summary.workspace` 指向的残存目录补取，另存 [source-supplement](source-supplement/manifest.json)，共六组、18 个 Python 文件，逐件留 SHA256。
3. 补取时间为 **2026-10-24**；不是当场代码指纹。八个 Cargo 复跑的 30 个检查结果（27 计分项＋3 门）均与原判卷一致，再生成计划 JSON 也与归档计划语义相等。这是结果一致性证据，**不能证明补录代码在运行时刻的逐字节同一性**。
4. WorkBuddy×DABstep 原 meta 无逐文件输入清单，但当时 `judge.checks.input_integrity` 记录“已核验 7/7 个输入副本，SHA-256 全部一致”；以历史判卷回执作有限佐证，不补造缺失清单。

补录／有限回执场的证据等级与时间一致性风险在[运行总账](../../运行总账-2026-10-24.md)、[未知登记](../../未知登记.json)明示，不能写成原归档本来完整或硬沙箱保证。

## 4. 从仓库根目录复现

仅需 Python 3 标准库；不使用 API key、不联网、不调用模型、不控制 GUI。历史工作区不必继续存在：补录代码已入此目录。

```bash
# 31 次临时副本判卷，更新本目录派生结果，不改原始现场
python3 -B 5-评测报告/复算/2026-10-24/recompute.py

# Lead 独立精确反例、oracle、七 checker 自测、token／结构校验与哈希核对
python3 -B 5-评测报告/复算/2026-10-24/verify.py
```

`recompute.py` 正常完成退出 0；checker 用例自身错误或不可重建会终止，**不把执行错误补成模型 0 分**。某些旧 checker 完成判卷后始终返回 0，故任务成败只读 JSON `reward`；`execution_exit_code` 另列。`verify.py` 任一验收失败退出 1。

`--collect-supplement` 仅为原机器本轮补录步骤，不是克隆仓库后复算的前置条件；已有文件若与源不同会拒绝覆盖。不得重收集后假称历史原件不变。

## 5. 收据与边界

- [机器结果与原现场哈希](results.json)
- [Lead 独立验收程序](verify.py)、[机器收据](validation.json)、[终端摘要](validation.log)
- [最终交付检查](delivery_check.py)、[交付检查收据](delivery-check.json)：计数、公开链接、秘密模式扫描（含压缩轨迹）、语法与非原始资料的空白检查；原始资料中的空白警告保留，不为格式化改动原证据；并检查全部已留指纹的文件确实已纳入 Git。
- [判卷修前／修后审计](../../../4-打分细则/判卷审计-2026-10-24/README.md)
- [可移植性验收收据](portability-validation.json)：从 Git 快照解包到全新临时目录、不借用本机忽略文件或原工作区，31/31 独立验收再次通过。
- [当期阶段报告](../../阶段报告-v2.0.md)

当前测试覆盖已知反例及指定不变量，不是一般正确性证明。临时目录、可信 runner 与 Python `-I -S` 不是 OS 安全沙箱，不能防所有同 UID／同进程敌意代码。当前评价仍是小样本、非完全同构的阶段观察；不等待仓外 G2R4，也不把未核验的仓外能力写成已交付。
