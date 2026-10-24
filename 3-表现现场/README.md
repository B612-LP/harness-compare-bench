# 表现现场

本目录存放各 Harness 的实际过程与结果（公告交付物），历史现场不覆盖。本轮为既有产物复算，**不新增模型/GUI 运行**。当前结论见[阶段报告 v2.0](<../5-评测报告/阶段报告-v2.0.md>)、[阶段二方案](<../1-评测方案/2026-10-24-阶段二方案.md>)；版本化成绩与命令见[本轮复算](<../5-评测报告/复算/2026-10-24/README.md>)。

## 当前批次索引与使用规则

| 批次 | 用途 | 本轮如何使用 |
|---|---|---|
| [r1021](<r1021-intsum-workbuddy/>) | WorkBuddy 旧题单场 | 历史能力/取证材料，不与当前五题混分 |
| [r1022](<r1022-cbase-deepseekflash/README.md>) | C组裸模型基线 | 方法史料，不是当前五题无Harness消融 |
| [r1023](<r1023-cli-dsf-low/README.md>) | 旧五题双CLI | 旧题饱和观察，不当当前成绩 |
| [r1024](<r1024-probe-区分度/README.md>) | 换库探针 | 历史定标，存在读gold等污染；按新总账override排除，不据原meta补clean |
| [r1025](<r1025-candidates/README.md>) | 新五题双CLI原场 | 污染两格由r1027替代；其他格按修复版复算 |
| [r1026](<r1026-desktop-15/README.md>) | WB/豆包GUI原场 | 非15场全完成；WB污染格替代，WB×LCB suspect排除不补0；元宝paused |
| [r1027](<r1027-isolated/README.md>) | 四场仓外工作区+软约束重跑 | 组合干预，不能归为隔离单因素效果；Cargo归档代码补录须披露来源/时间边界 |
| [r1028](<r1028-repeats/README.md>) | 十二场CLI重复样本 | 每格n=3仅为观察；不能证明无噪声、打平写死或模型上限 |

[独立运行总账](<../5-评测报告/运行总账-2026-10-24.md>)是计数与排除依据；目录数、矩阵格数、评分条目和自测数不等于独立运行数。新发现用证据override，不静默改原日志。当前A组同模型不等于全部变量一致，B组豆包默认模型不能归因Harness；CLI/GUI边界见[当前方案](<../1-评测方案/2026-10-24-阶段二方案.md>)。

**历史文字适用范围**：下方为2026-10-16两批的原汇总；其中“A−C即Harness增量”“价值本体”等因果措辞不作为本轮已验证结论。后续批次README中“逐题同分”“打平不是噪声”“模型上限”“工作区是有效修法”等强措辞也只留作历史，当前以新报告的限定结论为准。桌面采集已采用用户手工GUI，旧脚本化[操作卡](<r1026-desktop-15/START-HERE.md>)已过时；豆包无截图为既定取证口径，不本身算缺证据。

以下两批为 **glm**（r1016-*）与**小米**（r1016x-*）的历史两题材料，不代表当前全部现场。

---

## 批次一（2026-10-16，`r1016-*`）：CLI 赛道（Codex / DSH × GLM 各两份）

两个自建用例 × 两个 Harness × 同一模型（glm-5.3-flash），每用例先过两道闸门再收产品分。方案与控制变量见 `../1-评测方案/2026-10-16批次-CLI赛道方案.md`，判定标准见 `../4-打分细则/打分表.md`。

### 汇总表

