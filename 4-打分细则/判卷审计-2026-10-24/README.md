# 2026-10-24 判卷审计与修复

本次只修复当前已知反例，不新增题目、不新增产品运行。修前代码／truth 已分别冻结保存；新分派生到独立复算目录，历史现场原分不回写。

## 修复清单与红绿证据

| 用例 | 旧缺口 | 当前修复 | 验收位置 |
|---|---|---|---|
| BIRD 1.0 → 1.1 | 15 条正确答案后追加非法 JSON 行，schema 红但 headline 仍通过 | schema 独立硬门；不依赖同时漏题才能拒绝 | [数值／格式审计](numeric/README.md)、[40/40 收据](numeric/results.json) |
| DABstep 0.1 → 0.2 | 官方兼容 scorer 忽略费用差额符号、ACI 字母 | 官方兼容分保持；新增 `signed-aci-v1` 严格契约轨，符号与 ACI 全串核对；明确容差而不追加 14 位字面精度要求 | [双轨协议](numeric/README.md)、[独立回归脚本](numeric/run_audit.py) |
| Exercism 1.0 → 1.1 | 实现导入时 `os._exit(0)`，测试未跑却得满分 | checker-owned runner 完成回执、预期测试数及逐项 start/stop/success 身份核对；判卷只操作临时副本 | [执行审计](execution/README.md)、[修后 20/20](execution/after.json) |
| Cargo 0.1 → 0.2 | truth 阈值、case 字段、canonical 数据漂移未拒绝 | 原字段 `case`／阈值／关键项／gold 摘要／pinned 输入 SHA256 交叉校验，异常退出 2 | [执行回归脚本](execution/reproduce.py)、[完整性检查](execution/final-validation.json) |

BIRD 既有＋新增 selftest 21 项、DABstep 23 组、Exercism 16 项及 Cargo 自测均已通过；细分计数属于判卷测试，不计独立产品运行。数值／格式审计 40/40、执行审计 20/20 是各自固定测试矩阵，不能相加冒充模型运行次数。

## Lead 独立验收与真实现场影响

除实现者自测外，Lead 用另一份[独立验收程序](../../5-评测报告/复算/2026-10-24/verify.py)检查精确反例、oracle、七个题目 checker 自测、历史不可变性与复算一致性；机器收据在[validation.json](../../5-评测报告/复算/2026-10-24/validation.json)，终端摘要在[validation.log](../../5-评测报告/复算/2026-10-24/validation.log)。

[版本化复算](../../5-评测报告/复算/2026-10-24/README.md)仅对已归档产物做临时副本判卷，31 次复算不计新模型运行。DSH × DABstep 首跑 weighted 70→60、第三次 60→50，均为 q1871 符号漏判；两场 headline 原本即为 0，仍为 0。官方兼容分与原现场保持一致，不静默覆盖。

## 停止边界

- 本轮结清的是上述精确漏洞，不是证明判卷器一般正确。未见攻击面、同进程／同 UID 恶意 Python、伪造回执、宿主绝对路径访问及资源攻击等仍属风险；临时目录和 `-I -S` 不是 OS 安全沙箱。
- DABstep 严格轨仅修复已知符号／ACI 契约，不宣称官方 scorer 本身完全正确，也不静默收紧其他题目的容差。
- 旧 `corpus-squeeze` 相对路径缺陷属于已退役题风险，未在本轮修复；保留台账，不扩大跑测。
- 历史补录代码的采集日期、SHA256、原路径证据与时间一致性局限在[补录清单](../../5-评测报告/复算/2026-10-24/source-supplement/manifest.json)明示；不把今日补取包装成当场冻结。

结清状态、未解决项与停止追查条件见[未知登记](../../5-评测报告/未知登记.json)。本轮最终结论以[阶段报告 v2.0](../../5-评测报告/阶段报告-v2.0.md)为准。
