# L6 独立复核（task-19）

离线复算 / 判卷回归；independent-reviewer；仅本目录新增，原件只读、Git 只读、零模型、零网络。不计新增产品运行，也不重写 L4/L5 结论。

## 一、观察

**655/655 个独立核验谓词成立，0 个未解决差异；live_doc_drift=[]。**

| 清单 | 独立实测 |
|---|---|
| L6-A 原脚本 | 字节未改；非 main 加载后仅四常量迁址，原 main 15/15 断言与档案逐项 / 完整字段一致（生成时刻除外） |
| checker 自测 | 实跑 exit0，29/29；不把自测例数计作产品运行 |
| 历史两工作区 | Git 79cebe0 修前 checker 独立 case 布局 vs 修后 case，各自重判 L5 E3 / E2 中止的两个 wb-bird 工作区；逐个判分字段零翻转，键集恰增 n_tasks/guards_used |
| L6-C 自测 | receipt_check 16/16；manifest_receipt 6/6；均自跑，不采信归档 PASS |
| 真实历史回放 | 修前 / 修后规则分别读取 E1/E2 中止收据：E1 两版均 ok，E2 新版明确抓获 self-reference；E2 旧有 UUID 词法违规单独保留，不当新规则功劳 |
| D3 contract | bird 盘面 checker / case_snapshot 顶层及 files / checker_sha256 三方相同，完整 SHA 为 ffa7389adef32779686bbe56aef7d711db1d8d1c191ff5dd389310e6c01d1910；其他四 case 的 JSON 原始子树字节与 L5 一致，全部五 case 文件清单与 digest 现算一致 |
| E3 封印 | 独立枚举28源+5 external，逐件磁盘 / E3 blob / manifest SHA，三设计原件 D3/E1/E2/E3/磁盘，Git祖先链、旧binding / 旧manifest与各committer时刻均通过 |
| gate CLI | verify-execution ok=true；admission formal_admitted=1/1 / fails=[]；有效逐槽字段与原收据一致 |
| 绕过负例 | 6/6拒绝：plan磁盘漂移、错plan绑定SHA、错seal、错registered_at、release=false、缺mandatory external（对最后一个显式注入哈希自洽E manifest，以穿过早期SHA检查） |
| 真实槽抽验 | checker.stdout == score.raw_checker_output 重新规范序列化的每个字节；独立 earned=15 / possible=15，8dp=100.0；独立枚举首个调和 guards 与真实raw/meta一致 |

计数拆分：离线复跑与得分 / 负例谓词 129/129；独立封印 / case / 文件清单 / 起止SHA谓词 526/526。这是机械核验谓词总数，**不是独立统计样本量或新增调用次数**。checker29例仅以概览计数核对，不额外重复累加29；其余细分计数见收据。

## 二、证据

主汇总：[receipt.json](<5-评测报告/L6独立复核-2026-10-30/receipt.json>)；全量独立绑定：[binding-check-01.json](<5-评测报告/L6独立复核-2026-10-30/binding-check-01.json>)；离线执行：[offline-work-receipt-01.json](<5-评测报告/L6独立复核-2026-10-30/round-02/offline-work-receipt-01.json>)。

固定临时树 205 个文件、71,096,438 bytes；211 个原件 / 外部pin保护联合集最终无SHA漂移。完整路径和每文件字节/SHA位于 [snapshot-01.json](<5-评测报告/L6独立复核-2026-10-30/snapshot-01.json>)。清单不省略失败、没有把 unknown 变0。

批准的四常量迁址是 **非零注入**，并非宣称无任何运行时适配：原脚本 ROOT/CHECKER/SOURCES 指向临时同布局副本；ARCHIVE 指向本独立目录。源脚本字节、函数体、断言未改；原收据仍在判卷修订档案，两份独立复跑收据留在本目录及 round-02，均 exclusive create。四常量前后值由执行收据完整列出。

E3 完整 seal `aae5edacf959b93d833d9ef283085e891ab4361f`，D3 `1211b5b787049b9367af8b85aa99ab15d9d7104c`；registered_at=`2026-10-30T12:23:46+08:00`，精确等于 Git %cI；manifest完整 SHA `4e26e512af89d1fa70c3e66f6b9e31401470404c9a96df8391790b761415908b`。两次废seal的旧manifest/binding已从Git读取并单独保存，未使用当前磁盘字节强配历史manifest：

- E1 `1c27a6b6d15986868d3cc73c6420fbf8708a45bb`，registered_at=`2026-10-30T11:52:45+08:00`，28源 / 3外部；见 [E1-git-binding.json](<5-评测报告/L6独立复核-2026-10-30/E1-git-binding.json>) 和 [E1-git-manifest.json](<5-评测报告/L6独立复核-2026-10-30/E1-git-manifest.json>)。
- E2 `46d64eefcbe09515ee6a357873092c8f10c50625`，registered_at=`2026-10-30T12:15:41+08:00`，28源 / 3外部；见 [E2-git-binding.json](<5-评测报告/L6独立复核-2026-10-30/E2-git-binding.json>) 和 [E2-git-manifest.json](<5-评测报告/L6独立复核-2026-10-30/E2-git-manifest.json>)。
- E3 `aae5edacf959b93d833d9ef283085e891ab4361f`，registered_at=`2026-10-30T12:23:46+08:00`，28源 / 5外部；见 [E3-git-binding.json](<5-评测报告/L6独立复核-2026-10-30/E3-git-binding.json>) 和 [E3-git-manifest.json](<5-评测报告/L6独立复核-2026-10-30/E3-git-manifest.json>)。

标准证据行（原 evidence_line 工具脚本生成）：