| 现场 | 用例 | Harness/模型 | reward | 轨迹步数 | token in / out / cached |
|---|---|---|---|---|---|
| `r1016-intsum-nop/` | int-sum-sort | nop 空操作 | **0**（闸门 1 通过） | — | — |
| `r1016-intsum-oracle/` | int-sum-sort | oracle 参考解 | **1**（闸门 2 通过） | — | — |
| `r1016-wordfreq-nop/` | word-freq-report | nop 空操作 | **0**（闸门 1 通过） | — | — |
| `r1016-wordfreq-oracle/` | word-freq-report | oracle 参考解 | **1**（闸门 2 通过） | — | — |
| `r1016-intsum-codex/` | int-sum-sort | Codex 0.162.1 × glm-5.3-flash | **1** | 8 | 43,003 / 706 / 27,328 |
| `r1016-wordfreq-codex/` | word-freq-report | Codex 0.162.1 × glm-5.3-flash | **1** | 7 | 34,938 / 558 / 21,248 |
| `r1016-intsum-dsh/` | int-sum-sort | DSH 0.2.0-rc.2 × glm-5.3-flash | **1** | 5 | 5,452 / 452 / 15,168 |
| `r1016-wordfreq-dsh/` | word-freq-report | DSH 0.2.0-rc.2 × glm-5.3-flash | **1** | 6 | 7,758 / 2,318 / 21,824 |

**速读**：四道闸门全过；四个产品现场全部 reward=1，**含 word-freq-report 的平票决胜陷阱**（`a`/`dog`/`tests` 同为 5 次卡在 Top-5 边界，须按 ASCII 决胜才得分）——两个 Harness 都正确实现并拿下。两用例均为满分区间，**区分度证据要看过程面**：步数、token 账、行为模式（见各现场 trajectory.json），这正是"评测主体是 Harness"的素材。

---

## 批次二（2026-10-16，`r1016x-*`）：小米 MiMo V2.6 Flash 归因三件套（A×4 + C×2）

**切换原因**：glm-5.3-flash 周额度用尽。批次一保留为**第二模型切片**（A 组完整、C 缺），批次二用 `mimo-v2.6-flash` 凑齐 A（Codex/DSH）+ C（裸模型）全链——A−C 即 Harness 增量。用例、闸门、评分器与批次一完全相同（闸门为用例级，无需重跑）。

### 汇总表

| 现场 | 用例 | 组/对象 | reward | 轨迹步数 | token in / out / cached |
|---|---|---|---|---|---|
| `r1016x-intsum-bare/` | int-sum-sort | **C 组**裸模型（零脚手架） | **0** | 2 | 90 / 52 / — |
| `r1016x-wordfreq-bare/` | word-freq-report | **C 组**裸模型（零脚手架） | **0** | 2 | 310 / 329 / — |
| `r1016x-intsum-codex/` | int-sum-sort | A 组 Codex 0.162.1 | **1** | 7 | 36,022 / 1,000 / 32,448 |
| `r1016x-wordfreq-codex/` | word-freq-report | A 组 Codex 0.162.1 | **1**（重跑件） | 9 | 48,382 / 736 / 46,528 |
| `r1016x-intsum-dsh/` | int-sum-sort | A 组 DSH 0.2.0-rc.2 | **1** | 5 | 2,207 / 305 / 19,456 |
| `r1016x-wordfreq-dsh/` | word-freq-report | A 组 DSH 0.2.0-rc.2 | **1** | 6 | 2,384 / 581 / 27,200 |

**归因读法**：C=0/2，A=4/4 → **A−C 增量 = 满分**，且 C 的失败形态极具说服力——裸模型两次都试图**调用不存在的工具**：intsum 的回答是一句"先读输入文件"的开场白加一个 Shell 工具调用块（命令 `cat /app/input.txt`）；wordfreq 的回答是一整段 Bash 工具调用块包着 Python 脚本，连标点集合都和规格一致，但没有任何执行者。两次都是 API 层 `status: completed` 的合法回答，却不是交付物。**工具循环的执行权在 Harness 手里，这就是 Harness 的价值本体**。

