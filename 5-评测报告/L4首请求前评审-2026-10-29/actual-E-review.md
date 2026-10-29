# L4 实际 E 独立验收：PASS，可由 Lead 调度

**结论：实际E独立只读核验101/101、exit0；未发现当前E封印/字节绑定层面的剩余release blocker。E已具备由Lead按冻结合同调度的条件，可由Lead先释放cache18。本审计没有发出任何模型或产品调用；binding release bit=true与producer调度hold分开，只有Lead解除hold。**

live_doc_drift: []（本次实际E核验时点；后续每次派发仍须生产端即时重核）。本次只用只读git、标准库路径解析与原字节SHA；外部配置/包体只流式hash、不解码、不打印正文，不执行CLI、版本命令、SDK、模型、判卷或答案读取。

## 观察

读取真实[execution-manifest](<../../1-评测方案/自动循环L4-2026-10-29/execution-manifest.json>)与[runtime-binding](<../../1-评测方案/自动循环L4-2026-10-29/runtime-binding.json>)后，使用[原创独立核验脚本](<actual_E_readonly_check.py>)验证真实E，不调用候选gate/seal自身函数作为唯一证明。

完整[独立机器收据](<actual-E-readonly-check.json>)101项全部通过。另独占保存本次所验的[manifest字节副本](<actual-E-manifest-reviewed.json>)、[binding字节副本](<actual-E-runtime-binding-reviewed.json>)；没有改写原manifest、binding或重新封E。

## 证据

| 核验项 | 独立结果 |
|---|---|
| 身份与release位 | 设计D、预注册E、执行E精确匹配指定全ID；manifest.design一致；release bit为bool true |
| 仓内必需集合 | 独立AST读取已审closure常量并自行遍历，required集合与manifest **42成员精确相等**；无软链/路径越界 |
| 仓内原字节 | **42个E blob逐字节等于磁盘**，两者SHA均等于manifest值 |
| D/E三原件 | PREREGISTRATION、plan、contract三个D blob、E blob、磁盘字节全相同；plan/contract亦命中binding SHA |
| manifest绑定 | E中的manifest blob与磁盘原字节一致，实算SHA与binding完全一致；核验前后manifest/binding均未变化 |
| 时点与祖先 | registered_at字符串精确等于真实E提交%cI；manifest生成时点一致；D→E、E→HEAD祖先检查均通过 |
| 外部必需集合 | 独立解析当前launcher真实路径、包metadata、Codex native、DSH own lib与六项基础配置/应用标识，集合与manifest **17成员精确相等** |
| 外部原字节 | **17项规范绝对路径原件SHA全部命中**；只hash，不打印配置/包正文，不运行产品 |
| 受审候选对齐 | 本人已审gate/seal/replay/DSH展示delta、恢复版helper/validator等SHA命中；其他producer SHA与Lead提供的judge审过版本相同 |
| 构建声明边界 | manifest明确不声称exhaustive transitive product dependencies全封闭 |

完整命令与逐成员全SHA见机器收据；时刻/全ID在文末由脚本从canonical binding/独立收据生成，不手抄叙述。

## 解释

这次验的是**实际已提交E**，不再仅是合成git或候选前测：真实提交内源码、规则及manifest与消费时磁盘一致，必要外部成员不是真空自报，注册时点与祖先链闭合。它支持“此E可由Lead调度”，不证明产品能力、真实运行质量、供应商权重或可信外部时间戳。

DSH最后展示delta已在[7/7独立复核](<dsh-display-delta-check-v7.json>)中证明整模块AST在移除纯显示适配后等价，且实际E源SHA命中。WB safe_driver清注释尾空格的事实由Lead给出，本次核[其自测记录](<../../1-评测方案/自动循环L4-2026-10-29/selftest/comment-whitespace-equivalence.json>)新旧SHA/AST声明与实际manifest新SHA绑定；不冒称本人重建过旧body。WB/Codex/cache producer功能语义仍分别归其judge证据，不借本次101项重新宣称产品端到端验收。

