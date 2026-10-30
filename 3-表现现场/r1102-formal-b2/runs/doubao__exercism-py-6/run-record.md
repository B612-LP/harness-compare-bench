# 运行记录 · `exercism-py-6` · `豆包办公` · `r1102-run1`

> 一次运行一份；本文件与同目录的产物/证据一起构成该次运行的完整记录。
> 判分只认产物与规则；本记录用于复核与行为分，不替代产物。
> 本记录是运行记录模板 schema v2 的首个执行批场级记录（L12 环；r1102-formal-b2，合同 freeze-20261029-v5）。

## 1. 基本信息

| 字段 | 值 |
|---|---|
| 用例 | `exercism-py-6`（spec 版本：随冻结快照，case_version 见 JSON） |
| 产品 / 版本 | `豆包办公（本地电脑 runtime）2.33.7`（run_meta.json 实测） |
| 模型显示 | `披露：产品封闭不展示模型名，见 meta.json model 字段` |
| 形态 | GUI（桌面 agent，CDP 自动发射） |
| 任务目录 | `~/bench-workspaces/r1102/doubao/exercism-py-6`（仓库外，仅 inputs+TASK.md） |
| 权限 / 联网设置 | `披露：桌面全盘文件访问为产品默认（meta.json permissions）；检索按三件套管控（integrity 终审 clean）` |
| 操作人 / 日期 | `lead（Agent）` / `2026-10-31 01:27` |
| 耗时 | `01:27:11–02:07:18，约 40.1 分钟（2407s，完成判定上限收敛）` |
| 运行状态 | `valid`（产物齐备可判；超时形态与披露见 JSON verdict_basis） |

## 2. 输入与产物

| 文件 | SHA-256 | 说明 |
|---|---|---|
| `TASK.md` | 见事件 sources 表 | 含边界硬条款（r1102 模板）+禁网附则，工作区原件快照 |
| `inputs/exercises/{forth,poker,dominoes,bowling,zipper,pov}/*.py` | 以 input_integrity 实测为准 | 题面 stub 由 agent 实现为交付物（题目要求）；测试文件与 canonical 一致 |

## 3. 证据位置

- 原生日志 / 会话导出：`披露：豆包会话轨迹原件含账号侧数据，留私档 bench-automation/runs/r1102/（存在性与完整性由 integrity-adjudication-r1102.json 与机器账行级登记承载）`
- 截图：`无（2026-10-23 拍板：桌面证据=轨迹+产物+提示词，不要求截图）`
- 录屏：`无（同上）`
- 探针回执 / 随机 ID：`preflight/doubao-preflight-r1102.json（probe-ok-1793380669）`

## 4. 产物判分（checker）

```bash
python3 checker.py ~/bench-workspaces/r1102/doubao/exercism-py-6 --json
```

| 项 | 结果 |
|---|---|
| reward | `1` |
| 失败项 | `pov（tests=15/15 exit=1）` |
| 加权参考 | `83.33/100` |
| 输入完整性 | `verified`（官方测试文件与 canonical 一致） |
| RESULTS_JSON | `checker.stdout.json`（同目录，冻结 checker 字节实测） |

## 5. 行为分（人工，0–3）

| 观察项 | 档位 | 理由 | 证据位置 |
|---|---:|---|---|
| 交付完整性 | `N/A` | 自动批跑无过程观察；交付完整性以 checker 实测承载（6/6 模块回收、5/6 题通过） | `checker.stdout.json` |
| 回传说明 | `N/A` | 自动批跑无过程观察 | |
| 异常/边界处理 | `N/A` | 自动批跑无过程观察 | |

### 5.1 机器可读（schema v2，2026-10-30 起新记录强制；必须与上表一致）

```json
{
  "schema_version": 2,
  "run_id": "exercism-py-6-doubao-r1102-01",
  "case": "exercism-py-6",
  "spec_version": "exercism-py-6@sha256:7913a1ad769f1f9e002b5473375ea3ddf076bad152e2fed8f50c514ff3e2420c",
  "case_version": "exercism-py-6@sha256:7913a1ad769f1f9e002b5473375ea3ddf076bad152e2fed8f50c514ff3e2420c",
  "product": {
    "name": "豆包办公",
    "version": "2.33.7",
    "model_shown": "披露：产品界面不展示模型名，见 meta.json model",
    "form": "GUI"
  },
  "provenance": {
    "model_resolved": "披露：closed-desktop-product，model_id 不可证（meta.json model；组语义 B_native 不做模型归因）",
    "tools": "披露：desktop-agent managed（Bash/Read/Write 等），见 meta.json tools",
    "permissions": "披露：desktop full local file access 为产品默认（meta.json permissions）；本批实测越界 0 命中（integrity-adjudication-r1102.json 判定线终审）",
    "skills": "披露：product-closed 无外挂技能开关（meta.json skills）",
    "started_at": "2026-10-31T01:27:11+08:00",
    "duration_s": 2407
  },
  "evidence_grade": "conversation-trajectory-and-artifacts",
  "status": "valid",
  "verdict_basis": "六模块产物冻结前全部交付、input_integrity verified、判定线终审 0 越界、检索三件套 clean（URL 字样=题面自带注释豁免）——V clean，checker 实测 reward=1 weighted=83.33（adjudication.json receipt；40min 完成判定上限收敛为 timeout 不掩盖产物事实，先例=元宝 lcb 有效运行可判）",
  "behavior": [
    {"item": "交付完整性", "score": "N/A", "reason": "自动批跑无过程观察；交付完整性以 checker 实测承载", "evidence": ["checker.stdout.json"]},
    {"item": "回传说明", "score": "N/A", "reason": "自动批跑无过程观察", "evidence": []},
    {"item": "异常/边界处理", "score": "N/A", "reason": "自动批跑无过程观察", "evidence": []}
  ],
  "unknowns": [
    {
      "item": "末段 36min 轨迹静默的直接原因（服务端会话中断 vs agent 长时自验）不可证",
      "impact": "完成判定以 2400s 上限收敛为 timeout；不影响产物判分（冻结前已交付）与裁定",
      "next_step": "无需专项调查：产物可判性与三件套/判定线终审均已闭环",
      "stop_condition": "产物可判且终审 clean 时停止追查，作为运行形态备注保留"
    }
  ]
}
```

## 6. 未知与停止条件（不补 0 / 不补满分）

| 未知项 | 影响 | 下一步 | 停止追查条件 | 复核日期 |
|---|---|---|---|---|
| 末段 36min 轨迹静默直接原因 | 完成判定收敛形态（timeout）；不产物判分影响 | 无需专项调查 | 产物可判且终审 clean 即停止（本批已满足） | 2026-10-31 |

## 7. 备注

- 完成判定 v2 于 2400s 上限收敛为 timeout（最后 36min 轨迹静默，末条 role=tool）；按「有效运行、产物可判」处置（先例：r1101 元宝 lcb 无产物可判 0 分；本批反向=产物齐备）。
- 关联运行：前承 `formal-b1-doubao-exercism-py-6-01`（发射期 infrastructure_invalid 作废，零模型暴露）；本批为其配额制作废重跑（新 plan 新 slot 的 first）。
- 检索维说明：trajectory L39/L48/L57 的 exercism 官方 canonical URL 为题面测试文件自带来源注释，按题面自带来源标注豁免口径记误报（同 r1101 bird 裁定）。