**跨模型观察（2026-10-21 已更正口径）**：表观差异（Codex input 3.4–4.8 万 vs DSH prompt 0.2–0.8 万）主要来自计价口径——Codex 的 input 含缓存读，DSH 的 prompt 不含（cached 单列）。按统一口径（input + cached）复算：Codex:DSH = 2.09× / 1.18×（glm 两用例）、1.66× / 1.64×（mimo 两用例）；未缓存口径 2.88× / 1.76× / 1.62× / 0.78×。比值方向在 3/4 切片一致，但量级远小于表观；且 Codex 首轮输入含 `<skills_instructions>`（属 SKILL 层注入，见 `r1016x-wordfreq-codex/*/agent/trajectory.json` 第 1 步）。**因此不能把表观量级差直接当作 Harness 编排规模证据**，详见 `5-评测报告/阶段报告-v1.0.md` §5.2 与复算脚本 `5-评测报告/复算/token-recompute.py`。

### 环境层留痕（批次二特有）

今天的代理链路下载质量差（node tarball 撕裂 ×1、codex 平台二进制缺失 ×1），两份 codex 安装步阵亡后重跑，重跑件已入库。两次失败尝试的原始日志未随本仓保留（不构成可复核证据），因此只作为过程备注：**不计入运行数、不参与任何结论**；"环境层"的判定以"重跑后 reward=1"的现场为准。该未复核项已登记在 `5-评测报告/未知登记.json` 的 `env-netflake` 条目（含下一步与停止条件）。缓解方向（见方案文档）：预装 agent 的自定义基础镜像消除每 trial 现装。

---

## 每个现场目录里有什么（= 可复核证据链）

```
r1016*/                          # 作业级
├── config.json / result.json     # 作业配置与汇总
├── job.log
└── <task>__<id>/                 # trial 级
    ├── config.json               # 完整配置快照（agent/模型/kwargs/overlay → 一键复现）
    ├── result.json               # 成绩 + 时间线四段 + token 账
    ├── trial.log                 # 执行日志（含安装/运行全过程）
    ├── verifier/
    │   ├── reward.txt            # 分数出处
    │   └── test-stdout.txt       # 判卷现场（逐项 PASS/FAIL）——0 分先读它
    └── agent/
        ├── trajectory.json       # ATIF v1.7 轨迹（行为分析主料）
        ├── codex.txt / dsh.txt / bare-response.json   # 原生事件流 / API 请求响应留证
        └── sessions/**           # 原生会话落盘（codex rollout JSONL / dsh session.v4.jsonl）
```

## 标准阅读顺序（拿任何一份现场都这么读）

1. `trial/config.json` → 确认考场配置没被污染（版本、模型、web 开关、overlay）
2. `trial/result.json` 时间线 → 环境安装 vs agent 干活 vs 判卷各占多久
3. `verifier/test-stdout.txt` → 测试跑全了没有（排除环境层冤案）→ 每项 PASS/FAIL
4. `agent/trajectory.json` → 行为链条：几步、调了什么工具、写后有没有自查、token 花在哪
5. `agent/sessions/**` → 需要逐帧取证时下到原生会话层

## 备注与口径

- **trap 判定**：word-freq 的期望值由评分器按与参考解同一规则现算；批次一两个 Harness 的输出与 gold 一致（92 / 35）。
- **cached 口径差异**：Codex 的 cached 含于 input；DSH 的 cached（cacheReadTokens 累计）与 input 分列——表内按各自轨迹字段原样呈现，统一口径（input + cached）后重算见 `5-评测报告/阶段报告-v1.0.md` §5.2。
- **superseded 留痕**（不入正式对比、不计入运行数；原始记录未入仓，不作为可复核证据）：
  - `superseded-r1016-intsum-dsh-no-traj/`——轨迹转换器早期缺陷（Step.message 校验）时期的 DSH 首跑，reward=1 但轨迹未回填；正式件为 `r1016-intsum-dsh/`（重跑，双跑互为复现）。轨迹缺失属工具链缺陷，不作为产品行为证据。
  - `superseded-r1016x-wordfreq-codex-netflake*/`——安装步网络故障后重跑；见上节「环境层留痕」。
- 桌面赛道（五款产品对比）的录屏/现场规范另行设计，命名约定不变。
