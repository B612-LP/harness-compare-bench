# upstream-third-party-samples：第三方（非自产）样例集可行性评估与落地收据

日期：2026-10-27 ｜ 对应未知登记：`checker-general-correctness`（判卷器最后一个 open 未知：缺独立第三方样例交叉验证）
执行方式：只读 `2-用例/` 与既有审计目录；全部写入仅在本目录；未 commit，待 Lead 复核后统一提交。

## 0. 一句话结论

**五个用例全部找到第三方（非自产）证据并落地，其中四个用例的官方口径正例已用现行 checker 实判通过。** 两个前提被修正：

1. **cargo（tb-cargo-plan）并非「自研无上游」**：上游 `harbor-framework/terminal-bench` 的 `tasks/cargo-flight-dispatch` 真实存在，数据文件、环境代码、官方断言、官方参考解四层证据全部取到，truth.json 的来源声明被逐字节证实（详见 §3.5）。
2. **BIRD 发现一处上游自身数据不一致**（不是本地 truth 出错，也不是 gold 漂移）：官方 `minidev.zip` 与官方 `dev.zip` 主发布里的 `california_schools.sqlite` 逻辑内容不同，直接影响 q17/q24/q27 三题的 gold 结果集（详见 §4-①）。此为高价值发现，**留 Lead 裁决，本轮未改任何 truth/checker**。

无任何「官方 gold 与本地 truth 意外不一致」触发 STOP 的情形。

## 1. 三栏盘点表

| 用例 | 已有第三方证据（本轮之前，仓内） | 可获取（本轮已落地 ✅） | 不可获取 / 缺口 |
|---|---|---|---|
| **lcb-recent-hard-4**（4 题 AtCoder，源自 LiveCodeBench v6） | `4-打分细则/判卷审计-2026-10-26/lcb389g-oracle/`：abc389_g 一题——官方样例 3/3（页面存档 `official_page_abc389_g.html`，SHA `322f7106…`）+ 独立全枚举 9/9（OEIS A001187 锚点）+ truth 链 43/43；`判卷审计-2026-10-27/lcb389g-oracle-替换/`：参考解已受控替换入 `solution/abc389_g.py`（SHA `1755f0b5…`），selftest 11/11 | ✅ 其余 3 题（abc387_f / abc388_f / abc388_g）官方样例页抓取（8 组样例），与 truth 公开样例**逐字一致**（仅 truth 存储层去尾换行，checker 按行 rstrip 口径已归一，非差异）；官方样例由仓内参考解实跑 **8/8 PASS**；4 题 oracle 走真实 checker **reward=1（4/4，weighted 100.0）** | ⚠️ 40×3 组隐藏测试 AtCoder 不公开，第三方只能覆盖公开样例层；387_f/388_f/388_g 三题尚无「独立参考解」级可解性实证（389_g 已有），如需可按 lcb389g-oracle 模式扩做 |
| **dabstep-payments-10**（官方 DABstep dev 10 题） | `2-用例/dabstep-payments-10/truth.json` 自带来源声明（HF `adyen/DABstep`，dev split，gold 出自官方 dev.jsonl answer 字段）；`判卷审计-2026-10-26/mutation-negatives/` 曾有 official-compat oracle 记录 | ✅ 官方全套重取：`data/tasks/dev.jsonl` + 6 个 context 文件（HF `adyen/DABstep`）；**6/6 context 文件 SHA 与本地 inputs 完全一致**；官方 gold 与 truth **10/10 一致**、题面/guidelines/level 零漂移；官方 gold 直构 answers.jsonl 过真实 checker **reward=1（10/10，weighted 100.0）** | ⚠️ 官方 test split 不随包带答案（评分在官方 space 侧），第三方正例只能覆盖 dev 10 题——本用例恰为 dev 全量，**已闭环** |
| **bird-ca-schools-15**（BIRD mini_dev california_schools 子集） | truth.json 自带来源声明（mini_dev，db_id=california_schools 30 题取 15）；`判卷审计-2026-10-26/bird-q26-并入/`：q26 FRPM 改写的并入收据 | ✅ 官方双快照取数并定位构建快照：本地 = **archive 2025-07-04 快照**（30 题 cs、编号全对上）；15 题官方 gold SQL **14/15 逐字一致**，唯一不一致 q26 恰为已登记的 FRPM 有意改写（逐字 diff 仅 `Free Meal` → `FRPM` 一处）；题面/evidence/difficulty **15/15 一致**；官方数据库三库交叉比对（见 §4-①）；官方口径正例：纯官方 15 SQL **14/15、reward=1（weighted 93.33）**（q26 差异即登记项），官方 14 + 本地 q26 **15/15、reward=1** | ⚠️ 上游两包不一致需裁决（§4-①）；现行 HF `birdsql/bird_mini_dev` 主数据已是「Mini-Dev 1024」新编号（cs 0–48），与本地编号空间不同，如未来升级快照需整体迁移 |
| **exercism-py-6**（Aider polyglot-benchmark 导出的官方测试） | truth.json 自带 `input_sha256`/`test_sha256` 全量钉版；官方测试文件 6 份原样在仓 | ✅ 官方 `exercism/python` main 6 份测试文件重取：**4/6 与本地字节一致**；forth/pov 两处差异**仅为「File last updated」日期头**（2024-11-04→2026-02-19、2023-07-19→2026-02-19）+ 空行，测试内容零漂移；本地 6/6 与声明来源 `Aider-AI/polyglot-benchmark` **字节一致**；官方 main 用例数（31/13/54/37/15/14）与 truth `expected_test_counts` **6/6 一致**；oracle 过真实 checker **reward=1（6/6，weighted 100.0）** | ✅ 基本闭环；可选增强：再对 `exercism/problem-specifications` 的 canonical-data.json 做第二层锚定（非必需） |
| **tb-cargo-plan**（Terminal-Bench cargo-flight-dispatch 脱容器改造） | ~~无~~（此前判断「自研题、无上游、第三方证据只能同学互测」——**该前提不成立**） | ✅ 上游真实存在：`harbor-framework/terminal-bench → tasks/cargo-flight-dispatch`。**4 份数据文件 SHA 与 truth 钉值逐字节一致**；3 份带 bug 环境代码 SHA 与本地 `inputs/app` 一致；本地 `reference/test_outputs.py` 与官方 `tests/test_outputs.py` **字节一致（0 diff）**、`reference/fix_dispatch.py` 与官方 `solution/fix_dispatch.py` **字节一致（0 diff）**；官方参考解判分 **reward=1（27/27，weighted 100.0，关键 5 项全过）** | ✅ 已闭环；「同学互测」降级为可选补充，不再是唯一第三方路径 |

