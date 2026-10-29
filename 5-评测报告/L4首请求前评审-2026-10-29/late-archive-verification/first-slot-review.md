# DSH 首槽晚补会话：身份与结构完整性支持，非正式准入恢复

**结论：首槽指定副本独立核验36/36，支持确属本次执行的root/child过程档案；22个受保护输入项SHA前后无漂移。collected_at确实晚于执行结束，必须作为late_archive侧车保留。原meta/gate/注册与执行时间、score、usage和污染裁定均不改；恢复成功不自动formal。task-10保持in_progress，等待余五槽。task-7不重开。**

live_doc_drift: []（仅本次明确列出的22个输入项；不宣称扫描整个用户目录）。原始prompt/轨迹/凭据不在本报告或机器收据中展示；只在内存解压这两个指定zstd副本，无其他用户会话扫描、无全局session源读取、无模型/产品/判卷调用。

## 观察

首槽为冻结计划中的dabstep r1。读取[晚补采集记录](<../../../3-表现现场/l4-20261029-cli/dsh/recoveries/l4-20261029-cli-dsh-dabstep-payments-10-r1/recovery-record.json>)及[该槽原meta](<../../../3-表现现场/l4-20261029-cli/dsh/runs/l4-20261029-cli-dsh-dabstep-payments-10-r1/meta.json>)，仅将记录列明的两份副本交给本地zstd解码器，输出完全留在内存。

[独立程序](<verify_late_archive.py>)生成[36项机器收据](<dab-r1-verification-01.json>)。采集与核验的真实时刻、原执行窗及延迟秒数均由下方脚本生成字段给出，没有回填成原运行时采集。

## 证据

| 项 | 独立结果 |
|---|---|
| root会话 | cwd与原meta.workspace严格相等；第一user文本UTF-8字节SHA与原prompt原物完全一致；UUID出现在该槽原stdout |
| child会话 | depth1、parentSession指向上述root；初始user任务block与root实际tool/call的.prompt参数逐字节相等；root轨迹含child UUID，child UUID也出原stdout |
| 子会话prompt边界 | child的完整初始消息含委派任务/上下文，**不是根prompt**；不把不同角色硬凑成同一prompt。验证的是实际父启动参数与子任务block的精确对应 |
| 原物SHA链 | 副本压缩字节SHA/字节数与采集record的source/copy字段一致；原prompt/stdout实算命中原meta记录 |
| 时间 | 两份副本mtime、session createdAt及事件time均在原执行窗±5秒内；沿用采集记录已披露容差，不另扩窗 |
| 可解析/结构终态 | zstd均exit0；child159、root351条JSONL全为可解析对象，均以turn/end结束；tool call/result ID多集闭合，无未配对ID |
| 只读保护 | 该原run树、两副本、采集record及指定冻结源/规则/binding共22项前后SHA相同；没有向原run/session目录新增文件 |

原meta仍为status=ok、scored 7/10、weighted=70、integrity_verdict=violation、session_scan_lines=0、usage.requests=null。这些是原观察，不因晚补档改写，也不把capture缺失误称模型能力为零。

## 解释

这补足了采集者此前未解压因而未确认的“内容身份”环节：root初始输入与原prompt完全相同；child通过实际父子ID与委派prompt绑定，而不是仅凭目录名/mtime推断。

晚补副本还含可用于**另外离线过程复核**的commit-point usage记录（root54、child22个assistant usage字典）。本程序保持missing/null/explicit zero分开，原usage不回填；这些记录数不冒称完整HTTP尝试分母、计费、节省比例或能力优势。污染语义裁定与正式准入仍归judge/auditor，不由JSONL可解析或恢复成功自动替代。

## 未排除因素、停止条件与下一步

