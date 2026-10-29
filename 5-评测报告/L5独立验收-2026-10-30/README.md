# L5 独立验收（task-14，judge）— 2026-10-30

- 批次：E3 封印（preregistration==execution_seal=`d8366da32694713d4f77c740f935229f9e298df4`，binding registered_at=2026-10-30T02:16:07+08:00，released），6 计划槽。
- 方法：全程零模型/零网络；canonical 判定只用 `1-评测方案/工具链/l5-execution/gate.py`（sha256 `38b42a87c30c87d277f0a8984c4300919da3867826790a01fd24af6766b05ce9`）自行复跑；不采信 builder 的 runner_formal_eligible 与自报分数。本 judge 无 git 权限（本任务明令禁 git 操作），E3 blob 一致性以 binding 钉扎 sha 链替代证明（见「未排除因素」）。
- 机器收据：`verify-receipt-l5.json`（sha256 `a05dafca6b7f5bb36f55ab770f1db4e51aea630ce9e4a38ca12f7561dff97d05`，evidence-kit receipt_check 全绿：drift 键在位/0 违规/0 坏证据行）。

## 一、观察

canonical gate v2 准入：**6 槽中 5 槽 formal=True，1 槽 formal=False**（WB bird）。六槽独立复算分数（8dp）：codex-dab 70.00000000、codex-cargo 74.07407407、dsh-dab 70.00000000、dsh-cargo 70.37037037、wb-dab 60.00000000、wb-bird raw 100.00000000（gate 判 partial 不折满，formal=False）。builder 自报六分数与我的独立复算**全部一致**。

## 二、证据

1. **canonical 准入**（`canonical-gate-admission.json`，gate_admission ×3 产品自行执行）：codex 两槽 fails=[]；dsh 两槽 fails=[]；wb-dab fails=[]；wb-bird fails=2：①`meta.judge.guards_used 缺失（无法按 guard 重算 earned/possible）` ②`status=ok 但证据/判卷不完备：partial 记账（unknown 不折满）`。
2. **U1 封印溯源**（`u1-sealed-content-check.json`）：磁盘 plan/contract/manifest sha256 与 binding 钉扎值逐一相等；manifest 23 repo + 17 external 共 40 件全量实算零失配；preregistration_commit==execution_seal_commit；六槽 meta.registered_at 均等于 binding registered_at，且 started_at（02:16:59–02:24:39）严格晚于封印时刻。
3. **发射验收点**（`per-slot-emission-checks.json`）：六槽 inputs_verification.ok=true；meta.judge{checker_sha256==contract、guards_used、correct、n_tasks} 齐全（唯 bird guards_used/n_tasks 缺省，见三）；score.checker_sha256==contract、reported/meta.weighted 均 8dp；canonical 重算（raw checks−guards→earned/分母）与 reported 全等。
4. **R3（DSH×2）**：session_capture.match_method=exact×2、capture 非空×2、usage 非整线 null×2。**R6（WB）**：renderer_ready 在 meta×2（均 ready/0.0s/1poll）。**R7（WB）**：slot-accounting-frame（generated_at=2026-10-30T02:23:11+08:00）两槽 execution_state=executed + 真实 score（bird 100.0/dab 60.0）→ frame actual 非 null×2；write-once 副本 6 件在位；**cmd_accounting 覆盖事件**（runner :2075 write_json_atomic，本批重跑把 receipts/slot-accounting-frame.json 的 E2 版覆盖为 E3 版）系 runner REPORT.md L133-138 主动披露，E2 版恢复指引=`git show b32d844:"3-表现现场/l5-20261030-wb-gateway/receipts/slot-accounting-frame.json"`。
5. **R4**：`gate-v2-history-recompute-receipt.json`（gate sha==当前磁盘 gate，同一判卷器）all_pass=true、baseline 17 槽 0 跳过、唯一 diff=bird registrations 白名单 fail 在 v2 消失——与我在 L4 的「gate 过严误报」sidecar 裁定（L5-8）完全一致。**R5**：`cache-mapping-v2/recompute-receipt.json` all_pass=true、unit selftest 6/6、18 probe 槽、erratum_ref 在位。
6. **中止档案**：0152seal 收据 kind=lead_abort_seal_repair（E=7474b84 WB adapter 仍 pin l4 gate → 统一重封）；E2 档案 kind=lead_abort_e2_seal_repair（DSH ev.mkdir FileExistsError → E2 已完成 4 槽失格重封）+2 份 supplement（dsh cargo not_executed 记账、codex ws/voided-claim 件）；两档案与 E3 六计划槽**零直接混淆**（E3 canonical runs 为独立新目录）；真实消耗按制度单列披露、无 formal 资格。

## 三、解释

bird formal=False 是 gate 语义的**如实执行**而非数据缺陷：bird checker 文档缺 guards_used/n_tasks 缺省字段 → gate 无法按 guard 重算 earned/possible → 按合同「unknown 不折满」计 partial。按 judge 纪律不补值、不放水：raw 100.00000000 保留为 observed，formal 资格不给。wb-probe 的 cmd_accounting 覆盖事件只影响 E2 档案 frame 的新鲜度（E2 版可经 b32d844 恢复），不影响 E3 六槽判定与本次验收；修复=该行改 write_json_once（一行，随下次重封 pin，建议入 L5 池）。

## 四、未排除因素

1. **E3 blob 一致性未经 git 独立复算**：本任务明令禁 git 操作，我以「磁盘文件 sha256==binding 钉扎值」替代证明封印内容一致性；binding 本身为 gate 信任锚，若 binding 被置换则该证明链失效（gate 自身以 binding 为准入输入，风险闭环于 gate 语义）。
2. **b32d844 恢复指引未独立执行**（需 git show），仅核其与 REPORT.md 披露一致。
3. bird 分数 100.00000000 的分母语义（raw 19 checks vs 合同分母 15）在 guards_used 缺失下无法归一，keep as observed。
4. gate v2 对「insufficient_fields 缺省」的处置（缺 guards_used 即 partial）是当前冻结语义；若后续合同修订补齐 bird judge 字段，须重封后复判，本收据不自动延展。

## 五、可复现实验

```bash
cd /Users/b612-lp/Documents/harness-compare-bench
# ① canonical 准入（三产品）
python3 -c "import importlib.util;from pathlib import Path;s=importlib.util.spec_from_file_location('g','1-评测方案/工具链/l5-execution/gate.py');g=importlib.util.module_from_spec(s);s.loader.exec_module(g);print(g.gate_admission(Path('1-评测方案/自动循环L5-2026-10-30/runtime-binding.json'),'codex',repo=Path('.'),plan_dir=Path('1-评测方案/自动循环L5-2026-10-30')))"
# ② 收据自检（应全绿）
python3 1-评测方案/工具链/evidence-kit/receipt_check.py 5-评测报告/L5独立验收-2026-10-30/verify-receipt-l5.json
```

配套中间产物：`canonical-gate-admission.json`、`u1-sealed-content-check.json`、`per-slot-emission-checks.json`（均在本目录，sha256 见收据 artifact_sha256 键）。