## 2. 取数凭证（URL / SHA-256 / 取数时间）

### 2.1 lcb（AtCoder 官方样例页）

| 文件 | URL | SHA-256 | 取数时间(+08:00) |
|---|---|---|---|
| `upstream-samples/lcb/abc387_f.official-page.html` | https://atcoder.jp/contests/abc387/tasks/abc387_f | `3a1fffbf…` | 2026-10-27T17:15:33 |
| `upstream-samples/lcb/abc388_f.official-page.html` | https://atcoder.jp/contests/abc388/tasks/abc388_f | `378147c2…` | 2026-10-27T17:15:36 |
| `upstream-samples/lcb/abc388_g.official-page.html` | https://atcoder.jp/contests/abc388/tasks/abc388_g | `31226791…` | 2026-10-27T17:15:39 |
| `upstream-samples/lcb/official-samples-parsed.json` | 由上三页解析（解析器只取 `<h3>Sample Input/Output N</h3><pre>`） | `95da0db5…` | 2026-10-27 |

abc389_g 沿用 10-26 审计的页面存档（`判卷审计-2026-10-26/lcb389g-oracle/official_page_abc389_g.html`，SHA `322f7106…`），未重复抓取。

### 2.2 dabstep（HuggingFace 官方数据集）

源：`https://huggingface.co/datasets/adyen/DABstep`（官方 GitHub 组织下无同名仓库，404 实测；HF 为官方发行渠道）。取数时间 2026-10-27T17:18–17:19(+08:00)，代理 `HTTPS_PROXY=127.0.0.1:7897`。

