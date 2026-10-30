# L7 综合结论（2026-10-30）——共享验证器语义默认值显式化与运维卫生规程

- 数据基座：judge 独立验收收据 `verify-receipt-l7.json`（sha256 `4e3866987a61cd683eff95f971bd479b55e0e54f5912e72a64223dfff3a494aa`）与机器账 `seven-ledger.json`（sha256 `2255e7dc4729e8a320a973086b73745da30288c26a1be0aad9513ee99be0352c`，生成器本目录 `ledger_build.py`，O_EXCL 拒写）。r7 复跑为 judge 以同内容脚本 /tmp 副本自跑（原收据 write-once 不覆盖），未采信 lead 收据。
- 分账声明：本环为零真实模型调用的工具链/规程环；无产品运行分账；最近真实批=L6（formal 1/1）。

## 一句话结论

**L7 双交付独立验收全过：L7-A 将 gate 的语义默认计划目录制度性拔除（CLI 必填/API None 即 GateError/--selftest 例外），判分语义零改动（r7 12/12 独立复跑+selftest PASS+24 变更行逐行声明类+P4 封印 pin 精确拒佐证）；L7-B P4 ps 卫生规程条目化+全量扫描零 Bearer 字面量（156 文件，9 命中全为 env 透传允许形态，judge 独立佐证 0 命中）；历史复算经 r1-r6 五版探索后按设计改为「基线收据引用固定」，其「跨批重演按设计不可行」论证经 judge 独立核可成立；历史批 L4 0/17、L5 5/6、L6 1/1 基线不变。**

## 一、观察

1. **时序与身份**：main c8710fb（PR#10 L5+L6 集成点，13:10:47）→ D1=a186ff3（13:13:05，预注册）→ D2=47bd685（13:42:35，实现），D1 祖先于 D2 且先于 D2；修前 gate 提取字节==封印钉值 38b42a87…，修后==磁盘 25dbf52e…（三方一致）。
2. **L7-A 独立复算（r7 12/12）**：N1a/N1b CLI 缺参即拒（含 L7-A 标记）；N2 `verify_execution(plan_dir=None)`→GateError（非 TypeError）；N3 `load_execution_seal(None)`→GateError；N4 坏 plan-dir fail-closed；S0 修订版 selftest PASS（judge 另行直跑复现）；P0 修前字节==封印钉值；P4 修订版复判 L6 恰因 gate.py sha-mismatch（want=38b42a87）拒——**失败=封印 pin 而非语义漂移**；G1/G2/G3 三批基线收据在档（L4 0/17、L5 5/6、L6 1/1）。
3. **diff 分类**：5 hunk/24 变更行逐一核对=常量拔除+注释、verify_execution/load_execution_seal/gate_admission 三签名显式化+GateError、CLI 两参必填——**判分路径零触及**（guards 重算 747-770 等逐段未动）。
4. **L7-B**：OPERATIONS-hygiene.md（P4 规程：token/Bearer/key 不入 ps 可见参数/日志/收据正文，凭据 env/文件传递，定期 grep 巡检）在案；bearer-scan-receipt-l7：**156 文件、0 字面量、9 命中全部 env-var-passthrough 允许形态、all_clear PASS**；judge 独立自扫（l6 现场+工具链 Bearer 字面量正则）=**0 命中**互证。
5. **设计变更（history-replay-design-note）**：r1-r6 五版跨批重演探索全档 VOIDED（judge 抽验 r1=22 断言 5 过、r5=17 断言 14 过，真实留档）；其结构发现——封印钉定使「manifest==E blob==磁盘」三方一致在工链演进后的当前盘上按设计不可满足、树内 binding 系 E 后重写遗物、封印树不含 E 后证据——**judge 独立核可成立**（r1 发现=P4 复现；r4 与 L6 废封纪要互证；r3 与 L4 验收已知互证；三方一致机制为本 judge L5/L6 验收亲证）。最终验收面改为：修订版自身行为（N/S 组）+封印 pin 精确性（P 组）+三批基线收据引用固定（G 组）。
6. **影响面**：l6 现场显式传参（L6 修复）不受影响；l4/l5 冻结现场调 gate 无显式参=PREREG 明示 documented known-impact（现场封存不重跑），未来重跑须先适配（池）。

