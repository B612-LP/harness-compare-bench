# 自动循环 L2 预注册 —— 契约与证据链卫生

- 循环：L2（自动迭代第 2 轮）；lead：lead（DSH 主 agent）
- 预注册落盘时间：2026-10-29 15:49+08:00（实钟；D4 教训：时间标签一律落盘时刻，事件以 git 提交哈希锚定）
- 输入：L1 验收报告问题池条目 ①②③④⑤（[ACCEPTANCE.md §四](<../自动循环L1-2026-10-29/ACCEPTANCE.md>)）
- 排除项及理由：⑥（provider-cache 语义请求级验证 + runner 代际 spread 消融）需真实模型调用与新增运行，独立成轮；⑦（WorkBuddy 正式批次）需批次级 slots 规划，独立成轮。两者保留问题池，优先级不变。

## 一、循环定性：零模型调用闭环

本循环全部工作为离线操作——历史回放执行、冻结合同构建、校验器开发与自检、文档勘误——不调用任何模型 API、无 token 消耗、无新增产品运行。执行中如发现某包必须调 API 才能完成，立即停止该包并按未知登记披露，不得即兴扩大范围。

## 二、总则（防过拟合闸，沿用 L1，不豁免）

1. 本预注册先于一切包工作；封印 = 本文件首次 commit+push 的哈希。封印后修改走 AMENDMENT 显式程序（勘误动机 + 时间线 git 锚定）。
2. 无重试纪律：回放/构建/测试均为确定性本地操作；因环境故障重跑须在收据 `corrections` 记录重跑事件；禁止对「结果不满意」重试。
3. 合同继任语义：freeze-20261029-v2 仍是 r1030 正式批次（官方表 10 行）的合同记录；v3 是后续批次的治理继任者，不得改变任何历史分数、准入裁定或 v2 目录任何字节。
4. 历史文档修改一律 dated 勘误框：原句保留、勘误增量、日期实钟；禁止静默改写。
5. 关键时间点以 git 提交哈希锚定，不写预写的未来时刻。
6. 完全分账：包A 事件归 `grading_regression`；包B 自检归 `self_test`、judge 六账重算归 `offline_recompute`；包C 自检归 `self_test`；包D 为记录修正，不入六账、入循环台账。L2 新事件全部登记进 v3 活台账（见包B），由执行者本人登记，lead 不代写。
7. 结论一律五段结构（观察—证据—解释—未排除因素—可复现实验）；本轮无新增模型运行，不产生任何排名主张。

## 三、包A：判卷历史回放补证（盲审 D3）

- **问题**：[AUDIT.md D3](<../../5-评测报告/对抗性盲审-2026-10-29/AUDIT.md>)——2026-10-27 收紧批的「B13a 并入后 24 场历史回放 flipped=0」收据（`replay-results.json`）的 after 轨实为 B13a 并入前 cargo 字节 `70acdbb7…`；现行合同 cargo checker 为 `d84b1111…`。B13a 合同从未直接跑过 24 场回放。另 README §4 表 `ledger_match 15/24` 与 19:28 刷新后 JSON 的 16/24 不同步。
- **方法**：新建 `replay_b13a_2026_10_29.py`（**不改动** `replay_2026_10_27.py` 及其收据），协议完整继承原脚本：回放对象 = 运行总账 case∈{bird, lcb, cargo} 且 eligible 且 run_dir 在本机的行；历史现场只读；判分在 /tmp 临时副本进行（canonical 输入重组协议）。after 轨 = 现行 `2-用例/<case>/checker.py` 字节：bird `994be0b3…`、lcb `63845361…`、cargo `d84b1111…`（封印前实测 SHA-256 前 8 位）。before 轨不变。
- **产出**：`replay-b13a-results.json`（收据含逐场产物 SHA、before/after 明细、ledger_match、after 轨三 checker SHA 自证）；README 补充段与 §4 表 dated 勘误（「已刷新」表述更正为指向 B12/B14 合同回放 + 本收据；15/24 更正为 16/24 并注明属旧收据）。
- **验收标准**：n_replayed=24 与旧收据一致；逐场记录齐全；after 轨三 SHA 与上述一致；勘误框日期实钟、原句保留。
- **停止条件**：任一历史有效场翻转（reward 或 weighted 变化）→ 立即停止该包，报 lead：B13a 违反硬闸门，走回退或版本决策，进验收报告，不静默处置。
- **禁读边界**：builder 不得读取 `2-用例/*/truth.json` 与 `solution/`；checker 调试仅允许 `--selftest` 或对历史产物判分（脚本机械复制 canonical 输入，不经手答案内容）。
- **write-scope**：`4-打分细则/判卷审计-2026-10-27/checker-tightening-B2-B8-B12-13-14/`；分账：`grading_regression`。

