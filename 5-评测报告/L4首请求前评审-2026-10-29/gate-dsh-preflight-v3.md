# L4 gate/DSH 第三候选独立复验

**结论：原15项gate及原2项停止判据全部符合预期，但本候选仍RELEASE BLOCKED。停止原物可跨槽借用、运行器未在停止未确认时阻断判卷，replay仍将局部投影称为full。task-7保持in_progress，E仍禁。**

live_doc_drift: []（固定被测快照范围；下方脚本另列工作树相对固定快照的当前漂移）。本人未执行模型、任何产品CLI、真实checker或答案读取；仅合成JSON/git视图和已知自建Python进程组测试。Rust事故仍按Lead已核处置：1 accidental_cli_start、插件真请求至少1、DeepSeek请求unknown；不是全队zeroAPI，不计计划槽/合成pass，不作正式产品证据。

## 观察

Lead宣布候选停写后先建立[第三源码快照](<gate-dsh-source-snapshot-v3.json>)，固定gate、DSH、replay与validator。所有前轮首失败文件不覆盖。

- **原gate15/15**通过；新增6个停止原物绑定负例中4通过、2误收，共[19/21](<gate-adversarial-v3.json>)，exit1。
- **原停止2/2**通过；增加EPERM/KILL判别2分支，共[4/4](<dsh-stop-adversarial-v3.json>)，exit0。
- replay语义/完整投影覆盖[6/9](<replay-adversarial-v3.json>)，exit1。legacy unknown/vacuous与score不评估已诚实修正；完整工具与reasoning事件仍漏。
- 作者合成自测在固定源码独立重跑：[gate43/43](<author-gate-selftest-v3.json>)、[replay10/10](<author-replay-selftest-v3.json>)，均exit0；这些不是产品运行数、不覆盖新增独立反例。

## 证据

### 原判据复验（不换目标）

[第三gate检查器](<gate_adversarial_v3.py>)复用不可变[第二轮检查器](<gate_adversarial_v2.py>)与[原始检查器](<gate_adversarial.py>)。唯一新增正例fixture条件为新版要求的真实合成termination-receipt文件及SHA、pgid、group_confirmed_gone、发出/确认时点；原15个预期真值不变。

原8实证缺陷、WB effort="unknown"漏管理、无/false/EPERM停止证明三项均拒；正常CLI、WB observed、停止证据完备timeout正例仍准入。额外4个负例正确拒绝：原物SHA篡改、原物缺失、原物verified_stop=false、group_confirmed_gone=false。

**仍误收的两个新增例：**

1. 同一有效格式且hash自洽的停止原物，slot_id改成另一计划槽，当前槽仍formal=true。原物存在与hash正确不证明停止的是本槽，gate未检查原物slot_id等派发身份。应至少核slot_id及预先记录的launch PGID/身份链，不应跨槽借用停止证明。
2. 原物doc.verified_stop=true但meta.termination_receipt.verified_stop=false，当前槽仍formal=true。此为同一证据链的可见矛盾；需明确权威字段并拒绝矛盾或移除冗余误导字段，不能无说明同时留下两种裁定。本例不是把未知当产品零分。

### 实际停止原判据与权限分支

[第三停止检查器](<dsh_stop_adversarial_v3.py>)复用[原真实父子进程检查](<dsh_stop_adversarial.py>)，只适配新版参数签名：传入派发时PGID。受测代码不向任何用户进程发送信号。

- 父进程TERM退出-15、子进程忽略TERM：新版约10.38秒后升级KILL并组级确认消失才返回verified_stop=true；子已无存活、计数273→273，返回后无写入。finally仍按已知自建PGID清理并确认计数稳定。
- TERM/probe/KILL持续EPERM：verified_stop=false、group_confirmed_gone=false。
- probe持续EPERM、KILL送达、后续probe仍EPERM：仍false，**没有用送达真值替代消失证据**。
- probe EPERM、对已知组KILL明确ESRCH：允许true，此处ESRCH才是组级消失证据，不是将EPERM当gone。

