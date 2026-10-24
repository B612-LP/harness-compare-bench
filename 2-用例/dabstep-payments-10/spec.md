# dabstep-payments-10 判分规格（spec）

版本：**v0.2（2026-10-24，official 兼容 + 符号/ACI 契约双轨）** ｜ 判分入口：`checker.py` ｜ 达标线：得分率 ≥ **0.8**
定位：**hard · 多步数据推理题**（DABstep 官方 dev 10 题的本地化移植，含官方 scorer 语义），与同批 `ledger-replay`（账本重放） / `corpus-squeeze`（受限压缩）互补：本题考「读口径文档 + 大表聚合 + 规则筛选 + 格式精确」。

## 1. 用例定位

投喂 7 个输入文件（6 个 context 数据文件 + `questions.jsonl` 10 题），要求产品按 `inputs/manual.md` 的口径（账户类型、MCC、ACI、费用规则字段、费用公式、自然月、国内交易定义）逐题作答，在运行目录交付 `answers.jsonl`（每行 `{"task_id","answer"}`，答案严格按每题 `guidelines` 的格式）。

题干为 DABstep dev 划分的官方 10 题（3 easy + 7 hard）：2 题全表聚合（国家计数 / 欺诈国家）、1 题商户欺诈费风险判定、6 题费用规则匹配与金额计算、1 题规则集列举与增量计算。hard 题需要把手册口径、`fees.json` 的 1000 条规则、`merchant_data.json` 的 30 个商户画像、`payments.csv` 的 13.8 万条流水交叉使用，不能靠单轮直觉作答。

## 2. 判分模式

- **headline 为二值 0/1**（`BINARY=True`）。`reward = 1` 当且仅当下列三条同时成立：
  1. `answers_format`（否决项）：`answers.jsonl` 结构合法——10 个 `task_id` 各恰好一行、无未知/重复 `task_id`、`answer` 为 JSON 字符串；文件须为 UTF-8、≤2 MB。
  2. `input_integrity`（否决项）：运行目录附带的输入副本（如果存在）与 canonical `inputs/` 逐一 SHA-256 相同；未附副本记为「未核验」，不扣分。
  3. **得分率** = 10 题逐题二值（官方 `question_scorer` 判定 pred 与 gold 等价）/ 10 ≥ **THRESHOLD=0.8**。
- `weighted` = 得分率 × 100（保留 1 位小数），用于聚合与定位；`checks` 给逐题明细（`id`/`pass`/`note`，note 含 pred 与 gold）。
- 为什么否决项不并入得分率：10 题制下漏 1 题仍有 0.9 得分率，但产物已违反交付契约（不可比、不可复现），故单独否决且 `weighted` 仍照实给出（如漏 1 题：reward=0、weighted=90.0），便于事后区分「算错」与「交付不合规」。

### 官方 scorer 判定语义（移植自 DABstep，CC-BY-4.0）

- 数值：先做字符串归一，再比较；两数都 <1 时用 `math.isclose(rel_tol=1e-4, abs_tol=1e-4)`，否则按较短小数位四舍五入后比较，再退到 `isclose`。→ 小数末位差异（如 `0.1201321` vs `0.120132`）可通过；量级错（如 `0.13`）不通过。
- 列表：按 `,`/`;` 切分、去空白、排序后逐项比较（**顺序无关**，多/少一项即 FAIL）。
- 字符串：大小写/标点/空白归一后比较；单侧单词语义包含；否则相似度 >0.95。→ `"b.be"` 与 `"B. BE"` 等价；`"Not Applicable"` 硬答其它内容会 FAIL。
- 判定为**纯确定性字符串/数值归一，无 LLM judge**；不使用网络。

### v0.2 双轨（本轮最小修复）

