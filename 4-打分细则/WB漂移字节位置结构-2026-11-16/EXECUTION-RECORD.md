# EXECUTION-RECORD — WB漂移字节位置结构-2026-11-16（builder 执行记录）

- schema：wb-drift-loc-v1（预注册 v1，冻结 README SHA256 `c95d8e6d850ca3f517cc7295f51dc0fdde895506bdc58ecb2ae3817d579ba1b1`）
- 执行时间：2026-11-16（Asia/Shanghai）；完全离线，无网络、无新产品/模型调用。
- 公开仓库 HEAD（构建时）：`d7e9cb766f6289fbc5803175750e4395a8b49ecb`（= 预注册基线 d7e9cb7）。

## 命令（`<archive-root>` = bw-retest/workbuddy 档根占位；路径不入包）

```bash
# 生成包内正式结果（--output 独占创建）
python3 verify.py --root <公开仓库根> --archive-root <archive-root> --output result.json

# 测试套件（21 用例；真档案端到端由 WB_DRIFT_ARCHIVE_ROOT 门控，未设响亮 FAIL）
WB_DRIFT_ARCHIVE_ROOT="<archive-root>" python3 -m unittest discover -s . -p "test_verify.py" -v

# 双档一致性（同一档案的独立副本作为第二档）
WB_DRIFT_ARCHIVE_ROOT="<archive-root>:<副本根>" python3 -m unittest discover -s . -p "test_verify.py"
python3 verify.py --root <公开仓库根> --archive-root <archive-root>   # stdout 摘要
```

## 交付物（本包 4 个新文件，均为本次新建）

| 文件 | 字节数 | SHA256 |
|---|---|---|
| verify.py | 见收据 | 见收据 |
| test_verify.py | 见收据 | 见收据 |
| result.json | 28,102 | `8ba0e34a50ed3f65e96055d3973114bfbdc91624ec5c1e72ce3042da14bc1f5a` |
| EXECUTION-RECORD.md | — | — |

（verify.py / test_verify.py / EXECUTION-RECORD.md 的最终 SHA 与字节数以 RUN-RECEIPT.md 收据为准；result.json 先生成、其 SHA 上表已定。）

## 结果摘要（复算，以 result.json 为准）

- **W1 硬等**：与 `4-打分细则/WB重复槽输入与交互量结构-2026-11-16/result.json` 的 w1.groups 逐 case 逐字段（classification / envelope_span_cross_rep_equal / spans_by_rep / 3 pairs 各 7 字段）完全一致，all_equal=true；该参照文件 SHA256=`97fbe9220ec2173b00b70bd3cdf28fadb20844b85aa144e04a773b3d3117e68e`。
- **逐差异登记**：40 处逐对实例（信封外 28 + 信封内 12；dab 6/7/7、tb 7/7/6），逐处 {case, pair, offset, rel_position, lane}。
- **簇/孤立分类**：两 case 信封外漂移位同为 rel {+93, +94, +96, +97}（含含端点宽 5B ≤ 8B，跨 case 区间重叠 [93,97]），即窄簇；各 case 另有 1 个 case 固定孤立位（dab rel +330、tb rel +318），3/3 pairs 固定且三 rep 两两互异。信封内差异：dab rel {−6149, −772}、tb rel {−6111, −746}，均三 rep 两两互异。
- **context_sha**：8 个漂移事件（每 case 4 个：簇 / 孤立位 / 2 信封内）全部 isolated_substitution（三 rep 剔除本事件漂移字节后 ±16B 窗聚合 SHA 一致），block_shift_candidate=0。
- **两两互异**：逐位置 12/14 三 rep 互异；例外 2 处（dab rel +93 一对 rep 同字节、tb rel +93 一对 rep 同字节），按冻结 §2「任一对相同 ⇒ 记非逐运行唯一」登记；簇级（每对 rep 在簇内存在差异字节）两 case 均 3/3 通过。例外位不改变簇级/孤立位判定（见 branch.caveat）。
- **分支判定**：B-FIXED-POSITION-TOKEN（≥2 case 满足 C1 位置级 4/5=80.0% ≥ 80%、C2 簇级两两互异、C3 全部孤立替换、C4 孤立位固定互异孤立替换；窄簇跨 case 相对区间一致且宽 ≤8B）。

## 判读口径与敏感性（透明披露，详见 result.json analysis_rules / survey_note_reconciliation）

1. 「33 处」与同句逐对计数（6+7+7+7+7+6=40）不自洽：按 README 冻结行「勘察注记可被包内复算推翻」，以复算 40 处登记；tb 信封内 2/2/3 复算为 2/2/2。
2. ≥80% 取「位置级」口径（信封外漂移位置 4/5=80.0%，两 case 均恰好达标）；逐对实例口径 11/14=78.57% 与簇道实例 11/11=100% 同步披露于 `branch.conditions_by_case.*.C1_instance_fraction_disclosed`。
3. 「三 rep 两两互异」分支层按簇级断言；逐位置例外（+93 两 case 各 1 处）按 §2 记录规则登记。若采最严格替代口径（实例级 ≥80% 且逐位置互异），branch 将翻为 B-SCATTERED——该敏感性如实披露，最终口径裁定权在预注册文本（位置结构裁定的自然单位为位置）。

## 语义实现决定（预注册未明示处的确定性补全，均登记于 result.json analysis_rules）

- **漂移事件并组**：相邻漂移位间距 ≤8B 视为同一漂移事件（与冻结 ≤8B 窄簇刻度一致）；context_sha 按事件级 ±16B 窗、剔除本事件漂移字节后聚合。理由：等长文本下若窗内剔除「全部差异字节」则三 rep context 必然全等，块移位候选不可达（数学事实）；事件级并组使 gap 9–16B 的跨事件共窗污染可被检出为 block_shift_candidate（合成用例已验证可达）。真实数据簇内 gap ≤2B、事件间最近间距 233B，8B/16B 阈值对结果无差别。
- **非 git 根**：baseline_commit 对非 git 根（合成测试根）记 `non-git-root`（确定性），真实仓库根记录实际 HEAD。

## 异常与偏差

- 无 STOP 级冲突：冻结 README SHA 开工验证一致；预注册逐条可实现。
- 实现过程中修正的自查项（均在本包/测试内，未触任何既有文件）：信封长度换算（开标记 42B）、合成参照与篡改档案的耦合（测试构建顺序）、`analysis_rules` 字面信封标记文本改写为不重复登记（内容无关纪律）。
- 无未恢复错误；测试 21/21 双档全绿；双档 stdout 与 result.json 逐字节一致；fresh==stored 通过。

## 未动文件清单（只读承诺）

- 公开仓库：除本包目录下 4 个新文件（verify.py / test_verify.py / result.json / EXECUTION-RECORD.md）外，未新建、未修改、未删除任何文件；未做任何 git 写操作（无 add/commit/branch/checkout）。硬等参照 `WB重复槽输入与交互量结构-2026-11-16/result.json` 只读。
- 私档：只读；唯一写物为 builder 运行收据（存私账本内，路径按内部入口登记，不在此公开）。
- 双档一致性用的档案副本与全部临时输出在 /tmp（`/tmp/wb_drift_archive_copy`、`/tmp/stdout_*.txt`、`/tmp/fresh_copy.json` 等），不入包不入库。