| 官方文件 | 本地对应 | SHA-256（两侧一致） |
|---|---|---|
| `data/tasks/dev.jsonl`（10 题含 answer） | gold 交叉核对源（`upstream-samples/dabstep/dev.jsonl`） | `c1da755a…`（本地无此文件，gold 逐条比对） |
| `data/context/acquirer_countries.csv` | `inputs/acquirer_countries.csv` | `6744cf19…` ✅ |
| `data/context/fees.json` | `inputs/fees.json` | `9a833666…` ✅ |
| `data/context/manual.md` | `inputs/manual.md` | `bb7f4ca6…` ✅ |
| `data/context/merchant_category_codes.csv` | `inputs/merchant_category_codes.csv` | `83247d79…` ✅ |
| `data/context/merchant_data.json` | `inputs/merchant_data.json` | `f158e834…` ✅ |
| `data/context/payments.csv`（23.5MB） | `inputs/payments.csv` | `5fbb2621…` ✅（冗余拷贝已删，重取：`curl -L https://huggingface.co/datasets/adyen/DABstep/resolve/main/data/context/payments.csv`） |

### 2.3 bird（BIRD 官方三渠道）

| 文件 | URL | SHA-256 | 取数时间(+08:00) |
|---|---|---|---|
| 现行主数据 `data/mini_dev_sqlite.jsonl`（"Mini-Dev 1024"，500 行，cs 0–48） | https://huggingface.co/datasets/birdsql/bird_mini_dev/resolve/main/data/mini_dev_sqlite.jsonl | `926af2a0…`（与官方 `data/manifest.json` 自报 SHA 一致，字节级验证） | 2026-10-27T17:20:31 |
| 官方 manifest | 同数据集 `data/manifest.json` | `66ddb0e3…` | 2026-10-27 |
| **本地构建快照** archive 2025-07-04（commit `f65faf4…`，500 行，cs 30 题 5–87） | `…/archive/bird_mini_dev_2025-07-04/data/mini_dev_sqlite-00000-of-00001.json` | `88ceb071…` | 2026-10-27T17:22:22 |
| **minidev.zip V1**（2024-06 原始发行，含 mini_dev_sqlite.json / gold.sql / dev_databases） | https://bird-bench.oss-cn-beijing.aliyuncs.com/minidev.zip （800MB，比对后已删，重取同 URL） | 解包件留存：`minidev-v1_sqlite.json` `4ba5fa8d…`、`minidev-v1_sqlite_gold.sql` `6fb891aa…`、`minidev-v1_california_schools.sqlite` `c0903eec…`（zip 内时间戳 2024-06-13/19） | 2026-10-27T17:24 前后 |
| **主发布 dev.zip**（dev_20240627，嵌套 dev_databases.zip） | https://bird-bench.oss-cn-beijing.aliyuncs.com/dev.zip （346MB，比对后已删，重取同 URL） | 解包 `dev_databases/california_schools/california_schools.sqlite` = `986817d7…` | 2026-10-27T17:27 前后 |

本地库：`2-用例/bird-ca-schools-15/inputs/db/california_schools.sqlite` = `a9e7d92a…`（11,116,544 字节，与 minidev-v1 同字节数但内容见 §4-①；与主发布 dev.zip 逻辑一致）。

### 2.4 exercism（官方 exercism/python main + 声明来源 polyglot-benchmark）

取数时间 2026-10-27T17:23–17:29(+08:00)。源：
- 官方：`https://raw.githubusercontent.com/exercism/python/main/exercises/practice/<slug>/<slug>_test.py`（bowling `6b9a80b6…`、dominoes `9645efc8…`、forth `fe7954ea…`、poker `b39f0232…`、pov `803f32f1…`、zipper `a3cf6e5e…`）
- 声明来源：`https://raw.githubusercontent.com/Aider-AI/polyglot-benchmark/main/python/exercises/practice/<slug>/<slug>_test.py`（forth `05f78a51…`、pov `a5127ac1…`，与本地字节一致；其余 4 题与官方 main 同 SHA）