- 默认 `--scoring official-compat`：上述官方函数原样保留，顶层 `reward/weighted/score_rate/correct/checks/failed` 保持兼容；版本 `dabstep-official-port-v0.1`。**官方会丢弃负号和 ACI**，例如 q1871 正数误过、q2697 `Z:13.57` 误过，因此不能称为严格合同结论。
- `--scoring strict-contract`：顶层与退出码改取 `signed-aci-v1`。仅 q1871 要求全串带符号十进制，q2697 要求全串 `ACI:fee`、ACI 大小写归一后相同、金额保留符号；拒绝非有限数、解释性前后缀。两题数值均 `math.isclose(rel_tol=1e-4, abs_tol=1e-4)`，不走官方的「较短小数位四舍五入」捷径。仍接受近似值及补零，不新增 14 位字面精度要求；不是所有 guidelines / 格式语义一般正确性的保证，其他题仍按官方。
- JSON **始终**另有 `official_compat` 与 `strict_contract` 两个对象，各含 `scorer_version/reward/weighted/score_rate/correct/checks/failed`；严格对象另含 `scope/numeric_tolerance`，顶层 `scoring_mode` 标明所选轨。结构与输入硬门两轨共用，阈值仍 0.8。单题拒绝不等于整场否决：错两题仍可 0.8 通过。
- 旧 v0.1 checker/truth 已在[审计冻结区](../../4-打分细则/判卷审计-2026-10-24/numeric/frozen/)按 SHA-256 固定；不覆盖历史运行或历史分数。严格复算必须另标 checker v0.2 / `signed-aci-v1`，不重跑模型。

## 3. 观察项（权重）

| id | 观察项 | 权重 | 通过条件 | 0 分条件 |
|---|---|---:|---|---|
| `answers_format` | 产物结构（否决项） | —（否决） | `answers.jsonl` 存在且 10 题各一行，`answer` 为 JSON 字符串 | 缺失 / 题数不符 / 未知或重复 task_id / 非法 JSON / answer 非字符串 |
| `input_integrity` | 输入完整性（否决项） | —（否决） | run_dir 中附带的 7 个输入副本逐一匹配 canonical SHA-256 | 任一附带的输入副本被改（即使答案全对也 0）；未附副本不扣分 |
| `q5` | 问题 5（easy）：签发国家交易数最高者 | 10 | 与国家码 gold 等价 | 不等价 |
| `q49` | 问题 49（easy）：欺诈交易最多的 ip_country | 10 | 与 `X. Y` 选项 gold 等价 | 不等价 |
| `q70` | 问题 70（easy）：商户高欺诈费率罚款风险 | 10 | 与 yes/no 或 `Not Applicable` gold 等价 | 不等价 |
| `q1273` | 问题 1273（hard）：GlobalCard 信用交易 10 EUR 平均费用 | 10 | 6 位小数等价（scorer 容差内） | 不等价 |
| `q1305` | 问题 1305（hard）：账户类型 H + MCC 描述下同口径平均费用 | 10 | 同上 | 不等价 |
| `q1464` | 问题 1464（hard）：`account_type=R` 且 `aci=B` 的费用 ID 列表 | 10 | 列表集合等价（顺序无关） | 缺/多项或不等价 |
| `q1681` | 问题 1681（hard）：Belles_cookbook_store 2023 年第 10 天适用费用 ID | 10 | 列表集合等价 | 不等价 |
| `q1753` | 问题 1753（hard）：Belles_cookbook_store 2023-03 适用费用 ID | 10 | 列表集合等价 | 不等价 |
| `q1871` | 问题 1871（hard）：2023-01 相对费用 ID=384 改为 1 的差额 | 10 | 14 位小数等价 | 不等价 |
| `q2697` | 问题 2697（hard）：Belles_cookbook_store 1 月最低费用 ACI 与成本 | 10 | `{ACI}:{fee}` 格式等价 | 不等价 |

合计 100 分（10 题 × 10）；两个否决项不占分，但任一不通过即 `reward=0`。

## 4. 运行目录约定

```
<run_dir>/
  answers.jsonl   # 必需产物：10 行 {"task_id": "<str>", "answer": "<str>"}
                  # 也接受 run_dir/output/、run_dir/outputs/ 下同名文件
  inputs/...      # 运行器把 cases/<id>/inputs/ 整个拷入；若存在则逐一核验 SHA-256
```

