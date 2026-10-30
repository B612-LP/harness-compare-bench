# L6 综合结论（2026-10-30）——bird 槽 formal 修复实证与单槽批正式判定

- 数据基座：judge 独立复算收据 `l6-judge-canonical-rerun.json`（sha256 `5b9a7f2875ede329863969aa863a34b73916b6e3afeb26e55f2c64ca3c4dfd4c`，E 前验收 `5-评测报告/L6独立验收-L6-2026-10-30/verify-receipt-l6.json` sha256 `be3434a3c1847a1d7804b65c0a3880fbd672e61b1ab47852d56b728ffcfa4332`）；机器账 `six-ledger.json`（sha256 `1ae5bd78c4e32b25835786861878e931e845db4cfa0b7096e0f0b6eb5ed52eee`，生成器本目录 `ledger_build.py`，O_EXCL 拒写）。
- 分账声明：本文属「判卷回归/离线复算+单槽产品运行」合成结论；正式比较表仅纳入 1 个 formal=True 槽。

## 一句话结论

**L6 单槽批（E3=aae5edac，registered_at=2026-10-30T12:23:46+08:00）1/1 executed、canonical formal 1/1：bird 槽 raw 100.00000000（15/15，guards 调和一致）经 L6-A 元数据修复后首次获得 formal 资格——L5 同槽的 checker 字段缺省根因修复实证；L6-C 收据自引排除规则以历史差分（E2 旧 8→新 9 违规、恰 +1 抓获 AUD-L5-O1 实例）独立实证；E1/E2 两代废封全程零消耗如实入账；封印链 D1→D2→D3→E1(废)→E2(废)→E3 时序单调、git 全对账。**

## 一、观察

1. **正式判定**：槽 `l6-20261030-wb-gateway-bird-ca-schools-15-r1`——ok，148s，1 attempt；judge 独立复跑 gate_admission：**formal=True，fails=[]，contamination_cleared=true，evidence_complete=true**（与 lead 收据逐项一致但未采信、系独立复算）；integrity_verdict=clean；inputs_verification.ok=true。
2. **分数链（8dp）**：score.reported=100.00000000 == meta.weighted == raw 重算 15/15→exp8=100.00000000；score.checker_sha256==contract pin（ffa7389a…）。
3. **L6-A 修复实证（本环修订一）**：meta.judge.guards_used=`[input_integrity,answers_file,answers_schema,answers_coverage]` 发射在案，gate 按 guard 重算 earned=15/possible=15==contract 分母，judge.correct/n_tasks 与 raw 重算全等——L5 时同槽因 `guards_used 缺失` formal=False，本轮同判据全绿，**修复因果直接可证**。判分语义零改动（修前/修后冻结工作区零翻转，L6 验收已证）。
4. **L6-C 修复实证（本环修订二）**：receipt_check 自引排除规则 selftest 16/16；历史差分（judge 以 79cebe0 旧版工具独立落地自跑）E1 零变化、E2 abort-receipt 8→9 违规恰 +1=自引条目抓获；manifest_receipt.py（self_excluded/write-once/O_EXCL）PASS——AUD-L5-O1 wart 闭环工具化。
5. **封印链对账（git）**：D1=8c3e4b9(10:50:20) → D2=f10881c(11:35:00) → D3=1211b5b(11:45:03) → E1=1c27a6b(11:52:45，**废，零消耗**：runner 站点常量 L5 硬编码→plan-read 阶段 fail-closed，零 claim/零 registration/零发送) → E2=46d64ee(12:15:41，**废，零消耗**：verify_execution 未传 plan_dir→gate 默认读 L5 plan，REFUSED 先于 claim) → E3=aae5edac(12:23:46)。时序单调；E3 提交内 plan/contract/manifest blob 与磁盘逐一相等；manifest 28 仓内+5 外部全量实算零失配；runs/ 目录仅含 E3 唯一槽目录（零消耗核算的磁盘佐证）。
6. **别名/模型身份**：declared_alias=deepseek-v4.1-flash，driver_create_model_param=「DeepSeek V4.1-Flash」+session-db model 字段双证；actual_request_model=not_observable_in_this_batch（**不可观测≠已证**，如实披露不折算）。
7. **native_terminal**：文件在案且 sha256==meta 钉扎值（38e68ebb…），非空。

## 二、证据