### 2.5 cargo（harbor-framework/terminal-bench）

源：`https://raw.githubusercontent.com/harbor-framework/terminal-bench/main/tasks/cargo-flight-dispatch/…`，取数时间 2026-10-27T17:30–17:31(+08:00)。

| 官方文件 | 本地对应 | SHA-256（一致性） |
|---|---|---|
| `environment/data/aircraft.json` | truth `input_sha256` / `inputs/app/data/` | `5042e4c7…` ✅ |
| `environment/data/airports.json` | 同上 | `25bb33e3…` ✅ |
| `environment/data/manifest.json` | 同上 | `e29b8743…` ✅ |
| `environment/data/weather.json` | 同上 | `5b5b3caa…` ✅ |
| `environment/{aircraft,dispatch,navigation}.py`（带 bug） | `inputs/app/` 三文件 | `7b2afc42…`/`7a435b3a…`/`b7932e8f…` ✅ 3/3 |
| `tests/test_outputs.py`（官方断言） | `reference/test_outputs.py` | `083168c3…` ✅ 字节一致 |
| `solution/fix_dispatch.py`（官方参考解） | `reference/fix_dispatch.py` | `5c0dcb0a…` ✅ 字节一致 |
| `instruction.md` / `task.toml` | 中文改写题面的英文原文参照（留档 `upstream-samples/cargo/official/`） | `a7b03333…` / `79a9e014…` |

## 3. 第三方交叉核对结果（一致率汇总）

| 用例 | 核对项 | 结果 |
|---|---|---|
| lcb | truth 公开样例 vs 官方样例（3+3+2 组，逐字） | **8/8 内容一致**（truth 存储去尾换行，checker 口径归一，见 §4-③）；官方样例实跑 8/8 PASS；oracle 过真实 checker 4/4 reward=1 |
| dabstep | 官方 dev gold vs truth gold（10 题）；context 文件（6 件） | **10/10 gold 一致**；**6/6 SHA 一致**；题面/guidelines/level 零漂移；官方 gold 正例 reward=1 |
| bird | 官方（archive 2025-07-04 快照）gold SQL vs truth（15 题） | **14/15 逐字一致**；唯一差异 q26 = 已登记 FRPM 有意改写（diff 仅一处列名）；题面/evidence/difficulty **15/15 一致**；数据库层交叉见 §4-①；官方正例 reward=1 ×2 |
| exercism | 官方测试文件（6 份）+ 用例数 + oracle | 与声明来源 **6/6 字节一致**；与官方 main 4/6 字节一致、2/6 仅日期头（§4-④）；用例数 6/6 一致；oracle reward=1 |
| cargo | 数据（4）+ 环境（3）+ 断言（1）+ 参考解（1） | **9/9 字节一致**（数据/环境对 truth 与 inputs，断言/参考解对 reference/）；官方参考解判分 27/27 reward=1 |

**总体：无一例「官方 gold 与本地 truth 意外不一致」。** 全部差异均为：已登记的有意改写（bird q26）、存储口径（lcb 尾换行）、上游自身版本漂移（exercism 日期头）或上游自身数据不一致（bird 两包，见下）。

## 4. 第三方差异清单（留 Lead 裁决；本轮未改任何 truth/checker）

### ① 【高价值】BIRD 上游自身两包数据不一致 → q17/q24/q27 结果集分叉