```bash
python3 checker.py <run_dir>          # 人读报告 + 末行 RESULTS_JSON
python3 checker.py <run_dir> --json   # 默认 official-compat；JSON 始终双轨
python3 checker.py <run_dir> --json --scoring strict-contract # 严格顶层/退出码
python3 checker.py --selftest         # 正/负控制与守卫自测，必须全 PASS 才可用于正式评分
```

退出码：`0` = reward 1；`1` = reward 0；`2` = 用法错误 / `--selftest` 失败 / 用例自身不一致（truth 漂移、canonical 输入被改、solution oracle 漂移）。

正式判分最后一行 JSON 形如：

```json
{"case":"dabstep-payments-10","reward":0,"weighted":90.0,"score_rate":0.9,"threshold":0.8,"correct":9,"n_tasks":10,"gates":{"answers_format":false,"input_integrity":true},"checks":[{"id":"answers_format","pass":false,"note":"结构违规：缺少 1 题未作答：1871"},{"id":"input_integrity","pass":true,"note":"已核验 7/7 个输入副本，SHA-256 全部一致"},{"id":"q5","pass":true,"note":"pred='NL' ｜ gold='NL'"}]}
```

## 5. 判分器自测（`--selftest` 覆盖，原始输出见 `selftest.stdout.txt`）

自测全程使用 `tempfile.TemporaryDirectory()`，不写仓库、不读 `/tmp`、不联网。v0.2 共 **23 组**（原 20 组 + 3 组符号/ACI 双轨回归）；原 20 组历史清单如下。新增断言：q1871 翻符号、q2697 换 ACI 均官方 10/10、严格 9/10；两者叠加 q49 错答，官方 9/10 reward=1、严格 7/10 reward=0。
独立脚本另测输出目录抽取、CLI 选择/退出码、容差内外、oracle 与结构硬门，见[数值判卷审计](../../4-打分细则/判卷审计-2026-10-24/numeric/README.md)。

| # | 组 | 期望 | 断言 |
|---:|---|---|---|
| 1 | oracle：`solution/answers.jsonl` 原样 | 1 | — |
| 2 | oracle + canonical 输入副本（运行器拷贝形态） | 1 | gates 全绿、`input_integrity=verified` |
| 3 | oracle 等价写法（空白/大小写/列表乱序/数字补零） | 1 | 10/10 判对（scorer 归一容错） |
| 4 | 容错边界：仅 q49 答错（9/10=0.9） | 1 | `correct=9` 且 `q49` 在 failed |
| 5 | 达标线边界：错 2 题（8/10=0.8，恰好过线） | 1 | `correct=8` |
| 6 | nop：空运行目录 | 0 | `weighted=0`、`answers_format` fail |
| 7 | **漏答 1 题**（9 行，得分率 0.9 但结构否决） | 0 | `failed == ["answers_format","q1871"]` |
| 8 | **多答 1 题**（11 行，未知 `task_id=9999`） | 0 | `answers_format` fail |
| 9 | **格式错：某行缺 `answer` 字段** | 0 | `answers_format` fail |
| 10 | **格式错：`answer` 为 `null`（非字符串）** | 0 | `answers_format` fail |
| 11 | **格式错：某行非法 JSON（尾随逗号）** | 0 | `answers_format` fail |
| 12 | **重复 task_id**（10 行，q2697 写成 q1871） | 0 | `answers_format` fail |
| 13 | **近正确负例：q49 错国家码 + q1273 错数值 + q1464 错列表（0.7）** | 0 | `correct=7`、`weighted=70.0` |
| 14 | **近正确负例：`Not Applicable` 题（q70）硬答 yes 且另 2 题错（0.7）** | 0 | `correct=7` |
| 15 | **守卫：附篡改的 `inputs/payments.csv`（答案全对）** | 0 | `failed == ["input_integrity"]` |
| 16 | **守卫：附篡改的 `inputs/questions.jsonl`（答案全对）** | 0 | `failed == ["input_integrity"]` |
| 17 | 守卫：canonical `inputs/payments.csv` 被改 | ERROR(2) | 抛 `CaseError`（`--selftest` 捕获后 exit 2） |
| 18 | 守卫：`truth.threshold` 漂移（0.8→0.9） | ERROR(2) | 抛 `CaseError` |
| 19 | 守卫：`truth.input_sha256` 漂移 | ERROR(2) | 抛 `CaseError` |
| 20 | 守卫：`solution/answers.jsonl` oracle 漂移 | ERROR(2) | 抛 `CaseError` |

