# L4 最终本体候选局部复验：gate/seal/replay通过，DSH两支路待修

**结论：本候选仍RELEASE BLOCKED。共同gate原21/21、lead seal构建必需集合19/19、replay诚实范围10/10符合预期；DSH未确认停止的normal-exit及spawn异常记账仍有确定故障。E/API继续禁，task-7保持in_progress。**

live_doc_drift: []（固定被测字节；工作树对快照的当前漂移另由文末脚本生成）。全程只做合成文件/注入git、假npm布局和纯Python对象Popen桩；本轮没有启动实际子进程、产品CLI、checker或模型，没有读取实际profile/ASAR/vendor payload正文、题库truth/solution/历史答案。全队Rust incident仍按已知插件真出站、provider unknown/incomplete处置，不能笼统zeroAPI。

## 观察

先保存[最终本体候选快照](<gate-dsh-source-snapshot-v4.json>)，不追动态修改原树；首失败链全部保留。

| 本体 | 独立复验 | 当前结论 |
|---|---|---|
| 共同gate | [原21项21/21](<gate-adversarial-v4.json>) | 原物/hash/verified=false/跨槽/双说矛盾均按旧判据处理，局部关闭 |
| lead seal | [19/19](<seal-build-adversarial-v4.json>) | 六基础路径、CLI launcher/metadata、Codex native与DSH自有lib JS必需成员拒漏，局部关闭 |
| replay | [10/10](<replay-adversarial-v4.json>) | 诚实降级局部text/usage投影，不称完整流，不称未测score等值，S6局部关闭 |
| DSH runtime | [10/13](<dsh-runtime-adversarial-v4d.json>) | timeout false停止链正确；normal-exit false及spawn异常缺有效记账，仍阻断 |

[作者gate合成自测重跑](<author-gate-selftest-v4.json>)exit0（51项）；[作者seal自测重跑](<author-seal-selftest-v6.json>)18项exit0。这里只是作者合成自测重跑，不是产品运行数、不能抵消下列独立支路失败。

## 证据

### 共同gate：原21项通过，适配必要原物但不改预期

[第四gate检查器](<gate_adversarial_v4.py>)保留[前轮21项](<gate_adversarial_v3.py>)预期；新版生产门要求正常CLI也有组闭包原物，因此为正常合成正例增加normal_exit/verified_gone/pgid/时点/hash，不改变能力分数或拒例。WB正例使用exit_code=None加native_terminal原始completed封套，不伪造OS exit0。

原21项包括原8实证、effort未知哨兵管理、真实停止正例、原物缺失/篡改、verified=false、group_confirmed=false、跨槽借原物、meta/doc双说矛盾；现在全部符合预期。该结论不替代WB producer九项正常门接线或E后真实native数据的语义审查。

### DSH：checker0/后槽Popen0局部通过，但“有有效首槽记录”仍失败

[原创runtime检查器](<dsh_runtime_adversarial_v4.py>)在生产run_slot/cmd_run上注入必须命中的对象桩，不经PATH、不启动任何产品或真实进程；checker/capture/rebuild/snapshot均为带计数的禁止调用钩子。三个世界使用不同临时根，独立记录首槽返回、下一槽调用、meta/原物/持久halt。

1. **timeout停止未确认：通过。** 首槽code3，checker/capture/rebuild/snapshot均0，Popen桩总1；持久halt使下槽code3且新增Popen0；termination原物verified_stop=false、weighted=null，partial证据在位。
2. **正常退出后组停止未确认：两项失败。** checker0、capture0、后槽新增Popen0与持久halt正确。但生产早退分支使用termination（None）而非effective_stop/closure，触发None.get错误并被吞；首槽没有meta/termination原物，stdout却称status=timeout。不能把正常退出分支伪造为真实timeout，也不能以halt存在替代每槽有效记账。
3. **Popen抛OSError、从未启动：一项失败。** 组闭包段引用未赋值launched_pgid，抛UnboundLocalError，首槽没有有效not_executed或error/partial记录。此世界没有实际进程，不额外要求全批halt；硬问题是记账缺失/未处理异常，不是把后续独立spawn本身当违规。

