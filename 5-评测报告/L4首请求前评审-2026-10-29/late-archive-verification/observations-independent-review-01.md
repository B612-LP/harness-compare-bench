# L4 综合观察汇总独立只读审查：v1两缺陷，v2修复通过

**结论：固定v1独立324项中322通过，存在拒因丢失与后验模式硬断言两项缺陷；固定v2独立351/351通过，两项均修复，原数值/分数/usage/正式0结论未被改写。当前v2可用于本批描述性汇总，未发现剩余已知数据错误；不构成正式产品排名、因果效应或可信实钟认证。**

live_doc_drift: []（审查固定快照与所列原始输入；Lead已授权生成的v2另立版本，不冒作v1源未变）。未执行builder/build、模型、产品CLI、checker、gate或网络请求；只读公共文件、解析结构、独立重算与hash。未修改任一原始产物、原v1/v2、judge源或E源；新增仅在本reviewer scope。

## 观察与版本

| 版本 | 固定源与产物 | 独立结果 |
|---|---|---|
| v1 | [固定指纹](<observations-source-snapshot-01.json>)，原[observations-final](<../../../5-评测报告/L4综合结论-2026-10-29/observations-final.json>) | [322/324](<observations-v1-independent-check.json>)；两项真实缺陷保留 |
| v2 | [固定指纹](<observations-source-snapshot-02.json>)，新[observations-final-v2](<../../../5-评测报告/L4综合结论-2026-10-29/observations-final-v2.json>) | [351/351](<observations-v2-independent-check-02.json>)，exit0 |

[独立v1程序](<review_observations_01.py>)与[独立v2程序](<review_observations_02.py>)没有调用被审builder；从冻结plan/contract、原meta/notexec、raw响应/请求/transport/intent与已钉住judge snapshot分别重算。

## 证据

### v1两项真实缺陷及v2闭合

1. **拒因丢失。**Codex cargo r1的judge源使用gate_admission_independent.block_reason，v1仅取fails并默认[]，于是formal=false却输出空canonical_fails，丢掉已有拒因。v2逐槽精确保留canonical_fails（源缺失为null）、canonical_block_reason、canonical_accounting；17槽与同一snapshot完全相同。
2. **把结果模式变成构建前提。**v1断言所有HTTP200、repeat=2048、其余=0并强制alias相等。这些是本批已观察值，不是应决定是否保留反例数据的设计不变量。v2去掉HTTP/2048/alias事后硬断言；alias一致性变成观测flag，值仍如实列。若未来出现不同结果，不应为符合本批模式而隐藏或改数据。

### 当前v2实际数据核验

- **覆盖/状态：**17冻结product slot精确去重覆盖，16份原meta和1份notexec互斥。producer_status、开始/结束/duration、原weighted/reward逐值相同；snapshot accounting为16 partial、1 not_executed，formal逐行求和与源summary/汇总均为0。
- **来源hash：**38个唯一引用的path/全SHA/bytes重算一致，包括immutable judge snapshot、plan、原meta/notexec、18份raw响应和rulings。另直接对16个产品的stdout、stderr、prompt共48份原文件重算SHA（及原流bytes）命中原meta，没有展示原文。
- **分数：**原weighted保留，未把reward=0/1冒作correct_count。只在judge.correct为合法整数时，以冻结分母重算8dp诊断reference；未知正确数保留null。WB cargo原70.37没有被反向修成8dp正式分。四个CLI product×case的3-rep序列、duration和观察range独立重算一致，不是总体方差或runner代际因果效应。
- **usage：**18个选定read pointer/state与各raw响应完全相同；missing/null/explicit zero不混写。chat两个alias逐值核、没有相加；creation_named_field只表示选定命名字段，不表示服务端所有creation字段或计费状态。
- **6对请求：**不只数(protocol,block)标签；逐组确认fresh/repeat/nonce-control恰各1，fresh与repeat原请求字节完全相同，control请求不同，request/response SHA与transport也一致。六组真实配对成立，但不是六个独立总体统计样本，不能只凭read=0断言绝对cold或无creation。
- **snapshot与跨版：**v1/v2消费同一immutable judge snapshot，引用SHA/bytes完全一致。v1原产物仍命中最初固定SHA。去掉新生成时刻、新增canonical字段、明确的null-vs-empty修复及alias观测flag后，v1/v2全部其余数据精确相等。builder在build函数之外整模块AST相同。
- **实钟：**所有时间带时区；生成时刻非未来、晚于全部原产品结束/探针完成记录，文件mtime同秒级一致；产品duration与秒级起止差在1.1秒舍入容差内。此支持本机实钟/记录先后自洽，不是NTP、可信时间戳或防回填认证；不同producer计时边界不自动相同。
- **只读：**审查读取的输入SHA前后零漂移。源码本身仅会在源快照目录独占新增快照、在指定out独占新增产物；没有原件覆盖/删除/模型调用代码。本审计没有执行它，以免当前judge变版触发新快照写入；未把“只读源”误说为完全不产生派生文件。

