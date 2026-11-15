# EXECUTION-RECORD — 判分收据同字节结构-2026-11-16（builder）

执行时间：2026-11-16 05:12–05:35（Asia/Shanghai）
执行者：builder（receipt-builder，Agent Teams 子代理）
工作目录：仓库根（HEAD=c27f73191e915192ec9387671ef703c32f716746，开工已验、收工未变）
完全离线执行：无网络、无新产品/模型调用；仅只读公开仓库与指定私档；仅包目录内新建 4 文件；未改任何既有文件；无 git 写操作；临时物只写 /tmp。

## 1. 冻结预注册核验（开工门）

- README.md SHA256 = `47c0fef7c563863b926af13cb1e8a3d3ea53272f63b32581aaf9c311490ed074`（3044B）——开工验证通过，收工复核未变。
- 预注册判据逐条字面实现；无判据放宽。未触发 STOP（详见 §6 冲突处置）。

## 2. 交付物（包目录内 4 个新文件）

| 文件 | 字节 | SHA256 |
|---|---|---|
| verify.py | 44009 | `fdeb7cf5e7319477635af0e3ce5734dc5df66fdbae052a126eade330a3aa744d` |
| test_verify.py | 33405 | `81e79d46bd20da7fedc1e6c6938705723912f331446cbe75445e53bde384341d` |
| result.json | 75581 | `57f2200a6c396ed6311b9e74edfcb7a6b53e38b23f73ac96edec35e9bf872e22` |
| EXECUTION-RECORD.md | （本文件） | 见收工自检输出 |

README.md（冻结，未动）：3044B，`47c0fef7…490ed074`。

## 3. 命令

```bash
python3 verify.py --root <repo根> --archive-root <launch-r1109 根>            # 人类摘要 stdout
python3 verify.py --root <repo根> --archive-root <launch-r1109 根> --output result.json
RECEIPT_COLLAPSE_ARCHIVE_ROOT=<launch-r1109 根> python3 test_verify.py        # 26 测试
RECEIPT_COLLAPSE_ARCHIVE_ROOT=<launch-r1109 根> python3 -O test_verify.py     # 26 测试
python3 test_verify.py                                                        # 未设门控 → 2 gated 测试 loudly FAIL（符合冻结要求）
```

（上表 `<repo根>`/`<launch-r1109 根>` 为脱敏占位；私有绝对路径不入包文件，见 RUN-RECEIPT.md。）

## 4. 判定结果（详见 result.json）

- **BRANCH VERDICT = B-STRUCTURAL-COINCIDENCE**（s1∧s2∧s3∧classification_complete 全真；4 个 B-COPY-ANOMALY 触发条件全部未 firing；无 V1/V2 矛盾）。
- collapse 对（2）：bird r2/r3 main（700B，`1dbdcbd884a3a45d…`）与 retrorun（470B，`49d665753085e721…`），均同元组 + 对内 incident 材料（len+SHA）相同 + explanation_complete=True。
- diverge-with-same-tuple 对（12）：dabstep/exercism/lcb/tb-cargo 各 3 对，全部 differing paths={rep, run_id}（per-rep-material），即 score 元组、raw_checker_output、note 跨 rep 全同，差异全部落在逐 rep 标识字段。
- cross-tuple-different（4）：bird r1-r2、r1-r3 两族（main+retrorun），字节互异 ✓。
- mtime 同秒组（2）：13:09:10（bird main 三收据，批量重写，晚于其余全部槽）；12:13:58（retrorun r1/r2，r3 为 ：59）；其余 12 槽严格递增；order violations=0。
- incident 材料表：三 rep 全同（main cause len=390 `9bee326882d0833f…`；main/retrorun stdout len=25 `7b512ba7d7a5a327…`；retrorun cause len=160 `c5d0523e532f3073…`）。
- workspace 聚合复算见 §5。

## 5. 异常与重大发现

### 5.1 anomaly `workspace-survey-premise-refuted`（一等登记）

预注册 §2 记载的已勘察前提「bird r2/r3 workspace 互异（r2≠r3）」被包内复算**驳斥**：

