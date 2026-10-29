# DSH 六槽晚补档独立复核：六行身份齐备，一项采集时钟未知

**结论：按slot_id合并恰6个冻结槽，无重复/替换；8份指定zstd副本支持六槽身份与结构完整性。160项检查159通过、1项unknown（cargo r3未记录collected_at/采集起点），不能称160/160全PASS。93项受保护输入并集最终复hash无漂移。原formal总数0维持，晚补证不自动准入；没有产品重跑或原meta/gate/时间回填。**

live_doc_drift: []（仅机器收据列明的93项输入；不宣称全host/其他用户目录）。仅在内存解压Lead明确授权的本批副本，未读全局session源或其他用户会话，未展示原prompt/轨迹/凭据，未启动模型/产品CLI/判卷器。task-7保持已完成；本报告完成task-10的六行复核范围，不是重新裁定产品分数。

## 观察

使用[原程序](<verify_late_archive.py>)完成首槽与其余四槽；cargo r3原record缺collected_at，首次KeyError诊断[保留](<cargo-r3-first-batch-diagnostic.json>)。随后[第二版](<verify_late_archive_v2.py>)只将缺字段处理成unknown，不把at猜成collected_at，继续该唯一指定副本的内容核验。原首份收据、原记录均未覆盖。

最终[六行汇总](<final-six-summary-01.json>)按冻结slot_id与[明确授权列表](<authorized-six-slots.json>)精确合并，核唯一性/覆盖度；[汇总程序](<aggregate_six.py>)再次核所有原件/副本/记录/指定冻结源的输入SHA并集。

## 证据：最终恰六行

| slot_id（合并键） | 副本 | 身份/结构 | 采集字段 | 原分数（不重判） | 核验收据 |
|---|---:|---|---|---|---|
| `l4-20261029-cli-dsh-dabstep-payments-10-r1` | 2 | 支持 | 明确晚于结束 | 7/10，weighted=70.0 | [收据](<dab-r1-verification-01.public.json>) |
| `l4-20261029-cli-dsh-tb-cargo-plan-r1` | 1 | 支持 | 明确晚于结束 | 19/27，weighted=70.37037037 | [收据](<verification-l4-20261029-cli-dsh-tb-cargo-plan-r1-01.public.json>) |
| `l4-20261029-cli-dsh-tb-cargo-plan-r2` | 1 | 支持 | 明确晚于结束 | 20/27，weighted=74.07407407 | [收据](<verification-l4-20261029-cli-dsh-tb-cargo-plan-r2-01.public.json>) |
| `l4-20261029-cli-dsh-dabstep-payments-10-r2` | 2 | 支持 | 明确晚于结束 | 8/10，weighted=80.0 | [收据](<verification-l4-20261029-cli-dsh-dabstep-payments-10-r2-01.public.json>) |
| `l4-20261029-cli-dsh-dabstep-payments-10-r3` | 1 | 支持 | 明确晚于结束 | 7/10，weighted=70.0 | [收据](<verification-l4-20261029-cli-dsh-dabstep-payments-10-r3-01.public.json>) |
| `l4-20261029-cli-dsh-tb-cargo-plan-r3` | 1 | 支持 | unknown（未记录起点） | 20/27，weighted=74.07407407 | [收据](<verification-l4-20261029-cli-dsh-tb-cargo-plan-r3-02.public.json>) |

每槽均验证：副本压缩SHA/bytes与原采集链一致、原stdout UUID、header cwd与原meta.workspace、root第一user文本与原prompt逐字节相等、JSONL全可解析及终态/tool ID配对。两个有child的槽进一步验证parent UUID、root轨迹含child UUID、child初始任务block与父实际tool/call.prompt逐字节相等；child不被硬当root prompt比较。

### cargo r3时钟：未知继续未知

作者已提供不可覆盖[语义旁挂](<../../../3-表现现场/l4-20261029-cli/dsh/recoveries/l4-20261029-cli-dsh-tb-cargo-plan-r3/record-at-semantics.json>)，明确：其at是copy循环后记录构造/完成时刻，采集起点没有捕获；其他五份collected_at为copy前单一now()字段。collector为一次性内联代码，没有持久源可独立重读，因此该调用顺序是作者声明，不冒称本评审独立见证。

[本评审旁挂核验](<cargo-r3-clock-companion-review.json>)独立重算原record SHA并只对该指定副本stat，确认当前APFS birthtime/mtime及两者相等的异常；源record/旁挂前后不变。当前文件元数据可约束复制文件创建，不单独证明历史采集起点/完成时钟，也不能把mtime当源mtime。故该槽内容身份支持，collected_at/collection_start仍null/unknown，不用at或birthtime补齐。