## 四、包B：冻结合同 v3（盲审 D2 + 问题池⑤）

- **问题**：① v2 config `work_registry.path` 指向 v1 台账，v2 registry 追加的 7 条收据（5×`work:r1030-selftest-*` + `work:r1030-cli-preflight` + `work:wb-admission-preflight-20261029`）未进机读六账（v2 six-ledgers self_test=8、interface_preflight=11 均不含）；② freeze.lock 的 pin 无类别之分，叙述性活文档（如准入预检 README）与合同要素同列，L1 合并后 sweep 的 sealed-drift 事件即源于此。
- **方法**：新建 `4-打分细则/可信冻结-2026-10-29-v3/`（由 v2 目录复制派生，**v2 目录字节零改动**）：
  1. `freeze.py`：`RULE="freeze-20261029-v3"`，`BASE`/`OUT` 指向 v3 路径；六账构建新增 work_registry 事件并入（config `work_registry.path` → v2 台账，SHA `27974b75…`）：selftest→`self_test`、preflight→`interface_preflight` 固定映射，按 event_id 去重；lock pins 增 `pin_class ∈ {contract, live_doc}`——凡直接作为判分/准入输入的文件=contract，人类叙述文档=live_doc；verify 语义：contract pin 漂移=硬失败（exit≠0，现状不变），live_doc pin 漂移=输出 `live_doc_drift` 列表且 exit=0（封印纪律上仍以「还原+旁挂」为操作规范，v3 README 写明）。
  2. v3 活台账 `work_registry_live.json`（append-only，L2 起新事件入此账），pin_class=live_doc。
  3. `test_freeze.py` v3 扩展：(i) 7 收据入六账；(ii) live_doc 漂移→exit0+列表；(iii) contract 漂移→失败。全部测试通过。
  4. config-schema.json 同步 pin_class 与活台账字段；构建产物输出 `5-评测报告/可信冻结-2026-10-29-v3/`。
- **验收标准**：v3 build 成功、verify `ok=true`、test_freeze 全过；six-ledgers v3 含上述 7 个 event_id（总数=旧数+去重后新增数，builder 报告实际值）；v2 目录 `git diff` 为空且 v2 verify 仍 `ok=true`；v3 README 写明继任语义（v2 仍为 r1030 合同记录，v3 供后续批次；v3 不重新准入任何历史行）。
- **停止条件**：若 v3 构建需要改动 v2 任何字节，或 freeze.py 无法在不改 v2 的前提下复用 → 停止，披露并提出替代方案。
- **write-scope**：`4-打分细则/可信冻结-2026-10-29-v3/`、`5-评测报告/可信冻结-2026-10-29-v3/`；分账：`self_test`。

## 五、包C：runner schema v2 规范与校验器（judge D1/D2/D5）

- **问题**：r1031 判读发现——D1：全批无 `registered_at`，注册先于运行只能锚点级间接佐证（lead 已裁决不回填，字段列为下一轮 runner 必备）；D2：codex 收据 `reported` 2 位小数 vs r1030 口径 8 位；D5：dsh meta 缺 `selection/attempts/stdout_bytes` 等、`transport_retries` 列表型 vs codex 整型。
- **方法**：新建 `1-评测方案/工具链/runner-schema-v2/`：
  1. `SCHEMA.md`：必备字段集以 r1031 codex 侧为基线对齐——新增必备 `registered_at`（ISO8601 带时区，值=预注册封印提交时间戳引用；校验 `registered_at < started_at` 且 ≥ 封印时刻）、`preregistration_commit`；dsh 侧补齐 `selection/attempts/stdout_bytes/stdout_sha256/stderr_bytes/stderr_sha256`（`archived_stdout` 保留为 dsh 特有映射字段并注明）；`transport_retries` 统一整型（明细可另列 `transport_retry_events`）；机读 `reported/weighted` 唯一精度 = 8 位小数（展示层可另列 2dp）。每字段注明动机锚点（D1/D2/D5）。
  2. `validate_runner_meta.py`：`--spec` 模式对合成 fixtures 自检；`--retro` 模式对 runs 目录只读产出兼容矩阵。
  3. `retro-r1031-matrix.json`：r1031 20 场只读扫描的 delta 报告（预期：registered_at 缺 20/20、dsh 缺字段 10/10、transport_retries 类型 dsh 10/10 list、codex 2dp 收据 2 场）。**该矩阵是披露，不是对 r1031 的追溯判定**（D1 已闭项）。