- 复算聚合（公式 sha256("\n".join("rel\x00filesha") sorted)，已登记 result.workspace_formula）：r2=r3=`d467043a992efa3c78048b58272f94b3a6172705f4a92a8d3a92bda9087af640`（TASK.md 5183B `dc63632ad541ad48…` + answers.jsonl 3098B `a53015f170ef6148…`；逐文件字节 cmp 相同；目录 mtime r2=11:59、r3=12:02 之外内容全同）。
- 简报所引声称值 r2=`5427f9da…`、r3=`1bbb0fa3…` 不可复现：17 种 content-only 公式（bytes 拼接、json、tar 等）全部得到相同值；仅把 slot 名、绝对路径或目录 mtime 编进公式的做法才产生差异——均非内容级互异。
- 处置：未放宽任何判据、未把声称值硬编码进 verify.py；前提驳斥作为 anomaly 记入 result.json（`anomalies[0]`，survey_premise_supported=false）与本记录。继续执行依据：预注册明文要求「包内复算」且简报要求独立复算「不可照抄」；§3 分支条件全部为收据级，workspace 不入分支条件。
- 诚实边界：由于 r2/r3 workspace 内容级相同，冻结探针面**无法证明** r2/r3 是两次不同执行；本包裁定的是「收据作为记录是否忠实/有无复制证据」，不是「两次执行是否独立」。冻结面外的轨迹级佐证（不入分支判定，仅此处记录）：agent.jsonl 三 rep 互异（r1=180313B、r2=82573B、r3=161682B）；checker.stdout.json r2=r3=2725B（13:09 重写版）；adjudication.json 三 rep 均 1590B@14:54。
- 旁证：非 bird 的 workspace 跨 rep 相同在本档案是常态（dabstep/exercism/tb-cargo 三 rep 全同、lcb r2=r3 同），与「收据忠实反映确定性内容」一致。

### 5.2 隐私审计标识符白名单校准（非放宽）

强化 privacy_audit 为递归全叶保护后，真档案首跑 exit 2：lcb 收据内字符串值 `abc387_f`（练习文件名，len=8）与 result 必然登记的 workspace 文件集结构路径 `solutions/abc387_f.py` 发生子串碰撞。处置：把 workspace 相对路径的全路径/后缀/分量/基名/词干加入 allowed_strings（观测面标识符白名单）；长值文本（≥16 字符前缀子串）仍全拦。该碰撞属观测面结构标识符复现，非收据值文本泄漏。收工扫描：verify.py/test_verify.py/result.json 均不含 `/Users`、`bench-private`、`http` 字样；result 不含 cause/stdout 值文本（仅 len+SHA）。

### 5.3 其他登记事实

- retrorun 的 stdout 材料与 main 的 stdout 材料相同（len=25，同 SHA）；cause 跨族不同（160 vs 390）——已入 result.cross_family_incident_material_comparison。
- 双 schema：bird 3 槽 flat 键集（含 judging_incident）；其余 12 槽 nested 键集（元组在 score.* 内，无 incident）——15 槽如实枚举，无 schema 缺失。

## 6. 冲突与 STOP

- 未触发 STOP。简报「已勘察事实」与实测的唯一冲突是 §5.1 的 workspace 前提；按预注册「包内复算」优先原则处置并一等登记，未放宽判据。
- 分支判定完全按 §3 字面实现；B-COPY-ANOMALY 第一条（同元组+incident 材料异+收据同字节）实现为矛盾 → exit 2 fail-closed（V1），检测到即终止。

## 7. 收工自检（全部通过）

- 双档一致：python3 与 python3 -O 对真档案 stdout 逐字节相同；26 个测试双档全绿。
- fresh==stored：CLI 重跑 result 与包内 result.json 逐字节相同（cmp 通过）。
- 套件门控：RECEIPT_COLLAPSE_ARCHIVE_ROOT 未设时仅 2 个真档案 gated 测试 loudly FAIL，其余 24 通过——拒绝静默跳过。
- git status：仅 `?? 4-打分细则/判分收据同字节结构-2026-11-16/`（本包新增），无其他改动；HEAD 未变。
- README SHA 未变（`47c0fef7…490ed074`）。
- 隐私扫描：§5.2 三项全零命中。
- 未动文件清单：除上述 4 个新建文件外，仓库与档案根下所有文件均未读改写（档案只读；/tmp 临时脚本 rc-explore.py、探针 JSON 已留在 /tmp，不入包）。

## 8. 局限

- 本包判定限定在冻结探针面（收据字节/键集/元组/incident 材料 SHA/mtime/存在性 + workspace 结构聚合）；不能裁定「bird r2/r3 两次执行是否独立发生」，该问题需要轨迹级或过程级证据（冻结面外）。
- retrorun 收据仅 bird 存在（3/15 槽），其比较仅覆盖 bird 族。
