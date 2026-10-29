# L4 阶段I共同gate与DSH候选：首次独立预审

**结论：RELEASE BLOCKED。固定快照的独立10项检查仅2项符合预期，8项暴露误收/误拒；不得释放本版gate/DSH，更不等于全E ready。**

live_doc_drift: []（仅固定源码快照与本报告收据，不宣称尚未完成的E无漂移）。task-7保持in_progress。模型/API/checker实际执行均0；仅对源码只读审阅、在tmp构造合成文件并注入只读git视图。没有读取题库truth/solution或历史答案，没有修改builder代码。

## 观察与固定证据

Lead宣布stageI停写后，先固定gate/replay/README/DSH/seal至新tmp；完整源SHA与路径见[快照](<gate-dsh-source-snapshot-v1.json>)。之后Lead可修原树，本首轮复核只针对快照。

[原创独立检查器](<gate_adversarial.py>)不引用作者自测结论；构造正常合成plan/contract/binding、原始流/计数字段，调用快照gate_admission的公开注入接口。完整[首失败收据](<gate-adversarial-v1.json>)exit1，正常正例与released=false拒收两项符合预期；其余8项结果如下。

| 反例 | 应有判定 | 实际快照判定 |
|---|---|---|
| status=ok、exit_code=9 | 不准入 | formal=true |
| slot时限1800秒、实际1秒、timed_out=true | 不是genuine timeout | formal=true |
| judge/receipt使用非合同checker SHA | 不准入 | formal=true |
| meta产品、rule、order与plan/contract不同 | 不准入 | formal=true |
| 原checker.stdout为0/10，meta/receipt为7/10 | 拒绝来源矛盾 | formal=true |
| notexecuted缺封印引用及reason/stop_source | 记账不完整 | accounting_complete=true |
| WB本批observed gateway且方法/边界齐备 | 正例应可按交付态准入 | 被无条件拒绝 |
| WB effort=unknown但managed_unknowns为空 | 未管理未知阻断 | formal=true |

这些是新self_test命令中的合成检查数，不是产品运行数。假git视图只用于隔离真值表，不替代之后真实E祖先/blob链验收。

## 证据定位与解释

快照对应仓内文件路径：

- [gate.verify_execution](<../../1-评测方案/工具链/l4-execution/gate.py#L168-L302>)默认require_release=true及source逐项SHA方向正确；原seal工具v3逃逸修复已单独[局部验过](<seal-preflight.md>)，但这不自动保证admission真值。
- [gate身份/状态](<../../1-评测方案/工具链/l4-execution/gate.py#L419-L456>)缺product/rule/order对齐、ok与exit_code一致性。
- [gate WB分支](<../../1-评测方案/工具链/l4-execution/gate.py#L475-L506>)observed的fails.append位于else内部但不受缺方法if约束，导致有证据也必失败；managed_unknowns仅校已提供条目的形状，不检查实际unknown是否逐项覆盖/白名单集合。
- [gate来源/评分](<../../1-评测方案/工具链/l4-execution/gate.py#L516-L602>)不解析原checker.stdout、snap checkerSHA仅取快照存在但未实核；meta/receipt内部一致不能替代来源与合同一致。
- [gate超时/记账汇总](<../../1-评测方案/工具链/l4-execution/gate.py#L611-L643>)仅以timed_out布尔+有证据判genuine，无真实时限/停止证据约束；accounting_complete以中文fails子串筛选，漏reason/封印缺失。

上列行号仅对应本首轮快照；实现者后续修复会移动行号，固定字节与可重建反例以机器收据SHA为准。

## 静态确定的DSH/replay及集成阻断

1. **DSH正常场误拒**：[lab归档字段](<../../3-表现现场/l4-20261029-cli/dsh/tools/lab.py#L648-L726>)写full_file却未写full_sha256，gate要求后者；run流程未将工作产物复制到ev/workspace，gate要求该目录。真实有session也不能通过。需judge的全run mock实证修正，不以历史归档链3断言代替。
2. **未知补零**：同段无评分时weighted=0.0；无session时requests=0，即使旁注未知也不应把不可观察调用数写成0。
3. **timeout停进程证据不完整**：[lab subprocess.run](<../../3-表现现场/l4-20261029-cli/dsh/tools/lab.py#L629-L647>)超时默认仅停止直接子进程，未start_new_session/停止进程组或证明工具后代均停。后续立即判卷有残留写入竞态；达到题目时限与停止证据都需记录，不能只timed_out=true。
4. **外部依赖闭包仍自报**：[lab.verify_released](<../../3-表现现场/l4-20261029-cli/dsh/tools/lab.py#L528-L540>)仅遍历manifest.external_files，expect_ext参数未用，未强制当前实际profile两件/AGENTS等EXTERNAL_FILES必须在manifest；空集合可真空通过。实际CLI build/profile加载链也须按E要求锁定，不能仅metadata固定字符串。
5. **注册源链还需等值**：gate.verify_execution未明确preregistration_commit==execution_seal_commit、manifest.design_commit==binding.design_commit，D/E只比plan/contract而未比PREREGISTRATION。seal bind正向生成这些相同不意味着消费者可省校验；应加篡改binding与D/E正文的负例。
6. **replay产能夸大**：[replay_dual](<../../1-评测方案/工具链/l4-execution/replay_dual.py#L132-L206>)current.full_stream用agent-session目录存在判true，实际未生成完整投影流、未比较分数；缺raw的字节写0。legacy_usage从session另造投影而非历史读已删除log的真实路径。标equivalent_simulation有帮助，但仍须将未执行重建/未判分列unknown或实现后留实际文件/hash，不能凭目录存在报告能力。两个副本仍直接读取母本session计算legacy_usage，而不是各自完整独立副本；应限定模拟范围。

## 未排除因素、停止条件与下一步

以上未对实际运行做质量判断；没有模型失败或新分数。作者25/25、8/8、3/3数量仅为其自测声明，本轮独立反例不被自测绿抵消。Lead已即时收到首轮阻断与固定SHA，可修原树；独立复核不得代改。

修复后须新快照/新receipt复验：正常/真实timeout/infra/notexec全真值表、WB未知白名单与本批证据、完整来源SHA与原始评分、E/release/外部闭包、完整run mock及进程停止链。直到这些通过、其他runner齐备、真实E封印且Lead明确release之前，真实请求仍禁止。

## 可复现实验

```bash
/usr/bin/python3 -B '5-评测报告/L4首请求前评审-2026-10-29/gate_adversarial.py' \
  --source '/private/tmp/l4-gate-dsh-reviewed-g60f35dc/1-评测方案/工具链/l4-execution/gate.py' \
  --validator '1-评测方案/工具链/runner-schema-v2/validate_runner_meta.py' \
  --out '<新的独立review收据路径>'
```

原收据禁止覆盖。tmp路径可能清理，复现按快照SHA找对应源码；测试生成完全synthetic证据，不需要真实模型、checker或答案资产。

## 脚本生成证据行

```text
5-评测报告/L4首请求前评审-2026-10-29/gate-dsh-source-snapshot-v1.json · a80412c2 · 1664B · 2026-10-29T20:40:42+08:00
5-评测报告/L4首请求前评审-2026-10-29/gate_adversarial.py · 1ec4d64e · 9786B · 2026-10-29T20:40:42+08:00
5-评测报告/L4首请求前评审-2026-10-29/gate-adversarial-v1.json · e3d58b5a · 12074B · 2026-10-29T20:40:42+08:00
```