- **验收标准**：fixtures 自检全过；retro 矩阵数字与 judge 独立抽查一致；SCHEMA 每字段含动机锚点。
- **停止条件**：若 retro 发现 schema 与 r1031 实际字节语义冲突 → 披露，不现场改历史产物。
- **边界（显式 unknown）**：lab.py 实跑集成不在本包，留待下一真实批次预注册；本包交付的是规范+校验器+模板级 fixtures。
- **write-scope**：`1-评测方案/工具链/runner-schema-v2/`；分账：`self_test`。

## 六、包D：r1030 记录勘误（问题池④）

- **问题**：[r1030 README](<../../3-表现现场/r1030-formal-a1/README.md>)「归档缺陷披露」节称 `tools/lab.py 已修（日志经 staging 移动）`——经 r1031#1 证伪：rmtree（:308）先于 staging 移动（:317），该修复未生效；实际生效修复是 r1031 `tools-dsh/lab.py` 的结构性修复（日志自落盘起即入 staging）。
- **方法**：在该节下加 dated 勘误框：原句保留，注明「已修」声明不成立及生效修复的真实位置，指针到 r1031 批次 README 与 meta.corrections。阶段报告-v4.1 经查无此传导（封印前 grep 验证），不涉及。
- **验收标准**：勘误框日期实钟、原句保留、指针可达。
- **write-scope**：`3-表现现场/r1030-formal-a1/README.md`；不入六账。

## 七、角色与隔离

| 角色 | 成员 | 包 | 上下文 |
|---|---|---|---|
| builder-a | builder-dsh（复用） | 包A + 包D | 有 L1 历史（判卷链熟悉，利大于弊） |
| builder-b | builder-codex（复用） | 包B | 有 L1 历史 |
| builder-c | builder-schema（新建） | 包C | fresh |
| judge | judge-l2（新建） | 独立验收全部包 | fresh，只接受本预注册的验收标准，不接受 builder 主张文本 |
| auditor | auditor-l2（新建） | 敌意盲审全部交付物 | fresh，独立重放/重算，输出分级 {blocking, defect, observation, note} |

- builder 只交付事实与产物，不写分析结论；分析结论归 judge/auditor/lead（L1 口径）。
- judge/auditor 的验收依据 = 本预注册条文 + 仓库现存收据；发现 builder 未申报的问题按分级入账。

## 八、循环流程与停止

封印（本文件 commit+push）→ 三 builder 并行执行（write-scope 不相交）→ judge 独立验收 → auditor 敌意盲审 → lead 五段结论验收报告（`1-评测方案/自动循环L2-2026-10-29/ACCEPTANCE.md`）→ PR（本分支 `loop2-2026-10-29`）→ **停止，等用户放行**。lead 是唯一 git 操作者，提交一律显式路径，不用 `git add -A`；里程碑积极提交。

## 九、已知未知登记（老师④格式：影响/下一步/停止条件）

1. **lab.py 实跑集成未验证**：包C 交付规范+校验器，模板未经真实 API 运行检验。影响：schema 可能在真实批次暴露工程缺口。下一步：L3 预注册时集成并入首次真实批次验收。停止条件：集成完成或 schema 废弃。
2. **live_doc pin 报告制是否足够**：live_doc 漂移降为报告不阻断，可能弱化叙述文档的封印力。影响：封印纪律依赖操作规范自觉。下一步：auditor 本轮敌意评估该设计；L3 依据评估结果决定是否收紧。停止条件：出现一次因报告制导致的证据链断裂 → 收紧为硬失败。
3. **⑥⑦ 未入本轮**：cache 语义与 runner 代际消融、WB 正式批次仍开放。影响：r1031 spread 归因中 runner 代际因素未消融。下一步：L3 候选。停止条件：消融实验完成。
