# 判分收据同字节结构（r1109 DSH score-receipt）— 预注册 v1

- 冻结：2026-11-16T05:01+08:00（任何 result 计算前）。离线纯算法；0 新运行；不改分数/门/25 格。执行记录进包内 EXECUTION-RECORD.md，不写本页。

## 1. 问题
bird r2/r3 的 score-receipt.json 与 score-receipt.retrorun-benchprivate.json 各自逐字节相同（且 mtime 同秒），而 exercism/lcb 三重复收据互异；两工作区互异。同字节是「结构性重合」（收据不含运行独有字段，同结果元组⇒同字节；同秒=回判批量写入）还是「复制/覆盖错误」（收据非逐运行忠实记录）？

## 2. 冻结判据（内容无关：键名、SHA、字节数、mtime、计数；不读任何值文本）
- 全 15 槽收据 schema 键集枚举；按「结果元组」(earned, possible, reward, rule_version, checker_sha256) 分组：
  - 同元组且同 case 的 rep 对：收据字节相同 ⇒ 记 collapse（结构性重合候选）；不同 ⇒ 记 diverge-with-same-tuple（含运行独有材料的证据）。
  - 不同元组的对：收据必不同，违反 ⇒ exit 2。
- judging_incident 子键集与 cause/pre_fix_checker_stdout 的字节长度+SHA256（不读文本）逐 rep 登记并比较。
- retrorun 收据存在性映射（哪些槽有）+ 同上比较。
- mtime 矩阵（逐收据，秒级）与同秒组登记。
- 工作区互异性：bird r2/r3 workspace 文件集 SHA 聚合（已勘察 r2≠r3，包内复算）。
- 观测面仅 r1109 DSH 15 槽；WB/Codex/元宝/豆包不在范围。

## 3. 分支
- B-STRUCTURAL-COINCIDENCE：所有 collapse 对均可由「同元组+incident 材料无运行独有内容（长度/SHA 相同）」解释，且 diverge-with-same-tuple 对的 divergence 可定位到 incident 子键的逐 rep 材料；mtime 同秒组与回判批量语义一致 ⇒ 收据忠实，§4.34 的 unexplained 标记可关闭为结构性。
- B-COPY-ANOMALY：出现下列任一 ⇒ 收据非逐运行忠实的证据：同元组但对内 incident 材料 SHA 不同而收据仍同字节（矛盾，exit 2）；collapse 模式与元组分组不一致；mtime 与回判批量语义矛盾（如 r3 早于 r2 写入）；retrorun 收据含逐运行材料（互异对）而 bird r2/r3 同字节无材料解释。
- 数据不足以二选一 ⇒ B-INDETERMINATE，如实登记哪一探针缺失。

## 4. 交付
verify.py（--root 必填 + --archive-root 必填指向 launch-r1109；stdout 摘要；--output 独占创建；双档 stdout 逐字节一致；fail-closed exit 2）+ test_verify.py（≥14，双档全绿，真档案测试环境变量门控拒绝静默跳过）+ result.json（schema receipt-collapse-v1，含 prereg sha256 与 baseline_commit）+ EXECUTION-RECORD.md。不改本页与任何既有文件。

## 5. 解释边界
内容无关纪律：不读 cause/stdout 文本，逐 rep 材料 SHA 只证「是否同一字节串」，语义由文本本身在私档承载；不推断回判实现意图；不构成对任何分数的修改建议。
