# EXECUTION-RECORD — WB漂移token形状-2026-11-16

- 日期：2026-11-16（Asia/Shanghai）
- 角色：builder（预注册包构建与裁定执行，完全离线，无网络、无新产品/模型调用）
- 冻结依据：本包 README.md（SHA256 见下，v1 冻结），逐条按 §2 值无关判据实现；无判据冲突。

## 0. 开工门与仓库状态

- baseline_commit（执行时）：`8202648e9b00bca19cd21ebfea7871b64736760d`（=公告 8202648，满足「或后代」），branch=main。
- 开工时 `git status --porcelain`：仅 `?? 4-打分细则/WB漂移token形状-2026-11-16/`（本包目录，含冻结 README.md）。
- 收工复核：HEAD 与 branch 不变；`git status --porcelain` 仍仅本包目录新增；本包内既有文件（README.md）SHA 未变。全程未改动任何既有文件、未做 git 写操作。

## 1. 判据实现要点（值无关，冻结 §2）

- 数据源与环 6/11 同一 W1 提取：`runs/<slot>/trace/*.jsonl`（每槽恰 1）、`type=message` 且 `role=user`（恰 1）、`content` 恰 1 block 且 `type=input_text`、取 text 的 UTF-8 字节序列；只做位置/边界/字节类运算。
- 漂移 offsets 硬等：复算=逐 case 三对 rep 文本逐字节差异并集；硬等=环 11 公开包 result.json `case_analysis.<case>.events[*].positions_offset` 全集（含 envelope_span 复算与登记一致性门）；不等或 span 不符即 fail-closed exit2。实测：dabstep-payments-10 7 位、tb-cargo-plan 7 位，两 case 均等；envelope span 复算与环 11 登记一致。
- 逐 offset×rep 登记：包含该漂移字节的极大数字 run 的 [起,止)、长、漂移字节在 run 内 index、run 左邻字节类（digit/alpha/other；bof=文本首）；漂移字节非 digit 时 `run_found=false` 只登记该字节类。分隔字节只登记类不登记值；不读任何字节值；跨 rep 只比较 run 边界（起/止/长），不比较字节值。
- S1（信封外簇恰两组长 2 run、隔恰 1 非数字字节、两 case 同构）：簇=信封外漂移位中 rel_position（offset−信封闭合）跨 case 对齐（交集）者，沿用环 11 cross-case 对齐规则、无阈值；信封外其余=isolated_external；信封内=internal。逐 rep 断言 n_runs==2、各长 2、run 字节与簇 offsets 恰合、gap==1 且类≠digit、shape_signature=DD?DD、跨 case 结构元组相等。
- S2：全部漂移 run 边界（起/止/长）三 rep 相等（逐 offset 断言）。
- S3：信封内孤立位 run 长=1 且左邻=alpha（逐 rep；按复算信封内集合断言）。

## 2. 执行命令（占位：`<repo>`=公开仓库根；`<archive-root>`=WorkBuddy 复测档根，完整本机路径不在本文登记）

```bash
# 逐档裁定（--root、--archive-root 必填）
python3 verify.py --root <repo> --archive-root <archive-root>
python3 verify.py --root <repo> --archive-root <archive-root> --output result.json

# 双档一致性：第二档=同一档案的独立副本（/tmp，临时物不入包）
python3 verify.py --root <repo> --archive-root <archive-root-A> > /tmp/stdout_A.txt
python3 verify.py --root <repo> --archive-root <archive-root-B> > /tmp/stdout_B.txt
cmp /tmp/stdout_A.txt /tmp/stdout_B.txt          # 逐字节一致

# fresh == stored（CLI 重跑 vs 包内正式 result.json，逐字节 cmp 相等）
python3 verify.py --root <repo> --archive-root <archive-root> --output /tmp/fresh.json
cmp result.json /tmp/fresh.json

# 测试套件（默认档 + -O 档；真档案用例经环境变量门控，多根用 os.pathsep 分隔）
WB_TOKEN_SHAPE_ARCHIVE_ROOT="<archive-root-A><os.pathsep><archive-root-B>" \
  python3 -m unittest test_verify -v          # Ran 21 tests — OK
WB_TOKEN_SHAPE_ARCHIVE_ROOT="<archive-root-A><os.pathsep><archive-root-B>" \
  python3 -O -m unittest test_verify          # Ran 21 tests — OK
```

- 全程 stdout/result 未打印任何字节值（仅 offset/rel、边界、长度、字节类、计数、SHA256、布尔位）。

## 3. 裁定结果（n=3 rep × 2 case）

