# 裸底数→Harness 增益三层分解（L37 主项 B，派生账）

- **plan_id**: `l37-20261103`（零发射环）；本文件为 L37 环派生分析收据公开副本，**零模型调用、零联网、零新运行、零判卷执行**，公开仓只读未改任何文件。
- **数据来源**：裸底数两代 = `3-表现现场/r1022-cbase-deepseekflash/`（无内联地板，老五题）+ `3-表现现场/r1105-bare-matrix/`（现行五题内联裸底数，inline-low n=3）；正式账 25 格 = 六个可信冻结（v2/v4/v5/v6/wb-v1/wb-v2）的 `official-main-table.json` + `six-ledgers*.json`；tb 断言面 = `r1105-bare-matrix/tools/assertion-diff-tb.json`。逐文件 SHA-256 见同名 JSON 的 `input_shas`（59 个文件）。
- **结论身份**：全部结论为观察账/派生账，**不改任何官方表数字、不构成正式表准入变化**。正式账 n=1/格，如实披露。

---

## 一、逐题分数底表（weighted 0–100；括号内二值 reward；bare 为 n=3 逐场+均值）

| 题 | bare inline-low (n=3) | codex | dsh | workbuddy | doubao | yuanbao |
|---|---|---|---|---|---|---|
| bird-ca-schools-15 | 93.33/100/100 → **97.78** (1,1,1) | 93.33 (1) 14/15 | 100.00 (1) 15/15 | 100.00 (1) 15/15 | 93.33 (1) 14/15 | 93.33 (1) 14/15 |
| dabstep-payments-10 | 10.0×3 → **10.00** (0,0,0) | 70.00 (0) 7/10 | 70.00 (0) 7/10 | 60.00 (0) 6/10 | 70.00 (0) 7/10 | 20.00 (0) 2/10 |
| exercism-py-6 | 83.33/100/100 → **94.44** (1,1,1) | 100.00 (1) 6/6 | 100.00 (1) 6/6 | 100.00 (1) 6/6 | 83.33 (1) 5/6 | 100.00 (1) 6/6 |
| lcb-recent-hard-4 | 100×3 → **100.00** (1,1,1) | 100.00 (1) 4/4 | 100.00 (1) 4/4 | 100.00 (1) 4/4 | 75.00 (1) 3/4 | 0.00 (0) 0/4 |
| tb-cargo-plan | 70.37×3 → **70.37** (0,0,0) | 81.48 (0) 22/27 | 74.07 (0) 20/27 | 74.07 (0) 20/27 | 85.19 (0) 23/27 | 0.00 (0) 0/27 |
| **五题合计** | **372.59**，headline 3/5 | 444.81，3/5 | 444.07，3/5 | 434.07，3/5 | 406.85，3/5 | 213.33，2/5 |

bare 失败明细：dabstep r1/r2 过 q5、r3 过 q70（weighted 恒 10.0）；tb 三场失败集完全一致（8 项，三场 checker result.json 字节同 SHA `c5371818f93d…`）；bird r1 失 q25；exercism r1 失 forth；lcb 无失败项。正式账每格 `admission.eligible=true`（v2 formal-a1 / v4-v6 formal-b1-b3 / wb-v1+v2），排除场（doubao exercism/tb b1 场、wb-v1 首批 dabstep/lcb/tb 三场）均 `eligible=false` 未入底表。

---

## 二、三层分解（层间不重复计账：L1 只记代际 headline 对照；L2 记现行五题全部分数差；L3 只记 tb 断言面）

### L1 信息内联增益（信息进上下文 vs 完全不可见）

- **可计算项（跨代形态对照）**：headline 二值 0/5（r1022）→ 3/5（r1105 inline-low）；weighted 均值 18.0 → 74.52（Δ+56.52）。
- **逐题 Δ：不可计算，如实置空**。r1022 用老五题（int-sum-sort / word-freq-report / jielong-fullchain / ledger-replay / corpus-squeeze，weighted 20/20/20/20/10），r1105 用现行五题——题集无逐题配对，headline 差混杂题集更换，**不能读作纯内联增益**。r1022 另有 thinking 档位未钉与 checker 启发式差异（r1022 未知#1/#3）。
- **机制证据**：r1022 失败形态 = 执行结构缺失——无工具且无内联，模型看不到输入仍输出确定数字（int-sum-sort 幻觉产物），五题全带 format_strict 类格式守卫失败；r1105 内联后现行四题不再出现该形态，唯一残留地板 dabstep 恰是两份大文件未进内联包的题（该对照的记账归 L2）。