[固定DSH源](</private/tmp/l4-gate-dsh-reviewed-v4-a1n45c5e/3-表现现场/l4-20261029-cli/dsh/tools/lab.py#L828-L916>)对应两支路已即时通知Lead。受测源仍是本快照；修复必须新快照/新receipt。

保留的reviewer失败链：[v4](<dsh-runtime-adversarial-v4.json>)最初缺PIPE桩常量；[v4b](<dsh-runtime-adversarial-v4b.json>)未覆盖ev_dir的定义时默认repo参数，导致多世界共用固定tmp快照输出目录；仅修reviewer fixture后[v4c](<dsh-runtime-adversarial-v4c.json>)已隔离根。最终v4d再去掉“从未spawn失败也必须全批halt”的非合同额外假设，保留停止未确认两支路后槽Popen0原判据。前述fixture失败不归因产品源码，所有首次收据不删不覆盖。

### seal：强制具体构建身份，不冒称第三方全闭包

[独立seal检查器](<seal_build_adversarial_v4.py>)将PATH resolver替换为两个不可执行假npm布局，不读取真实产品文件。验证：DSH profile两件、全局AGENTS、实际Codex HOME config、WB Info.plist/app.asar六基础路径常量；双CLI launcher、其存在的包metadata、实际Codex darwin-arm64 native payload、DSH自有lib顶层JS在所测布局内全列必需集合，逐项漏封均拒；缺Codex native或CLI resolver硬停。

实际manifest生成函数的exhaustive_transitive_product_dependencies_pinned明确false，独立验证其未冒称所有第三方SDK/Node运行时/动态依赖全封闭。较早build-config-identities八项观测不是最终必需集合依据；最终需使用manifest实际生成与消费校验集合。这里证明集合机制，不证明实际vendor字节来源可信或运行时必然加载某个已声明文件。

### S6：允许诚实降级的原判据已满足

[第四replay检查器](<replay_adversarial_v4.py>)仍用前轮同一合成reasoning、工具参数、长工具结果marker。当前字段改为partial_text_usage_projection，明确遗漏reasoning/tool_call/tool_result/turn边界、非完整流；实际投影bytes/hash可重算，母本不变；legacy usage unknown、扫描vacuous、双侧score not_evaluated。原“实现完整能力或诚实缩小范围”判据接受此降级，不再要求一个已明示局部投影保留全部事件；旧失败收据不重写。

## 解释

局部关闭有清晰范围：gate能拒掉前轮21反例中的非法证据，seal能拒漏指定配置/构建成员，replay已停止夸大范围。这不自动保证每条生产异常路径留下有效一槽记录。

停止未确认时不调用checker/后槽Popen是必要条件；正常分支若因此无meta，或spawn异常抛出而不记账，仍不能在full-plan对账里隐去该槽。需要修生产异常边界与真实状态，不应补假起止/空流/零分或把正常结束改写为timeout。

## 未排除因素、停止条件与下一步

- 仅剩本快照DSH两支路待修并复验；本报告不是全E ready、不是任何producer release，也不是产品质量结论。
- WB producer正常九项门仍由judge审接线；具体native/vendor原物数据审留E后。本轮WB合成completed封套不证明实际子工具全停。
- Rust事故为1 accidental_cli_start、已知插件真请求至少1、DeepSeek请求unknown/incomplete；排除计划槽/合成pass。显式桩与真实入口防复发由judge继续审。
- Lead已说明L4采用merge commit而非squash，保留原D/E为main祖先，不撤E→HEAD校验；科学合同不变。E后selftests须在/tmp副本运行，避免封入manifest的runtime源码根新增receipt导致成员漂移。
- 修复后只重测DSH两支路和timeout正控制，使用新不可覆盖receipt；gate/seal/replay已局部关闭的旧代码不重复消耗测试。真实请求仍须全部准入证据、真实E封印及Lead显式release。

## 可复现实验

输出必须使用不存在的新文件。固定源与完整hash见快照，以下命令均不需要产品CLI、模型或答案资产。

```bash
/usr/bin/python3 -B '5-评测报告/L4首请求前评审-2026-10-29/gate_adversarial_v4.py' --source '<fixed-gate-source>' --validator '<fixed-validator-source>' --out '<new-gate-receipt>'
/usr/bin/python3 -B '5-评测报告/L4首请求前评审-2026-10-29/dsh_runtime_adversarial_v4.py' --source '<fixed-dsh-source>' --out '<new-runtime-receipt>'
/usr/bin/python3 -B '5-评测报告/L4首请求前评审-2026-10-29/seal_build_adversarial_v4.py' --source '<fixed-seal-source>' --out '<new-seal-receipt>'
/usr/bin/python3 -B '5-评测报告/L4首请求前评审-2026-10-29/replay_adversarial_v4.py' --source '<fixed-replay-source>' --dsh-source '<fixed-dsh-source>' --out '<new-replay-receipt>'
```

## 脚本生成证据行与漂移状态

```text
5-评测报告/L4首请求前评审-2026-10-29/gate-dsh-source-snapshot-v4.json · b4f4db41 · 2348B · 2026-10-29T22:25:18+08:00
5-评测报告/L4首请求前评审-2026-10-29/gate_adversarial_v4.py · b5b89050 · 6924B · 2026-10-29T22:25:18+08:00
5-评测报告/L4首请求前评审-2026-10-29/gate-adversarial-v4.json · e826b96f · 35692B · 2026-10-29T22:25:18+08:00
5-评测报告/L4首请求前评审-2026-10-29/dsh_runtime_adversarial_v4.py · 6288c76a · 8324B · 2026-10-29T22:25:18+08:00
5-评测报告/L4首请求前评审-2026-10-29/dsh-runtime-adversarial-v4.json · e9413993 · 5583B · 2026-10-29T22:25:18+08:00
5-评测报告/L4首请求前评审-2026-10-29/dsh-runtime-adversarial-v4b.json · d78c643e · 7204B · 2026-10-29T22:25:18+08:00
5-评测报告/L4首请求前评审-2026-10-29/dsh-runtime-adversarial-v4c.json · e4d9c1ef · 12211B · 2026-10-29T22:25:18+08:00
5-评测报告/L4首请求前评审-2026-10-29/dsh-runtime-adversarial-v4d.json · 9258ccae · 12029B · 2026-10-29T22:25:18+08:00
5-评测报告/L4首请求前评审-2026-10-29/seal_build_adversarial_v4.py · a79812a0 · 6462B · 2026-10-29T22:25:18+08:00
5-评测报告/L4首请求前评审-2026-10-29/seal-build-adversarial-v4.json · 15850d0d · 4988B · 2026-10-29T22:25:18+08:00
5-评测报告/L4首请求前评审-2026-10-29/replay_adversarial_v4.py · 7a2803cc · 6084B · 2026-10-29T22:25:18+08:00
5-评测报告/L4首请求前评审-2026-10-29/replay-adversarial-v4.json · 30d633a5 · 3408B · 2026-10-29T22:25:18+08:00
5-评测报告/L4首请求前评审-2026-10-29/author-gate-selftest-v4.json · 9dda7b8f · 14669B · 2026-10-29T22:25:18+08:00
5-评测报告/L4首请求前评审-2026-10-29/author-seal-selftest-v6.json · 2ee72d6b · 1922B · 2026-10-29T22:25:18+08:00
/private/tmp/l4-gate-dsh-reviewed-v4-a1n45c5e/1-评测方案/工具链/l4-execution/gate.py · 77d8e8b4 · 118010B · 2026-10-29T22:25:18+08:00
/private/tmp/l4-gate-dsh-reviewed-v4-a1n45c5e/1-评测方案/工具链/l4-execution/replay_dual.py · 8b710a6e · 21205B · 2026-10-29T22:25:18+08:00
/private/tmp/l4-gate-dsh-reviewed-v4-a1n45c5e/3-表现现场/l4-20261029-cli/dsh/tools/lab.py · 2a378846 · 86097B · 2026-10-29T22:25:18+08:00
/private/tmp/l4-gate-dsh-reviewed-v4-a1n45c5e/1-评测方案/自动循环L4-2026-10-29/execution_seal.py · f1ef0340 · 11236B · 2026-10-29T22:25:18+08:00
```

```json
{
  "generated_at": "2026-10-29T22:25:18+08:00",
  "scope": "live tree vs v4 fixed snapshot; repairs are separate candidates, not an E admission",
  "live_doc_drift": [
    {
      "path": "3-表现现场/l4-20261029-cli/dsh/tools/lab.py",
      "snapshot_sha256": "2a378846035526ee22d02120757ca56520463c27c9d1dd0b1e167343dcd032a2",
      "live_sha256": "556942828bc737578c10be40bb3d2b55824b6641d89ef6a3370edff35e76ec88"
    }
  ]
}
```