- **现象**：同一官方 gold SQL 在三个 `california_schools.sqlite` 上执行，结果集：`dev.zip 主发布` vs `本地` **15/15 全一致**；`minidev.zip V1` vs `本地` **q17/q24/q27 三题不一致**（明细见 `upstream-samples/bird/bird-db-crosscheck.json`）。
- **根因**：`satscores.cds` 前导零——主发布 dev.zip 与本地均 **0 行**带前导零；minidev.zip V1 打包件有 **211 行**带前导零（如 `'01100170000000'` vs `'1100170000000'`，同为 TEXT 存储且声明类型相同）。凡 `satscores ⋈ schools/frpm ON cds` 的查询，前导零行 join 失配 → 结果集不同（q17 58↔50 行、q24 1165↔1068 行、q27 行数同但单元格值不同）。frpm/schools 两表三库逐行一致。
- **定责**：**上游发行件之间不一致，不是本地改库**。本地与 BIRD 主发布 dev.zip（dev_20240627）逐行逻辑一致。
- **影响面**：case 内部判分自洽性不受影响（checker 对 gold 与候选 SQL 用同一个本地库执行）。影响的是「与官方 mini_dev 官方评分口径的逐题可比性」：若以 minidev.zip 口径为准，q17/q24/q27 的 gold 结果集应不同。
- **建议（供裁决，本轮未动）**：在 truth.json `source` 或 spec.md 补注「数据库取自主发布 dev.zip（dev_20240627），与 minidev.zip V1 打包件存在 satscores.cds 前导零差异，影响 q17/24/27」；或裁决改用 minidev 口径（需同步改库与 gold，动静大，不建议轻动）。BIRD 官方团队口径未知，两包均来自官方 OSS。

### ② bird q26：官方 `Free Meal Count (Ages 5-17)` vs 本地 `FRPM Count (Ages 5-17)`

已登记的有意本地改写（truth.source.modification、`判卷审计-2026-10-26/bird-q26-并入/`），本轮逐字 diff 确认改动仅此一处列名，**非漂移**。官方口径正例实测：纯官方 15 SQL → 14/15（q26 失败、行数 5 vs gold 6），reward=1（93.33% ≥ 80% 阈值）——阈值设计恰好吸收了这处已登记差异。

### ③ lcb truth 公开样例存储去尾换行

truth.json 的 `input`/`output` 字符串不带末尾 `\n`，官方页样例带。checker 按行 rstrip + 丢末尾空行归一，无判分影响。如实记录，无需动作。

### ④ exercism forth/pov 上游日期头更新

官方 main 于 2026-02-19 更新了两文件的「File last updated」注释头 + 空行，测试用例零变化。本地版本 = polyglot-benchmark 快照 = 官方内容级一致。无需动作。

### ⑤ 更正：cargo 有上游

父任务前提「tb-cargo-plan 自研、无上游、第三方证据只能同学互测」**不成立**：`harbor-framework/terminal-bench`（terminal-bench 现仓库）下 `tasks/cargo-flight-dispatch` 完整存在，且 truth.json 的 source 声明（含 source_url）被 9/9 字节级证实。同学互测仍可做，但不再是唯一第三方证据路径。

## 5. 官方口径正例判分记录（现行 checker，只读判分，temp run_dir，判后即删）

| 用例 | 正例构造（来源） | 命令 | 结果 | 存档 |
|---|---|---|---|---|
| lcb | `solution/` 四题参考解 → `run_dir/solutions/` | `python3 checker.py <run_dir> --json` | **reward=1，4/4，weighted 100.0**（43/43、43/43、42/42、43/43） | `upstream-samples/lcb/official-positive-checker-result.json`、`official-samples-run-receipt.json` |
| dabstep | 官方 `dev.jsonl` answer 直构 `answers.jsonl` | 同上 | **reward=1，10/10，weighted 100.0** | `upstream-samples/dabstep/answers.official-gold.jsonl`、`official-positive-checker-result.json` |
| bird A | 官方 archive 快照 15 题原版 SQL | 同上 | **14/15（q26 失败=已登记差异），reward=1，weighted 93.33** | `upstream-samples/bird/answers.official-v1-pure.jsonl`、`checker-result.official-v1-pure.json` |
| bird B | 官方 14 题 + 本地 q26（登记版） | 同上 | **15/15，reward=1，weighted 100.0** | `upstream-samples/bird/answers.official-plus-local-q26.jsonl`、`checker-result.official-plus-local-q26.json` |
| exercism | `solution/` 六题 oracle 置入临时 inputs | 同上 | **reward=1，6/6，weighted 100.0**（用例数 54/37/13/31/14/15 全对） | `upstream-samples/exercism/official-positive-checker-result.json` |
| cargo | `solution/` 三文件覆盖临时 inputs/app（checker oracle 等价构造） | 同上 | **reward=1，27/27，weighted 100.0，关键 5 项全过** | `upstream-samples/cargo/official-positive-checker-result.json` |

