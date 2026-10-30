# L5 预注册：工具链可验证性修复与 formal 恢复复验

## 1. 封印与范围

本轮是一个完整闭环，完成后停止等待放行。分支 `loop5-2026-10-30`。两阶段封印沿用 L4：D=本设计及 plan.json/contract.json 的 git 提交，先于实现；E=实现完成、合成负例通过后的 execution-manifest.json 与全部执行代码/配置提交，先于任何真实模型请求。E 的完整提交 ID 与时刻由只读 git 提取进入 runtime-binding.json；registered_at 严格等于 E 提交时刻，不手填。计划/合同必须同时存在于 D 和 E 且字节一致。

本轮研究对象是 **L4 遗留问题池中的工具链缺陷修复及其复验**，不新增能力研究问题，不跑 bare_model_probe（0 槽）。历史批次全部冻结产物不改：v1/v2/v3 合同不动，L4 的 formal 0/17 结论永久不变，不向旧表加槽位、不补写旧行。本轮真实批次的唯一目的是**复验发射修复能恢复 canonical formal 准入**，不构成能力比较或跨产品排名。

## 2. 修复项、修前/修后与验收判据

每项按判卷器修订纪律存档：修前代码、修后代码、正例、近似错误例、独立验收、历史复算影响。冻结版一律不改，修复落在新的版本化文件。

- **R1（池 L5-1）runner 必需字段发射**：修前=codex/dsh lab 与 WB runner 未向 meta 发射 `inputs_verification`、`meta.judge.{checker_sha256,guards_used,correct,n_tasks}`，receipt 缺 `score.checker_sha256`/8dp `reported`，WB receipt 缺 `earned` 镜像。修后=派发前对 contract 输入快照机械比对并发射 `inputs_verification{ok,checked}`；判卷后发射完整 `meta.judge` 与 `score.{checker_sha256,reported(8dp)}`、`meta.weighted(8dp)`；WB `earned` 镜像 `reward`。正例=合成完整运行过 gate 全部 field-compliance；近似错误例=checker_sha256 错配/计数差 1/缺 guards_used 各 1，gate 必须 fail。停止条件：真实槽 canonical fails 中发射类缺字段=0。
- **R2（池 L5-3）ws 模型可见元数据移除**：修前=runner 预写 `ws/meta.json`（含 checker_sha256、config_ref 仓库绝对路径），模型可见并可回显。修后=pre-run meta 只写仓内证据目录（`meta.partial.json`），ws 运行期间仅含允许 inputs+TASK；终件 meta.json 仍只写 ev。正例=修后 dry 运行 ws 归档无 meta.json；近似=旧实现 ws 残留必须被 ws 清单检出。
- **R3（池 L5-4）DSH capture marker 修正**：修前=`"-dsh-%s-%s--"` 拼接与 DSH 真实会话名编码不符 → capture 全空。修后=由 ws 解析绝对路径按 DSH 编码推导目录名（`--`+abs[1:].replace('/','-')+'--'，非 ASCII 段按 DSH `~XXXX~` 转义），未命中时 fallback 后缀扫描并记录 match_method；preflight 增加零模型 dry 验证（构造临时 ws/伪会话目录验证匹配器命中）。真实槽验收=capture 非空且身份链过验，才恢复 usage 结论。
- **R4（池 L5-8）gate v2 not_executed 白名单**：修前=not_executed 目录内任何额外条目判「疑似虚造」，R3 强制的 `registrations/` 预持久登记被误判（dated sidecar 已证）。修后=新版 gate（`1-评测方案/工具链/l5-execution/gate.py`）白名单额外放行且仅放行 `registrations/` 一个名字，逐项 SHA 记录入收据；其余额外条目仍 fail。历史复算影响=gate v2 复判 L4 全 17 冻结行：**仅 bird 槽该 fail 消失，其余 16 行 fails 与判定逐条一致**；summary 除该 fail 相关计数外不变。任何其他差异即修复缺陷，不得选择性接受。
- **R5（池 L5-5）cache 归一化映射 v2**：修前=预设平铺键缺 `usage.input_tokens_details.cached_tokens` 嵌套路径，mapping 层 missing 与 raw 阳性并存。修后=增加嵌套路径（映射表版本化）；对 L4 全 18 probe raw inventory 离线重算，输出与 offline-recompute-erratum 表一致（6 对 repeat=2048、fresh/control=0）→ 撤该 finding。全程零 API。
- **R6（池 L5-2）WB renderer 就绪等待**：修前=CDP 端口已起但 page target 未就绪时发送前异常。修后=发送前非生成式轮询 page target 至就绪（deadline 内），超时则该槽落 notexecuted.json 记 not_executed，不重试兜跑。正例=mock 延迟就绪被等待捕获后正常发送；近似=超时路径正确落盘 not_executed。
- **R7（L4 收尾项）WB frame 路径解析与 receipts 非破坏写**：修前=frame 命令路径解析失败致 actual 状态 null，且重跑覆盖 tracked receipt。修后=路径解析修复+write-once（冲突拒写另存时间戳副本）。
- **纪律项 D1（池 L5-6）**：producer 报告显式披露 setsid 脱组残留写者边界，停后 ws 双采样常态化。**D2（池 L5-7）**：报告模板统一 raw 精度与 canonical 8dp 双口径并陈。