首次[v2审计收据](<observations-v2-independent-check.json>)中的两个失败是本reviewer仍将“原产物/mtime”指向v1路径造成，非v2数据错误。仅修审计路径后取得后续351/351；首次收据保留，不抹去或归因被审实现。

## 解释与使用范围

v2修正了信息投影，而不是改原始能力观察或追认准入。16个record_state=executed指实际执行记录覆盖，**不等于**R1证据完备executed，更不等于formal有效样本；v2新增canonical_accounting已允许直接看见partial。正式0不应写成产品能力0，也不应拿16替代有效正式样本数。

builder直接pin的是产品meta与cache raw响应；产品原始stdout/native trace/prompt的SHA是本审计额外核的，不能反过来夸称builder自身已遍历重算所有产品原始证据。原DSH stdout是原投影、不自动等同完整原生会话；晚补侧车不回填进原meta或formal。

## 未排除因素、停止条件与后续

- 目前通过仅针对本批已经存在且可解析的17+18记录，不保证builder是未来所有损坏JSON、失败/未发probe、缺score等输入的通用容错聚合器。新输入异常应保留unknown/完整分母，不静默删槽或借用本次PASS。
- fresh/nonce-control是计划条件名，计数命中模式是实测结果；不能推供应商所有缓存机制、同一权重、货币节省或自然恢复。
- WB首槽notexec原reason中“本批零new_task/sendPrompt”是该历史记录当时的上下文，不得扩大成后来四个WB槽或全队zeroAPI。Rust事故口径、未排除因素仍保留。
- SHA与snapshot证明字节版本，不替代污染语义、判卷guard、供应商来源或独立实钟认证。若引用源/SHA/slot集合或计数变化，须新版本复核，不能重写v1或原证据。
- 当前未发现v2剩余数据缺陷，可据此写描述性结论；仍禁止超出上述范围的因果归因、总体方差、跨产品正式排名或把formal0解释为模型零能力。

## 可复现实验

```bash
/usr/bin/python3 -B '5-评测报告/L4首请求前评审-2026-10-29/late-archive-verification/review_observations_01.py' --root '<repo>' --snapshot '<fixed-v1-snapshot>' --out '<new-scope-receipt>'
/usr/bin/python3 -B '5-评测报告/L4首请求前评审-2026-10-29/late-archive-verification/review_observations_02.py' --root '<repo>' --snapshot '<fixed-v2-snapshot>' --out '<new-scope-receipt>'
```

输出仅用本scope的新文件。v2程序也固定引用v1已审源作AST/跨版对照，复现时须保留机器指纹所列快照；没有原始调用或重判环节。

## 脚本生成版本字段与证据行