[固定DSH停止函数](</private/tmp/l4-gate-dsh-reviewed-v3-je7lb7mc/3-表现现场/l4-20261029-cli/dsh/tools/lab.py#L578-L667>)仅ESRCH能确认消失；父wait仅用于回收，不直接置verified。**停止primitive的前轮两个安全缺陷局部关闭。**此结论仅覆盖被管理进程组，不自动证明逃离该组的任意另开会话后代可控。

### 运行器与replay仍开放

**停止未确认仍判卷：**[固定DSH run_slot](</private/tmp/l4-gate-dsh-reviewed-v3-je7lb7mc/3-表现现场/l4-20261029-cli/dsh/tools/lab.py#L802-L866>)无论stop_process_group返回verified_stop真假，都继续归档；之后仍调用score_case。gate事后拒formal不替代runtime“停止确认后才判卷”的条件。需在false/未知时只保留partial/停止诊断并阻断判卷、停止后续派发；不可边存活写入边评分。

**replay范围诚实化大部分已完成：**[固定replay](</private/tmp/l4-gate-dsh-reviewed-v3-je7lb7mc/1-评测方案/工具链/l4-execution/replay_dual.py>)现不从母本session补造legacy usage，legacy扫描vacuous；双侧score明确not_evaluated，不再称分数恒等；母本前后SHA相同；current实际内存重投影，bytes/hash可独立重算，不再只是目录存在。

但_rebuild_events只保留session、assistant text、step_end/final。独立[合成trace检查器](<replay_adversarial_v3.py>)发现：reasoning、tool_call参数、完整tool_result三个marker都在DSH rebuild_full_stream中保留、在replay中全部丢失，而输出仍叫full_stream、注释称与lab同语义。应补齐所声明事件，或诚实改为partial_text_usage_projection并列遗漏；不要求假装原样重演旧/新整个pipeline。S6只能部分解除，不能宣称完整流重建齐备。

## 解释

这轮真实改进明确：gate不再仅信outcome/stop_source字符串；原物hash、verified_stop与组级消失门有效；DSH组级停止由真实子进程反例与权限注入分支共同支持。WB未知哨兵也已覆盖。不能用新增独立反例抹掉这些已经实证的局部关闭。

剩余问题在证据身份和生产流程：一份正确停止收据不能授权另一个槽，停止原物的矛盾不能被默默略过；即使最终formal拒绝，生产端也不应在未确认停写时评分。replay的测量范围声明必须精确到实际保留的事件，不以“确实算出hash”证明投影完整。

## 未排除因素与停止条件

- S1 full_sha/workspace、S2 unknown补零、S5 E等值链前轮局部修复保持；mandatory external四件+repo Codex/cache配置前轮[9/9独立验证](<seal-external-adversarial-v4.json>)未被本轮改动，但不等于实际CLI/build动态加载闭包已验。
- 本轮未替代judge的真实入口/全run mock验收；Rust事故incomplete及显式桩防复发仍由Lead/judge审查，未知provider请求不推成0。
- WB native停止链不在本轮DSH进程组结论之内，DB terminal或15秒安静窗口不能直接当全部子工具停。
- 跨槽停止原物、false停止后仍评分、replay完整性声明必须清理；其他runner与实际E依赖链仍需验。E封印+Lead显式release之前，计划真实请求继续禁止。

## 可复现实验

原收据不可覆盖，输出使用新的不存在路径。固定tmp可能被清理，按完整快照SHA恢复对应字节。

```bash
/usr/bin/python3 -B '5-评测报告/L4首请求前评审-2026-10-29/gate_adversarial_v3.py' \
  --source '/private/tmp/l4-gate-dsh-reviewed-v3-je7lb7mc/1-评测方案/工具链/l4-execution/gate.py' \
  --validator '/private/tmp/l4-gate-dsh-reviewed-v3-je7lb7mc/1-评测方案/工具链/runner-schema-v2/validate_runner_meta.py' --out '<new-gate-receipt>'
/usr/bin/python3 -B '5-评测报告/L4首请求前评审-2026-10-29/dsh_stop_adversarial_v3.py' \
  --source '/private/tmp/l4-gate-dsh-reviewed-v3-je7lb7mc/3-表现现场/l4-20261029-cli/dsh/tools/lab.py' --out '<new-stop-receipt>'
/usr/bin/python3 -B '5-评测报告/L4首请求前评审-2026-10-29/replay_adversarial_v3.py' \
  --source '/private/tmp/l4-gate-dsh-reviewed-v3-je7lb7mc/1-评测方案/工具链/l4-execution/replay_dual.py' \
  --dsh-source '/private/tmp/l4-gate-dsh-reviewed-v3-je7lb7mc/3-表现现场/l4-20261029-cli/dsh/tools/lab.py' --out '<new-replay-receipt>'
```

## 脚本生成证据行与漂移状态

```text
5-评测报告/L4首请求前评审-2026-10-29/gate-dsh-source-snapshot-v3.json · 60c93826 · 2345B · 2026-10-29T21:35:54+08:00
5-评测报告/L4首请求前评审-2026-10-29/gate_adversarial_v3.py · f2bdd0eb · 5596B · 2026-10-29T21:35:54+08:00
5-评测报告/L4首请求前评审-2026-10-29/gate-adversarial-v3.json · 53ad22df · 35033B · 2026-10-29T21:35:54+08:00
5-评测报告/L4首请求前评审-2026-10-29/dsh_stop_adversarial_v3.py · 08cf0ec7 · 3868B · 2026-10-29T21:35:54+08:00
5-评测报告/L4首请求前评审-2026-10-29/dsh-stop-adversarial-v3.json · 1aa064d0 · 11195B · 2026-10-29T21:35:54+08:00
5-评测报告/L4首请求前评审-2026-10-29/replay_adversarial_v3.py · a033bdde · 5470B · 2026-10-29T21:35:54+08:00
5-评测报告/L4首请求前评审-2026-10-29/replay-adversarial-v3.json · 76e26af9 · 2923B · 2026-10-29T21:35:54+08:00
5-评测报告/L4首请求前评审-2026-10-29/author-gate-selftest-v3.json · 8ad544e7 · 12185B · 2026-10-29T21:35:54+08:00
5-评测报告/L4首请求前评审-2026-10-29/author-replay-selftest-v3.json · cb9da406 · 660B · 2026-10-29T21:35:54+08:00
/private/tmp/l4-gate-dsh-reviewed-v3-je7lb7mc/1-评测方案/工具链/l4-execution/gate.py · 56a3f534 · 97745B · 2026-10-29T21:35:54+08:00
/private/tmp/l4-gate-dsh-reviewed-v3-je7lb7mc/1-评测方案/工具链/l4-execution/replay_dual.py · 61fcd9f0 · 19793B · 2026-10-29T21:35:54+08:00
/private/tmp/l4-gate-dsh-reviewed-v3-je7lb7mc/3-表现现场/l4-20261029-cli/dsh/tools/lab.py · c6366d94 · 73298B · 2026-10-29T21:35:54+08:00
```

```json
{
  "generated_at": "2026-10-29T21:35:54+08:00",
  "scope": "live tree vs v3 fixed snapshot; repairs are separate candidates, not an E admission",
  "live_doc_drift": [
    {
      "path": "1-评测方案/工具链/l4-execution/gate.py",
      "snapshot_sha256": "56a3f534cdd9bed21dce5786f738cb634e36242dda973d8276f6cd0b11b7b87e",
      "live_sha256": "eaf4b57cc1a346c5ba0b96cc25042761518032af644a31bcf04c2e08b8f6fdd8"
    },
    {
      "path": "3-表现现场/l4-20261029-cli/dsh/tools/lab.py",
      "snapshot_sha256": "c6366d9496bbc99738dfa76de1e25758c7a058e38150b4faa0eb32d480870c63",
      "live_sha256": "1a24ca602e59120d1792b04a80d073ae53b59e38efe20ddc92976b37b19787ff"
    }
  ]
}
```
