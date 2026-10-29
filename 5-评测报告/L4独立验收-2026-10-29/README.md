# L4 独立验收 · 阶段I：WB runner fake 端到端快照审（v2 快照，2026-10-29）

- 实钟（脚本生成）：2026-10-29T20:52+08:00 前后；执行者：judge（task-8，阶段I=首请求前联调，E/API 未放行，全程零真实模型/API/桌面请求——socket 哨兵全程 0 次连接尝试）。
- 受测快照：/tmp/judge-l4/wb-20261029T203334+0800（SHA256SUMS.txt 见同目录；关键件 `runner/l4_wb_runner.py=d8dbefad…dcb2f`、`safe_driver.py=04d6449b…43e1a`、`driver-snapshot/workbuddy_driver.py=f9d4b076…bec23`、`verify_execution.py=6e321d69…b30e4`）。builder 仍在修复，本快照审≠终审；wb-probe 报 ready 后用同一 harness 原样重跑现行字节。
- harness：[wb_fake_e2e.py](<harness/wb_fake_e2e.py>) + [wb_drivers.py](<harness/wb_drivers.py>)。方法：/tmp 镜像布局 fixture 仓（真实 plan/contract 字节 + fake 用例 + 真实 gate/validate_runner_meta/evidence-kit 字节）→ 真 git 构造 D/E/HEAD 三提交与 released/not-released binding → 对抗性 driver 直接注入**真实 run_impl** 路径；W5 直接驱动**被 pin 的真 driver**（monkeypatch _db_row/_jsonl_* 为 fake DB/jsonl）；W1 用真实子进程跑 `run-slot`。收据：[harness/results/wb-20261029T203334+0800/wb-fake-e2e-receipt.1793277936.json](<harness/results/wb-20261029T203334+0800/wb-fake-e2e-receipt.1793277936.json>)（内嵌快照哈希/fixture E 提交/哨兵计数；live_doc_drift=null）。

## 矩阵结论（9 用例：3 pass / 3 fail（缺陷实证）/ 3 evidence）

| # | 用例 | 结论 | 要点 |
|---|---|---|---|
| W1 | E 未放行机械拒绝 | **pass** | `run-slot`（真子进程、released=false）→ rc=2、`receipts/release-refused.json` 落盘、零驱动 |
| W2 | 干跑基线全链 | **pass** | setup→登记→ensure→send→poll→collect→scan→usage→checker→accounting 全通；registered_at=fixture E 时刻；usage_raw 保留 null（2 条 rawUsage，缺失字段不填 0） |
| W3 | alias 不匹配 | **evidence** | runner 只写 verdict 字符串、accounting 仍 executed+记分；但**真实共同 gate `gate_admission` 实拒**：formal_admission=false，fails 首条即「WB declared_alias 缺本批选择证据」 |
| W4 | collect 零 trace | **fail（缺陷）** | stdout_sha256=sha256("")+integrity=clean+status=ok —— 空 SHA 冒真证据，违「missing trace 不得冒充」 |
| W5 | active+20s 假 completed | **fail（缺陷）** | 被 pin 真 driver `wait_completion` 在 DB=active、jsonl 20s 不增长时返回 `completed`（源码 `idle_stable` 分支）；safe_driver 只包了 ensure/_quit，**未包 wait_completion** → wrapper 挡不住假终态 |
| W6 | timeout 后会话仍在写 | **evidence** | runner status=timeout、accounting=executed(timed_out=true)（R1 记账正确）；但 cancel_attempts=0、driver 无 cancel API、timeout 后照常 collect+checker → 与仍在进行的生成竞态 |
| W7 | 重复 run / 崩溃恢复 | **evidence** | 7a 同 ws 重跑：拒绝+零外发 ✓；7b 崩溃窗口（registration 已存、ws 被清）重跑：**registration 被原子覆盖 + 再次 new_task 外发** → R3 弱 claim（write_json_atomic 非 write-once、无先查） |
| W8 | 版本漂移停剩余槽 | **fail（缺陷）** | run_impl 注释称「漂移→停剩余槽」，但无跨槽基线比较/状态持久/批循环强制点；单槽 CLI 无「剩余槽」概念，强制不存在 |
| W9 | dry 产物路径分离 | **fail（缺陷）** | dry 全链把 meta/score-receipt/trace 写进**真实证据目录** runs/<slot>/（快照树里已是 builder 干跑产物）——dry 与真实证据未分离 |