以上运行均从临时目录判分，未向 `2-用例/` 写入任何文件；checker/truth SHA 判分前后未变（见 §7）。

## 6. 到「第三方样例集结清」还差什么

1. **bird §4-① 裁决**（唯一实质未决项）：确认数据库口径（建议：维持主发布 dev.zip 口径 + 在 truth/spec 补注差异声明），并把本收据与 `bird-db-crosscheck.json` 一并归档。
2. **lcb 隐藏测试层**：AtCoder 不公开 hidden tests，第三方天花板就是「官方公开样例 + 独立参考解」。可选增强：为 abc387_f/abc388_f/abc388_g 各做一份独立参考解 + 独立暴力对拍（复用 `lcb389g-oracle` 模式与验收流程），把三题提升到与 389_g 同级的可解性实证。
3. **dabstep test split**：官方不公开 test 答案，**不可获取**（结构性缺口，非执行缺口）；dev 10 题已闭环。
4. **exercism**：已闭环；可选 canonical-data.json 二次锚定。
5. **cargo**：官方证据链已闭环；同学互测降级为可选补充。
6. 上游漂移监控（低优先级）：`birdsql/bird_mini_dev` 现行主数据已是新编号（Mini-Dev 1024），`exercism/python` 会继续更新测试头；如未来重建用例需先钉快照 ID/commit。

## 7. 纪律声明与自证

- 只读访问 `2-用例/`、`4-打分细则/判卷审计-2026-10-26|27/`；写入仅在本目录（含 `upstream-samples/` 数据子目录）。
- 未修改 checker.py / truth.json / 总账 / CHANGELOG；未 `git add/commit`。
- 判分运行后复核（判分前已录，判分后未变）：
  - `2-用例/lcb-recent-hard-4/checker.py` = `e07654d4…`，`truth.json` = `8a9ae6de…`（与 10-27 替换收据 §4 记录一致）
  - `2-用例/bird-ca-schools-15/checker.py` = `01447ab6…`，`truth.json` = `c5bb7999…`
  - `2-用例/dabstep-payments-10/checker.py` = `01dfc976…`，`truth.json` = `9e6e395f…`
  - `2-用例/exercism-py-6/checker.py` = `8d6208ab…`，`truth.json` = `6e4a66ad…`
  - `2-用例/tb-cargo-plan/checker.py` = `bac8cc61…`，`truth.json` = `982754f1…`
- 大文件不入库：`minidev.zip`（800MB）、`dev.zip`（346MB）、dabstep `payments.csv` 冗余拷贝（23.5MB）比对完成后已删除，重取命令见 §2。本目录现存约 13MB，最大单文件为官方参考库 `minidev-v1_california_schools.sqlite`（11MB，q17/24/27 差异物证，建议保留）。
- 全部取数走 `HTTPS_PROXY=http://127.0.0.1:7897`；本目录所有文件 SHA-256 见 `upstream-samples/sha256-manifest.txt`。

## 8. 复现要点

```bash
export HTTPS_PROXY=http://127.0.0.1:7897
# lcb：抓官方页 → 解析样例 → 与 truth 公开样例比对 → 参考解实跑
curl -sL https://atcoder.jp/contests/abc387/tasks/abc387_f -o page.html
# dabstep：官方数据重取（payments.csv 23.5MB）
curl -sL https://huggingface.co/datasets/adyen/DABstep/resolve/main/data/tasks/dev.jsonl -o dev.jsonl
# bird：三渠道（快照 json / minidev.zip 800MB / dev.zip 346MB）
curl -sL https://huggingface.co/datasets/birdsql/bird_mini_dev/resolve/main/archive/bird_mini_dev_2025-07-04/data/mini_dev_sqlite-00000-of-00001.json -o archive.json
# exercism / cargo：raw.githubusercontent.com 逐文件，URL 见 §2.4/§2.5
# 正例判分模板（各用例同型）：
RUN=$(mktemp -d) && cp answers.jsonl $RUN/ && python3 2-用例/<case>/checker.py $RUN --json; rm -rf $RUN
```