[lead绑定自检说明](<../../1-评测方案/自动循环L4-2026-10-29/selftest/execution-seal-binding-check.json>)披露manifest独占生成后，汇总打印len(int)发生console错误。本审计不把打印异常当manifest失败或零调用证明；只根据当前实际E blob、磁盘与binding字节核验成功给出意见，也不臆造重封历史。

## 未排除因素、停止条件与下一步

- binding已一次生成true，**并不表示本审计已向producer发release**；本次开始与结束均未执行模型/产品CLI。Lead可现在按合同解除cache18调度hold，不得绕过producer派发前即时source/config核验。
- 任何后续源码/配置/应用包体/必需集合漂移，必须停止相应派发并披露；当前PASS不覆盖任意未来字节。E后自测仍在/tmp副本跑，避免manifest源码根新receipt触发成员漂移。
- merge commit保留D/E为main祖先，不撤祖先门；合并后的消费仍须实际验证E→HEAD。
- PGID scope/host guarantee none、短窗口workspace探测非全host停写证明、未知管理、原始流/完整投影区分等既有边界保留；任何闭包未证/仍写迹象按合同partial、无checker、halt。
- Git时间只是精确绑定依据，不是不可伪造时间戳；SHA证明字节一致，不证明证据语义或供应商真实性。E后真实vendor/native原物仍需独立裁定与全分母判卷。
- Rust事故仍独立记账：1 accidental_cli_start、已知插件真出站至少1、DeepSeek unknown/incomplete，排除计划槽/合成pass，不据本次只读零调用扩大为全队zeroAPI。

## 可复现实验

```bash
/usr/bin/python3 -B '5-评测报告/L4首请求前评审-2026-10-29/actual_E_readonly_check.py' \
  --root '/Users/b612-lp/Documents/harness-compare-bench' \
  --out '<new-reviewer-scope-receipt>'
```

脚本还独占保存固定名称的manifest/binding副本；仅更换out文件名不足以在原目录重跑。完整复现须在同一D/E历史的全新仓库副本中，保留相同外部环境、把脚本放在其限定reviewer目录，且该目录尚无这两份副本；不得删除/覆盖本次原始收据来重跑。全测试数为预检断言，不是产品运行样本数。

## 脚本生成 canonical 字段与证据行

```json
{
  "design_commit": "bb14897a7d1ac26c06697bb80a15d94158cd8ae0",
  "execution_seal_commit": "5674de65c05c632eb20fbd2e30bdeb7e08c6753a",
  "registered_at": "2026-10-29T23:13:56+08:00",
  "binding_release_bit": true,
  "manifest_sha256": "da1a4fa09a2f64fefdf2a5339c83b8c9a992ad5c95cb79d810c46f671f7cd017",
  "binding_sha256": "bf73ed8071d5dbd36dadc723ae7764e4b60d0fa14a0183c93649c56b4b98ff18",
  "audit_generated_at": "2026-10-29T15:19:56.105684+00:00",
  "counts": {
    "total": 101,
    "passed": 101,
    "failed": 0
  },
  "repo_members": 42,
  "external_members": 17,
  "scheduling_opinion": "Eligible for Lead release, not launched by reviewer",
  "live_doc_drift": []
}
```

```text
5-评测报告/L4首请求前评审-2026-10-29/actual_E_readonly_check.py · cb40e8d9 · 13652B · 2026-10-29T23:23:11+08:00
5-评测报告/L4首请求前评审-2026-10-29/actual-E-readonly-check.json · 6c1f2d46 · 49870B · 2026-10-29T23:23:11+08:00
5-评测报告/L4首请求前评审-2026-10-29/actual-E-manifest-reviewed.json · da1a4fa0 · 8524B · 2026-10-29T23:23:11+08:00
5-评测报告/L4首请求前评审-2026-10-29/actual-E-runtime-binding-reviewed.json · bf73ed80 · 660B · 2026-10-29T23:23:11+08:00
```