### 原结果与receipt展示边界

原meta的实际分数在表中只作原观察，不重判；capture为空、usage null、污染裁定和最终原formal0保持。晚补日志可供judge/auditor额外复核过程与commit-point usage，不能倒写成运行时已存在的完整母本。

首次[规范检查](<first-slot-receipt-check.json>)发现原JSON中UUID尾12位被原helper词法当作不合规hex token；这是展示障碍，不是会话身份失配。没有改helper、没有豁免sha字段、没有改原始收据。只用[展示适配程序](<make_public_json_view.py>)生成新的public.json视图，以标准JSON Unicode转义UUID字符串；[等值证明](<public-json-equivalence.json>)逐份确认json.loads后所有ID/path/sha/整数/布尔值完全相同，原件不变，独立大写SHA字面也不会被该适配改变。表中链接这些完全等值视图，原机器收据继续保留。

## 解释

这补足的是晚补档的身份与结构链，不是模型重跑或正式准入追认。根prompt精确一致、实际委派prompt精确对应、原stdout UUID与事件时间共同支持本批绑定，强于只凭目录名/mtime；但SHA/JSONL/正常turn_end不是语义无污染证明，也不是完整HTTP尝试分母或可信时间戳。

原有7/10等机械得分不能因capture缺失被说成模型能力0；同样，恢复出日志与usage也不能自动将原formal0改成有效正式样本。过程可复核性、原能力观察、正式准入分别列示。

## 未排除因素、停止条件与后续

- 真实global session源的采前/采后稳定性仅为collector record历史声明；本评审只核副本与该SHA链、当前输入稳定性，不冒充直接源读或历史时钟实测。影响：不能独立重建更早源历史；下一步：judge结合原stdout/prompt与已披露采集链限定使用；停止：身份/SHA/时间不匹配即unknown，不凑齐。
- cargo r3采集起点未知，作者语义旁挂不补事实。其他五槽有明确collected_at且晚于执行结束；这些仍是原采集字段，不是外部可信时间证明。
- 缺失/null/显式0在晚补commit-point usage中分开保留，原usage不回填；记录数不冒称全部内部HTTP请求数，不推计费/节省比例/质量优势。
- 结构完整性通过不替代污染语义审查、正式准入、判卷回归或产品来源真实性审查。judge/auditor可引用本侧车，原源/原record/meta/gate/时间/分数不变。
- 六槽已按授权全部审到，一项未知明示；不为追求全绿追加未授权源读取或重跑，不扫描其他用户session，不建立伪母本。

## 可复现实验

先按[授权列表](<authorized-six-slots.json>)逐一运行原程序；缺collected_at的cargo r3使用v2，预期exit1并输出unknown，不能把此exit当产品失败。所有输出用本scope的新路径，不覆盖既有收据。解压仅到内存。

```bash
/usr/bin/python3 -B '5-评测报告/L4首请求前评审-2026-10-29/late-archive-verification/verify_late_archive.py' --root '<repo>' --run-id '<explicit-frozen-run-id>' --out '<new-scope-receipt>'
/usr/bin/python3 -B '5-评测报告/L4首请求前评审-2026-10-29/late-archive-verification/verify_late_archive_v2.py' --root '<repo>' --run-id 'l4-20261029-cli-dsh-tb-cargo-plan-r3' --out '<new-scope-receipt>'
```

汇总/展示脚本输出也为独占新文件；完整重放需在不含这些同名派生输出的新reviewer目录树/仓库副本中进行，不能删旧收据腾位置。

## 脚本生成字段与证据行

