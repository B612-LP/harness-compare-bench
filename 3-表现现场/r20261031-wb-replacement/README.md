# WorkBuddy 判废项唯一替代证据（W-v2）

仅承接首批已经判废的三个槽位，各一次；首批有效的BIRD/Exercism不重跑。父原分/判废证据不改写，机械first登记不表示无前承。

| 用例 | 实测原分 | reward | 最终裁定 |
|---|---:|---:|---|
| [dabstep-payments-10](<runs/dabstep-payments-10/run-record.md>) | 6/10（60.0） | 0 | valid |
| [lcb-recent-hard-4](<runs/lcb-recent-hard-4/run-record.md>) | 4/4（100.0） | 1 | valid |
| [tb-cargo-plan](<runs/tb-cargo-plan/run-record.md>) | 20/27（74.07） | 0 | valid |

三场全量事件见[事件包](<formal-wb-replacement-events.json>)，逐场分数与闸门见[批次汇总](<batch-summary.json>)。

TASK.md为真实发送原字节，与预注册公开prompt及prompt-proof绑定；并非脱敏派生提示。轨迹仍是明确删节的公开派生，不是完整原始轨迹；原件私留，每行原/派生SHA、映射、规则和限制均保留。

相较首批，提示头路径中立化且明确系统临时目录在工作区外，这是跨批协议差异，不能宣称单变量因果提升。UI模型标签、low及产品日志端点不证明后端模型身份；不与A/B混排。DAB2697不支持能力归因。

代码型产物在逐条工具与实际代码审查后，以原冻结checker在OS隔离中判卷；原始分数与最终准入独立，不因满分放行，也不将unknown补0或满分。

公开产物重建与隔离复算的准确命令模板见[分数复核说明](<RECOMPUTE.md>)；分数可复算不等于原始轨迹完整公开。
