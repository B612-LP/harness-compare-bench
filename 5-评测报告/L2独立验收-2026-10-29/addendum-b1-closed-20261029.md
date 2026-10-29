# Addendum：B-1 复验闭项（2026-10-29，实钟记录 17:04+08:00）

- 触发：lead 通知 B-1 已由 builder-codex 修复（commit `ab4be14`，2026-10-29T17:01:39+08:00），judge 按限定范围复验（不重跑 33 项全量）。
- 本文件为 [verify-receipt.json](<verify-receipt.json>) 的补充裁定；原文件未改动。

## 复验项与实测

| # | 检查 | 命令/对象 | 实测 | 结果 |
|---|---|---|---|---|
| 1 | v3 test_freeze | `python3 -B test_freeze.py`（v3 目录） | exit=0；**Ran 44 tests, OK**；尾行 `[live-ledger] events=5（仅报告，不断言）` | ✓ |
| 2 | 重写测试六点不变量 vs lead 裁定 | 读 `test_live_ledger_structural_invariants` | (a) 存在且可解析；(b) `schema_version==1`；(c) 逐条必备字段 event_id/kind/executor/timestamp/registered_at/source.path+sha256 且 `f.stamp` 强制 ISO8601 带时区（freeze.py:104 `tzinfo is None → Invalid`）；(d) event_id 无重复 + 时间非严格升序（`ts==sorted(ts)`）；(e) 活台账非任何 contract pin；(f) 事件数仅 print 不断言 | ✓ 六点一一对应 |
| 3 | 测试名替换与总数 | grep | `test_live_ledger_exists_and_empty` 已不存在，`test_live_ledger_structural_invariants` 1:1 替换，总数 44 不变 | ✓ |
| 4 | v3 verify | `freeze.py verify`（repo root） | exit=0；`ok=true`；`live_doc_drift=[]` | ✓ |
| 5 | v2 verify + 零改动 | `freeze.py verify`（v2）+ `git status --porcelain` | exit=0 `ok=true`；v2 双目录 porcelain 空 | ✓ |
| 6 | 新哈希 | shasum | lock=`544a7f96cb62…d2527` ✓；test_freeze=`aa374cbab639…312b8` ✓；README=`61fb267dbf7c…9dd25` ✓ | ✓ |
| 7 | 输出目录 vs `ae6b37d` 逐字节 | `git show ae6b37d:<file>` 与现文件 sha256 两两比对 | **11/11 全部 SAME**（含 lead 点名三项：six-ledgers `5b2e51cb…`、summary `02d6c843…`、official `95d07517…`） | ✓ |
| 8 | output-manifest 预期变化核对 | 读 manifest 内容 | **实测 manifest 未变化**（`84003413…` 与 ae6b37d 相同）：其 scope 仅覆盖 11 个输出文件自身哈希，**不引用** freeze.lock/test_freeze/freeze.py——故「覆盖变更 contract 文件而变化」的预期不成立，未变才是正确行为（无陈旧引用风险）。此为对 lead 预期的一个实测更正，非缺陷 | 实测更正 |
| 9 | README corrections 勘误框 | 读 v3 README :56-58 | dated `2026-10-29T17:00:17+08:00（实钟）`；corrections id=`pkgb-test-live-ledger-fix-20261029`；原断言（`events==[]`）引述保留、注明「未静默删改」；重建重锁（17 pin 重算）与 44 测试总数不变声明与实测一致 | ✓ |

## 补充裁定

- **B-1 → closed**（fixed in-loop，commit `ab4be14`；测试语义修正与重锁符合 lead 裁定，六点不变量与裁定一致，数据产物零字节漂移，披露框合规）。
- **包B 最终裁定：partial → pass**（B-1 闭项后，包B 验收标准全项满足：v3 build/verify ok、test_freeze 44/44 OK @HEAD、v2 零字节改动且 verify 绿、six-ledgers 110/13/7/3/5/13、7 收据各恰 1 次、official A=0/B=0、pin 10 contract/7 live_doc、AMENDMENT-L2-1 双哈希、README 继任语义+dated 勘误框）。observation B-2/B-3 与 note X-2 维持原状（B-3 的 L3 enum 扩列义务不变）。
- 其余三包裁定不变：包A pass、包C pass（C-1 已披露存证，义务留 L3）、包D pass。

## 哈希锚

- 本文件与原收据同目录；原 [verify-receipt.json](<verify-receipt.json>) sha256 `3de0dfa29bd8b9958e54febff1e7c40afd9dc4ef33805d4d6b264ba8b389cff5`（未改动）
- 复验运行留痕：/tmp/judge-l2/{v3-test-ab4be14.log, v3-verify-ab4be14.json, v2-verify-ab4be14.json}
