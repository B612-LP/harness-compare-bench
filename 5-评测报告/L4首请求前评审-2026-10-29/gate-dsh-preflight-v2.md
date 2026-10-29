# L4 gate/DSH 修复轮独立复验：仍阻断 release

**结论：RELEASE BLOCKED。原8实证缺陷已局部修正，但真实停止链仍失败，新增WB effort未知哨兵漏管，replay原静态阻断未修。E未封，不放行真实计划请求。task-7保持in_progress。**

live_doc_drift: []（本文固定快照范围；当前工作树相对快照漂移另见下方脚本生成状态，不宣称全E已无漂移）。本复核没有执行模型、DSH/Codex/WB CLI、真实checker或读取答案资产；停止测试只启动自建Python父子进程写临时计数，finally已KILL自建进程组且计数停止。**不能将本人零调用扩大成全队零API**：已知另有stageI误启动Rust Codex且有插件网络请求，见“未排除因素”。

## 观察

先固定新[gate/DSH源码快照](<gate-dsh-source-snapshot-v2.json>)，保持原[首失败收据](<gate-adversarial-v1.json>)及[原检查器](<gate_adversarial.py>)不改。使用[修复轮检查器](<gate_adversarial_v2.py>)复验同一8实证反例；仅将合成正例升级为新版必要字段（原始JSON checks、guards_used、inputs_verification、PREREG相同合成blob），外部集合隔离仅用于真值表，另行独立测mandatory集合。

- 原10项（8缺陷+正常/release=false控制）全部符合预期；另5项中仅真实停止正例通过，共**11/15**符合预期。[完整收据](<gate-adversarial-v2b.json>)exit1。
- 三种1800.1秒timeout：缺termination、stop_verified=false、明确EPERM且child_alive，仍全部genuine_timeout=true/formal=true。
- WB observed gateway+effort="unknown"+managed_unknowns=[]仍formal=true。原WB unknown反例因gateway未知未管理而被拒，不证明effort未知单独已受约束。
- [独立进程停止检查](<dsh_stop_adversarial.py>)**0/2**符合安全预期，[收据](<dsh-stop-adversarial-v2.json>)exit1：权限拒绝被写already gone；实际TERM忽略子进程在stop正常返回后继续写临时计数。

## 证据

### 原8项逐项对照（判据不变）

| 原问题 | 修复轮结果 |
|---|---|
| ok+exit9仍formal | 已拒，局部关闭 |
| 1秒/1800秒假timeout | 已拒，局部关闭；不代表停止链通过 |
| 错checker SHA | 已拒，局部关闭 |
| 产品/rule/order错位 | 已拒，局部关闭 |
| 原checker0/10、meta/receipt7/10 | 已拒，局部关闭 |
| notexec缺封印/reason/stop_source | accounting_complete=false，局部关闭 |
| WB observed有效正例误拒 | 现可准入，局部关闭 |
| WB unknown且缺管理 | 原例现拒，但effort哨兵单独漏管仍开放 |

首次修复轮收据[gate-adversarial-v2](<gate-adversarial-v2.json>)保留：reviewer合成fixture的raw checker与judge共用dict，添加guards_used误改raw receipt导致3正例失败。仅在reviewer检查器复制judge字典，源码目标未变；上表依据后续v2b，不能把首次正例失败当产品缺陷，也不能删掉首次失败。

### 原6静态blocker逐项对照

| 项 | 当前状态与解除范围 |
|---|---|
| S1 full_sha/workspace缺失 | [DSH归档段](<../../3-表现现场/l4-20261029-cli/dsh/tools/lab.py>)已写full_sha256并复制workspace；静态局部修复，端到端mock由judge负责，不能用作者5/5声明冒称本复核实跑 |
| S2 unknown补零 | 无session requests=null、unscored weighted=null，静态局部关闭 |
| S3 timeout停止 | **开放实证阻断**：虽start_new_session+killpg，但只wait CLI；父退出不是组内子工具全停，PermissionError更非already gone |
| S4 外部集合真空 | [最新seal独立快照](<seal-source-snapshot-v4.json>)明确DSH两profile+全局AGENTS+实际Codex HOME config四件mandatory；repo Codex/cache配置入files。[原创9项](<seal-external-adversarial-v4.json>)9/9通过，[作者15项重跑](<author-seal-selftest-v4.json>)exit0；此成员集合漏洞局部关闭，实际CLI构建/动态加载闭包仍须E前核实 |
| S5 E等值链缺校验 | 固定gate已加preregistration==E、manifest.design==binding.design和PREREG D/E blob相等；[作者合成gate重跑](<author-gate-selftest-v2.json>)36/36 exit0，静态局部关闭；仍非真实E验收 |
| S6 replay能力夸大 | **开放**：[replay](<../../1-评测方案/工具链/l4-execution/replay_dual.py>)与首轮字节相同；目录存在≠full流重建，不应冒称实际比较分数，missing raw补0/母本直读等原问题仍在 |

