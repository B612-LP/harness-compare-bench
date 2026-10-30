> ⚠️ **本操作卡已过时（2026-10-23）**：脚本控制 GUI 的流程不再使用（用户改为纯手工 GUI），且运行目录已迁到仓库外的 `~/bench-workspaces/r1027/`；现行做法见 `../r1027-isolated/README.md` 与本节 README 顶部的作废说明。下文仅保留为历史。

# 桌面三端跑批 · 操作卡

> 一场你只做两件事：**在 App 里开一个新会话** + **在终端按一次 Enter**。
> 计时、截图、判分、建档都由 `tools/desk.py` 完成。

## 一、开跑前（一次性，2 分钟）

1. 三个 App（WorkBuddy / 元宝 / 豆包）都用你自己的账号登好。
2. **WorkBuddy 选模型 `DeepSeek V4.1-Flash`**（A 组要求与两个 CLI 同模型）；元宝专家模式、豆包办公保持默认模型（B 组，不跨组排名）。
3. 权限已实测可用：屏幕录制 ✅（自动截图）、辅助功能 ✅（自动粘贴）。若某次自动粘贴失败，改为手动 `Cmd+V` + 回车，其余不变。

## 二、单场流程（操作约 30 秒，剩下是等它干活）

```bash
cd ~/Documents/harness-compare-bench/3-表现现场/r1026-desktop-15
./tools/run.sh workbuddy bird-ca-schools-15
```

| 步骤 | 你做什么 |
|---|---|
| ① | 在 App 里开**新会话**，把光标点进输入框 |
| ② | 回终端按一次 **Enter** → 脚本自动粘贴开场白并回车发送（**计时从这一刻开始**） |
| ③ | 等它跑；跑完按一次 **Enter** 收尾（屏幕静默 150 秒也会自动收尾） |
| ④ | 若终端问「步数」：WorkBuddy 会自动读，另两家直接回车跳过 |

收尾后终端会打印本场 `reward / weighted / 耗时 / 步数`，并给出**下一场的完整命令**，复制即可。

## 三、顺序（按产品分组，少切 App）

| 产品 | 顺序 |
|---|---|
| `workbuddy` | `bird-ca-schools-15` → `exercism-py-6` → `dabstep-payments-10` → `lcb-recent-hard-4` → `tb-cargo-plan` |
| `yuanbao` | 同上 |
| `doubao` | 同上 |

先跑 bird（最短，当冒烟），tb 最可能超时，放每个产品的最后。

## 四、先做冒烟：3 场

三个端各跑 `bird-ca-schools-15` 一场，只验两件事：**能不能读工作目录**、**能不能把产物写进工作目录**。

- 能读能写 → 直接继续剩下 12 场。
- 只能上传/下载（读不到本地目录）→ 记一笔 `fs=unavailable`，产物下载后执行
  `python3 tools/desk.py land runs/<产品>/<用例>` 把 `~/Downloads` 里本场新文件搬进 run_dir，再判分。
  这本身就是 Harness 差异，**不补做、不重跑**，报告里单列。

## 五、每场产物（都在 `runs/<产品>/<用例>/`）

```
inputs/             输入（不许改；exercism / tb 两题例外，题目要求改代码）
TASK.md             开场白原文（含绝对工作目录声明）
answers.jsonl / solutions/ / flight_plan.json …   被测端产物
shots/0001.jpg …    自动截图（默认每 20s 一张，收尾留 6 张、压到 1400px）
meta.json           起止时间 / 耗时 / 步数 / reward / weighted / 产物清单
checker.stdout.json 判分原始结果
```

## 六、出问题怎么办

| 症状 | 处理 |
|---|---|
| 自动粘贴没生效 | 手动 `Cmd+V` + 回车，再按 Enter 让脚本继续计时 |
| 想重跑某场 | 加 `--force`（会把 `inputs/` 恢复出厂，不会污染） |
| 中途要停 | `Ctrl-C`（照常判分建档，`finish_reason=ctrl-c`） |
| 忘了跑到哪 | `python3 tools/desk.py status` |
| 全部跑完 | `python3 tools/desk.py collect` → 生成 `MATRIX.md` |
| 只想重判某场 | `python3 tools/desk.py judge runs/<产品>/<用例>` |

## 七、时间预算

单场：bird ≈3min、exercism ≈2min、dabstep ≈5min、lcb ≈4min、tb ≈3min（按 CLI 批的耗时上浮估）。
**一轮 15 场 ≈ 45–60 分钟，其中你实际动手 <15 分钟。**