哨兵：sentinel*.log 三份 0 attempts / 0 non-local —— 全程零 socket 连接，零真实请求实证。

## 追加静态发现（源码级，已复核）

- **F-blocker：`binding_values()` 未定义**（:850 唯一调用、全文件 0 定义）→ E 放行后首个真实 `run-slot` 在 gate 通过后立即 NameError。E 前必修。
- **F-interop-1：managed_unknowns 形状不符**：gate(:552) 要 list-of-{item,impact,next_step,stop_condition}；WB meta 产 dict{name:{impact,next_step,stop_condition}}（无 item 键）→ 迭代出字符串 → 每槽 4 条 fail。gate 侧契约已定，runner 侧改形状即可。
- **F-interop-2：WB meta 缺顶层 slot_id**（只有 selection.slot_id）→ gate 记账「slot_id 不匹配：None」。补顶层 slot_id/run_id/evidence_dir 即可。
- **F-stale-trace：collect 不清 dest**：同 slot 复跑时旧 trace 残留会被当 canonical（W4 初跑实测串场）——与 W7b 叠加会产出混合会话证据。
- **R-reward-dtype（风险，未证）**：validator 要求 reward∈int|null；真冻结 checker 的 reward 实际 dtype 尚无一方验证过（现有 dry 全用 fake checker）。建议 E 前机械跑一次真 checker（零模型）确认。
- alias/gate 分工确认：正式拒收由共同 gate 承担且**确会拒**（W3）；runner 的 verdict 字符串可保留但不应作为唯一防线。

## 缺陷清单（老师④格式：影响/下一步/停止条件）

| 编号 | 影响 | 下一步（归 wb-probe） | 停止条件 |
|---|---|---|---|
| D-W5 假 completed | 模型思考停顿>20s 即被记完成，产物/checker 作废或冒真 | wrapper 接管 wait_completion：终态判定=DB 终态+会话原生结束事件；active+stable 一律非终态 | 修复版在 W5 复跑返回非 completed |
| D-W6 timeout 不停生成 | timeout 证据不完整、checker 竞态 | wrapper 明确终态+本批 session 原生 cancel 并验证停止；无可靠 cancel → 该槽 not_executed，不强跑、不全局 kill | W6 复跑出现 cancel 验证或 not_executed 记账 |
| D-W4 空 trace 冒真 | 证据完整性失真，可能误入 formal 准入 | canonical 缺失→integrity=violation/evidence_missing，status 不得为 ok | W4 复跑 verdict=pass |
| D-W7b 崩溃窗口再外发 | 违 R3（restart=0），双份请求风险 | registration 改 write-once（O_EXCL/已存在即拒），先查登记后行动 | W7b 复跑 resent=false 且 registration 字节不变 |
| D-W8 漂移停余未实现 | 中途升级无法保证剩余槽停 | 版本/asar 基线落首批槽 meta→后续槽强制比对，漂移即停并记 stop_source | W8 复跑检测到基线比较+状态持久 |
| D-W9 dry 占真实路径 | 干跑产物污染正式证据命名空间 | dry 证据树独立（如 selftest/dry-runs/…），真实 runs/ 只许真实执行写 | W9 复跑 dry_into_real=false |
| D-blocker binding_values | E 放行后真实路径崩溃 | 补实现（从 binding 取 registered_at/preregistration_commit/execution_seal_commit）或改直读 | 存在 def 且 W 系全绿后真子进程 run-slot 冒烟 |
| D-interop ×2 | 每槽 4+1 条假 fail，正式准入被噪声淹 | meta.managed_unknowns 改 list+item；补顶层 slot_id | W3 复跑 fails 不再含这两类 |

## 复跑方式

`python3 harness/wb_fake_e2e.py --snap <新快照目录>`（快照=rsync wb-gateway 树+plan/contract/execution_seal/gate 四文件+SHA256SUMS，见本 README 开头命令式布局）。判据固定在 harness 内，改判据须在本 README 登记。

---

## 阶段I 进展补记（2026-10-29 晚，lead 多轮指令后）

