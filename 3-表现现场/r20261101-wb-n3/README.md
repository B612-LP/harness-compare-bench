# WorkBuddy W 组 n=3 重复性批 · 2026-11-01

WorkBuddy 桌面端五题 × 3 重复（15 槽，零技术失败、零配额事件、零重发零补跑零择优），同一冻结合同（freeze-20261031-wb-v2）判分。本目录只承载本批实际运行与判卷证据；**零正式表准入**，不入任何代际 official 表。本目录为 2026-11-02 补齐的公开派生层（此前公开侧仅有[CHANGELOG 登记行](<../../CHANGELOG.md>)，逐场收据存仓外私档的不对称已在报告 v1.3 首发时如实披露，本目录发布即收口）。

## 五段结论

**观察**：五题各 3 场，V/F 逐题全体一致——bird 3V、dabstep 3F、exercism 3V、lcb-recent-hard 3V、tb-cargo-plan 3F，headline 3/5 与 WorkBuddy 正式账逐题完全重合，无一场翻转；加权分存在真实样本方差：bird 93.33→100→100、dabstep 60→60→70、tb 70.37→70.37→74.07、exercism 与 lcb 恒 100。

**证据**：[批次收据](<batch-summary.json>)15 行逐槽十字段留痕（唯一 ID、题目版本、产品版本 5.9.3 批前批后零漂移、模型 UI 选择、工具计数、权限、技能状态、运行时间、证据等级、最终裁定 V/F）；逐槽完整记录见 [runs/](<runs/>)（run-record-v2 净化转录）；分账见 [batch-events.json](<batch-events.json>)（15 product_run + 1 interface_preflight）与 [six-accounts.json](<six-accounts.json>)；分布表见 [headline-distribution.json](<headline-distribution.json>)。判分 = 冻结合同 checker 原字节、OS 隔离沙箱（禁网络、禁题库/冻结工作区写入），逐槽 execution 收据 SHA256 在 batch-summary 行内。

**解释**：报告[结论六](<../../5-评测报告/竞品评测报告-v1.3.md>)「正式行 n=1/格」的未排除因素中，结果面部分收口——W 五格的达标结论在三次独立真实产品发射下均不因采样噪声改变；headline 层面的 W 成绩是稳定的。结果面一致 ≠ 分数恒等：单值 weighted 的批间小差异可能只是采样方差，不足以单独支撑「产品进步/退步」类结论，跨批比较应看 V/F 格局与分布而非单点分。

**未排除因素**：n=3 仍属小样本；15 场全部同一产品版本 5.9.3、同一天（跨版本漂移未测）；网关后端身份未知（仅 UI 选择 DeepSeek V4.1-Flash，不做同模型归因）；会话间系统上下文差异不可控。逐断言级失败集 diff 的覆盖疑虑已结清（非存留风险）：tb 三场 19/27×2、20/27×1 的波动已由同日[断言级全量 diff](<../../5-评测报告/断言级重复性-diff-2026-11-02/README.md>)覆盖（W 轨 15 槽全部可分析、零 unanalyzable；tb 波动由 3 个翻转断言承载，其余为确定性稳定失败核）。

**可复现实验**：每槽 prompt SHA-256 在案；复现路径 = 同冻结合同下重建工作区（inputs + TASK.md）→ 产品执行 → 冻结 → 沙箱 checker。批内判分可由私档 execution 收据 SHA256 对账；checker JSON 明细（含完整 result.checks）在私档，验收方按槽抽查。

## 运行分账

15 行全部判分完成、零筛除：`final_adjudication` 取 V/F（reward 达标线口径，9V/6F），无 launch_invalid、无配额事件、无中断行。rep-major 交错序发射（13:17–14:40），完成判定全部为 database_terminal_and_stable_5s；批前 interface preflight 一次微型往返（单列，不入产品运行账）。

## 口径与披露

- **工具与权限**：15 场工具调用全部本地类（Read/Bash/Write 等），逐场自动扫描 + 人工审阅：0 处工作区外路径标记、0 网络工具调用；权限模式 fullAccess 为产品原生会话元数据，如实披露、不当作隔离保证；无评测者技能注入（未观察到技能调用不等于全局禁用）。
- **审批标签披露**：逐场 review 记录的 `final_review` 标签因审批函数未回写而停留 `pending`，审批事实由三布尔位（工具审阅/代码审阅/checker 可执行）+ `approved_at` 时间戳承载；收据字节不改，此处如实披露（与双独立验收结论一致）。
- **公开记录为派生材料**：私有路径以 `<local-path>` 占位；原始轨迹/凭据私留；哈希证明收据间一致性，不证明真实时间或内容真实性。
- **V/F 口径**：V/F 为 reward 达标线判定（判分维度），与运行有效性（准入维度）相互独立；本批 15 槽均为有效准入运行，零正式表准入是批次定位声明而非质量判断。
- 重复性观察的横向解读见[竞品评测报告 v1.3 §6.4](<../../5-评测报告/竞品评测报告-v1.3.md>)；同日 B 组两轨见[豆包批](<../r20261101-doubao-n3/README.md>)与[元宝批](<../r20261101-yuanbao-n3/README.md>)。
