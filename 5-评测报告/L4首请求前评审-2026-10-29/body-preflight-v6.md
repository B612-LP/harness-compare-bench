# L4 本体 pre-E 最后局部结论：通过，等待真实 E blob 审查

**结论：本次已审字节与判据范围内，未发现剩余本体release blocker。DSH原13关键runtime判据加唯一新增post-launch EIO场景的6项断言，共19/19、exit0；前轮OSError捕获边界风险解除。该结论不是E封印验收或API放行。task-7继续in_progress，等待Lead提供实际E blob/manifest/binding清单。**

live_doc_drift: []（固定受审字节范围；当前原树与快照对照见下方脚本状态）。本轮无模型、产品CLI、真实checker或真实子进程执行；Popen强制为Python对象桩，EIO只注入一次已创建proc之后的communicate，真实调用生产run_slot/cmd_run异常处理。不读取答案、真实vendor配置正文或全局规则原物。

## 观察

仅固定[DSH最后delta快照](<dsh-runtime-source-snapshot-v6.json>)，不重开gate/seal/replay、停止primitive与全部作者控件。使用[最后runtime检查器](<dsh_runtime_adversarial_v6.py>)保留[既有13项](<dsh_runtime_adversarial_v4.py>)，只增一个post-launch EIO世界；完整[19项收据](<dsh-runtime-adversarial-v6.json>)全部通过。

## 证据

- **Popen从未启动**：仅Popen调用自身的OSError被记not_executed；身份、封印引用、reason、stop_source齐，无假meta/session/score。保守halt是producer政策，不是本评审新增硬门。
- **已启动后EIO**：对象proc已由Popen返回并记PID/PGID后，communicate注入OSError(5)。生产函数进入真实error/partial，weighted=null、不生成notexecuted；调用必要组清理一次，checker/capture/rebuild/snapshot均0。组停止未证时持久halt，后槽Popen新增0。未将已启动过程冒称never started。
- **normal-exit停止未确认**：保持status=error、underlying exit0、timed_out=false；有partial meta及停止原物，checker0/后槽新增Popen0。
- **timeout停止未确认控制**：保持真实timeout语义，停止原物false、score null、checker0/后槽新增Popen0。

