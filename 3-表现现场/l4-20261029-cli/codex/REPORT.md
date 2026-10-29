# REPORT — L4 Codex 六槽（l4-20261029-cli/codex）

- 执行者：builder-codex；阶段 I（实现+零模型预检/合成测试）完成时刻：2026-10-29T20:2x+08:00（实钟见收据）
- 设计封印 D：`bb14897a7d1ac26c06697bb80a15d94158cd8ae0`；计划/合同：`1-评测方案/自动循环L4-2026-10-29/{plan.json,contract.json}`
- 状态：**阶段 I 完成，停待 E 封印 + lead 释放**。真实模型调用 0 次（此句仅指各轮 selftest/preflight 进程自身未发模型调用；阶段 I 整体含一次已知事故出站请求，见下方 Incident 记录——DeepSeek provider 请求未知）。

## 文件清单

| 文件 | 说明 |
|---|---|
| `tools/lab.py` | 六槽 runner 主入口：preflight/prepare/run/judge/dual-archive/status/selftest |
| `tools/dual_archive.py` | legacy/current 双归档离线反事实投影（equivalent_simulation 标注，母本 write-once） |
| `tools/selftest.py` | 合成自检（socket 哨兵禁网，零凭据读取） |
| `config/codex-config.toml` | E 候选配置快照（隔离 CODEX_HOME，与 r1031 语义一致；E 后不许改） |
| `preflight/codex-preflight.json` | 零模型预检收据（model_calls=0，ok=true） |

## 槽位（全部读自 plan.json，禁止自造）

6 槽：dab/cargo × rep1..3，order 1–6（rep1 dab→cargo，rep2 cargo→dab，rep3 dab→cargo），timeout 1800/2400 按 plan。stratum=`cli_current_sentinel`，模型 deepseek-flash low，路由 api.deepseek.com wire responses。

## 阶段 I 测试计数

`tools/selftest.py`：**73/73 PASS**（socket 哨兵全程禁网；不读凭据）。
新增：E-blocker 负例（超时孙代工具持续写入→进程组 TERM 送达+行为学写入停止+termination.json 收据；沙箱拒组探活如实披露 limitation）、slot claim 重复调用零额外 Popen、真实 validate_meta/classify 组件（gate.load_runner_validator：mock ok-meta=pass；transport-error meta=selection null+非空 diagnostic 真值表）。证据名对齐 builder-dsh 契约 C：prompt.txt/agent.jsonl/agent.stderr.txt/agent-session//workspace//checker.stdout/score-receipt.json（固定格式 D：earned/possible/reported 8dp=round(earned/possible*100,8)，possible==contract.denominators）。覆盖：plan 槽位不变量（6 槽/顺序/用例集/自造槽拒绝）、write_once 非破坏、gate fail-closed 全家族（binding 缺失/gate 缺失/gate 拒绝/未释放/plan 哈希不符）、prompt 路径内嵌+sha 稳定、usage 四态 presence（missing/null/zero/positive，对齐 lead 源码勘误：r1031 `or 0` 合并缺陷不在 L4 复现）、双归档投影（legacy 无流=r1030#1 复现、current 全量、equivalent_simulation 标注、母本不动）。

## 零调用证明

1. `preflight` 收据 `model_calls: 0`；
2. `run` 命令实测（E 前）：exit 3，`{"fail_closed": true, "reason": "runtime-binding.json 不存在…"}` —— gate 检查先于 `load_api_key()` 与任何网络路径；
3. selftest 全程 socket 哨兵（任何联网尝试即断言失败）；
4. 全工具无其他网络出口（唯一 `http` 路径在 cache 探针侧且同样 gate 前置）。

## 命令接口（E manifest 入口）

- 主入口：`3-表现现场/l4-20261029-cli/codex/tools/lab.py`
- 子命令：`preflight` / `prepare <slot>` / `run <slot>` / `judge <slot>` / `dual-archive <slot>` / `notexecuted <slot> <reason> <stop_source>` / `status` / `selftest`
- runtime 源码与实际配置（须 E 封印覆盖）：`tools/lab.py`（sha256_8=91f527ed）、`tools/dual_archive.py`（sha256_8=5935e127）、`tools/selftest.py`（sha256_8=91254333）、`config/codex-config.toml`（sha256_8=bc70bc91）

## 执行语义（E 后）

- 门：binding 存在 + `released_for_model_calls=true` + plan/contract SHA 实算一致 + `gate.verify_execution` 通过，四者任一不满足即 exit 3 fail-closed；
- `registered_at` = binding 值（==E 提交时刻），meta 落盘且断言早于 started_at；
- 每槽全新仓外工作区 `~/bench-workspaces/l4-20261029-cli/codex/<slot_id>/`；whole-execution restarts=0（无整 CLI 重启/无 transport-retry 重启），status ∈ {ok, timeout, infrastructure_error} 与能力失败（`capability_failure` 字段）分开；timeout 按 plan 值停进程留部分产物按冻结 checker 全分母判卷；
- 原始证据母本 write-once（stdout/stderr/session/prompt/产物/meta/config），双归档投影在沙箱副本执行，母本哈希前后比对；
- 判卷：机械执行冻结 checker（contract 锁字节），runner 不读 truth/solution；超时/中断用 start_new_session+进程组 TERM→有界等待→KILL 清理（组信号被环境拒时回退直接子进程并如实披露），termination.json 先于评分持久化；timeout 准入分支带 timed_out=true+全套原始证据+全分母收据（builder-dsh 契约 E）；infra error/transport-error 恒 selection=null+非空 diagnostic 不折满；CODEX_HOME config.toml 与 E 候选快照逐字节强制比较，漂移即 fail-closed 停槽。