- judge 独立复算：`l6-judge-canonical-rerun.json`（本目录；gate 复跑+8dp/guards/native_terminal/别名/E3 blob 对账/零消耗核算全数据）。
- E 前门禁：`5-评测报告/L6独立验收-L6-2026-10-30/`（七项 PASS 含 F-1 contract pin 抓获→D3 闭环）。
- 判卷修订档案：`5-评测报告/L6判卷修订-2026-10-30/`（pre/post/diff/recompute/历史回放收据）。
- 废封纪要：`1-评测方案/自动循环L6-2026-10-30/seal-supersession-E1-20261030T1153.md`（E1/E2 根因+授权 diff+零消耗实证+defaults 审计 85 项收据索引）。
- lead 侧收据对照：`gate-admission-e3.json`/`gate-formal-check-e3.json`（判定与 judge 复跑一致，一致性本身入账）。

## 三、解释

bird 槽 formal 从 L5 的 False 到 L6 的 True 是**单因素修复的直接结果**：L5 时 gate 因 judge.guards_used 缺失无法按 guard 重算而按「unknown 不折满」拒绝；L6-A 以纯增量两键补齐元数据（判分语义零改动，冻结区零翻转佐证），gate 同判据全绿。中间三次封印失败（F-1 contract pin、E1 站点常量、E2 plan_dir 默认值）均属工具链适配面而非判分器或数据问题，且全部 fail-closed 在消费前拦截——fail-closed 设计在此环三次兑现零成本。L6-C 将 AUD-L5-O1 的「收据自引」从一次性 observation 升级为可复用规则+write-once 生成器，历史差分证明其恰好命中目标实例且无误伤。

## 四、未排除因素（未知，含影响/下一步/停止条件）

| # | 未知 | 影响 | 下一步 | 停止条件 |
|---|---|---|---|---|
| U-1 | actual_request_model 本批不可观测（alias 双证=driver 参数+session 库字段） | 模型身份为「声明+旁证」而非请求级实证 | 后续环可加请求级捕获面（如 provider 侧 request-id 对账） | 请求级实证或明确放弃并永久标注 not_observable |
| U-2 | gate DEFAULT_PLAN_DIR 语义默认值残留（L5-性存在于依赖模块默认） | 靠显式传参覆盖维持正确；未来新增产品若漏传将 fail-closed（不会错判但会阻断） | L5 池已录「运行路径默认值审计」规程化；下版 gate 可将默认值改为显式必传 | gate 新版显式化并回归 L4/L5 行为不变 |
| U-3 | WB runner selftest 70/71（T22d 为 L5 锚定已知败） | 已知状态有档，非本环缺陷 | T22d 随 L5 fixture 退役时一并处置 | fixture 退役或 L5 锚定语义更新 |
| U-4 | 样本量 n=1（单槽批） | 本环结论仅覆盖 bird 修复因果，不支持跨产品泛化 | 后续正常批恢复多槽结构 | 无（结构性事实，非待办） |

## 五、可复现实验

```bash
cd /Users/b612-lp/Documents/harness-compare-bench
# ① judge 独立 gate 复跑（workbuddy 单槽）
python3 -c "import importlib.util;from pathlib import Path;s=importlib.util.spec_from_file_location('g','1-评测方案/工具链/l5-execution/gate.py');g=importlib.util.module_from_spec(s);s.loader.exec_module(g);print(g.gate_admission(Path('1-评测方案/自动循环L6-2026-10-30/runtime-binding.json'),'workbuddy',repo=Path('.'),plan_dir=Path('1-评测方案/自动循环L6-2026-10-30')))"
# ② 六账重建（O_EXCL）
python3 5-评测报告/L6综合结论-2026-10-30/ledger_build.py --out /tmp/l6-ledger-recheck.json && python3 -c "import json;a=json.load(open('/tmp/l6-ledger-recheck.json'.replace('.json','.json')));b=json.load(open('5-评测报告/L6综合结论-2026-10-30/six-ledger.json'));a.pop('generated_at');b.pop('generated_at');print('deterministic-rebuild-equal:', a==b)"
# ③ 封印链时序
git log --format="%H %cI %s" -1 8c3e4b9e f10881cc 1211b5b7 aae5edac
```

## 附：L6 池结转

| 池项 | 内容 | 去向 |
|---|---|---|
| L5-P4 | ps 操作规程加固（ps 误印 Bearer 事件，L5 已证零入库） | 留池：运维规程条目化 |
| L3 尾项 | L3 遗留观察项（随 L4/L5 处置记录，不回写历史结论） | 留池 |
| 本环新增建议 | gate DEFAULT_PLAN_DIR 显式化（U-2）；T22d 随 L5 fixture 退役（U-3） | 下版 gate/fixture 退役时处置 |