## 二、证据

- `verify-receipt-l7.json`（本目录）：时序/身份/diff 分类/r7 12 项全 results/设计论证核可/PREREG 措辞偏差/L7-B 数据/引用件哈希（全 64 位实算）。
- 修订档案：`5-评测报告/L7验证器修订-2026-10-30/`（README、pre/post、diff、r7 收据、r1-r6 VOIDED 链五版全档）。
- L7-B：`1-评测方案/工具链/OPERATIONS-hygiene.md` + `1-评测方案/工具链/bearer-scan-receipt-l7.json`。
- 七账：`seven-ledger.json`（七类分账，本目录 `ledger_build.py` 生成）。

## 三、解释

L6 三代废封（F-1 contract pin、E1 站点常量、E2 plan_dir 缺省）暴露的同一类根因——「共享验证器的语义默认值让调用方漏传也能跑、但跑错批」——在本环被制度性关闭：默认值不复存在，任何调用方要么显式传参要么 fail-closed。跨批重演的放弃不是验收缩水：五版探索证明封印钉定系统的目的正是让历史批裁定不随 HEAD 漂移，「重建封印世界+后置证据的混合体」复杂度与可信度都不如引用封印时刻原始收据—— judge 以自己 L5/L6 验收亲证的三方一致机制独立核可此论证。PREREG 与实现存在一处措辞级偏差（见四 O-1），fail-closed 意图完全达成。

## 四、未排除因素（未知/观察，含影响/下一步/停止条件）

| # | 项 | 影响 | 下一步 | 停止条件 |
|---|---|---|---|---|
| O-1 | **PREREG 措辞级偏差**：预注册写 `plan_dir=None→ValueError`，实现为 GateError（非 ValueError 子类） | 无判分/准入影响（fail-closed 意图完全达成且更利于调用方按 GateError 捕获）；r7 N2 断言与实现一致 | 记录即可；后续 PREREG 异常类型措辞以实现复核为准 | 无（ observation 闭项） |
| U-1 | l4/l5 冻结现场 gate 调用无显式参（documented known-impact） | 现场封存不重跑，无现实影响 | 未来若需重跑，先按 L7-A 口径适配（池结转） | 适配版重跑复现基线 formal |
| U-2 | T22d（L5 锚定已知败）未退役 | runner 位于已封存 L6 现场，改动即破坏历史批零改动红线 | 留待未来 WB 新现场一并处置（池结转） | 新现场 fixture 退役 |
| U-3 | lead 消息「155 文件」vs 收据实值 156 | 微差（口径计数时刻），以收据为准 | 无（收据为权威载体） | 无 |
| U-4 | 样本口径：本环零真实批 | L7 结论仅覆盖工具链/规程面，产品判定沿用 L6 | 后续正常批回归多槽结构 | 结构性事实，非待办 |

## 五、可复现实验

```bash
cd /Users/b612-lp/Documents/harness-compare-bench
# ① gate selftest（S0）
python3 1-评测方案/工具链/l5-execution/gate.py --selftest          # 期望 PASS
# ② 近似错误例（N1a/N1b）
python3 1-评测方案/工具链/l5-execution/gate.py --verify-execution 2>&1 | grep "L7-A"
# ③ r7 全 12 断言独立复跑（write-once：复制脚本改输出路径后自跑）
python3 -c "import json;d=json.load(open('5-评测报告/L7验证器修订-2026-10-30/l7-gate-recompute-receipt.json'));print(d['counts'])"  # 在档收据
# ④ 时序
git log --format="%H %cI %s" -1 a186ff38 47bd6855 c8710fbc
```

## 附：池结转

| 池项 | 内容 | 去向 |
|---|---|---|
| l4/l5 现场重跑适配 | 冻结现场调 gate 无显式参（U-1） | 未来重跑前适配 |
| T22d 退役 | L5 锚定已知败随 L6 封存现场（U-2） | 未来 WB 新现场 |
| PREREG 异常类型措辞 | O-1 observation | 后续预注册模板注意 |
