# DSH 两支路最终局部复验：原13项全部通过

**结论：原两支路release blockers局部解除，原13 runtime判据13/13、exit0。未重跑已关闭的gate/seal/replay或停止primitive。该局部PASS不等于全异常覆盖、E/API放行或正式产品验收。task-7保持in_progress，待Lead处置下述新静态异常边界风险。**

live_doc_drift: []（固定被测源码范围；当前工作树相对快照状态由文末脚本生成）。本人本轮无模型/API、真实产品CLI、checker或子进程执行；只用生产函数上的强制Python对象Popen桩，未读truth/solution/历史答案或实际vendor配置正文。Rust incident仍incomplete、已知插件真出站与DeepSeek unknown，不推成全队zeroAPI。

## 观察

Lead宣布DSH修复ready停写后，仅复制[新lab源码快照](<dsh-runtime-source-snapshot-v5.json>)。为保持模块文件层级常量可导入，同字节快照保留仓库相对深度；未修改builder源码。

使用完全不变的[原13项runtime检查器](<dsh_runtime_adversarial_v4.py>)运行，结果[13/13、exit0](<dsh-runtime-adversarial-v5.json>)。保留所有[上一失败](<dsh-runtime-adversarial-v4d.json>)，未覆盖首次失败或再增加“spawn必须halt”判据。

## 证据

| 同一世界/原判据 | 新固定源码结果 |
|---|---|
| timeout停止未确认正控制 | code3；真实timeout状态；停止原物verified=false；score null；checker/capture/rebuild/snapshot全0 |
| timeout后续槽 | 持久halt在位，后槽code3、增加Popen0 |
| normal-exit停止未确认 | 有meta与termination原物；status=error、underlying exit_code=0、timed_out=false；不再None.get失败或伪造timeout |
| normal-exit判卷与后槽 | checker/capture/rebuild/snapshot全0；后槽新增Popen0，持久halt有效 |
| Popen从未成功启动 | 不再引用未赋值PGID；notexecuted含身份、封印引用、reason、stop_source，无meta/虚造session/score；作者保守选择halt可接受但非本复核新增硬门 |

[固定源码对应分支](</private/tmp/l4-dsh-runtime-reviewed-v5-kmp_lptv/3-表现现场/l4-20261029-cli/dsh/tools/lab.py#L828-L930>)已选择effective_stop，保留真实phase与underlying returncode；原13项没有改目标。

## 解释

两项原确定缺陷现有直接闭合证据：正常结束但未证明组停写，不再丢首槽partial记录，也不再改写为timeout；真正Popen失败不再因未定义变量中断记账。已发但停止未知时，checker0和后槽Popen0都由实际函数控制流计数支持，而不是仅靠作者stdout中的“0”声明。

[前轮本体结论](<gate-dsh-preflight-v4.md>)的gate21/21、seal19/19、replay10/10仍为其各自固定字节的局部结论，本轮没有重复运行，不能相加当产品运行数或新完整端到端验收。

## 未排除因素、停止条件与下一步

**新静态异常边界风险已即时通知Lead，但依本次仅原13项的范围未追加新场：**源码except OSError覆盖Popen、communicate以及timeout停止调用整个try区域，而该except无条件声明process never started并记not_executed。若Popen已返回proc后communicate发生EIO/OSError，则“从未启动”的结论不成立；同分支也未对已经启动的组做停止清理。应将never-started捕获收窄到Popen，或以proc是否已存在分流：未启动可notexec，已启动必须真实error/partial并处置组停止。此为代码可见的条件性风险，不把尚未测试的失败当已发生产品事故，也不把13/13当异常全集证明。

在此边界处置明确前，不笼统宣布整个runtime全部准入就绪；不扩展成“所有spawn失败必须全批halt”。后续是否追加该异常路径独立负例由Lead确认。WB producer/native正常门、Rust防复发、实际E及vendor原物审仍不在本次局部PASS内。API继续禁，只有Lead可在最终条件齐备后显式release。

## 可复现实验

```bash
/usr/bin/python3 -B '5-评测报告/L4首请求前评审-2026-10-29/dsh_runtime_adversarial_v4.py' \
  --source '/private/tmp/l4-dsh-runtime-reviewed-v5-kmp_lptv/3-表现现场/l4-20261029-cli/dsh/tools/lab.py' \
  --out '<new-nonexistent-receipt>'
```

原输出禁止覆盖；临时快照可被清理，按快照完整SHA恢复对应源码。13项均为self_test，不是产品样本。

## 脚本生成证据行与漂移状态

```text
5-评测报告/L4首请求前评审-2026-10-29/dsh-runtime-source-snapshot-v5.json · 320333ab · 470B · 2026-10-29T22:31:53+08:00
5-评测报告/L4首请求前评审-2026-10-29/dsh_runtime_adversarial_v4.py · 6288c76a · 8324B · 2026-10-29T22:31:53+08:00
5-评测报告/L4首请求前评审-2026-10-29/dsh-runtime-adversarial-v5.json · 5916efb8 · 18076B · 2026-10-29T22:31:53+08:00
/private/tmp/l4-dsh-runtime-reviewed-v5-kmp_lptv/3-表现现场/l4-20261029-cli/dsh/tools/lab.py · 55694282 · 94035B · 2026-10-29T22:31:53+08:00
```

```json
{
  "generated_at": "2026-10-29T22:31:53+08:00",
  "scope": "live lab vs v5 fixed source; not an E admission",
  "live_doc_drift": []
}
```