第 17–20 组用「临时用例副本 + 符号链接 canonical 输入」模拟，不改动仓库内 `inputs/`；任何一组不符合预期 → `--selftest` exit 2。

**修改 checker 后必须重跑**：`python3 checker.py --selftest` 全绿 + §8 oracle 回归。

## 6. 来源、许可证与数据

| 项 | 内容 |
|---|---|
| 基准 | **DABstep: Data Agent Benchmark for Multi-Step Reasoning**（Adyen + Hugging Face） |
| 数据集 | https://huggingface.co/datasets/adyen/DABstep （10 题取自 **dev** 划分，官方随包提供答案） |
| 榜单/主页 | https://huggingface.co/spaces/adyen/DABstep |
| 官方仓库 / 判分器 | https://huggingface.co/spaces/adyen/DABstep 内的 `dabstep_benchmark/evaluation/scorer.py`（GitHub 上同名 `adyen/DABstep` 仓已 404，勿引；本用例 checker.py 移植其 6 个函数并标注来源） |
| 许可证 | **CC-BY-4.0** — https://creativecommons.org/licenses/by/4.0/ |
| 读取日期 | **2026-10-22**（由 Lead 实拉至 `/tmp/tb-probe/dabstep/`，本用例原样拷入） |
| 改写说明 | ① `questions.jsonl` 删除官方 `answer` 字段，仅保留 `task_id/question/guidelines/level`（英文原题保留原句并在此标注来源）；② 6 个 context 数据文件原样使用，未改一字；③ `instruction.md` 用中文重写任务书；④ checker.py 的 scorer 部分为官方实现移植（CC-BY-4.0），其余为自写。 |
| 版权归属 | 数据与题面 © Adyen / Hugging Face，按 CC-BY-4.0 使用并署名；本用例判分逻辑与文档由 harness-compare-bench 编写。 |

**输入清单与体积**（`truth.json.input_sha256` 逐文件记录）：

| 文件 | 字节 |
|---|---:|
| `payments.csv` | 23,581,339 |
| `fees.json` | 531,118 |
| `manual.md` | 22,127 |
| `merchant_category_codes.csv` | 26,611 |
| `merchant_data.json` | 6,857 |
| `acquirer_countries.csv` | 194 |
| `questions.jsonl`（派生，去答案） | 3,889 |
| **inputs 合计** | **24,172,135（≈23.0 MiB）** |

用例总体积 ≈ 24.3 MB（含 truth/checker/solution 文本），满足 ≤25 MB 目标；`payments.csv` 无法无损裁剪（题涉及全表聚合），故原样保留并在 `case.json` 给 `timeout_s=1800`。

## 7. gold 与交叉校验记录（2026-10-22）

- **gold 来源**：DABstep 官方 dev 划分 `dev.jsonl` 的 `answer` 字段（10 条，官方随包提供），落盘为 `solution/answers.jsonl`。`truth.json.gold` 与 `solution/answers.jsonl` 由 checker 启动时的官方 `question_scorer` 交叉校验（任一漂移 → ERROR 退出码 2），避免「改 solution 骗 oracle」。
- **独立复算抽查（3 题，与官方 gold 一致）**：
  - `q5`：`payments.csv` 按 `issuing_country` 计数，NL=29,622 > IT=28,329 > BE=23,040 → **NL** ✓；
  - `q49`：`has_fraudulent_dispute=True` 按 `ip_country` 计数，BE=2,493 > IT=1,652 > SE=1,627 > FR=843 → **B. BE** ✓；
  - `q1273`：`fees.json` 中 `card_scheme=GlobalCard` 且「适用于信用交易」的规则（`is_credit ∈ {true, null}`）共 144 条，`avg(fixed_amount + rate×10/10000) = 0.120132` → 与 gold `0.120132` 完全一致 ✓。