- **真实源历史稳定性不是本评审直接重读证明。**采集record声称复制前后源稳定且给出source/copy SHA；本次独立验证副本与该链一致，并确认副本在本评审前后不变，但没有读取全局session源。影响：不能独立重建采集前源历史；下一步：judge结合原stdout/prompt与采集记录裁定此侧车可用范围；停止：若SHA、cwd、身份、prompt或时间有不匹配，结论必须unknown，不凑齐。
- 副本mtime与日志时间并非可信时间戳/签名。正常turn/end和ID闭合支持结构完整性，不证明所有内部HTTP均被记录或语义无污染。
- collected_at明确为晚补；不新建伪母本，不修改E脚本、原meta、原gate、原分数/时间或usage。原formal结果保持。
- 首槽当前可供judge作身份/过程完整性复核。其余五槽仅在Lead逐个明确提供完成副本后用同法追加，最终合成六行；不预扫描其他用户session或自动拿新发现目录补齐。

## 可复现实验

```bash
/usr/bin/python3 -B '5-评测报告/L4首请求前评审-2026-10-29/late-archive-verification/verify_late_archive.py' \
  --root '/Users/b612-lp/Documents/harness-compare-bench' \
  --run-id 'l4-20261029-cli-dsh-dabstep-payments-10-r1' \
  --out '<new-nonexistent-JSON-in-this-reviewer-scope>'
```

程序只读该明确run及该record列出的副本，解压到内存，不输出raw文本；输出必须是本子目录中新的不存在文件。任何匹配失败保持unknown，不能覆写首份收据或回填原记录。

## 脚本生成事实与证据行

```json
{
  "run_id": "l4-20261029-cli-dsh-dabstep-payments-10-r1",
  "verified_at": "2026-10-30T00:04:45.438750+08:00",
  "collected_at": "2026-10-29T23:50:35+08:00",
  "collected_after_finished_seconds": 854.0,
  "status": "identity_and_structural_completeness_supported",
  "counts": {
    "checks": 36,
    "passed": 36,
    "unknown_or_failed": 0
  },
  "original_prompt_sha256": "e507efee260b46095a09a1191cfa11c570e51e8f074f4cc7d448445dd1af6b2f",
  "original_stdout_sha256": "f2d20b5feebabbbdea06f9d13d95a9c4abc84ad3ff350c66bb8b1d74790340f0",
  "original_meta_sha256": "572f394aa3977d3a8228922f192de7580ce1194115a3cc462a7ba271f886cc7c",
  "original_observation_not_reclassified": {
    "status": "ok",
    "integrity_verdict": "violation",
    "score_status": "scored",
    "weighted": 70.0,
    "registered_at": "2026-10-29T23:13:56+08:00",
    "started_at": "2026-10-29T23:28:04+08:00",
    "finished_at": "2026-10-29T23:36:21+08:00",
    "judge_counts": {
      "correct": 7,
      "n_tasks": 10
    },
    "usage_requests": null,
    "session_scan_lines": 0
  },
  "live_doc_drift": []
}
```

```text
5-评测报告/L4首请求前评审-2026-10-29/late-archive-verification/verify_late_archive.py · 0cd90f55 · 19105B · 2026-10-30T00:12:42+08:00
5-评测报告/L4首请求前评审-2026-10-29/late-archive-verification/dab-r1-verification-01.json · e4dee72e · 26317B · 2026-10-30T00:12:42+08:00
3-表现现场/l4-20261029-cli/dsh/recoveries/l4-20261029-cli-dsh-dabstep-payments-10-r1/recovery-record.json · 8c63da31 · 3002B · 2026-10-30T00:12:42+08:00
3-表现现场/l4-20261029-cli/dsh/recoveries/l4-20261029-cli-dsh-dabstep-payments-10-r1/session/23afbcc7-dde2-46ad-aa8d-f1680ede9573/session.v4.jsonl.zstd · 02e3f18d · 213022B · 2026-10-30T00:12:42+08:00
3-表现现场/l4-20261029-cli/dsh/recoveries/l4-20261029-cli-dsh-dabstep-payments-10-r1/session/session-e4f07e0c-375c-4618-84f2-3bfdae54bf32/session.v4.jsonl.zstd · 17ddfd01 · 375048B · 2026-10-30T00:12:42+08:00
```