### L2 工具/数据可达增益（bare inline-low → 带文件工具的 harness，现行五题）

- **dabstep（数据规模墙，增益主体）**：bare 10.0 → codex/dsh/doubao 70.0、wb 60.0、yuanbao 20.0；weighted Δ = +60/+60/+60/+50/+10。机制：裸协议预注册地板——`payments.csv`（23,581,339 B/13.8 万行）+ `fees.json`（531,118 B）超上下文未内联（dabstep r1 meta `inline_missing`+`floor_note`；spec.md:127-128），裸 1/10 correct；CLI 有文件工具可流式读全表。**数据可达必要不充分**：达标线 score_rate≥0.8（spec.md:14,32），0.7/0.6/0.2 均不过线 → 五款二值全 0；q2697 官方 scorer 判分歧义已按报告 §4 撤出能力归因。
- **bird（检索题）**：bare mean 97.78 ≥ codex/doubao/yuanbao 93.33、≤ dsh/wb 100；二值 Δ=0（双端全 1）。weighted 差在 bare 自身 n=3 波动量级内（极差 6.67）。裸 r1 93.33 失 q25 vs codex 93.33 失 q27——同分不同错题（r1105 结论一口径）。
- **exercism/lcb（编码题）**：bare 已 reward 1，二值 Δ=0（doubao lcb 75.0 仍过线）；**yuanbao lcb 0.0 是低于裸底数的形态反例**。
- **tb**：weighted Δ = +11.11/+3.70/+3.70/+14.82/−70.37（codex/dsh/wb/doubao/yuanbao），二值全 0——该题记账归 L3 断言面。
- **汇总量（只在此记一次）**：五题合计 bare 372.59 → codex 444.81（+72.22）、dsh 444.07（+71.48）、wb 434.07（+61.48）、doubao 406.85（+34.26）、yuanbao 213.33（**−159.26**）。dabstep 数据可达贡献加权总增量的 83%（codex 60/72.22）、84%（dsh 60/71.48）、81%（wb 50/61.48）；doubao dabstep +60 超过其总增量 +34.26（被 lcb −25、exercism −11.11 抵消）；yuanbao 总增量为负，占比不适用。

### L3 迭代自纠增益（tb 失败断言集，用 r1105/tools/assertion-diff-tb.json，不重算 checker）

- 分数面：bare 70.37（19/27）×3 → codex 81.48（22/27，Δ+11.11）、dsh 74.07（20/27，Δ+3.70）。
- 断言面（三方失败集两两互异，`pairwise_distinct=true`）：
  - bare 8 项；codex 5 项；dsh 7 项。
  - codex 消除 bare 的 4 项（leg2_fuel_below_planned / leg2_remaining_below_reserve / route_feasible / tow_within_limit）但**新引入 tow_leg1**；dsh 消除 2 项（route_feasible / tow_within_limit）同样新引入 tow_leg1。
  - 三方共同失败 4 项：landing_weight_leg2 / leg2_weight_limits_fuel / total_time_includes_turnaround / **total_time_value**。
- **关键断言门（tb spec.md:12）**：reward=1 需 ≥20/27 且关键 5 项（route_order / ground_speed / crosswind_dest / reserve_holding / total_time_value）全过。total_time_value 在三方共同失败集内 → bare 19/27、codex 22/27、dsh 20/27 均 `critical_ok=false`，**断言面增益必要不充分**。
- 机制读法：harness 侧处理形态（多轮+工具+闭环）改变了『哪些断言失败』的构成，但三方共同 4 项（含关键项）未被任何 harness 修复。**不能归因『迭代自纠』单因素**：bare 单轮无迭代是形态定义性差异（协议设计），harness 侧=模型+工具+多轮混合，且 bare=deepseek-flash 而 A 组 harness 模型不同且封闭。
- B/W 形态对照（分数面 only）：doubao 85.19、wb 74.07、yuanbao 0.0 均二值 0；三款失败断言集不在收据范围内，不推断。

---

## 三、弱命题边界（沿用 r1105 RESULTS 结论一/四口径）