## 3. 真实批次（product_run 共 6 固定槽）

| order | slot | case | timeout |
|---|---|---|---|
| 1 | l5-20261030-cli-codex-dabstep-payments-10-r1 | dabstep-payments-10 | 1800 |
| 2 | l5-20261030-cli-codex-tb-cargo-plan-r1 | tb-cargo-plan | 2400 |
| 3 | l5-20261030-cli-dsh-dabstep-payments-10-r1 | dabstep-payments-10 | 1800 |
| 4 | l5-20261030-cli-dsh-tb-cargo-plan-r1 | tb-cargo-plan | 2400 |
| 5 | l5-20261030-wb-gateway-bird-ca-schools-15-r1 | bird-ca-schools-15 | case.json |
| 6 | l5-20261030-wb-gateway-dabstep-payments-10-r1 | dabstep-payments-10 | case.json |

选题理由：dab/cargo 为 L4 已见极差的诊断性选题，便于与历史 observed 并列参考（不配对比较）；WB bird 直接复验 R6，dab 提供 WB 第二数据点。case/输入/checker/timeout 字节取自 L4 合同冻结快照（freeze-20261029-v2 checker bytes），不修订 checker 语义。CLI：deepseek-flash、low、route api.deepseek.com、skills/web off、离线题解约束、whole-CLI restart=0；WB：声明 alias deepseek-v4.1-flash、gateway www.workbuddy.cn、独立交付层，不跨路由归因。每槽全新仓外 workspace 与新会话，命名空间 l5-20261030，不复用 r1030/r1031/l4。bird 若就绪等待超时按 R6 落 not_executed，同类失败复现即停该槽。

## 4. 执行前闸门与判定

E 释放前：修复代码合成正/负例全过；gate v2 对 L4 冻结 17 行复判满足 R4 历史影响判据；mapping v2 对 L4 cache raw 重算满足 R5 判据；DSH dry 验证命中；WB mock 就绪正/负例过。真实运行仅 lead 释放 E 后开始。

主判定（预注册）：修复后真实槽在无污染、无 E 漂移、证据链完整前提下 canonical **formal=true**。若发射类 fails>0 → 修复未达停止条件，如实归档；若出现新的非发射类 fail（污染/隔离/输入等）→ 按合同判，不回改修复以凑通过。DSH usage 结论恢复以 capture 非空+身份链过验为前提。分数保持 raw 精度记录，canonical 8dp 重算并陈（D2），不做跨产品排名、不做与 L4 的配对能力推断。

## 5. 分账、证据与职责

product_run=6 固定槽；self_test=各修复项合成正/负例；offline_recompute=gate v2 复判 17 冻结行 + mapping v2 重算 18 cache probe；grading_regression=R4/R5 判卷工具修订档案（修前/修后/正例/近似错误例/独立验收/历史复算影响）；interface_preflight=零模型预检；bare_model_probe=0。未执行/部分执行单列，不凑完成数。

lead 只做 git/封印/调度/释放。mechanism-engineer：R1/R2/R3（codex+dsh lab v5）+合成例；wb-probe：R6/R7+WB 合成例+WB 两槽执行；freeze-engineer：R4 gate v2/R5 mapping v2+grading_regression 档案+六账；builder-codex/builder-dsh：E 后各执行 2 槽；judge：独立验收（不依赖 builder 分数/结论）；independent-reviewer：离线复算（R4 历史影响、R5 一致性）干净环境复核；auditor：敌意审查（至少核 E 绑定、修复 diff 最小性、formal 复判）。结论按观察—证据—解释—未排除因素—可复现实验五段。

## 6. 停止与剩余问题

凭据/标准答案泄漏、越界污染、E 代码漂移、准入误收、readiness 同类失败复现 → 立即停相关执行并归档，不静默重跑。未知必须含影响/下一步/停止条件。R1–R7 未列尽的 L4 池尾项（如 L5-3 的逐条轨迹归因纪律）继续保留问题池，不承诺本轮全部完成。事故单列不并六账；不改 CHANGELOG、不写周报。
