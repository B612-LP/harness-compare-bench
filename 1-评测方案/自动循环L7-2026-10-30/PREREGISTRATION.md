# L7 预注册（自动循环 2026-10-30）

- **plan_id**: `l7-20261030`
- **分支**: `loop7-2026-10-30`（自 **新 main** `c8710fb` = PR#10 L5+L6 集成点切出）
- **集成前置（D 前已完成）**: PR#10 已合并 L5+L6 至 main（快进式，36 commits，合并后 main 跑
  test_freeze 全绿）；本环零真实模型调用、零新现场。
- **D 封印**: 本文件提交后立即执行；实现 commit 必须晚于 D。
- **验收**: judge + auditor 双验（零模型工具链环，沿 L3 先例；reviewer 不派）。

## 选题（源自 L6 池结转）

| 池项 | 处置 |
|---|---|
| gate DEFAULT_PLAN_DIR 显式化 | **L7-A（主项）**：L6 三次废封实证「共享验证器语义默认值」跨批错位风险，制度性拔除 |
| L5-P4 ps 操作规程 | **L7-B（次项）**：运维规程条目化 |
| T22d fixture 退役 | 不入本环——runner 位于已封存 L6 现场（E3 钉），改动即破坏历史批零改动红线；留待未来 WB 新现场 |
| L5/L6 未合并 main | **已完成（D 前）**：PR#10 |

## L7-A 设计（共享验证器修订，全套纪律照判卷器修订执行）

- **修前**：`l5-execution/gate.py` 5 处锚定 `DEFAULT_PLAN_DIR = 自动循环L5-2026-10-30`
  （常量、`verify_execution` 签名、`load_execution_seal`、`gate_admission` 签名、
  `--binding` CLI 默认值）——任何调用方漏传即静默读错批（L6 E2 REFUSED 实证路径）。
- **修后**：**默认值全数拔除，显式化 fail-closed**：
  - CLI：`--binding` 与 `--plan-dir` 均改必填（缺失即 argparse 报错退出，不再有隐式批）；
  - Python API：`verify_execution/gate_admission/load_execution_seal` 的
    `plan_dir=None` → `ValueError`（信息含「须显式传参（L7-A）」）；
  - gate 判分语义零改动（formal 真值表、重算口径、白名单均不动）。
- **正例（历史复算=历史复判）**：L4/L5/L6 三批以显式参数复跑 gate
  （L4 binding+plan-dir→期望 formal 0/17 基线不变；L5→5/6；L6→1/1）——三批收据
  复现原判，0 翻转。
- **近似错误例**：缺 `--plan-dir` → 明确报错；缺 `--binding` → 同；
  `--plan-dir` 指向不存在目录 → fail-closed；`plan_dir=None` 直调 API → ValueError。
- **影响面声明**：l4/l5 冻结现场 runner 调 gate 无显式参——现场已封存不重跑
  （documented known-impact）；若未来需重跑须先适配（记池）。l6 现场已显式（L6 修复）
  不受影响。gate 内置 selftest 如依赖默认目录则同步适配（实现期核）。
- **独立验收**：judge 独立复跑三批复算+近似错误例+diff 分类。

## L7-B 设计（运维规程，纯文档）

- 新增 `1-评测方案/工具链/OPERATIONS-hygiene.md`：敏感命令行卫生规程——
  token/Bearer/key 不得进入 ps 可见参数、日志正文、收据正文；凭据经 env 或文件传递；
  事件引用：L5 审计「ps 误印 Bearer、零入库实证」；巡检口径（定期 grep Bearer 字面量）。
- 配套自查：对 L6 现场与工具链目录复跑一次 Bearer/key 字面量扫描收据（零新代码）。

## 纪律承诺

D 先于实现；历史批零改动（gate 修订属共享工具链演进，照 AUD-L6-O2 先例：
修前/修后/正例/历史复算全套+三批 frozen contract 不动）；哈希/时刻脚本生成；
CHANGELOG 不动；live 台账收尾登记并**必跑 work-registry 不变量测试**（L6 新制度）；
收尾 PR 合并 main；结论五段结构。
