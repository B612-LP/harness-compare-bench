# L6 判卷器修订独立验收（task-18，judge）— 2026-10-30

- 范围：L6-A（bird checker 元数据两键纯增量）与 L6-C（receipt 自引排除+manifest_receipt 生成器）的独立复算验收；E 封印前门禁。全程零模型；git 只读（rev-parse/log/show/merge-base/diff/status）。
- 结论速览（初验 11:36）：清单 1–3、5 全 PASS；清单 4 FAIL 一处（contract bird pin=修前哈希）→ **已闭环（D3 复验 11:47，见文末 Dated）**。其余四 case 继承、分母、rule_version、plan_cardinality=1 均核过。
- 机器收据：`verify-receipt-l6.json`（sha256 `51ea7cc253bbe549819f1cfcf8b083fb668728e45bb32e712f1e141d782c73f6`，receipt_check 自检 ok/0 违规）。

## 一、观察

1. **时序与身份（清单1）**：D1=`8c3e4b9e595a8d49ddd10150a67cf101a8bea19c`（committer 2026-10-30T10:50:20+08:00）先于并 ancestor 于 D2=`f10881ccf8380f01159c43dd09b55cb826888130`（11:35:00+08:00）——预注册先于实现 ✓。修前三方字节一致：`git show 79cebe0:2-用例/bird-ca-schools-15/checker.py` == 档案 `checker.pre-l6.py`；磁盘 checker == 档案 `checker.post-l6.py`。pre sha256 `994be0b3b766e457…`（恰为 L5 wb-bird judge 所钉值，跨批一致）。
2. **纯增量与判分语义（清单1/2）**：unified diff +41/−3；−3 行逐条分类=docstring dated 补记、`CONTRACT_REVISION` 值替换（b2-tighten-2026-10-27→l6-meta-fields-2026-10-30，PREREG 明文声明）、selftest 总数计数——**计分路径零触及**；`CHECKER_VERSION` 保持 `1.2-q26-frpm`。`checker.py --selftest` = **29/29**（含两条 L6-A 元数据不变量分支）。
3. **冻结工作区修前/修后复算（清单2）**：两工作区（L5 bird 槽、E2 档案 wb__bird-r1）以 /tmp 副本判分（修前版置于含 truth/inputs 的镜像 case 目录）：两处 rc 0/0；reward=1/weighted=100.0/correct=15/checks 逐值全等；**唯一共同键差=`contract_revision`（声明内的修订标记）**；键集恰增 `["guards_used","n_tasks"]`、零删键；n_tasks=15、guards_used 恰为四守卫 id。
4. **gate 口径调和与近似错误例（清单2）**：按 gate.py:747-770 语义独立实现重算：两工作区计分项 15/15→exp8=100.0 ✓。负例：(a) 篡改 n_tasks=14 → 「meta.judge 计数 n_tasks ≠ raw 重算」**拒**；(b) guards_used 漏 answers_coverage → 「raw 计分项数 16 ≠ contract 分母 15」+计数不调和**拒**；对照原样→零 problems。
5. **L6-C（清单3）**：`receipt_check.py --selftest` = **16/16**；`manifest_receipt.py --selftest` = **PASS**。历史回放**差分证明**（旧版工具=79cebe0 版 receipt_check 独立落地自跑）：E1 abort-receipt 旧/新版均 ok（0 违规）；E2 abort-receipt 旧版 8 违规→新版 9 违规，**恰 +1=自引规则抓获 `abort-receipt.json`**（187 条 files_sha256 中唯一自引条目；其余 8 条为历史 12 位 hex 片段长度违规，与 L6-C 无关）。
6. **contract 继承面（清单4）**：其余四 case snapshots 与 L5 逐一全等、denominators 全等、rule_version=l6-20261030-batch-v1、plan_cardinality=1（单槽 bird rep1）。**但 bird pin=994be0b3…（修前）≠ 修订后 ffa7389adef32779…——FAIL，见四**。
7. **红线（清单5）**：`git status --porcelain` 仅 `?? 3-表现现场/l6-20261030-wb-gateway/`（L6 新现场，未跟踪）；自 D1 时点起对 2-用例（除 bird checker 授权修订）、truth.json、l4/l5 现场目录的提交记录=仅 D2 本身，**历史批零改动**。

## 二、证据

- 时序：git log/merge-base 输出（收据 timing 键）；身份：三方字节比对（收据 identity 键）。
- 复算：`/tmp/judge-l6/l6a-recompute.json` 全文嵌入收据 workspace_recompute 键；近似错误例与对照=near_miss 键。
- L6-C 差分：旧版工具经 `git show 79cebe0:…receipt_check.py` 落 /tmp 自跑，四组（pre/post × E1/E2）计数见收据 l6c_differential 键。
- 引用件 sha256（实算）：PREREGISTRATION、contract_L6、builder 两收据、gate——见收据 referenced_sha256。