- 其余 hard 题依赖手册完整口径（`capture_delay`/`monthly_volume`/`monthly_fraud_level`/`intracountry` 等字段叠加），未在本机独立复算；**gold 以官方 dev 答案为准**。
- `truth.json` 的 `input_sha256`（7 文件）与 `input_bytes` 由实拉文件计算；checker 启动即校验（任一漂移 → ERROR 退出码 2）。

## 8. oracle 回归

```bash
# 正对照：官方 dev 答案 → 必须 reward=1
TMP=$(mktemp -d); mkdir -p "$TMP/run/inputs"
cp cases/dabstep-payments-10/inputs/* "$TMP/run/inputs/"
cp cases/dabstep-payments-10/solution/answers.jsonl "$TMP/run/"
python3 cases/dabstep-payments-10/checker.py "$TMP/run" --json
# → {"reward":1,"weighted":100.0,"correct":10,...}
```

`--selftest` 第 1–2 组即覆盖该回归；实测 2026-10-22：oracle reward=1、weighted=100.0，12 个 checks 全 PASS。

## 9. 难度论证与边界

1. **不是单轮问答**：hard 题需要先读懂手册的字段口径，再在 `fees.json` 1000 条规则里按 6~8 个字段联合筛出适用规则，还要结合商户画像与流水的自然月聚合；任何一步口径理解错（如 `null` 语义、`intracountry` 定义、`account_type` 列表包含关系、`is_credit` 为 null 视为「适用于信用交易」）都会整体算错。
2. **大表约束**：`payments.csv` 13.8 万行 / 23.5 MB，必须做聚合而非逐个读；标准库 `csv` + 流式处理是可行路径（实测全表聚合 <1s）。
3. **判分区分度**：10 题二值 + 0.8 达标线 → 允许 2 题失手（真实产品的合理容错），但 0.7 及以下明确不过；easy 3 题（q5/q49/q70）只是入口题，hard 7 题决定胜负。
4. **格式红线**：`guidelines` 已写明「只给国家码 / `X. Y` / 指定小数位 / 逗号分隔列表 / `Not Applicable`」；`answer` 必须是 JSON 字符串（数字不加引号按结构违规处理），这与真实评测的产出契约一致。
5. **已知宽松点（官方 scorer 特性，非本用例放宽）**：数值容差 `rel/abs 1e-4`、列表顺序无关、字符串归一/相似度。这些容错降低「写法差异误杀」，但也会误过符号/ACI 错误；v0.2 严格轨仅修复这两类，不能由官方通过推断一般语义正确。`Not Applicable` 硬答不会因相似度通过。
6. **不可作弊路径**：改输入 → 输入指纹守卫；删题/多写 → 结构否决；编造答案 → 10 题二值判分；`answers.jsonl` 只从 run_dir 读取，不采信自述。

## 10. 变更记录

- **2026-10-24 v0.2**：保留官方兼容，新增 `signed-aci-v1` 符号/ACI 契约轨与 CLI 选项，固定数值容差 abs/rel=1e-4；checker/truth/spec 同步版本，旧代码冻结，不改历史分数或 gold/source。新增 3 组内置回归和仓库外临时运行目录的独立红绿回归。

- **2026-10-22 v0.1**：首版入 staging（`3-表现现场/r1025-candidates/cases/dabstep-payments-10/`）。7 个输入文件、`solution/answers.jsonl`（官方 dev gold）、`checker.py`（官方 scorer 移植 + 结构/输入/truth 三重守卫）、`truth.json`、`instruction.md`、`task.toml`、`case.json`；`--selftest` 20 组（5 正 + 11 负 + 4 守卫 ERROR）全绿；oracle reward=1（weighted=100.0）；nop reward=0；11 组负例全部 0；4 组守卫 ERROR 全部触发。