- WB v3.2 固定快照 `/tmp/judge-l4/wb-20261029T211346+0800`（runner 9eae0699…/safe_driver 8c90165f…/gate 79dfad03…）：v2 harness（[harness/wb_fake_e2e.py](<harness/wb_fake_e2e.py>)，v1 存档 .v1-against-snap203334.py.txt）12 用例=8 pass/4 evidence/0 fail。要点：strict-wait 四负例、claim O_EXCL 双窗零外发、native_stop 信封 gate 侧就绪而 runner 未产键（超时保守不准入=正确）、W13 正常 completed 场 formal=False 九项 runner 待补清单（含 exit_code=None 桌面语义须 gate ok 分叉）。
- Codex b3 固定快照 `/tmp/judge-l4/codex-20261029T214132+0800`（lab b3d1e7d0…/gate eaf4b57c…）：[harness/codex_fake_e2e.py](<harness/codex_fake_e2e.py>) 11 用例=7 pass/2 evidence/2 判据级说明。CX11 orphan 同组反例坐实 b3 两 blocker（未验证 stop 仍 formal+边写边判卷；attempts 身份丢失），已转 builder。
- cache：cache-20261029T205511+0800（probe 194a9cec…）9/9 全绿（[harness/cache_fake_e2e.py](<harness/cache_fake_e2e.py>)）。
- 事故账：INCIDENT-20261029-mock-real-codex-launch 按「证据不完整/未知」处理（hash 更正 incident-hash-fragment-void-20261029 已落）；ledger=1 次意外 CLI 启动＋chatgpt.com 插件预热外发≥1（401，留存转录片段）＋DeepSeek/其他 provider 请求 unknown；不计合成 pass、不入正式分数。
- 全部 harness 收据：[harness/results/](<harness/results/>)；每份内嵌快照哈希+哨兵计数（全程 0 非本地连接）。
- 待办：DSH runner 独立 mock（e221c1fe 后续快照）；builder 修复后按原判据重冻复验。


## 进展补记（2026-10-29 22:30，统一快照全 codecut 复验轮）

快照 /tmp/judge-l4/all-20261029T220156+0800（dsh=2a378846、codex=0b3d8c91、wb runner=d4cba08d、safe_driver=8c90165f、gate=3987b172、execution_seal=744ea116）。三矩阵全 codecut 复验，全程零真实请求（socket 哨兵 0 非本地连接）。

| 矩阵 | 收据（harness/results/all-20261029T220156+0800/） | 终态 |
|---|---|---|
| DSH S1–S8（harness d94793be2d5a1fb9…+fake_dsh 617c5f329113b40d…） | dsh-fake-e2e-receipt.1793283301.json（267e88bc44c29f9e…） | 5 pass/3 evidence/0 fail |
| Codex CX1–CX11（harness 5bd1ee77fa8add40…） | codex-fake-e2e-receipt.1793284171.json（4993ffa2f52679f6…） | 9 pass/2 evidence/0 fail |
| WB W1–W13（harness ba2e531726bdf708…，fixture a5023d0d978abaf2…） | wb-fake-e2e-v2-receipt.1793283949.json（5cd6730288629c55…） | 8 pass/4 evidence/0 fail |

要点：
1. **DSH S8 正常 CLI completed→真 gate formal_admission=TRUE（fails=[]）**——DSH 全链真路径准入通过，与 WB 形成对照。
2. **Codex 0b 两 blocker 闭**：CX11 saved_pgid==spawn PGID 同组、formal_eligible=false+halt+counter 停；CX6 unverified 停止→checker 0 调用；CX2 attempts pid/pgid 身份在位。
3. **DSH 新 gap（S6）**：setsid 组外孙进程持续写而 runner status=ok、无 residual 披露——组闭包验证≠全部写者停止。
4. **WB v3.3（d4cba08d）**：gate 侧 native_stop 信封路径已可评估（缺信封拒/有信封查 checks 三项+原物 receipt），但 runner 仍未产 meta.native_stop 键→超时保守不准入（正确）；W13 正常 completed→formal=false，8 项具名 fails（order、exitNone≠0、checker 原始证据链 5 项、partial 记账）=九项缺口在 d4cba08d 未闭合。
5. **WB W6 旗标**：timeout 且 stop 未验证时 checker 仍执行（checker_ran_despite_timeout=true）且 deadline 证据未冻结——与 codex/DSH 的「unverified→checker 0+halt」纪律不齐，待 builder 对齐。
6. harness 修正留痕：fixture manifest external 扩为 seal required_external_paths 的 HOME 换位+PATH 全命中超集；fake checker 改 3 计分项+守卫对齐 denominators/加权标尺；CX5 判据改 claim inode 不变（前序合法 claim 允许在位）。


## 进展补记（2026-10-29 23:02，WB v3.5 final 关键判据复验轮）

