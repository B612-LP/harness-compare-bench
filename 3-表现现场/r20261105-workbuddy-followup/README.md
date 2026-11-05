# WorkBuddy：旧超时任务的后观察

**同一请求后来completed；独立判卷仍未通过：19/27（70.37），关键4/5，reward=0。** 本阶段新增模型提交0，累计仍1；原1200秒timeout/未判卷记录原样保留，不进正式25格。

| 层次 | 本次证据 |
|---|---|
| 原窗口 | [旧分账](<../r20261104-desktop-observation/slots.json>)仍timeout、capture=false、分数null |
| 后观察终态 | 原生OP/既存request映射及原提示精确一致，request/assistant双completed；原生完成时间2026-11-05 01:15:00.064 +08 |
| 产物归属 | 同CID仅1请求/1用户turn，观测时无active child/background；原目录identity及两次受限读hash稳定 |
| 来源 | 78行选定trace，旧9行raw是精确前缀；顶层function调用28、结果28唯一闭合，不是tool_use块 |
| 判卷 | 9件捕获经安全审阅后，对复制件用原checker一次；三前置门通过，27核心断言过19 |

- [计数与时点](<accounting.json>)、[评分字段](<grading.json>)、[原checker输出](<checker.json>)。
- [事件投影](<trajectory.projection.jsonl>)只留类型/角色/工具名，不含参数、结果正文、profile、思考或原生ID；不是完整raw轨迹。[来源分账](<source-accounting.json>)只给hash，不能认证未公开原件。
- [捕获产物](<artifact-run/>)含三Python、四原数据与计划，按捕获字节发布；[原输入pins](<case-source-pins.json>)指向既有用例；[原任务/公开提示](<../r20261104-desktop-observation/prompts/workbuddy.md>)保持上次派生。
- 首个Bash调用/结果的产品时间戳相差3920.03秒；不能当命令CPU运行时长，也不能推出权限等待、模型或网络卡顿原因。后段是否有人介入/授权没有连续审计。本阶段未批准权限、取消或重发。

从仓库根运行 `python3 3-表现现场/r20261105-workbuddy-followup/verify.py` 仅核公开派生字节/分账，不执行候选或访问产品。安全审阅后可自行用既有checker复跑：`python3 2-用例/tb-cargo-plan/checker.py 3-表现现场/r20261105-workbuddy-followup/artifact-run --json`；临时目录不是OS隔离。

[方案](<../../1-评测方案/WB同任务后观察-2026-11-05/README.md>) · [评分补充](<../../4-打分细则/WB后观察补充-2026-11-05.md>) · [五段报告](<../../5-评测报告/WB同任务后观察补充-2026-11-05.md>)。