## Incident 记录

- INCIDENT-20261029-mock-real-codex-launch（独立记账：interface_preflight incident / accidental CLI start；不占 35 固定槽位、不评分、不计合成 pass）：
  - **整个阶段 I 口径**：因本事故，阶段 I 期间真实请求数 = **未知**（已知 chatgpt.com plugin-warm 出站 1 次 401；DeepSeek provider 请求未知、倾向未发生）；原始流灭失，证据等级 **incomplete**，不重建伪原件。
  - **最终修复轮口径**：最终 selftest（60/60，CODEX_BIN 桩注入）自身零真实请求——此句仅限该轮，不追溯覆盖事故运行。
  - 详见 `incidents/INCIDENT-20261029-mock-real-codex-launch.md`（含原句保留+dated 更正）+ `incidents/incident-receipt.json`。修复：CODEX_BIN 常量注入 + mock_never_real_codex 守卫。

## 已知限制与披露

- prompt 内嵌工作区绝对路径：跨槽路径不同为设计内显式保留混杂（预注册 §3B）。
- 双归档为 equivalent_simulation（非历史 pipeline 原样调用），适配 diff 逐条在 `projections/*/ADAPTATION.json`；legacy 投影如实复现 r1030#1 流丢失。
- CLI 进程内部不可观察 HTTP 重试：如存在则披露为不可观察（无外部可见计数手段）。
- 首失败修正（lead 审查，FIRST-FAILURE-close-process-group-esrch）：close_process_group 曾把父收割后 getpgid ESRCH 误推「组必消失」——已改为 Popen 启动时保存权威 saved_pgid（子即组长），父侧 getpgid 失败不替代 killpg(saved_pgid,0)，无组身份即 verified=false；receipt 身份统一 slot_id/run_id/event_id/pid/saved_pgid/attempt.pgid。OS 层手动复现证实语义正确：TERM(被忽略)→SIGKILL→killpg0 ESRCH；孤儿组回归出现「SIGKILL 调用返回成功但计数器仍写」——**根因 unknown/待 judge**（不得预设沙箱静默 no-op 定性；候选：monkeypatch 未还原/写者实际 PGID 归属不符/子 setsid 逃组[代码显式 False]/旧产物残留；judge 取证清单见 incidents/first-failure/）；行为断言记 WARN 待真实 runtime 按原判据复验；verified=false 纪律不受影响。缺陷版 42df0400 已冻结于 incidents/first-failure/。
- 进程组探活 PermissionError 属 DSH bash scope 限制而非机器性（lead 零模型探针 L4计划/selftest/process-group-interface.json 证实 killpg0→TERM→ESRCH 全通）：close_process_group 两分支齐备——探活可行即 verified=true 正常准入；EPERM 恒保守 verified=false+停批不绕过；最终 runtime 按实际证据判。

### 孤儿组回归 judge 取证清单（2026-10-29 追加；仅叙述，不改源）

- 现象：selftest 孤儿场景中 close_process_group 对 saved_pgid 先 TERM 后 SIGKILL，两次 killpg 调用均无异常返回，但计数器文件在闭合后仍增长（16→89 字节）。
- 根因定性：**unknown，待 judge**。不得记为「沙箱静默 no-op」机器事实。候选解释（judge 复验方向）：
  1. 测试 monkeypatch 未还原（本轮 selftest 全程挂 socket 哨兵；os.killpg 为未 patch 的 os builtin；time/sleep 未 patch）；
  2. 写者实际 PGID 归属与 saved_pgid 不符（归属需在 judge 环境以 ps/jpid 实测）；
  3. 子进程 setsid 逃组（fixture 显式 start_new_session=False，代码层面未见逃组，仍列候选）；
  4. 旧 writer 产物残留（本轮 counter 文件为当轮 tempfile 新建路径，此项基本可排除，仍列全）。
- 取证数据（当轮 receipt）：saved_pgid=27015（=helper pid，start_new_session=True 使 helper 为组长）；helper Popen 显式 start_new_session=True；inner 由 helper Popen 显式 start_new_session=False 派生；term_delivery="delivered+SIGKILL"；probe="still_alive_after_kill"；ack_at=2026-10-29T21:35:25+08:00；counter fixture=当轮 tempfile `td/orphan.out`（轮末已随临时目录清除，路径模式 `<tmp>/orphan.out`）；os.killpg 为 os 模块原生 builtin（源码未包装）。
- 对照组：手动 OS 复现（同一机器、同构 fixture、无 selftest 套件）TERM→SIGKILL→killpg0 ESRCH、写入停止，全通过——差异聚焦 selftest 运行上下文，judge 可对照。
- 处置：verified=false 为诚实结果；行为停止断言记 WARN，不占合成 pass；judge 于真实 runtime 复验。
