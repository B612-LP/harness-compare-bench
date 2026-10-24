# Execution 判卷修复收据（2026-10-24）

## 冻结与范围

仅修改 Exercism/Cargo 的 checker、规格与 truth 元数据，新增 Exercism trusted runner 及本审计目录。不改原 gold、官方测试、原始输入、参考解或历史运行；无 git commit、GUI、模型新运行或 G2R4 操作。

- [Exercism checker](<../../../2-用例/exercism-py-6/checker.py>)：**1.1**；[trusted runner](<../../../2-用例/exercism-py-6/trusted_runner.py>)。
- [Cargo checker](<../../../2-用例/tb-cargo-plan/checker.py>)：**0.2**。
- [最终代码哈希/时间戳](<frozen-artifacts.json>)；[修前 Exercism checker](<before/exercism-py-6/checker.py>)、[修前 Cargo checker](<before/tb-cargo-plan/checker.py>)，同目录亦保留各自原 truth/spec。
- CLI 保持 `checker.py RUN --json` / `checker.py --selftest`。成功结果增 `checker_version`；Exercism 每题增 `completion`；正式有效判卷 exit=0（分数由 JSON 判读），canonical/契约错误 exit=2。

## 红 → 绿证据

同一 [reproduce.py](<reproduce.py>) 在 temp 中复制素材，before 覆盖冻结原 checker/truth，after 使用当前 checker/truth。全部构造非模型运行，不增加独立运行样本数。原始输出均写入 JSON：

- [before.log](<before.log>) / [before.json](<before.json>)：**4/20** 契约验收通过；两 oracle、两旧 selftest 原已绿，仍有 **16 个红项**。
- [after.log](<after.log>) / [after.json](<after.json>)：**20/20** 全绿，进程 exit=0；Exercism selftest **16/16**，Cargo selftest nop/oracle/6 负例全部通过；两 oracle 均 reward=1、weighted=100，Cargo=27/27。
- [grade-copy-smoke.json](<grade-copy-smoke.json>)：便捷 temp 复算包装器两 oracle **2/2** 通过。

| 精确负例 | 修前 | 修后判据 |
|---|---|---|
| 六题 `import os;os._exit(0)` | reward=1/weighted=100 | input_integrity PASS、六题 FAIL、reward=0/weighted=0；缺完成回执 |
| 六题 `sys.exit(0)` / 伪造 unittest “OK” 后早退 | 均误判 1/100 | 同上；不信控制台、不仅看 returncode |
| 正确参考解 + 空套件 / 不调用测试回调 / 全部跳过 | 均误判 1/100 | 完整计数/测试身份/success 回调不满足，各 0/0 |
| 历史测试被改且缓存有 marker | checker 覆盖测试、删除缓存 | 原目录所有文件字节与清单保持不变 |
| Cargo truth.threshold=999 | oracle 仍 1/100、exit0 | error JSON、exit2，在执行候选前阻断 |
| Cargo case 漂移、额外 case_id、总数/关键项/summary 漂移、空哈希字典 | 原均 exit0 | 每项 error JSON、exit2 |
| Cargo canonical 数据漂移；同时更新 truth 对应哈希 | 前者忽略（1/100）；后者仅候选完整性返回0，仍无自身错误 | 两者均 error JSON、exit2 |

### 判据细节

Exercism 使用 `-I -S -B`，先载入可信 stdlib、安装回调，再导入候选。独立完成文件只在 suite 正常返回后生成。canonical AST 在父进程给出完整测试身份；discovered/tests_run/start/stop/success 必须逐项对应 canonical 54+37+13+31+14+15=**164** 项，且失败、错误、跳过、预期失败、意外成功均为0。缺回执/只 exit0 不算通过。

Cargo 保留原 truth 的 **case** 字段（原契约没有 case_id）；不改 threshold=20、total_checks=27、5个关键项或 expected_summary 原 gold。truth 的政策/summary 常量与四文件完整 pinned SHA-256 由 checker 交叉核验，再检查真实 canonical 字节；数据与 truth 一起变化也不能静默改题。每个关键项必须存在且通过，空集合不能真空通过。

## 一键复跑

仓库根目录执行（需要本机 Python 标准库，不需网络/模型/历史绝对路径）：

```bash
python3 '4-打分细则/判卷审计-2026-10-24/execution/reproduce.py' --phase before --output '4-打分细则/判卷审计-2026-10-24/execution/before.json' > '4-打分细则/判卷审计-2026-10-24/execution/before.log'
python3 '4-打分细则/判卷审计-2026-10-24/execution/reproduce.py' --phase after --output '4-打分细则/判卷审计-2026-10-24/execution/after.json' > '4-打分细则/判卷审计-2026-10-24/execution/after.log'
```

before 阶段 exit0 表示红例已成功采集，不表示旧 checker 安全；after 仅20项全部满足期望才 exit0，否则2。

## 历史证据只读复算

**不要在历史现场目录直接跑旧 Exercism checker**：旧版会覆盖六份官方测试、`rmtree(__pycache__)`，因此即使口头叫“只读评分”也有证据写回副作用。新版 grader 自身不再这样做，但仍建议统一使用 [grade-copy.py](<grade-copy.py>)，先复制到 temp 再判：

```bash
python3 '4-打分细则/判卷审计-2026-10-24/execution/grade-copy.py' exercism-py-6 '<历史workspace目录>'
python3 '4-打分细则/判卷审计-2026-10-24/execution/grade-copy.py' tb-cargo-plan '<历史workspace或临时补齐后的目录>'
```

Cargo 若归档缺 `inputs/app` 代码，不得拿缺件现场的0当模型失败；需按 lead 保存的 source-supplement 在另一个 temp 中组装，与 canonical 匹配的数据/hash核验后再判，原归档和原reward均不覆盖。此任务未对历史场次宣告独立验收 closed，交由 lead 的最终复算收据裁定。

## 已知攻击面与诚实边界

这不是任意敌意 Python 的安全沙箱。候选与 runner 在同解释器/同用户权限下运行，可 introspect/monkeypatch unittest 与计数回调、探测并伪造完成文件、读取/改写宿主可访问路径、调用子进程/网络或耗尽资源；临时目录、隔离启动和完成计数并不消除这些能力，超时也不是完整进程树隔离。Cargo 同样执行本机候选代码。复制到 temp 仅防判卷器自身对历史证据的写回，不能阻止恶意代码通过绝对路径触达原现场。

对真正敌意样本，应在额外低权限 OS 沙箱/容器中运行，原证据仅只读挂载、移除凭据/网络、限制进程树与资源，再复制数据判卷。本次只对列明的确定漏洞给红绿证据，不宣称任意攻击均已封堵。