[固定生产源码](</private/tmp/l4-dsh-runtime-reviewed-v6-6zos578v/3-表现现场/l4-20261029-cli/dsh/tools/lab.py#L878-L952>)把spawn-only try与post-launch OSError路径分开；不再使用前轮过宽捕获作“从未启动”结论。EIO是独立合成异常注入，不声称真实产品/模型发生了EIO。

## 解释

本轮闭合的是上一轮明确剩余风险，不是重复证明所有异常路径。当前本体pre-E局部结论组合为：

| 已审本体 | 独立证据/范围 |
|---|---|
| 共同gate | [原物/跨槽/双说等原21项21/21](<gate-adversarial-v4.json>)；含WB None exit_code加原生completed封套，不虚造OS 0 |
| lead seal | [构建必需集合19/19](<seal-build-adversarial-v4.json>)；native payload/CLI自有代码在所声明集合内强制，不冒称第三方全transitive闭包 |
| replay | [诚实局部投影10/10](<replay-adversarial-v4.json>)；partial_text_usage_projection、legacy unknown/vacuous、双侧score not_evaluated |
| DSH最后delta | [关键13项+一个EIO世界，19/19](<dsh-runtime-adversarial-v6.json>) |

前三项本轮没有重跑，分别绑定其[已审候选快照](<gate-dsh-source-snapshot-v4.json>)。任何后续源码delta不能自动继承PASS，必须在实际E清单比对中显式处理。这些计数是self_test断言，不可相加冒称产品运行样本数。

## 未排除因素、停止条件与下一步

- **组/host边界**：[源码声明](</private/tmp/l4-dsh-runtime-reviewed-v6-6zos578v/3-表现现场/l4-20261029-cli/dsh/tools/lab.py#L852-L856>)仅覆盖launched PGID，host_guarantee none；[双采样探针](</private/tmp/l4-dsh-runtime-reviewed-v6-6zos578v/3-表现现场/l4-20261029-cli/dsh/tools/lab.py#L710-L734>)只看短窗口workspace文件数/总字节增长，不证明没有脱组、延迟或等长写入者。影响：全host停写未被证明；下一步：E后逐槽结合组原物与workspace证据审；停止：检测仍写或闭包未证则partial、无checker、halt。不能把短窗口安静当全停保证。
- **PII派生边界**：[snapshot_config](</private/tmp/l4-dsh-runtime-reviewed-v6-6zos578v/3-表现现场/l4-20261029-cli/dsh/tools/lab.py#L183-L224>)仅对公开全局规则副本调用标签/凭据脱敏，源文件仅只读、source SHA仍取原字节。此为源码核验，不读取实际私人原物或声称所有PII形态已穷尽检测。
- **收据闸门**：Lead已接管恢复原[receipt_check](<../../1-评测方案/工具链/evidence-kit/receipt_check.py>)字节，撤销跳过digits+B的越界弱化；本轮不重审该已撤patch。仅使用恢复版机械检查本报告canonical证据行，不变更helper。
- **外部验收**：WB/Codex producer由judge独立审的结果属于其证据；本报告不把转述当本人重跑，也不替代E后真实native/vendor原物语义审。
- **事故口径**：Rust incident仍1 accidental_cli_start、已知插件真实出站至少1、DeepSeek请求unknown/incomplete；排除计划槽与合成pass，不能再笼统全队zeroAPI。
- **下一门**：Lead生成实际E后，核D三件blob不变、受审源码与真实manifest成员/全SHA、必要外部构建/配置、E祖先与精确绑定/release纪律。采用merge commit保留D/E祖先、E后selftests只在/tmp副本。实际E通过且Lead明确release前，API继续禁止。

## 可复现实验

```bash
/usr/bin/python3 -B '5-评测报告/L4首请求前评审-2026-10-29/dsh_runtime_adversarial_v6.py' \
  --source '/private/tmp/l4-dsh-runtime-reviewed-v6-6zos578v/3-表现现场/l4-20261029-cli/dsh/tools/lab.py' \
  --out '<new-nonexistent-receipt>'
```

首失败、各轮reviewer fixture修正与原阻断证据全部保留；不得覆盖原收据。

## 脚本生成证据行与漂移状态

```text
5-评测报告/L4首请求前评审-2026-10-29/dsh-runtime-source-snapshot-v6.json · c72096b0 · 471B · 2026-10-29T23:08:49+08:00
5-评测报告/L4首请求前评审-2026-10-29/dsh_runtime_adversarial_v6.py · eb5920e4 · 9166B · 2026-10-29T23:08:49+08:00
5-评测报告/L4首请求前评审-2026-10-29/dsh-runtime-adversarial-v6.json · 19eb481e · 26211B · 2026-10-29T23:08:49+08:00
/private/tmp/l4-dsh-runtime-reviewed-v6-6zos578v/3-表现现场/l4-20261029-cli/dsh/tools/lab.py · 671630d5 · 105009B · 2026-10-29T23:08:49+08:00
1-评测方案/工具链/evidence-kit/receipt_check.py · effda0ed · 14041B · 2026-10-29T23:08:49+08:00
```

```json
{
  "generated_at": "2026-10-29T23:08:49+08:00",
  "scope": "live lab vs v6 fixed source; body preflight only, not actual E admission",
  "restored_receipt_helper_sha256": "effda0ed1c89876849008421782a701cf3c18a6c80c2434b76db389290fc2eb3",
  "live_doc_drift": [
    {
      "path": "3-表现现场/l4-20261029-cli/dsh/tools/lab.py",
      "snapshot_sha256": "671630d5766cfe8b18bfcd821882239a4a1c0f974159f88b702dc4f68a620d0f",
      "live_sha256": "f246d0113219b325341ac35f75ad5e194a68da4a15a73a2761639133f6f4e19d"
    }
  ]
}
```
