# L5 干净临时环境独立复核（task-16）

分类：离线复算 / 判卷回归；不计产品运行、裸模型探针或接口预检。审计者 independent-reviewer；写界仅本目录。

## 一、观察

**复核完成，非全过：401/402 项成立；保留一项真实的 E2 档案自哈希不符。** 本次零模型、零网络、零产品 CLI/判卷器执行。所调用判卷准入模块是离线规则判断，不是题目 checker。

| 要求 | 独立结果 |
|---|---|
| R4 正例 / 近似错误例 | 原样脚本复跑 exit 0；8 个断言与在档收据逐项一致，其他有效 JSON 字段完全一致 |
| R4 历史复算 | 17 个唯一计划槽 / 4 个断言；逐字段等于在档收据；唯一投影差异仍是 bird 白名单 fail 消失，formal 仍为 0/17 |
| R5 映射复算 | 18 槽、28 个断言（含 responses erratum 逐槽比对）、另 6 个单元例全部一致；完整 raw/mapping/normalized 视图一致，别名不相加 |
| E3 绑定 | D/E3/磁盘三份原件逐字节一致；独立枚举 23 个仓内源与 17 个 external pins；源码 E3 blob/磁盘/manifest 三方 SHA 一致；registered_at 精确等于 E3 committer 时刻 |
| 中止档案 | E1 27 项 + E2 187 项，全量核 214 项 SHA；213 项匹配、1 项自引用不符；两份文件清单均无缺漏；两份 supplement 已对账 |
| 自选负例 | 恰 1 个大小写绕过 `Registrations`，加恰名 `registrations` 正对照；8 个细分判断成立，绕过仍 fail，score 保持 null |
| 输入保护 | 815 项受保护输入（含复跑收据与外部原件）最终重哈希无变化 |

唯一真实差异是 [E2 中止主收据](<3-表现现场/中止重封档案E2-20261030T0207/abort-receipt.json>) 的 `files_sha256["abort-receipt.json"]`：记录的 SHA 为 `57ccffe1140e10906f984aff693bb4428fb5f7be504a0f298c5b5b5a20d8714d`，当前原件实算为 `d8c176ef16003407ed46698e8b1ed1de03622da06060ea08c9efa3e03eb149af`，24,063 bytes。该自引用不满足“当前字节等于表内 SHA”，**未豁免、未改写原收据、未记作通过**；其余 213 项的实际原件与记录相符。这不等于所有中止证据均无效，也不能说档案全哈希通过。

## 二、证据

- 主机器收据：[independent-check-02.json](<5-评测报告/L5独立复核-2026-10-30/independent-check-02.json>)；其中完整列出逐断言比较、每个 E3 源 / external pin、214 项归档核验、Git 只读命令及其输出哈希、输入起止 SHA。
- 首次机器收据：[independent-check-01.json](<5-评测报告/L5独立复核-2026-10-30/independent-check-01.json>)，连同 [首次独立程序](<5-评测报告/L5独立复核-2026-10-30/independent_verification.py>) 原样保留；最终说明见 [finalize_verification.py](<5-评测报告/L5独立复核-2026-10-30/finalize_verification.py>)。首次 11 个 false 中 10 个来自审计者把准备态 null 错当已绑定运行值；另 1 个即上述真实自哈希差异。五份 Codex 准备模板的十个字段明确为 null，不补值、不当已登记证据；实际 claim / run 中的已知封印及时间另与 Git committer 实测核对。
- 原样复跑：[R4 8 断言](<5-评测报告/L5独立复核-2026-10-30/r4-acceptance-reproduced-receipt-02.json>)、[R4 17 槽历史表](<5-评测报告/L5独立复核-2026-10-30/r4-history-reproduced-receipt-02.json>)、[R5 18 槽映射](<5-评测报告/L5独立复核-2026-10-30/r5-mapping-reproduced-receipt-02.json>)。唯一允许的比较差异是脚本生成时刻，以及 R5 `scope` 从原工作树到临时树的精确绝对前缀替换；没有归一化掉状态、fails、SHA、得分或 usage 值。
- 环境与副本：[input-snapshot-01.json](<5-评测报告/L5独立复核-2026-10-30/input-snapshot-01.json>)、[reproduction-run-summary-02.json](<5-评测报告/L5独立复核-2026-10-30/reproduction-run-summary-02.json>)。固定副本 576 个文件、43,709,470 bytes；独立临时根 `/private/var/folders/rl/7n6h633s4c9dl69tvyb777000000gn/T/l5-independent-urge16kp`。源码脚本与原件逐字节相同，未执行 builder、模型、产品或题目 checker。
- 负例：[whitelist-negative-receipt-01.json](<5-评测报告/L5独立复核-2026-10-30/whitelist-negative-receipt-01.json>)。恰名目录通过；大写目录明确产生目录额外文件 fail，record_valid=false、formal=false，未被错误列为白名单证据。