1. **达标集重合 ≠ 同构**：bare 与 A 组双 CLI 达标集重合（3/5 同集），但同题分数与失败断言集互异（tb 三方失败集两两互异、bird 同分不同错题 q25 vs q27）——不构成同构，**不支持裸分数↔harness 分数互推**。
2. **L1 逐题 Δ 不可计算**（题集更换），headline 对照是跨代形态对照，混杂题集更换与 r1022 的 thinking/checker 未知项。
3. **正式账 n=1/格**：25 格均单场；bare inline-low n=3、inline-default n=1。bare n=3 内重测波动极差 bird 6.67（93.33↔100）、exercism 16.67（83.33↔100）→ weighted 差在该波动量级内的按波动解读，不作稳定增益断言。
4. **bare 单轮无迭代是形态定义性差异**（协议设计），非混淆变量；L3 只作形态对照，不作同模型因果归因。
5. **B/W 模型封闭**：doubao/yuanbao/workbuddy 只作形态对照；yuanbao lcb/tb 双 0 低于裸底数，『harness≥裸底数』不普遍成立。
6. **dabstep 地板分母=内联包裁剪决策**（预注册）：10.0 是信息不可达地板而非模型能力上限。
7. **7 事故场 meta 为事故后重建**：duration_s/started_at 如实 unknown；分数来自 API 响应原样离线重抽取后的 checker 判分，不受影响（r1105 已如实披露 buggy 脚本无版本副本）。
8. **跨组判卷器版本差异（bird）**：checker_sha256 A 组=994be0b3b766… vs B/W 组=ffa7389adef3…（其余四题跨组字节一致）；earned/possible 口径同 /15，组内对照不受影响，跨组 bird 对照含判卷器版本混杂——披露存在性，修订内容未核查。
9. 本分析零发射、零重判卷，全部结论为派生账。

---

## 四、复算命令清单（工作目录=公开仓根）

```bash
# 0. 输入完整性
shasum -a 256 "3-表现现场/r1105-bare-matrix/RESULTS.md"   # 逐文件对照本收据 input_shas

# 1. bare inline-low 逐场分数（15 场）
python3 - <<'EOF'
import json,glob
for p in sorted(glob.glob("3-表现现场/r1105-bare-matrix/runs/inline-low/*/RESULTS_JSON/result.json")):
    d=json.load(open(p)); fails=[c["id"] for c in d.get("checks",[]) if c.get("pass") is False]
    print(p, d["reward"], d["weighted"], fails)
EOF

# 2. 正式账 25 格（六个冻结 six-ledgers 的 score.value）
python3 - <<'EOF'
import json
pairs=[("可信冻结-2026-10-29-v2","six-ledgers.public-derived.json","A_same_model"),
("可信冻结-2026-10-29-v4","six-ledgers.json","B_native"),("可信冻结-2026-10-29-v5","six-ledgers.json","B_native"),
("可信冻结-2026-10-29-v6","six-ledgers.json","B_native"),("可信冻结-20261031-wb-v1","six-ledgers.json","W_gateway"),
("可信冻结-20261031-wb-v2","six-ledgers.json","W_gateway")]
for d,l,g in pairs:
    t=json.load(open(f"5-评测报告/{d}/official-main-table.json")); ids=set(t["groups"][g])
    for ev in json.load(open(f"5-评测报告/{d}/{l}"))["product_run"]:
        if ev.get("event_id") in ids:
            s=ev["score"]["value"]; print(ev["product"],ev["case_id"],s["reported"],s["reward"],f'{s["earned"]}/{s["possible"]}',ev["admission"]["eligible"])
EOF

# 3. tb 三方失败断言集与交并差（与 assertion-diff-tb.json 内嵌复算同源）
python3 - <<'EOF'
import json
def fails(p):
    d=json.load(open(p)); return {c["id"] for c in d["checks"] if c.get("pass") is False}
b=fails("3-表现现场/r1105-bare-matrix/runs/inline-low/tb-cargo-plan__r1/RESULTS_JSON/result.json")
c=fails("3-表现现场/r1030-formal-a1/runs/codex__tb-cargo-plan/checker.stdout.json")
ds=fails("3-表现现场/r1030-formal-a1/runs/dsh__tb-cargo-plan/checker.stdout.json")
print(len(b),len(c),len(ds)); print("bare&codex",sorted(b&c)); print("bare&dsh",sorted(b&ds)); print("all3",sorted(b&c&ds))
print("distinct:", b!=c and b!=ds and c!=ds)
EOF

# 4. r1022 无内联地板（老五题）
python3 - <<'EOF'
import json,glob
for p in sorted(glob.glob("3-表现现场/r1022-cbase-deepseekflash/*__bare1/RESULTS_JSON/result.json")):
    d=json.load(open(p)); print(p, d["reward"], d["weighted"])
EOF

# 5. dabstep 地板机制字段
python3 - <<'EOF'
import json
m=json.load(open("3-表现现场/r1105-bare-matrix/runs/inline-low/dabstep-payments-10__r1/meta.json"))
print(m.get("inline_manifest"), m.get("inline_missing"), m.get("floor_note"))
EOF
```

