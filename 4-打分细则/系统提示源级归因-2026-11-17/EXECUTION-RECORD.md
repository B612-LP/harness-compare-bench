# 系统提示源级归因 — 执行记录

- 日期：2026-11-17（Asia/Shanghai）；窗口 2026-11-16 22:24 起至 2026-11-17 12:00（用户口头授权"随便测试"）。
- 零新增模型/产品运行；全部材料来自既有私档（r1109 归档、capture r1 请求原文）与本机已安装构建的只读检查。
- 基线：公开仓 f16b61bc（v1.70 发布后）；本页验证器 BASELINE 钉该提交。

## 问题

capture req1 的 system（2593 B，SHA256 `8e17c07c…`）此前只有结构归因（对齐包/溯源包），没有源级归因：这 13 行提示词各自来自哪个源文件、哪些槽位是动态值、任务内容占多少字节。老师归因定责关注点（模型/Skill/Harness 三层分开）要求把 Harness 固定层落到可指认的源。

## 方法（私档探针，只读）

- 解析 `/Applications/DeepSeek Harness.app/Contents/Resources/app.asar`（运行时 0.2.2-rc.3）的 header JSON，在 8000 个 JS 文件的语料中逐行定位 capture system 13 行的唯一来源；`@deepseek-ai` 路径为 symlink 节点，读取经 resolve。
- 私档 `loop13/`（仓外）：`rebuild_probe.py` 多轮修正后实现 12 段抽取规则，从 9 个源文件快照逐字节重建 capture system（BYTE-EQUAL TRUE，7 轮迭代）；`work/sources/` 存 9 源快照与 manifest。
- 抽取规则按源码字面形态分类：静态整行、行内槽（`{{model}}`）、模板串（`${blockedAfter}`/`${toolName}`/`${visible.map…}` 嵌套模板）、条件拼接（read/edit 注册与否）。嵌套模板先槽替换再做 JS 转义还原（`\n`→换行），否则差 2 字节（字面 `\n` 4 字节 vs 真实换行 2 字节）。

## 结果（证据文件承载，此处仅摘要）

- 13/13 行全部归因到 9 个源文件（evidence.json sections 表含每行 kind/source/slots/sha256）。
- 槽位 4 类共 6 行：`{{model}}`（persona 模型名）、`blockedAfter`（goal 工具默认 3）、`toolName`（workflow）、`delegates`（subagent 列表 subagent, subagent_fork）。
- 任务/用户内容字节数 = 0：整条 system 是 Harness 固定层。
- 限制：只代表当前已安装构建（0.2.2-rc.3 + 本机 profile patch）的装配结果；persona 文本源头是 `cordis.patch.yml`（`You are a coding agent powered by the {{model}} model.`），{{model}} 由 profile patch 的 agent-default-model 注入；公开层不重放原文，只重放封印算术；私档真实性不经公开层认证。

## 验证器与套件

- `verify.py`（stdlib）：`--system --sources --build-evidence --output`（构建：9 源 SHA 核验→12 段抽取→拼装→与 system 原文逐字节比较）与 `--evidence --output`（公开重放：校验 13 节记录/kind 表/slot 声明/源 pin/system pin/limits/任务字节 0）。
- `test_verify.py`：21 用例（合成 9 源全管线、13 类篡改、重复键/非有限数拒绝、真档公开重放与 result 逐字节比较、CLI 拒绝与独占写、env 门控真档端到端）。四档实测：普通/-O × 有/无 `SYSATTR_ARCHIVE_BASE` 全 OK（无真档根时 skip=1）。
- 四路一致性（真档）：私档重建（普通/-O）与包内 evidence/result 逐字节相同；公开重放（普通/-O）与 result 逐字节相同。

## 时间线（文件系统时间，Asia/Shanghai）

- 02:59–03:10 asar 考古与 13 行定位；03:11–03:14 rebuild_probe.py 7 轮迭代至 BYTE-EQUAL TRUE；03:14:17–03:15:37 evidence/result 首建（实现中的构建器）；03:15–03:17 构建器定稿并幂等重建；03:17–03:20 test_verify.py 修复（fixture 嵌套模板形态、SYSTEM_BYTES patch、跨类 patch 泄漏、parse_float 守卫、CLI pin 拒绝用例）至四档全绿；03:21 本记录与 SELF-ACCEPT（初稿时间线为事后补写，分钟级与文件系统实记有出入，已按 mtime 订正）。
- 构建过程披露：evidence/result 首建于 03:14:17–03:15:37（实现中的构建器，`result_for` 尚未同形）；构建器定稿后幂等重建，与包内两件逐字节相同（FINAL-REBUILD-IDENTICAL 及 -O 版）；此后 verify.py 仅新增 `parse_float` 非有限数拒绝（终版 SHA 27e40536…；守卫加入的精确时刻无独立文件系统证据，终稿 inode 03:17:40，守卫后 03:20 复验 rp5/rp5O 与 result 逐字节一致）。
- 非作者独审：task-38 sysattr-auditor PASS（2026-11-17 03:22–03:31，独占私档 `until18-20261117-loop13-audit/independent-20261117T0325/`；独立从 asar 解析 9 源、自有抽取重建 2593B 逐字节等、CLI 四路/21×4 档/39 类对抗/隐私全过；5 项低危含本记录初稿时间线分钟级出入——已按文件系统时间订正，余 4 项不阻断留档）。

## 已知限制与诚实披露

- 迭代探针时首版常量曾含未实测占位值，均已以实测值替换并在冻结前复核（教训重申：常量必须当场测量）。
- 测试首跑 20 用例失败 2+13：根因是合成 fixture 的 subagent 嵌套模板形态与真实源不符（缺外层反引号）、`SYSTEM_BYTES` 未随合成 patch、跨类 patch 泄漏到真档用例；修正后四档全绿。失败目录未单独留存（中间态均已覆盖）。
- 公开重放无法独立证伪私档整体伪造；非作者独审（task-38）从原始 asar/私档独立重算补证。
