# judgment-test-pool（κ 一致性测试测项池，L39 staging）

生成：2026-11-03T16:09:33+08:00 ｜ 来源语料：L38 staging human-judgment-corpus.json（71 条）｜ 生成方式：零模型调用、零联网、零判分重算、只读公开仓与私档、不改既有文件。

## 一、方法

### 拆槽（construction=split，17→38）
- **HJ-069（11 槽 launch_invalid 聚合裁定）→ P-018..P-028**：读公开批次收据 batch-summary.json，把聚合裁定拆为逐槽测项；每条 case=该行事实字段（run_id/case/rep/槽后缀/conversation_id=null/status=null/grading=null/workspace_files_sealed=0/发射证据原文）+README 口径句；question 问逐槽 launch_verdict 定性；gold=pass（11/11 槽裁定一致，无缩减）。
- **HJ-006（q2697 十探针表）→ P-029..P-038**：读公开裁定 §6 探针表，拆为逐探针测项；case=冻结金标+兼容轨口径句+探针答案；question=「按 q2697 现行兼容轨单题判定，该答案应通过吗」；gold=表内兼容轨判定（通过→pass 6 条、拒绝→fail 4 条）。严格轨判定逐行保留于 gold_provenance.quote，不单列测项（任务预期 10 条）。
- 拆分件 source_corpus_id 指回 HJ-069/HJ-006；两源均无「槽内无独立可判金标」情形，无缩减。

### 构造（construction=built，38→60，22 条）
- 候选=availability=needs_construction 且未被拆槽占用的 46 条；封闭优先级 ruling > final_adjudication > correction_chain > replay_golden > revision_fixture_*；other/context_only/selftest_positive 不选。同类型内按 corpus_id 升序取前 N。
- 构造定义（封闭）：仅把公开仓既有证据重组为判读三元组——case=裁定前视角的情况事实与合同/规则文本（截取自公开文件，注明 path+locator）；question=封闭选项问题；labels=[pass,fail,uncertain]；gold=既有人工裁定的判定映射（逐字摘录或忠实转写，gold_provenance 附 path+locator+quote 溯源）。不新增人工判断。
- 入选 22 条=16 ruling（HJ-001/003/004/005/008/009/015/018/020/032/033/034/035/036/037/042）+1 final_adjudication（HJ-068）+5 correction_chain（HJ-013/022/023/024/025，语料序前五）。

### gold 语义
- pass=对所问判断的肯定；fail=否定；uncertain=无法确定。本池无 uncertain 设计位（既有人工裁定均为二值判定）。

## 二、池构成对账

| 构成 | 条数 | 池位 |
|---|---:|---|
| direct（既有 17 条直测项） | 17 | P-001..P-017 |
| split（HJ-069 十一槽） | 11 | P-018..P-028 |
| split（HJ-006 十探针） | 10 | P-029..P-038 |
| built（ruling×16 + final_adjudication×1 + correction_chain×5） | 22 | P-039..P-060 |
| **合计** | **60** | P-001..P-060 |

gold 分布（实测）：pass 47／fail 13／uncertain 0。

## 三、direct 项（P-001..P-017）

| pool_id | 语料 | 场次/行 | gold | 问句要点 |
|---|---|---|---|---|
| P-001 | HJ-049 | r1101 doubao/bird | pass | 扫描 5 命中均为题面自带→应 V |
| P-002 | HJ-050 | r1101 doubao/dabstep | pass | 零命中→应 V |
| P-003 | HJ-051 | r1101 doubao/lcb | pass | 零命中、产物 4 项→应 V |
| P-004 | HJ-052 | r1101 doubao/tb | fail | 出工作区读 checker/truth→应 X 非 V |
| P-005 | HJ-053 | r1101 doubao/exercism | fail | 发射期基础设施失败→infrastructure_invalid 非 V |
| P-006 | HJ-054 | r1101 yuanbao/bird | pass | 0/0、档位 auto→应 V |
| P-007 | HJ-055 | r1101 yuanbao/dabstep | pass | 0/0、档位 auto→应 V |
| P-008 | HJ-056 | r1101 yuanbao/exercism | pass | 0/0、六文件回收→应 V |
| P-009 | HJ-057 | r1101 yuanbao/tb | pass | 0 命中、0 分系未达标→应 V |
| P-010 | HJ-058 | r1101 yuanbao/lcb | pass | 无答案块、driver suspect、先例 B22→改判 V |
| P-011 | HJ-059 | wb bird | pass | 10 调用全在工作区→应 valid |
| P-012 | HJ-060 | wb dabstep | fail | 12 处 /tmp 写入执行→应 invalid |
| P-013 | HJ-061 | wb exercism | pass | 40 调用全在工作区→应 valid |
| P-014 | HJ-062 | wb lcb | fail | /tmp 写读+外部删除→应 invalid |
| P-015 | HJ-063 | wb cargo | fail | /tmp 复制/写/读/删→应 invalid |
| P-016 | HJ-070 | doubao-n3 exercism r2 | pass | 额度中断→quota_interrupted_superseded |
| P-017 | HJ-071 | doubao-n3 tb r3 | pass | 发射拒绝→launch_invalid |