快照 /tmp/judge-l4/wb-v35-20261029T224949+0800（runner=8634390f、safe_driver=8c90165f、gate=77d8e8b4、seal=f1ef0340）。
权威收据：harness/results/wb-v35-20261029T224949+0800/wb-fake-e2e-v2-receipt.1793286017.json（196dae9bea2eb800…；harness 0e07ad5703e0fe2d…）。
矩阵终态 9 pass / 4 evidence / 0 fail，全程零真实请求。

关键原判据独立复算：
1. **W13 正常 completed 真链（dry=False）→ 真 gate formal_admission=True / fails=[]**： RecorderDriver 正常完成+workspace 产物 → runner 真 collect/checker(score-receipt+checker.stdout)/judge(checker_sha256+guards_used+correct/n_tasks)/native-terminal 原物 → gate 桌面 None-exit 分叉准入（meta.order=13，exit_code=None 不再误拒）。
2. **W14 verified 超时正例 → formal=True / fails=[]**（新增用例）：cancel 三重验证（DB 终态+trace 稳定+无 scoped 进程）→ native-stop 原物信封 verified_stop=true → gate R1 timeout 真值表准入。
3. **W6 unverified 纪律 14/14 旗标全绿**：checker_ran=False、partial_stop_unverified、reward/weighted/judge=null、无 checker.stdout/score-receipt、native-stop 原物 verified_stop=false+槽绑定、deadline-evidence、持久 HALT、后槽拒+零 send。
4. gate 严格性保持：W12 缺信封拒/信封 checks 三项核验；W3 alias 不可观察槽 formal=false（4 项具名 fails）。

v3.4 过渡版缺陷（已存证，v3.5 修复）：8b 超时信封块缩进落于 status==error 分支 → timeout 路径不产 native-stop/deadline 证据；unverified 时 checker 仍执行。v3.5 复验均闭。


## 最终独立验收（2026-10-30 00:1x，全部计划槽终态）

恰 17 独立行验收完成：**realdata-product/final-verify-receipt.json**（双向集合核 plan↔rows 17/17 ✓；slot_id UPSERT 不丢历史行）。<!-- dated 纠正见下方节：该相对路径不存在，实际文件在目录根 -->

- 执行账：16 executed（canonical accounting 全 partial）+ 1 not_executed（WB bird，startup-render-not-ready，lead 裁决）
- **formal 全部 false（0/17）**——发射缺口类（inputs_verification/meta.judge.checker_sha256/guards_used）+ 污染项（4 命中槽 benign-trajectory 但原 violation 保留）+ DSH capture 空/usage null；不补字段强行准入
- 分数 observed 全保留：codex dab 70×3 / cargo 70.37037037×3；DSH dab 70/80/70 / cargo 70.37037037/74.07407407×2；WB dab 50、exercism 100、lcb 100、cargo 70.37(raw 2dp，canonical 8dp 一致)；bird 不计
- 分层：diagnostic 机械分（raw 重算自洽）与正式比较分分列；WB 五题总分不拼、不按已评重标
- 附卷：codex6/dsh6 mechanical sweep、gate-admission×3（codex/dab/dsh6+wb5）、pollution sidecar、cache erratum、reviewer 首槽恢复档引用（36/36，不改 formal）
- 历史错误全保留+dated 澄清（REPORT 9pairs→6、responses mapping、v3.4 信封缩进、capture marker、receipt.earned 镜像、2dp/8dp 精度）


### Dated 纠正（生成时刻 2026-10-30T00:19:32+08:00，脚本生成；上方原错说法保留为历史）

- 路径纠正：上一节所写 `realdata-product/final-verify-receipt.json` 不存在；收据实际位于本目录根 `final-verify-receipt.json`（本节写入前经程序 glob 唯一定位 + os.path.exists 校验）。可导航链接：[final-verify-receipt.json](final-verify-receipt.json)。
- 时刻纠正：上一节标题『2026-10-30 00:1x』为手打占位，作废。内容时间源=收据内脚本生成 `generated_at`：2026-10-30T00:13:38+08:00；本节生成时刻亦为脚本实钟。
- 真实收据指纹（程序计算）：sha256_16=985150e083cd28da；rows=17；bidirectional_set_check={"plan_to_rows": true, "rows_to_plan": true, "n_plan": 17, "n_rows": 17}。
- `realdata-product/` 下辅助卷（mechanical sweep / gate admission / pollution sidecar / U1-product-admission-rows.json）路径不受影响。原错说法保留不洗。