```json
{
  "generated_at": "2026-10-30T00:18:41.613895+08:00",
  "merge_key": "slot_id",
  "exactly_six_unique_frozen_slots": true,
  "counts": {
    "identity_supported_slots": 6,
    "collection_field_confirmed_late": 5,
    "collection_time_unknown_slots": 1,
    "session_copies": 8,
    "checks": 160,
    "passed": 159,
    "unknown_or_failed": 1
  },
  "protected_union_entries": 93,
  "protected_union_manifest_sha256": "d08582079166d4d5c539a033b8bc89b523a1b5fcb0b8d84e6a3c8a6b8c070640",
  "protected_union_rechecked_at_final_aggregation": true,
  "original_formal_total_per_Lead_not_recomputed": 0,
  "formal_effect": "none; original source/meta/gate/times/score/usage unchanged",
  "live_doc_drift": [],
  "clock_rows": [
    {
      "slot_id": "l4-20261029-cli-dsh-dabstep-payments-10-r1",
      "collected_at": "2026-10-29T23:50:35+08:00",
      "collector_record_at_separate": null,
      "collected_after_finished_seconds": 854.0,
      "collection_time": "confirmed_late_field"
    },
    {
      "slot_id": "l4-20261029-cli-dsh-tb-cargo-plan-r1",
      "collected_at": "2026-10-30T00:01:23+08:00",
      "collector_record_at_separate": null,
      "collected_after_finished_seconds": 1362.0,
      "collection_time": "confirmed_late_field"
    },
    {
      "slot_id": "l4-20261029-cli-dsh-tb-cargo-plan-r2",
      "collected_at": "2026-10-30T00:01:23+08:00",
      "collector_record_at_separate": null,
      "collected_after_finished_seconds": 1082.0,
      "collection_time": "confirmed_late_field"
    },
    {
      "slot_id": "l4-20261029-cli-dsh-dabstep-payments-10-r2",
      "collected_at": "2026-10-30T00:01:23+08:00",
      "collector_record_at_separate": null,
      "collected_after_finished_seconds": 489.0,
      "collection_time": "confirmed_late_field"
    },
    {
      "slot_id": "l4-20261029-cli-dsh-dabstep-payments-10-r3",
      "collected_at": "2026-10-30T00:01:23+08:00",
      "collector_record_at_separate": null,
      "collected_after_finished_seconds": 122.0,
      "collection_time": "confirmed_late_field"
    },
    {
      "slot_id": "l4-20261029-cli-dsh-tb-cargo-plan-r3",
      "collected_at": null,
      "collector_record_at_separate": "2026-10-30T00:02:29+08:00",
      "collected_after_finished_seconds": null,
      "collection_time": "unknown"
    }
  ]
}
```

```text
5-评测报告/L4首请求前评审-2026-10-29/late-archive-verification/verify_late_archive.py · 0cd90f55 · 19105B · 2026-10-30T00:21:56+08:00
5-评测报告/L4首请求前评审-2026-10-29/late-archive-verification/verify_late_archive_v2.py · 2188ca8a · 19503B · 2026-10-30T00:21:56+08:00
5-评测报告/L4首请求前评审-2026-10-29/late-archive-verification/aggregate_six.py · 61da17bc · 8958B · 2026-10-30T00:21:56+08:00
5-评测报告/L4首请求前评审-2026-10-29/late-archive-verification/make_public_json_view.py · 24277767 · 2970B · 2026-10-30T00:21:56+08:00
5-评测报告/L4首请求前评审-2026-10-29/late-archive-verification/final-six-summary-01.json · deaeea32 · 10242B · 2026-10-30T00:21:56+08:00
5-评测报告/L4首请求前评审-2026-10-29/late-archive-verification/cargo-r3-clock-companion-review.json · 26037126 · 2037B · 2026-10-30T00:21:56+08:00
5-评测报告/L4首请求前评审-2026-10-29/late-archive-verification/public-json-equivalence.json · da0b21da · 3320B · 2026-10-30T00:21:56+08:00
5-评测报告/L4首请求前评审-2026-10-29/late-archive-verification/cargo-r3-first-batch-diagnostic.json · d07fb104 · 1737B · 2026-10-30T00:21:56+08:00
5-评测报告/L4首请求前评审-2026-10-29/late-archive-verification/dab-r1-verification-01.public.json · cb033cd2 · 33477B · 2026-10-30T00:21:56+08:00
5-评测报告/L4首请求前评审-2026-10-29/late-archive-verification/verification-l4-20261029-cli-dsh-tb-cargo-plan-r1-01.public.json · c26f4a64 · 22776B · 2026-10-30T00:21:56+08:00
5-评测报告/L4首请求前评审-2026-10-29/late-archive-verification/verification-l4-20261029-cli-dsh-tb-cargo-plan-r2-01.public.json · a35b0d11 · 22776B · 2026-10-30T00:21:56+08:00
5-评测报告/L4首请求前评审-2026-10-29/late-archive-verification/verification-l4-20261029-cli-dsh-dabstep-payments-10-r2-01.public.json · b0781b34 · 33474B · 2026-10-30T00:21:56+08:00
5-评测报告/L4首请求前评审-2026-10-29/late-archive-verification/verification-l4-20261029-cli-dsh-dabstep-payments-10-r3-01.public.json · b5371761 · 22915B · 2026-10-30T00:21:56+08:00
5-评测报告/L4首请求前评审-2026-10-29/late-archive-verification/verification-l4-20261029-cli-dsh-tb-cargo-plan-r3-02.public.json · e18a7537 · 22895B · 2026-10-30T00:21:56+08:00
```