## 四、拆槽项（P-018..P-038）

### HJ-069 十一槽（P-018..P-028，gold 全 pass）

| pool_id | 槽 | launch_verdict（gold 所据原文） | 发射证据（原文节选） |
|---|---|---|---|
| P-018 | bird-ca-schools-15 r2 | launch_infra_invalid | 发送失败:Enter+实时坐标点击均未生效(Quill 已同步) |
| P-019 | bird-ca-schools-15 r2/b | launch_infra_invalid | Connection to remote host was lost. |
| P-020 | dabstep-payments-10 r1 | launch_infra_invalid | no conversation id |
| P-021 | dabstep-payments-10 r1/b | launch_failed | no conversation id; composer diag: {"inputLen":0,"url":"http |
| P-022 | exercism-py-6 r1 | launch_infra_invalid | no conversation id |
| P-023 | lcb-recent-hard-4 r1 | launch_infra_invalid | slot dir contains only before.json (no new-task.json, no err |
| P-024 | lcb-recent-hard-4 r3 | launch_infra_invalid | 发送失败:Enter+480s 重试窗内均未生效(Quill 已同步) |
| P-025 | tb-cargo-plan r1 | launch_infra_invalid | timed out |
| P-026 | tb-cargo-plan r2 | launch_infra_invalid | timed out |
| P-027 | tb-cargo-plan r1/b | launch_infra_invalid | 发送失败:Enter+900s 重试窗内均未生效(Quill 已同步) |
| P-028 | tb-cargo-plan r2/b | launch_infra_invalid | 发送失败:Enter+900s 重试窗内均未生效(Quill 已同步) |

### HJ-006 十探针（P-029..P-038，按现行兼容轨）

| pool_id | 探针 | 答案 | gold（兼容轨） | 严格轨（quote 内原文） |
|---|---|---|---|---|
| P-029 | 正例 | `E:13.57` | pass | 通过 |
| P-030 | 负例 N1 | `NexPay:13.57` | pass | 拒绝 |
| P-031 | 负例 N2 | `13.57` | pass | 拒绝 |
| P-032 | 负例 N3 | `E:13.6` | pass | 拒绝 |
| P-033 | 补充 | `Z:13.57` | pass | 拒绝 |
| P-034 | 补充 | `E:-13.57` | pass | 拒绝 |
| P-035 | 补充 | `E:14` | fail | 拒绝 |
| P-036 | 业务负例 B1 | `E:41.66` | fail | 拒绝 |
| P-037 | 业务负例 B2 | `E:16.63` | fail | 拒绝 |
| P-038 | 业务负例 B3 | `C:131.20` | fail | 拒绝 |

## 五、构造项（P-039..P-060）

| pool_id | 语料 | 类型 | 判读对象 | gold |
|---|---|---|---|---|
| P-039 | HJ-001 | ruling | q2697 维持兼容分口径+不用于能力归因 | pass |
| P-040 | HJ-003 | ruling | {card_scheme} 系题面笔误、按 ACI A–G 判读 | pass |
| P-041 | HJ-004 | ruling | 无匹配费率静默按 0 计并宣布最优 | fail |
| P-042 | HJ-005 | ruling | 未声明聚合口径给结论／反向凑金标 | fail |
| P-043 | HJ-008 | ruling | B13 legs 精确键集应并入出收紧版 | fail |
| P-044 | HJ-009 | ruling | gate v2 not_executed 恰名白名单并入 | pass |
| P-045 | HJ-015 | ruling | L6-A 两键并入+篡改元数据必拒 | pass |
| P-046 | HJ-018 | ruling | 收据 files_sha256 含自身→violation | pass |
| P-047 | HJ-020 | ruling | 缺 plan-dir/binding 应 fail-closed 拒绝 | pass |
| P-048 | HJ-032 | ruling | B2 多余键/SQL 注释走否决通道判 0 | pass |
| P-049 | HJ-033 | ruling | B8 stderr 披露式：stdout 正确应判过 | pass |
| P-050 | HJ-034 | ruling | B12 距离整数化按容差 0 应判红 | pass |
| P-051 | HJ-035 | ruling | B14 leg 缺 cargo_on_board_lbs 判 0 | pass |
| P-052 | HJ-036 | ruling | B13 整项（顶层+legs）应并入 | fail |
| P-053 | HJ-037 | ruling | B13a/B13b 拆分处置应执行 | pass |
| P-054 | HJ-042 | ruling | 夹具替换历史分数影响=0 无需重判 | pass |
| P-055 | HJ-068 | final_adjudication | tb 失败定性产品内容门+第 5 槽不再尝试 | pass |
| P-056 | HJ-013 | correction_chain | cache finding 自 mapping v2 起撤销 | pass |
| P-057 | HJ-022 | correction_chain | r1 收据跨 pin 复算设计误→废止 | pass |
| P-058 | HJ-023 | correction_chain | r2 收据冻结副本错位→废止 | pass |
| P-059 | HJ-024 | correction_chain | r3 收据部分世界复判→废止 | pass |
| P-060 | HJ-025 | correction_chain | r4 收据树内 binding 代际错位→废止 | pass |

## 六、未入选与剔除清单（如实登记，宁少不凑）

1. **类型配额未入池（可构造但未选）**：correction_chain 其余 8 条 HJ-026/027/031/038/044/064/065/066——证据公开可构造，但类型配额 5 条已满、按语料序前五入选。
2. **低优先级类型不选**：replay_golden×9、revision_fixture_positive×2、revision_fixture_near_miss×2（HJ-011/017）、selftest_positive×3、other×4、context_only×6——封闭优先级规则下低于已选类型且配额已满；HJ-006 按任务指令以拆槽入池不占配额。
3. **不可忠实构造剔除**：0 条（本环未出现金标不在公开证据中、需解释推断方能构造的条目）。
4. **拆槽缩减**：0 条（HJ-069 11/11 槽、HJ-006 10/10 探针均有独立可判金标）。

### 转写声明

- P-004 case 与 gold_provenance.quote：原裁定文本含本地私档备份库根目录名，转写以〈本地私档备份根目录名隐去〉占位（去路径转写，非原文逐字）。
- P-057..P-060 gold_provenance.quote：counts 为收据逐字字段；失败断言明细含本机临时目录绝对路径，不入 quote，以 case 内去路径转写描述替代。
- P-016 case：run_id 产品段 workbuddy 系 W 批模板段名忠实转录，批次 README 已声明产品身份以目录为准。
- P-012/P-014/P-015 case 与 review_basis：其中 /tmp/* 系被评运行越界写入行为的轨迹事实，逐字转录自被引公开证据（r20261031-wb-formal 轨迹与裁定文件），非本机隐私路径（L39 验收 auditor I-1 补登）。
- quote 口径（发射组装须知）：quote 分两类——行引逐字与按上述声明口径的忠实转写；转写类 quote 不得作为逐字原文引用，须按其声明口径表述，逐条口径判定方法见 §七（L39 验收 auditor I-2 补登）。

## 七、自检（脚本实测）

- [PASS] 总数=60——60
- [PASS] pool_id 唯一且连续 P-001..P-060
- [PASS] construction 三值枚举——{'direct': 17, 'split': 21, 'built': 22}
- [PASS] labels 统一 [pass,fail,uncertain] 且 gold 在内——{'pass': 47, 'fail': 13}
- [PASS] 每条 gold 有 gold_provenance(path,locator,quote 非空)
- [PASS] 每条 evidence.path 存在于公开仓且 sha256 实测一致
- [PASS] 行引类 quote 逐字可回溯（JSON 转写类单独核对）
- [PASS] direct 17 与语料 direct_test_item 一致且不重复计条
- [PASS] 拆槽 21=HJ-069×11+HJ-006×10
- [PASS] 构造 22 条与 meta 清单一致且不与 direct/拆槽源重叠
- [PASS] 隐私扫描：产出不含用户主目录绝对路径
- [PASS] 隐私扫描：产出不含私档备份库根目录名字样
- [PASS] 隐私扫描：产出不含本机用户名
- [PASS] 隐私扫描：产出不含系统临时目录前缀
- [PASS] 隐私扫描：产出不含系统私有根路径前缀
- [PASS] 隐私扫描：产出不含收据临时目录特征路径

自检说明：行引类 quote 由脚本按行号从源文件逐字提取；JSON 字段转写类 quote（integrity/wb 终审/批次行/额度行/探针收据/VOIDED counts）为字段值忠实转写， locator 指向字段；隐私扫描覆盖用户主目录绝对路径、私档备份库根目录名、本机用户名、系统临时目录等字样。

## 八、判读力注记（如实）

- HJ-069 十一槽逐槽判定原样保留（10×launch_infra_invalid + 1×launch_failed，gold 全 pass）：逐槽 verdict 取值无成文判别口径，判别力弱，为忠实覆盖裁定逐槽判定如实保留设计。
- HJ-006 十探针按现行兼容轨出题（gold 6 pass/4 fail）；严格轨判定逐行保留于 gold_provenance.quote，不单列测项。
- gold 语义：pass=对所问判断的肯定；fail=否定；uncertain=无法确定（本池无 uncertain 设计位）。