---

## 五、自检段（逐格对账 + 实际打开文件清单）

### 5.1 底表逐格对账（30/30 格，零漂移）

| 格 | 对账三方来源 | 结果 |
|---|---|---|
| bare×5 | r1105 RESULTS.md 结果矩阵 ↔ bare-matrix-events.json（17 场）↔ 15 场 checker result.json 逐场 | 一致（含 inline-default bird 93.33/lcb 100 两场） |
| codex×5 | v2 six-ledgers.public-derived.json score.value ↔ r1030 codex__* checker.stdout.json ↔ 报告 v1.3 §6.1 | 一致 |
| dsh×5 | v2 同上 ↔ r1030 dsh__* checker.stdout.json ↔ 报告 v1.3 §6.1 | 一致 |
| yuanbao×5 | v4 six-ledgers.json ↔ 报告 v1.3 §6.2 | 一致 |
| doubao×5 | v4（bird/dabstep/lcb）+ v5（exercism formal-b2）+ v6（tb formal-b3）↔ 报告 v1.3 §6.2 | 一致 |
| workbuddy×5 | wb-v1（bird/exercism）+ wb-v2（dabstep/lcb/tb）↔ 报告 v1.3 §6.3 | 一致 |

断言面与排除场对账：tb 三方失败集 assertion-diff-tb.json ↔ r1030 checker ↔ bare checker 三源一致；bird q25/q27、exercism forth、dabstep q5/q70 互换、codex/dsh 失 {q49,q70,q2697} 均一致；doubao exercism/tb b1 场与 wb-v1 首批三场确认 `eligible=false` 未入底表；六冻结 groups 内 25 个 formal 事件 admission 全部 eligible=true，history:* 行全部 rejected 未入底表。

### 5.2 数据缺口（如实）

- L1 逐题 Δ：无逐题配对（题集更换）——置空不构造代理指标。
- B/W 三款 tb/bird 失败断言集：无收据（assertion-diff-tb.json 仅三方），任务边界内不重算 checker。
- bird 跨组判卷器版本差异与 bare checker 版本对应关系：未核查，只披露存在性。
- tb `critical_ok` 逐项 critical 标志不在 checker.stdout.json（定义在用例 truth），只引用 spec.md:12 清单，未重算 truth。

### 5.3 实际打开的关键文件（55 个逐字/逐 JSON 检读 + 3 个仅哈希收编 + 3 个摘录检读；全部 59 个的 SHA-256 见 JSON `input_shas`）

- r1022：README.md、batch-results.json、5×`__bare1/RESULTS_JSON/result.json`（7）
- r1105：README.md、RESULTS.md、bare-matrix-events.json、tools/assertion-diff-tb.json、15×inline-low result.json、3×meta.json（bird/dabstep/tb r1）、2×inline-default result.json（22）；仅哈希未检读：six-accounts.json、batch-results.run1-extractor-bug.json、preflight-reasoning-pin.md（3）
- 六冻结：6×official-main-table.json + 6×six-ledgers*.json（12）
- r1030：formal-a1-events.json + 10×checker.stdout.json（11）
- 摘录检读：竞品评测报告-v1.3.md（§3/§6）、dabstep spec.md（:10,:14,:30,:32,:97-98,:127-128,:163-165）、tb spec.md（:12-16）（3）

*配合数据文件：`bare-floor-decomposition.json`（同目录，机器可读完整版：score_matrix/layers/weak_proposition_caveats/input_shas/reproduce/self_check）。*