```json
{
  "v1": {
    "source_files": [
      {
        "path": "5-评测报告/L4综合结论-2026-10-29/build_observations.py",
        "snapshot": "/private/tmp/l4-observation-review-0upzwzsb/build_observations.py",
        "sha256": "2ec64a476a4a897416c3ef19be1d25ddedc6e319878dda93e72d17527a72a5b3",
        "bytes": 9418
      },
      {
        "path": "5-评测报告/L4综合结论-2026-10-29/observations-final.json",
        "snapshot": "/private/tmp/l4-observation-review-0upzwzsb/observations-final.json",
        "sha256": "5f717c44281b64e645ad9018b8492c6caebd7bc1797f7ee368f10cd6eef9a3e6",
        "bytes": 42462
      }
    ],
    "audit_counts": {
      "total": 324,
      "passed": 322,
      "failed": 2
    },
    "source_judge_snapshot_sha256": "ebbbb696cc2fbd70f410fae184d6bd5f274db0cabaa809214ee78b9fd2cfc061",
    "unique_reference_files_verified": 38,
    "additional_product_raw_hash_checks": 48,
    "actual_cache_pairs": 6,
    "protected_input_files": 145,
    "time_observation": {
      "generated_at": "2026-10-30T00:25:55+08:00",
      "latest_recorded_finish": "2026-10-30T00:04:52+08:00",
      "reviewer_now": "2026-10-30T00:36:55.246105+08:00",
      "trusted_external_clock_attestation": false
    },
    "live_doc_drift": []
  },
  "v2": {
    "source_files": [
      {
        "path": "5-评测报告/L4综合结论-2026-10-29/build_observations.py",
        "snapshot": "/private/tmp/l4-observation-review-v2-l_fv1h3h/build_observations.py",
        "sha256": "acf58232c620b950d8eafd27f65a0fb45485f5d35715c7ae1dbd8fa38f501586",
        "bytes": 9353
      },
      {
        "path": "5-评测报告/L4综合结论-2026-10-29/observations-final-v2.json",
        "snapshot": "/private/tmp/l4-observation-review-v2-l_fv1h3h/observations-final-v2.json",
        "sha256": "7a1fd8ab738a9f0e8342d42101e9db3d96cb0abf5270845be296f222b8f189f5",
        "bytes": 44142
      }
    ],
    "audit_counts": {
      "total": 351,
      "passed": 351,
      "failed": 0
    },
    "source_judge_snapshot_sha256": "ebbbb696cc2fbd70f410fae184d6bd5f274db0cabaa809214ee78b9fd2cfc061",
    "unique_reference_files_verified": 38,
    "additional_product_raw_hash_checks": 48,
    "actual_cache_pairs": 6,
    "protected_input_files": 146,
    "time_observation": {
      "generated_at": "2026-10-30T00:32:54+08:00",
      "latest_recorded_finish": "2026-10-30T00:04:52+08:00",
      "reviewer_now": "2026-10-30T00:40:13.208687+08:00",
      "trusted_external_clock_attestation": false
    },
    "live_doc_drift": []
  }
}
```

```text
5-评测报告/L4首请求前评审-2026-10-29/late-archive-verification/observations-source-snapshot-01.json · 91536520 · 737B · 2026-10-30T00:43:56+08:00
5-评测报告/L4首请求前评审-2026-10-29/late-archive-verification/observations-source-snapshot-02.json · a2950d2d · 752B · 2026-10-30T00:43:56+08:00
5-评测报告/L4首请求前评审-2026-10-29/late-archive-verification/review_observations_01.py · 4f0901dd · 16378B · 2026-10-30T00:43:56+08:00
5-评测报告/L4首请求前评审-2026-10-29/late-archive-verification/review_observations_02.py · d2b71dcd · 18490B · 2026-10-30T00:43:56+08:00
5-评测报告/L4首请求前评审-2026-10-29/late-archive-verification/observations-v1-independent-check.json · ad9828de · 107182B · 2026-10-30T00:43:56+08:00
5-评测报告/L4首请求前评审-2026-10-29/late-archive-verification/observations-v2-independent-check.json · 697103e6 · 109770B · 2026-10-30T00:43:56+08:00
5-评测报告/L4首请求前评审-2026-10-29/late-archive-verification/observations-v2-independent-check-02.json · a7291a61 · 109957B · 2026-10-30T00:43:56+08:00
/private/tmp/l4-observation-review-0upzwzsb/build_observations.py · 2ec64a47 · 9418B · 2026-10-30T00:43:56+08:00
/private/tmp/l4-observation-review-0upzwzsb/observations-final.json · 5f717c44 · 42462B · 2026-10-30T00:43:56+08:00
/private/tmp/l4-observation-review-v2-l_fv1h3h/build_observations.py · acf58232 · 9353B · 2026-10-30T00:43:56+08:00
/private/tmp/l4-observation-review-v2-l_fv1h3h/observations-final-v2.json · 7a1fd8ab · 44142B · 2026-10-30T00:43:56+08:00
```