```text
5-评测报告/L6独立复核-2026-10-30/snapshot-01.json · 5c03391b · 39892B · 2026-10-30T12:38:17+08:00
5-评测报告/L6独立复核-2026-10-30/round-02/offline-work-receipt-01.json · 3ea6dc74 · 68629B · 2026-10-30T12:38:17+08:00
5-评测报告/L6独立复核-2026-10-30/binding-check-01.json · 11d3412a · 202415B · 2026-10-30T12:38:17+08:00
5-评测报告/L6独立复核-2026-10-30/round-02/l6-meta-recompute-receipt.json · a799c4c2 · 3195B · 2026-10-30T12:38:17+08:00
5-评测报告/L6独立复核-2026-10-30/round-02/gate-verify-execution-reproduced.json · 8ebab4da · 3788B · 2026-10-30T12:38:17+08:00
5-评测报告/L6独立复核-2026-10-30/round-02/gate-admission-reproduced.json · bacef2c9 · 2340B · 2026-10-30T12:38:17+08:00
5-评测报告/L6独立复核-2026-10-30/sandbox-policy.sb · f11522b6 · 652B · 2026-10-30T12:38:17+08:00
5-评测报告/L6独立复核-2026-10-30/prepare.py · 727953b7 · 4893B · 2026-10-30T12:38:17+08:00
5-评测报告/L6独立复核-2026-10-30/offline_work.py · dbd9c56b · 14509B · 2026-10-30T12:38:17+08:00
5-评测报告/L6独立复核-2026-10-30/offline_work_v2.py · dc220830 · 1100B · 2026-10-30T12:38:17+08:00
5-评测报告/L6独立复核-2026-10-30/binding_check.py · 3ffda264 · 12471B · 2026-10-30T12:38:17+08:00
5-评测报告/L6独立复核-2026-10-30/summarize.py · 5a3c2c49 · 12933B · 2026-10-30T12:38:17+08:00
5-评测报告/L6独立复核-2026-10-30/receipt.json · cda4408e · 6197B · 2026-10-30T12:38:17+08:00
```

## 三、解释

1. L6-A 的证据支持“元数据新增两键、这两个历史工作区判分不变”，而不是所有潜在输入均不变的证明；原 script 的 answers_file.note 仅路径占位比较沿用，独立重判也只归一真实搬迁相关 run_dir 与该 note，不遮盖分数/checks/failed_questions 等值差异。
2. L6-C 的自引用排除可由真实 E2 反例触发；新生成器不把自身列入清单。旧 E2 自哈希不符没有被改成真，也没有通过回放去改写原记录。
3. gate 正向 PASS 与独立盘面/Git/hash证据相互印证；负例使用固定副本，修改的只有测试世界。缺external世界的manifest读取是显式受控注入，不冒称真实旧E blob含缺项。
4. 真实 score-receipt.score.earned=1 是 binary reward，不是15题正确数；实际正确数由 checks 排除guards后独立数出15。guards推导采用实现声明的“按索引序首个调和组合”，本满分样本下并非唯一数学解；结果一致不证明任意检查顺序都能准确恢复语义guard集合。

## 四、未排除因素

- 环境是新tmp/独立cwd/最小显式env/Python隔离/deny network/原件写拒，不是新机器或空HOME。HOME为历史绝对external pin保留；只解码公开代码与获授权判卷资产，凭据配置仅做原始字节SHA，不打印SQL答案/密钥/会话原文。没有联网校时，Git时间只是本机历史一致性，不是可信第三方时钟。
- 两次废seal的“零消耗、pre-claim拒绝”是原作者记载；本复核独立核Git旧值、源码差分、已归档拒绝记录，不具备追溯证明过去所有远程副作用不存在的网络观测。不能把当前runs一槽或源代码哈希当历史零调用证明。
- manifest明示未锁完整传递产品依赖。任何源/pin变化、判卷资产SHA变化，或新增槽位/输入不属于本意见；下一步需重封重审，停止条件是本清单任一输入漂移或证据身份不一致。
- 正向gate包含原meta污染裁定；本任务未重新逐句独立做语义污染调查，也不从formal1/1推导产品排名/广泛能力、货币成本或历史失格槽自动恢复。
- 初轮审计者错误假设WB meta具有CLI专用weighted_8dp键，产生KeyError并中断汇总；已保留首代码、stderr及先前完整复跑输出。第二轮只将该审计断言改为实际WB meta.weighted与score.reported的8dp比较，重跑新输出根round-02，不改被测源码/原meta，也未把此审计者错误列为产品缺陷。

## 五、可复现实验

只在新的独立工作副本 / 输出路径复现，保持仓库相对布局，脚本会拒绝覆盖现有输出。准备入口创建固定tmp、旧checker独立case和SBPL；离线worker必须经同一deny-network策略及最小环境运行。首次程序与只修审计断言的v2入口均保留，v2复用原worker其余代码；精确迁址清单在机器收据。

```sh
/usr/bin/python3 -B '5-评测报告/L6独立复核-2026-10-30/prepare.py'
# 使用snapshot返回的temporary_root及sandbox-policy.sb，不能猜旧tmp地址。
# env -i HOME=... PATH=... TMPDIR=<newtmp>/tmp GIT_DIR=<readonly-repo>/.git ...
# sandbox-exec -f <newtmp>/offline.sb python3 -I -B .../offline_work_v2.py
# sandbox-exec -f <newtmp>/offline.sb python3 -I -B .../binding_check.py
# 最后只读汇总：
/usr/bin/python3 -B '5-评测报告/L6独立复核-2026-10-30/summarize.py'
```

清单全量对账和最终重哈希均基于明列的输入，不扩大遍历其他用户session；原件不改、旧失败不删、不重跑模型。要得出新结论必须使用新路径收据，不能复用旧PASS替换新差异。

live_doc_drift=[]