## 三、解释

L6-A 的「纯增量」在**判分语义层**严格成立（计分路径零触及、冻结工作区零翻转），文本层 −3 行全部属于 PREREG 预先声明的非判分类目；近似错误例证明新键实际参与 gate 重算而非装饰。L6-C 的自引规则以差分方式（8→9）证明了「恰好新增抓获 AUD-L5-O1 实例且无误伤」。contract pin FAIL 的直接后果：若以当前 contract 封 E，bird 槽 gate 将以修前 pin 校验修订后 judge/checker 链→必然 fail-closed；该值与 builder 自己收据里的 post_checker_sha256 不一致，指向 prepare_design --contract-only 的 pin 生成环节而非判分器本体。

## 四、未排除因素与 FAIL 项

| # | 项 | 影响 | 下一步 | 停止条件 |
|---|---|---|---|---|
| F-1 | **contract.json bird pin=修前哈希（FAIL）** | 按现 contract 封 E 则 bird 槽必然失配 fail-closed | lead 修正 pin=ffa7389adef32779686bbe56aef7d711db1d8d1c191ff5dd389310e6c01d1910 并说明生成环节根因；judge 复验 pin+继承面 | 复验 pin==disk checker 且其余四 case 继承不变；然后本验收清单4转 PASS |
| U-1 | 历史回放未覆盖 evidence-kit 全部历史 selftest receipts（抽查口径） | 极低；规则为纯增量且 selftest 16/16 含正负例 | E 前可一次性批量回放 kit 目录历史收据 | 批量回放中除 E2 外零新增 fail |
| U-2 | 修前版 truth 相对 `__file__` 解析——本次以镜像 case 目录隔离复算，未在真 case 目录写入任何文件 | 无（只读纪律保持） | 无 | — |

## 五、可复现实验

```bash
cd /Users/b612-lp/Documents/harness-compare-bench
# ① 时序
git log --format="%H %cI" -1 8c3e4b9e595a8d49ddd10150a67cf101a8bea19c f10881ccf8380f01159c43dd09b55cb826888130
# ② selftest
python3 2-用例/bird-ca-schools-15/checker.py --selftest            # 期望 29/29
python3 1-评测方案/工具链/evidence-kit/receipt_check.py --selftest # 期望 16/16
python3 1-评测方案/工具链/evidence-kit/manifest_receipt.py --selftest # 期望 PASS
# ③ 差分回放（E2 自引抓获）
git show 79cebe0:1-评测方案/工具链/evidence-kit/receipt_check.py > /tmp/rc_pre.py
python3 /tmp/rc_pre.py 3-表现现场/中止重封档案E2-20261030T0207/abort-receipt.json   # 8 违规
python3 1-评测方案/工具链/evidence-kit/receipt_check.py 3-表现现场/中止重封档案E2-20261030T0207/abort-receipt.json  # 9 违规（+1 自引）
# ④ pin 不符复现
python3 -c "import hashlib,json;from pathlib import Path;c=json.loads(Path('1-评测方案/自动循环L6-2026-10-30/contract.json').read_text());print(c['case_snapshots']['bird-ca-schools-15']['checker.py']);print(hashlib.sha256(Path('2-用例/bird-ca-schools-15/checker.py').read_bytes()).hexdigest())"
```

附：task-18 未见于共享任务板（板至 task-16），按 lead 消息指令执行，已回报请其知悉。


## Dated：F-1 闭环复验（2026-10-30T11:48:19+08:00，D3=1211b5b）

- **根因（lead 如实声明，与其 diff 相符）**：prepare_design.py 首版 --contract-only 只刷新顶层 checker_sha256 映射，漏了 case_snapshots 内嵌 per-file pin；缺陷版 contract 保留于 f10881c 可考，未销痕。
- **独立复验（全绿）**：①snapshot pin==顶层映射==盘面==`ffa7389adef32779…`；②顶层映射四 case==disk==L5；③snapshot files 8 件 disk 全 match，L5 相比仅 `checker.py` 与 `spec.md` 两件变化——**修订面恰为二件**；④truth/instruction/case.json/inputs（4 件递归）与 L5 逐字节一致；⑤case_version 新值 `bird-ca-schools-15@sha256:4ea5ee92…e35bdf8c`；⑥fail-closed 三断言（非 bird 重算==L5 / bird 修订面恰二件 / 快照 pin==顶层映射）在 prepare_design.py case_snapshot 实现核到。
- **判定**：清单 4 转 **PASS**；本验收七项全 PASS。F-1 由 judge 独立验收抓获→lead 修复→judge 复验闭环，全程留痕（f10881c→1211b5b）。
