# 表现现场

本目录存放各 Harness 执行同一任务的实际过程与结果（公告交付物）。
两个批次：**批次一 glm**（`r1016-*`，A 组两份 × 两 Harness）与**批次二小米**（`r1016x-*`，A+C 归因三件套）。目录命名：`r1016*-{用例}-{harness}`。

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

**跨模型观察**（批次一 glm vs 批次二 mimo）：Codex 的 input token 量级（3.4~4.8 万）与 DSH 的量级（0.2~0.8 万）差异在两个模型上都稳定复现——Harness 层的提示词/编排规模差异不随模型翻转，可进报告。

### 环境层留痕（批次二特有）

今天的代理链路下载质量差（node tarball 撕裂 ×1、codex 平台二进制缺失 ×1），两份 codex 安装步阵亡后重跑。证据保留于调研档案仓 `jobs/superseded-r1016x-*-netflake*`——**归因三域里"环境层"的现成素材**：reward 缺失 ≠ 模型/Harness 失败。缓解方向（见方案文档）：预装 agent 的自定义基础镜像消除每 trial 现装。

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
- **cached 口径差异**：Codex 的 cached 含于 input；DSH 的 cached（cacheReadTokens 累计）与 input 分列——表内按各自轨迹字段原样呈现，成本换算时统一口径后重算（见打分表三节）。
- **superseded 留痕**（调研档案仓 `jobs/` 下，均保留备查、不入正式对比）：
  - `superseded-r1016-intsum-dsh-no-traj/`——轨迹转换器早期缺陷（Step.message 校验）时期的 DSH 首跑，reward=1 有效但缺轨迹回填；正式件为 `r1016-intsum-dsh/`（重跑，双跑互为复现）。
  - `superseded-r1016x-wordfreq-codex-netflake*/`——安装步网络故障（见批次二环境层留痕）。
- 桌面赛道（五款产品对比）的录屏/现场规范另行设计，命名约定不变。
