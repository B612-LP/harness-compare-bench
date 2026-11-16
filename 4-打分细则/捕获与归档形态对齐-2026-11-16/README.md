# 捕获运行与归档槽形态对齐（2026-11-16，探索后冻结）

目的：把「请求侧最小捕获」（n=1，glm-5.3-flash）与归档 r1109 批 15 个 DSH 槽（deepseek-flash）在**可对齐层**上量化比较，回答：该唯一捕获运行在字节构成上是否落在归档批包络内。纯公开派生算术，0 新运行、0 内容值公开。

先验曝光（如实）：作者在冻结前已查看 slot0 与全部 15 槽数值分布（私档 loop2/DIRECTION.md 登记）；本协议非盲前预注册。

## 固定数据源（公开 pin，缺一即硬失败）
- [输入事件等长与同一性 evidence](<../输入事件等长与同一性-2026-11-16/evidence.json>) SHA256 `cc9089b18ca42f0357003d169ef9e01134e10e4b7881d66247f00d8bb8cb86b0`：15 槽 `prior_metrics.i_sequence` 与 `layers.L0.event_bytes`（长度必须逐槽相等）。
- [捕获 evidence](<../DSH请求侧最小捕获-2026-11-16/evidence.json>) SHA256 `f3e4fab3cd0d742ce4840f1e3b57423b62094c4cd8b7a939b3b347658b4aeaa1`：`capture.requests` 中 `seq==1` 行、`prefix_identity`。
- [捕获 result](<../DSH请求侧最小捕获-2026-11-16/result.json>) SHA256 `3de57557fe7f3c74e6abc041e5181fc415595299b9678ed59d271f8abe596357`（口径引用）。
- 本 README（自 pin）。

## 冻结定义
- 槽级对齐子集：`sys(s)=Σ L0.event_bytes[i] (i_sequence[i]=='system/message')`；`usr(s)=Σ ...=='user/message'`；`harness_only(s)=prior_metrics.i_bytes − sys − usr`。其余类型（spliced/header/context）属 harness I 事件层，不与 provider wire 层对齐，只单列。
- 捕获侧：`cap_sys`/`cap_usr` = seq==1 请求 roles 中 system/user 字节和；`cap_total=request_bytes`。

## 主要终点（描述性判定，非通过/失败门，不外推因果）
- P1 捕获 user ∈ [min,max](15 槽 usr) → `in_range|out_of_range` + 百分位。
- P2 捕获 system 同式判定（预期含模型名差异，出括为有效发现不是缺陷）。
- P3 `cap_sys+cap_usr` 对 15 槽中位数的比率与 [min,max] 判定。
- P4 同任务对照：exercism-py-6 三槽 usr vs `cap_usr` 比率（任务包装不同已披露，仅描述差距）。
- P5 工具结果字节增长因子（分母取自捕获 evidence 的 `workspace` 字段：TASK.md 85B、dominoes.py 34B；工具结果 227B/203B；配对不公开认证，只报两因子与「配对未验证」）。

## 边界
层不同（harness I 事件层 vs provider 请求层）；模型/provider/任务包装不同（capture 已知差异见捕获包协议）；n=1；字节非 token/成本；不认证 provider 行为或历史运行实际请求。判定词仅描述本数据，不写「代表」「等价」。

## 验收
verify.py 仅由上述公开 pin 计算（raw=public 同路径复算）；测试含 pin 篡改/序列-字节长度不等/越界/独占输出反例；非作者独审后发布；旧包/旧分/冻结原件不动。