只读 Git 实测（没有 git 写态命令）：

| 标识 | 完整 commit | committer 时间 |
|---|---|---|
| D | `8b1043d05c5b9dd9b3ae5aa5982cea4e9e852825` | `2026-10-30T01:17:14+08:00` |
| E1 | `7474b84aeaa7290c67ee2288d114953dd6cccadd` | `2026-10-30T01:51:27+08:00` |
| E2 | `02a4cac25f679b0e2359f9de6e2b10c82bd9ea0d` | `2026-10-30T02:00:33+08:00` |
| E3 | `d8366da32694713d4f77c740f935229f9e298df4` | `2026-10-30T02:16:07+08:00` |

D → E1 → E2 → E3 → 核验时 HEAD 的祖先链全部成立，committer 顺序不倒退；E1/E2 中止事件位于各自 seal 之后及下一 seal 之前。已知原 claim/meta 时间与对应 commit 时间一致；E2 目录中的 E3 作废 claim 按 [supplement 2](<3-表现现场/中止重封档案E2-20261030T0207/abort-receipt-supplement-2.json>) 明确视为 E3，不冒充 E2 运行。准备态 null、目录名时间及文件系统 mtime 均不被拿来补造 registered_at。

当前 [E3 binding](<1-评测方案/自动循环L5-2026-10-30/runtime-binding.json>) 记载且独立实算相符的 manifest SHA 为 `a653eacb06d28d57dc54673f978ed4008b51c0434c1816b2b6d3ad3b63b4b309`；以这一绑定值而非任务提示的截断示例为准。

标准证据行（下述代码块由原 evidence_line 工具生成；路径 / SHA / 字节 / 时刻均非手填）：

```text
5-评测报告/L5独立复核-2026-10-30/independent-check-02.json · 3354fc52 · 481479B · 2026-10-30T02:47:50+08:00
5-评测报告/L5独立复核-2026-10-30/independent-check-01.json · 95ac735b · 466651B · 2026-10-30T02:47:50+08:00
5-评测报告/L5独立复核-2026-10-30/whitelist-negative-receipt-01.json · 137e8444 · 2911B · 2026-10-30T02:47:50+08:00
5-评测报告/L5独立复核-2026-10-30/input-snapshot-01.json · 028b6ff5 · 131429B · 2026-10-30T02:47:50+08:00
5-评测报告/L5独立复核-2026-10-30/reproduction-run-summary-02.json · 1235c334 · 1491B · 2026-10-30T02:47:50+08:00
5-评测报告/L5独立复核-2026-10-30/r4-acceptance-reproduced-receipt-02.json · 7a1c6078 · 6959B · 2026-10-30T02:47:50+08:00
5-评测报告/L5独立复核-2026-10-30/r4-history-reproduced-receipt-02.json · 7595b007 · 12337B · 2026-10-30T02:47:50+08:00
5-评测报告/L5独立复核-2026-10-30/r5-mapping-reproduced-receipt-02.json · b1edf469 · 61673B · 2026-10-30T02:47:50+08:00
5-评测报告/L5独立复核-2026-10-30/r4-acceptance-run-02.json · d87e1853 · 1050B · 2026-10-30T02:47:50+08:00
5-评测报告/L5独立复核-2026-10-30/r4-history-run-02.json · ed94fb7c · 11740B · 2026-10-30T02:47:50+08:00
5-评测报告/L5独立复核-2026-10-30/r5-mapping-run-02.json · 69797b9f · 1037B · 2026-10-30T02:47:50+08:00
5-评测报告/L5独立复核-2026-10-30/whitelist-negative-run-01.json · 66ac175b · 819B · 2026-10-30T02:47:50+08:00
5-评测报告/L5独立复核-2026-10-30/prepare_review.py · 7d1c4f9f · 3535B · 2026-10-30T02:47:50+08:00
5-评测报告/L5独立复核-2026-10-30/guarded_run.py · bcf7ee41 · 2047B · 2026-10-30T02:47:50+08:00
5-评测报告/L5独立复核-2026-10-30/run_reproductions.py · 5cec6fec · 4032B · 2026-10-30T02:47:50+08:00
5-评测报告/L5独立复核-2026-10-30/independent_verification.py · a79d0ba4 · 16640B · 2026-10-30T02:47:50+08:00
5-评测报告/L5独立复核-2026-10-30/finalize_verification.py · aa4c2646 · 4996B · 2026-10-30T02:47:50+08:00
5-评测报告/L5独立复核-2026-10-30/whitelist_negative.py · e126cd8b · 4196B · 2026-10-30T02:47:50+08:00
5-评测报告/L5独立复核-2026-10-30/build_readme.py · 81bc0d0f · 11273B · 2026-10-30T02:47:50+08:00
1-评测方案/自动循环L5-2026-10-30/execution-manifest.json · a653eacb · 5921B · 2026-10-30T02:47:50+08:00
1-评测方案/自动循环L5-2026-10-30/runtime-binding.json · 7ee8b689 · 660B · 2026-10-30T02:47:50+08:00
3-表现现场/l5-20261030-cli/aborted-attempts-20261030T0152seal/abort-receipt.json · 20474b61 · 4754B · 2026-10-30T02:47:50+08:00
3-表现现场/中止重封档案E2-20261030T0207/abort-receipt.json · d8c176ef · 24063B · 2026-10-30T02:47:50+08:00
3-表现现场/中止重封档案E2-20261030T0207/abort-receipt-supplement.json · 64d49231 · 282B · 2026-10-30T02:47:50+08:00
3-表现现场/中止重封档案E2-20261030T0207/abort-receipt-supplement-2.json · ef9627b9 · 549B · 2026-10-30T02:47:50+08:00
```

