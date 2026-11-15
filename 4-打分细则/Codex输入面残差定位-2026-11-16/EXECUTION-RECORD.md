# EXECUTION-RECORD — Codex输入面残差定位-2026-11-16（builder 执行记录）

- 执行时间：2026-11-16 04:20–04:41 +08:00（Asia/Shanghai）
- 执行者：residual-builder（lead 委派 builder）
- 基线：公开仓库 HEAD = `8c5a481ccccf1d0109adf570a1c437db01fc6439`（运行时经 verify.py 从 .git 文件解析，无 git 子进程）
- 预注册 README SHA256 = `4773ef6eea26af4bd057cceea03dadb608ae2a2bb0e2f879c490ee415fe05088`（开工前自验通过，收尾后复核未变）
- 环境：macOS，Python 3.9.6（`python3` 与 `python3 -O` 双档），完全离线，无新产品/模型调用，无 git 写操作

## 交付物（包目录内全部新增文件；均为本包新建，不改任何既有文件）

| 文件 | SHA256 | 字节 |
|---|---|---|
| verify.py | `fca8a9ef4dc932359b4fd6974ff455bb62d7db20808b46a650aa7ce92bb9228a` | 35,476 |
| test_verify.py | `94087ead782e473e4fb91d08d8e1cd81e103d36246c346761dd55e1ffaa3ba29` | 21,690 |
| result.json | `5942732dc47634328e9b7ccc1e749493f50078ab98d9c506cf432f503bd970d7` | 167,615 |
| EXECUTION-RECORD.md | （本文件，写入后自报） | — |

README.md 为冻结预注册原件，本包未改动（收尾复核 SHA 与开工前一致）。

## 命令序列

```bash
# 冒烟与正式生成（archive-root 为私有档案根 launch-r1109）
python3 "4-打分细则/Codex输入面残差定位-2026-11-16/verify.py" \
  --root . --archive-root <launch-r1109>            # stdout 摘要，exit 0
python3 "4-打分细则/Codex输入面残差定位-2026-11-16/verify.py" \
  --root . --archive-root <launch-r1109> \
  --output "4-打分细则/Codex输入面残差定位-2026-11-16/result.json"   # 独占创建，exit 0

# 双档测试（含 env=CODEX_RESIDUAL_ARCHIVE_ROOT 指向 launch-r1109 的真实档案端到端）
python3 test_verify.py        # Ran 22 tests, OK
python3 -O test_verify.py     # Ran 22 tests, OK

# 自查
python3 verify.py --root . --archive-root <A> > /tmp/c1.out   # 与 -O 档 cmp 逐字节一致
python3 verify.py --root . --archive-root <A> --output /tmp/fresh_result.json
cmp /tmp/fresh_result.json  result.json                        # 逐字节一致
git status --porcelain        # 仅 ?? 4-打分细则/Codex输入面残差定位-2026-11-16/
shasum -a 256 README.md       # 与冻结值一致
```

## 关键结果（供速览；权威数据以 result.json 为准）

- 硬等校验 50/50 通过（15 槽 × user/developer canonical 字节合计 vs R3 slots[]/groups[]）；15 个 rollout SHA256 全部与 R3 trace_bindings 一致。
- 全局分支：**B-CONTENT-DRIFT**（保守口径，见下）。
- 三处目标残差全部 localized（status=localized_content）：lcb-recent-hard-4 developer、dabstep-payments-10 user、exercism-py-6 user；槽对字节合计差 ±1/0。
- 全部 135 处差异均为单叶值差（kind=value），仅三条键路径：`payload.id`（metadata）、`payload.internal_chat_message_metadata_passthrough.create_time` 与 `...turn_id`（按冻结歧义规则保守归内容侧）。content/text/arguments 零触及。
- 实测 15 槽条数 developer=1、user=2：无 count_mismatch（分支仍实现并由合成测试覆盖）。

## 异常与偏差记录（构建期修正与实测发现，均如实登记）

1. **R3 槽位命名**：首版 verify.py 以 `<case>-r<N>` 构造槽位名，首跑 fail-closed exit 2（「R3 bindings/slots must cover exactly the 15 preregistered slots」）；R3 实际槽位 ID 为 `codex__<case>__r<N>`，已修正为 `slot_id()` 构造。此为构建期代码修正，非数据异常。
2. **canonical layout span 语义修正**：初版 span 取同路径首个片段（键名字节）；已修正为记录节点值域（叶子=标量字节、容器=花括号到花括号子树），并保留逐字节覆盖自检。构建期修正。
3. **三槽逐 k 比较暴露 R3 成对合计未见的字节级漂移**：R3 max/min 槽位合计只暴露三处目标残差；本包按预注册 §2 对三槽逐 k 比较，登记了全部 10 个 组×role 组合的漂移（id/create_time/turn_id 长度中性或 ±1），含 tb user r2 槽合计 4026（R3 记录的 max/min 两槽同为 4027）。这是同一冻结档案（r1109，trace SHA 一致）的事后定位登记，不是新批次。
4. **保守分类口径**：预注册 §2 元数据判据字面为「键路径仅触及 payload 顶层非内容键」；实测 payload 存在嵌套封装层 `internal_chat_message_metadata_passthrough`，其嵌套键（create_time/turn_id）不在顶层判据与钉定封装键清单内，属歧义键，按冻结规则「任何歧义键归入内容侧（宁可保守）」处理，故三处目标残差分类 content_drift、全局分支 B-CONTENT-DRIFT。承载文本键 content[].text 在全部 15 槽逐字节稳定，零差异触及。该口径已连同等据写入 result.json（notes/content_keys_pinned）。
5. **count_mismatch**：实测数据无条数不齐；冻结分支（含部分阻断降级）仍完整实现，并以合成条数不齐用例验证「登记不定位、尾部不猜测」。

## 测试与自查（全绿）

- test_verify.py：22 个测试（≥14 达标），`python3` 与 `python3 -O` 双档全绿。覆盖：真档案端到端（env 门控，未设响亮 FAIL 拒绝静默跳过）、存储 result.json 与 fresh 分析一致、冻结分类规则单测（封装键/内容键/嵌套歧义保守/顶层时间戳）、canonical layout 字节覆盖与 span 语义、count_mismatch 登记不猜测、select_branch 三分支+部分阻断、fixture CLI 端到端（硬等防篡改 exit 2、README SHA 防篡改 exit 2、trace SHA 防篡改 exit 2、--output 拒绝覆盖、双档 stdout 与 result 逐字节一致、重跑确定性、result 内容无关性）。
- 双档 CLI stdout 逐字节一致（cmp 通过）；fresh --output 与存储 result.json 逐字节一致（cmp 通过）。
- git status 仅本包目录新增；README.md SHA 未变；隐私扫描通过（包内无私有绝对路径、无 /Users/、无 bench-private、无任何 payload 值/文本片段；result.json 仅含条数/序位/偏移/长度/键路径/SHA/提交号与包内静态说明文本）。

## 未动文件清单（只读引用，零修改）

- `4-打分细则/Codex输入面残差定位-2026-11-16/README.md`（冻结原件）
- `4-打分细则/R3不稳定来源分解-2026-11-16/`（result.json 作为硬等参照与 trace_bindings 来源，只读）
- `4-打分细则/机制重复口径澄清-2026-11-12/verify.py`（canon 公式参照，只读，本包自包含未 import）
- 私有档案 `launch-r1109`（15 个 rollout 只读，SHA 全部校验）
- 仓库其余全部文件（git status 仅本包目录新增）
- 临时产物仅写 /tmp（探针脚本、stdout 对照、fresh result 副本），已不进入任何交付物
