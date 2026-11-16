# 执行记录：捕获运行与归档槽形态对齐（2026-11-16）

## 时间线（Asia/Shanghai）
- 19:10 立项（私档 until14-20261117/loop2/DIRECTION.md）；19:11–19:12 探明两个公开 evidence 结构并预览数值（先验曝光已在协议登记）。
- 19:12 冻结协议 README.md；19:14–19:16 实现 verify.py/test_verify.py 并生成 evidence/result。
- 修复史（全部在首份打包 evidence 之前或之后如实分账）：
  1. verify.py 两处根路径笔误（exclusive repo=parents[2]→parents[1]；--root 默认同改），修复后首次 build 成功。
  2. validate_stored 初版比较包含 evidence_sha256 字段导致必然失败，改为剥离绑定字段比较 + 单独校验绑定。
  3. 测试三处修正：EndpointTests 槽名未带同任务前缀（`same-task slots missing`）；合成 P5 增长因子期望值算错；`1e999` 不走 parse_constant——verify.loads 补 `parse_float=_finite_float` 硬化（继承 capture 包独审 M1 教训；capture 包已发布冻结，本包起生效）。
  4. 公开重放首次写到 /tmp 被独占守卫拒绝（exit 2，未落盘）——守卫按设计生效，重放改为仓内临时路径后 cmp。

## 事实表（全部来自公开 pin，无内容值）
- 归档 15 槽 system ∈ [2535, 2541]B；user ∈ [7349, 9977]B；system+user ∈ [9884, 12518]B、中位 10291B；同任务 exercism-py-6 三槽 user 均 7503B。
- 捕获 seq1：system 2593B、user 9529B、合计 12122B（请求 33091B、5 消息、22 工具）。

## 终点判定（描述性）
- P1 捕获 user in_range（73.3 百分位）。
- P2 捕获 system **out_of_range**：比归档最大值高 52B（+2.0%）——模型/适配器差异进入系统提示字节，量化了跨 provider 的系统提示不可比幅度。
- P3 对齐和 in_range（中位的 1.1779 倍、73.3 百分位）。
- P4 同任务 user 差距 1.27 倍（捕获运行的 TASK.md 包装为另稿，协议已知差异）。
- P5 工具结果/工作区文件字节增长因子 **2.671 与 5.971**（分母取自捕获 evidence 的 workspace 字段：TASK.md 85B、dominoes.py 34B；配对不认证；小文件固定渲染开销占比高，与归档「Read 呈现包装」方向一致）。

## 整改（独审 F1，2026-11-16 19:33 后）
- 独审发现 P5 初版分母错配：214B 是 seq1 任务 user 消息字节（214+3111+679+5525=9529 交叉验证），不是工作区 TASK.md 文件字节；真实文件为 85B（SHA 68599aec…3f2c，且本就在公开 capture evidence 的 workspace 字段内）。
- 修复：README/verify/EXEC 同步改为由 capture evidence workspace 字段派生分母（硬编码两文件名集合，其他集合拒绝）；重生成 evidence/result；growth 因子 1.061/5.971 → **2.671/5.971**；测试新增 workspace 缺失/名单错误拒绝两例。P1–P4 不变。

## 整改（克隆验收 F2，2026-11-16 19:50 后）
- 发布验收（新克隆重放）发现 verify.py 输出守卫过严：exclusive() 把所有输出限制在包所在仓内，导致「克隆内验证、克隆外落收据」的标准重放形态被拒（本地回归与克隆验收 align 节点双双 exit 2；被守卫拒绝而未落盘，非数据缺陷）。
- 修复：exclusive/dump 增加 forbidden_roots 参数——仅 --build-evidence 禁止写入输入仓根（保护输入 pin），--output 允许任意不存在路径；测试改为「保护根拒绝 + 非保护路径放行」两例。evidence/result 字节不受影响（不重算）。

## 验证与验收
- 打包 evidence/result 由 `verify.py --build-evidence` 生成；公开重放（普通与 -O、stdlib、`--root` 显式仓根）result 逐字节同（私档 loop2/replay/ 双份）。
- test_verify.py 35 反例 ×2（普通/-O）全绿：pin 篡改、序列/字节长度不等、子集超界、seq1 缺失/重复、辅助请求、工具数错误、verdict/百分位、同任务缺失、存储证据/终点/绑定篡改、duplicate/nonfinite（NaN、1e999、Infinity）、bool、路径逃逸（含 /tmp 拒绝实证）、独占输出、真实冻结值（2593/9529/33091、slot0 2540/9653、out_of_range、1.27、1.061/5.971）、无内容值泄漏。
- 非作者独审：另行委派（独占私档 loop2/audit/），结果未回前本包不整合发布。

## 限制
见 result.json limits 六条；要点：层不可全对齐（只 system/user 子集）、模型/provider/任务包装不同、n=1、字节非 token、P5 配对不认证、判定词不外推。本包不改动任何旧包/旧分/冻结原件，0 新产品/模型运行。
