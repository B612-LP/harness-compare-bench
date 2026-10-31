# 正式批次 r1101-formal-b1（2026-10-30，B 组首次正式准入）

> 治理合同：`freeze-20261029-v4`（[注册计划](<registration-plan.json>) 先于任何运行封印，plan SHA-256 `87af87b54472202c23342eaa1e2aa5bc1e7d81a6048d159e93f0cffd076ac836` 绑定 config.official_slots）。内部执行计划：L11 环（私有，含老师反馈对照段）。

## 设计

- **组**: B_native（元宝专家模式 yuanbao-expert-web + 豆包办公 doubao），各 5 题 × n=1/格，共 10 slot，每 slot 仅 1 次 kind=first 发射（配额制，发射失败即停不重试）。
- **B_native 语义**: 产品开箱交付路径、模型封闭不可同模型归因；正式行不与 A_same_model 排名（policy.mixed_group_ranking=false）。
- **检索口径**: 元宝三件套（任务书禁检索条款 + 逐会话 `speechesV2[].internetSearch` 实值披露 + 批后 integrity_scan 与人工终审）；豆包三件套（任务书禁网条款 + 轨迹披露 + integrity_scan 兜底）——均按[检索口径-2026-10-27-落表](<../../4-打分细则/检索口径-2026-10-27-落表.md>)。实证 clean 记 V、实证命中记 X。
- **留痕**: 运行记录模板 schema v2 十字段强制（2026-10-30；桌面封闭字段=披露值+承载位置）。工作区 `~/bench-workspaces/r1101/<product>/<case>/`（仓库外，仅 inputs+TASK.md）。
- **判分**: 冻结 checker（SHA 见 config.case_snapshots）只读判分，产物目录判分 + 负例自测收据。

## 运行器

- 元宝：`bench-automation/drivers/yuanbao/pp_case_b1.py`（pp_case_1027 协议逐字继承，批身份/路径命名空间改为 r1101）。
- 豆包：`bench-automation/run_batch.py --batch r1101`（工作区预生成含禁网附则 TASK.md）。

## 事件与准入

- 运行后按 import-schema 产出 `formal-b1-events.json`（product_run 10 + interface_preflight 2 + self_test 1），`freeze.py build` 生成 official-main-table（预期 B_native=10、A_same_model=空；rejected 含全部历史行）。
- 全量导入不选优；infra 失败最多 1 次重试且如实登记；unknown 不补零不折算。