## 三、解释

R4/R5 的在档结论已由独立进程对同样字节输入复现，不是直接采信实现者总结。R4 修订修复的是 not_executed 目录白名单记账，不能把 formal=false 改成通过；R5 修订修复的是映射覆盖，不代表新增任何模型请求、cache 收益或经济成本结论。

“干净环境”在这里的精确定义是：全新临时输入树 / cwd、最小化显式环境、Python 隔离模式与禁止写 pyc、OS `deny network*`，原件不可写，Python 仅准只读 Git 子进程。为了验证历史封印中的绝对外部路径，HOME 明确保留；不是空 HOME、容器或异机。OS 拒读该 HOME，除仓库及逐一枚举的 external pin；CPATH / SDKROOT 等系统 Python 启动注入键在运行收据中可见，未冒充完全空环境。只读取明确的外部文件做字节哈希，未解码任何凭据正文。

`live_doc_drift=[]` 仅表示审计起止输入没有变化，**不表示已有自哈希矛盾不存在**。最终主收据退出码 1 是这一保留差异，不是 R4/R5 复跑失败。

## 四、未排除因素

1. E2 自引用记录的哈希不是当前主收据哈希：影响是不能宣称整个归档自校验全过；下一步如需修正，应由授权所有者新建外置、不可覆盖的更正侧车并注明所指版本，不能为了自指固定点而重写原表；停止条件是出现其他文件 SHA 漂移或新旧版本无法区分时，不继承本意见。
2. E3 仅验证显式源 / 配置 / 构建 pin，manifest 明示并未锁完整传递产品依赖。影响是不能推出整个主机、供应商内部实现或运行语义已冻结；下一步只有在新增代码 / 依赖 / pin 后重新审查；任一现有 pin 变动即停止继承本次绑定意见。
3. Git 时间与文件时间属于本机记录，不是 NTP 或外部可信时间戳。这里只能支持已列 seal、已知 registered_at 与中止事件间的一致性；需外部时钟结论时应另取授权证据，不能以本复核替代。
4. 中止两批的真实消耗在原档案中已明确披露。本次只核字节与已列元数据，不重建 HTTP 尝试分母、不证明进程组历史停止、不证明所有 trace 的语义完整或无污染；不可用本复核恢复 formal、回填 usage，或把未计计划槽解读为未发生消耗。
5. 此处一项大小写负例是规定的抽测，不是完整安全证明，也不推广成所有路径 / 软链 / 损坏 JSON 都已覆盖。

## 五、可复现实验

入口程序按固定相对布局识别仓库。复制到同样布局的独立工作副本并使用全新输出路径后，依次运行：

```sh
/usr/bin/python3 -B '5-评测报告/L5独立复核-2026-10-30/prepare_review.py'
/usr/bin/python3 -B '5-评测报告/L5独立复核-2026-10-30/run_reproductions.py'
/usr/bin/python3 -B '5-评测报告/L5独立复核-2026-10-30/independent_verification.py'
# whitelist_negative.py 须按 guarded_run + 同一 deny-network SBPL 运行；完整调用已在工具运行日志保留。
/usr/bin/python3 -B '5-评测报告/L5独立复核-2026-10-30/finalize_verification.py'
/usr/bin/python3 -B '5-评测报告/L5独立复核-2026-10-30/build_readme.py'
```

现有输出均 exclusive create，直接原地复跑会拒绝覆盖；不得删除原证据来“清理失败”。复现结果应仍为三脚本 exit 0、逐断言一致、大小写负例拒绝，以及同一 E2 自引用差异；若输入变了，明示新差异，不得套用旧 PASS。

第一次三项包装器 exit 1 的 stdout/stderr 已保留：审计者的初版 SBPL 把中文输出目录编码为 JSON ASCII 转义，未匹配真实路径，导致包装器写运行收据被拒。后续只修审计策略的 UTF-8 路径表达，未改变被测源码或原件。另一次审计者准备态 null 判断失误的首程序 / 首收据亦完整保留；这些不得归咎于 gate 产品缺陷或抹掉真实自哈希问题。

live_doc_drift=[]