- offsets 硬等：全部相等（两 case 各 7 位；环 11 并集复算一致）；envelope span 复算与环 11 登记一致。
- S1=true：两 case 信封外簇均为恰两组长 2 数字 run、隔恰 1 非数字字节（gap 字节类=other）、run 字节与簇 offsets 恰合、shape_signature=DD?DD、跨 case 同构；三 rep 一致。
- S2=true：全部 14 offset 的 run 边界（起/止/长）三 rep 相等（42 项登记，run_found=false 计 0）。
- S3=true：信封内孤立位（每 case 2 处）run 长=1 且左邻=alpha（逐 rep 成立）。
- 分支判定：**B-DIGIT-RUN-FIXED-SHAPE**（S1∧S2∧S3 全过；exit_code=0）。
- 勘察注记偏差（如实登记，以复算为准）：冻结勘察注记称信封内 3 孤立位；复算信封 span 下每 case 信封外尚有 1 孤立位（rel +330 / +318，与环 11 登记的 rel_position 一致），信封内实为每 case 2 处。孤立位形状（run 长 1、左邻 alpha）在全部 3+3 处成立，形状结论不受 lane 标注差异影响；已在 result.json `survey_note_reconciliation` 三条目登记。口径敏感性（若采「信封外簇=全部信封外漂移位」替代口径则 S1 破翻 B-SHAPE-VARIABLE）已按冻结行如实披露于 `analysis_rules.cluster_caliper_disclosure`。

## 4. 交付物 SHA256 与字节（收工时点）

| 文件 | 字节 | SHA256 |
|---|---|---|
| verify.py | 37438 | `6f7622f6db5e0112226368927f54f3072399a04e48ab9db51323936c7fcb7ede` |
| test_verify.py | 28045 | `dc46a28d9d3a274d4436f2f552069b015850ee42bf20880ff97253973276aa9b` |
| result.json | 38511 | `70850b1a0cb9fff3cfe7989a0bab26b879132b8fea4beb62290cd97868431c9f` |
| EXECUTION-RECORD.md | （本文） | 见收据 |
| README.md（既有，未动） | 3275 | `c7fee55520d54ee24ba99a9c0a7c6f35018864511085b0ec02e30f377a9a8ee8`（=冻结值 ✓） |

- result.json：由 verify.py `--output` 独占创建生成（schema=wb-token-shape-v1，含 prereg sha256、baseline_commit、值无关声明、逐 offset×rep run 登记 42 项、S1/S2/S3 断言、分支、硬等与 span 一致性记录、勘察注记对账）；CLI 重跑 fresh 与 stored 逐字节一致；双档 stdout 逐字节一致。
- test_verify.py：21 用例（≥12），双档（默认/-O）全绿；真档案端到端经 `WB_TOKEN_SHAPE_ARCHIVE_ROOT` 门控（未设置时响亮 FAIL，不静默跳过）；合成用例覆盖 DD?DD 判定、run 边界跨 rep 一致性、alpha 邻接孤立位、S1 三组破形、S2 破形、S3 左邻破形、offsets 硬等防篡改（漂移→exit2 且不写 --output）、--output 拒绝覆盖、README SHA 防篡改、值无关（result+stdout 无文本内容/无本机路径、登记键值域受限）。

## 5. 异常与修复记录（开发期，全部发生在交付定稿前）

1. verify.py 初版将内部 `_text`（bytes）随 `extraction.per_slot` 带入 result，--output 序列化 TypeError exit2；修复为排除该私有键（该键本就不应出结果）。
2. verify.py 初版 isomorphic 判定误写「结构元组集合大小==case 数」，应为「==1」；冒烟发现并修复。
3. test_verify.py 初版 overrides 以 tail 相对 offset 语义误改信封内字节（负索引 ValueError）与 CLOSE 标记内字节；改为整段文本 offset 语义并支持逐 rep 三元组。
4. 测试预期两处与实现语义不符（S1 per_rep 不携带 run 边界改经 S2 核对；合成档填充字节为 alpha，run 起点左邻类预期修正）；均为测试侧修正，verify.py 判据行为不变。
5. 执行期无 fail-closed 触发（硬等、span、布局、消息结构全部通过）；无数据不足情形。

## 6. 值无关自查（收工）

- result.json 与 stdout：无任何漂移字节值/分隔字节值（仅字节类 digit/alpha/other/bof）；无信封标记或消息文本字面；无本机绝对路径（硬等参照仅相对路径）；登记键值域经测试断言受限。
- EXECUTION-RECORD.md：无私档路径字样（`<archive-root>` 占位）、无字节值。
- 临时物仅 /tmp（双档副本、stdout/fresh 对照件），未入包。

## 7. 未动文件清单

- 既有文件零改动：本包 README.md（SHA 未变）；仓库内其余全部既有文件未触碰（git status 仅本包 4 个新增文件：verify.py、test_verify.py、result.json、EXECUTION-RECORD.md）。
- 未做任何 git 操作（无 add/commit/branch）；未启动任何网络、新产品或模型调用。