停止链实证细节：[收据](<dsh-stop-adversarial-v2.json>)中自建父进程TERM退出-15，stop约1.6ms正常返回ack；忽略TERM子进程仍活，临时计数1→8继续写。finally对已知自建PGID KILL后计数稳定。不是只靠meta字段猜测。PermissionError用注入os权限失败，不向任何非自建进程发信号。

## 解释

[固定gate](</private/tmp/l4-gate-dsh-reviewed-v2-f89to7im/1-评测方案/工具链/l4-execution/gate.py#L748-L766>)将duration>=limit且attempt.outcome=timeout或diagnostic.stop_source当停止证据，未要求termination.stop_verified，也未核其对应真实runtime停止证明。[固定DSH](</private/tmp/l4-gate-dsh-reviewed-v2-f89to7im/3-表现现场/l4-20261029-cli/dsh/tools/lab.py#L578-L594>)只在CLI wait超时才升级KILL，CLI先退会遗留忽略TERM后代；权限拒绝也被吞。随后直接判卷/归档可与幸存工具写入竞态。

修正需要生产端与消费者两端同时生效：捕获派发时PGID、完整组/后代停止与权限失败处理、停止后再score；不可仅补stop_verified=true字符串。准入端必须拒绝缺/false停止证明及明确权限失败。对WB也不能把DB terminal后15秒安静窗口视为子工具已全停。

WB effort使用非空字符串校验，"unknown"非空于是逃过管理。应识别未知哨兵并要求对应影响/下一步/停止条件，不应强迫未知实际effort伪报low，也不应把允许的未知自动当产品零分。

## 未排除因素与停止条件

- 本轮只针对固定gate/DSH和mandatory seal集合，不代表Codex/cache/WB完整E准备度，不读取或重判真实产品答案。
- Lead通报stageI事故已确认**1 accidental_cli_start；已知插件真请求>=1，DeepSeek请求unknown**。原始temp logs丢失、仅SHA与片段，stub-key/无usage不能排除provider请求。必须独立分账、排除计划槽位与合成pass，不能作合法产品证据。E release前judge需复核新显式桩入口防复发；不得再笼统称全队zeroAPI。
- mandatory四件配置只证明必需成员不可遗漏，不证明实际运行器确用该文件或CLI/build不漂移；E消费前实际加载链与文件实hash仍需对应。
- 直到停止实证、WB未知管理、replay原阻断、其他runner与事故防复发检查齐备，再真实E封印并经Lead明确release；任何一项未清不得放行。

## 可复现实验

所有目标使用上述固定快照。以下输出路径必须换成新的不存在文件；原收据不得覆盖。

```bash
/usr/bin/python3 -B '5-评测报告/L4首请求前评审-2026-10-29/gate_adversarial_v2.py' \
  --source '/private/tmp/l4-gate-dsh-reviewed-v2-f89to7im/1-评测方案/工具链/l4-execution/gate.py' \
  --validator '1-评测方案/工具链/runner-schema-v2/validate_runner_meta.py' --out '<new-receipt>'
/usr/bin/python3 -B '5-评测报告/L4首请求前评审-2026-10-29/dsh_stop_adversarial.py' \
  --source '/private/tmp/l4-gate-dsh-reviewed-v2-f89to7im/3-表现现场/l4-20261029-cli/dsh/tools/lab.py' --out '<new-stop-receipt>'
/usr/bin/python3 -B '5-评测报告/L4首请求前评审-2026-10-29/seal_external_adversarial.py' \
  --source '/private/tmp/l4-seal-reviewed-v4-7niwsb28/execution_seal.py' --out '<new-config-receipt>'
```

下方证据行及漂移状态由脚本生成；tmp快照未来可能被清理，按收据全SHA定位对应源码复现。作者自测数不是产品运行数、也不替代上述独立反例。

## 脚本生成证据行与漂移状态

```text
5-评测报告/L4首请求前评审-2026-10-29/gate-dsh-source-snapshot-v2.json · 71bb20c6 · 2011B · 2026-10-29T21:14:54+08:00
5-评测报告/L4首请求前评审-2026-10-29/gate_adversarial_v2.py · 5bd32725 · 6659B · 2026-10-29T21:14:54+08:00
5-评测报告/L4首请求前评审-2026-10-29/gate-adversarial-v2.json · 29a9e775 · 24697B · 2026-10-29T21:14:54+08:00
5-评测报告/L4首请求前评审-2026-10-29/gate-adversarial-v2b.json · 420dd680 · 23238B · 2026-10-29T21:14:54+08:00
5-评测报告/L4首请求前评审-2026-10-29/dsh_stop_adversarial.py · f418668f · 6291B · 2026-10-29T21:14:54+08:00
5-评测报告/L4首请求前评审-2026-10-29/dsh-stop-adversarial-v2.json · 45072875 · 2725B · 2026-10-29T21:14:54+08:00
5-评测报告/L4首请求前评审-2026-10-29/seal-source-snapshot-v4.json · 43ff2bb7 · 720B · 2026-10-29T21:14:54+08:00
5-评测报告/L4首请求前评审-2026-10-29/seal_external_adversarial.py · dfddbb86 · 4608B · 2026-10-29T21:14:54+08:00
5-评测报告/L4首请求前评审-2026-10-29/seal-external-adversarial-v4.json · 20b5ab60 · 2912B · 2026-10-29T21:14:54+08:00
5-评测报告/L4首请求前评审-2026-10-29/author-gate-selftest-v2.json · 08679d37 · 10241B · 2026-10-29T21:14:54+08:00
5-评测报告/L4首请求前评审-2026-10-29/author-seal-selftest-v4.json · 44e8f332 · 1655B · 2026-10-29T21:14:54+08:00
/private/tmp/l4-gate-dsh-reviewed-v2-f89to7im/1-评测方案/工具链/l4-execution/gate.py · f8a4ca08 · 86883B · 2026-10-29T21:14:54+08:00
/private/tmp/l4-gate-dsh-reviewed-v2-f89to7im/3-表现现场/l4-20261029-cli/dsh/tools/lab.py · e221c1fe · 64504B · 2026-10-29T21:14:54+08:00
/private/tmp/l4-seal-reviewed-v4-7niwsb28/execution_seal.py · a756938d · 9842B · 2026-10-29T21:14:54+08:00
```

```json
{
  "generated_at": "2026-10-29T21:14:54+08:00",
  "scope": "live tree vs gate/DSH v2 fixed snapshot; expected ongoing repairs, not an E admission",
  "live_doc_drift": [
    {
      "path": "1-评测方案/工具链/l4-execution/gate.py",
      "snapshot_sha256": "f8a4ca082396e2e6eb61ccede06a224acac98efe80bfaff2fed1cb5a51a4d577",
      "live_sha256": "56a3f534cdd9bed21dce5786f738cb634e36242dda973d8276f6cd0b11b7b87e"
    },
    {
      "path": "3-表现现场/l4-20261029-cli/dsh/tools/lab.py",
      "snapshot_sha256": "e221c1fe07465cd1b38fb43037d1ae9bc2eacdd5054c0c2b1c23fec8301d372f",
      "live_sha256": "b322060006afca1c3eec58c5add69969ad6a08bef4f2cca0df932c0319a36e43"
    },
    {
      "path": "1-评测方案/自动循环L4-2026-10-29/execution_seal.py",
      "snapshot_sha256": "96c434b1d845529bda857ae88606acb31f90057b9c0cff8fadf44ec51238a3db",
      "live_sha256": "a756938d490634f19daa93454450d67fba4221c446bddad554f6c1b71992217c"
    },
    {
      "path": "1-评测方案/自动循环L4-2026-10-29/test_execution_seal.py",
      "snapshot_sha256": "32ff96ad29054e9a4ffa7a647cfd4a9b71aa32daa5bc88c40d2d0cecc61d4a6a",
      "live_sha256": "aac79e3e153989cb5e326b960266566fbcb30ef705d8b1c52b93bea2624d6c69"
    }
  ]
}
```
