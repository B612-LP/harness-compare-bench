# 自动循环 L1 验收报告（2026-10-29，lead 出品，循环停止点）

按用户授权节奏（2026-10-29：全自动运行、每完成 1 个闭环停止交验收），L1 三工作包全部收束。**循环就此停止，等用户放行再开 L2。** 周报未写（用户保留项）、CHANGELOG 未动（用户保留项）。

## 一、三包结论

| 包 | 交付 | 结论 |
|---|---|---|
| A n=3 可重复性（r1031，20 场） | [RESULTS.md](<../../5-评测报告/可重复性-n3-2026-10-29/RESULTS.md>)（judge 独立验收）+ [现场](<../../3-表现现场/r1031-variance-n3/README.md>) | 20/20 全 valid 零污染零重试。**主判据 gap₀=0.74：codex spread 21.11、dsh spread 3.70，均 ≥0.74 →「r1030 产品差与重复性方差不可区分」**；真实单场产品差比重复波动小一个数量级以上（敏感性口径比值 1.46/8.31，未勘误时会被反向误读）。codex headline {3,3,4}（dab rep3 翻绿 70→80），dsh {3,3,3}。n=3 只描述不排名 |
| B v2 全交付对抗盲审 | [AUDIT.md](<../../5-评测报告/对抗性盲审-2026-10-29/AUDIT.md>) | **0 blocking**；D1/D4 已在循环内修正，D2/D3 入问题池。判卷合同本体经敌意复核无缺陷（17 pin/10 slots/220 指针/逐场重算） |
| C WB 请求级补证 | [wb-preflight-r2.json](<../../1-评测方案/准入预检-2026-10-29/wb-preflight-r2.json>) + evidence-r2/ 14 文件 | 收场(a) 证据补齐：**未知① answered_r2**——WB 模型面绕过一切代理直连 `www.workbuddy.cn`（腾讯 EdgeOne，双 POP 与 resolver 精确匹配 + REA 静态端点表互证），**非 api.deepseek.com**；**未知② answered_route_level_r2**——`deepseek-flash`(直连) ≠ `deepseek-v4.1-flash`(网关计费条目)，路由级不等价。裁定维持 not_admitted_to_formal_a1（理由升级为路由不同正面刻画），进 A 组留未来正式批次。产品本体零改动，环境全还原有证明 |

## 二、循环机制的自证（本轮最有价值的部分）

预注册封印→judge 自检→auditor 盲审的**三方独立收敛**抓住了一个传导性数字错误（r1030 DSH 总分 414.07 实为 444.07，gap₀ 30.74→0.74，经 AMENDMENT-1 修正，D4 勘重后时点只锚 git 记录）；cargo r2 integrity 误报经「亲核证据→裁定→corrections 落盘→judge 行级复核制衡」闭环；两个 builder 的缺陷披露（r1031#1 继承缺陷、dabstep r3 usage 投影差异）均如实入册。**防过拟合闸全部实际生效，无一豁免。**

## 三、L1 分账（老师要求②）

| 类别 | 计数 | 去向 |
|---|---|---|
| product_run | 20（codex 10 + dsh 10） | `3-表现现场/r1031-variance-n3/` |
| self_test | runner 自测（dsh selftest/ + tools-codex 记录）+ 验收工具 r1030 自检 | 各批次目录 + `5-评测报告/可重复性-n3-2026-10-29/` |
| interface_preflight | CLI×2 + WB 包C 探针 | 各 preflight/ + 准入预检 r2 |
| 离线复算 | 包B 盲审全程 + 包A judge 重算（150 分值） | AUDIT.md / RESULTS.md |
| 判卷回归 | 本轮无判卷器修订（合同冻结），无新增 | — |
| 裸模型探针 | 无新增 | — |
| 其他 | 验收裁定 1（cargo r2 benign-reviewed，经 corrections）；修正案 1（AMENDMENT-1+D4 勘重） | 各在案 |

## 四、问题池（L2 候选输入，均含影响/下一步/停止条件，详见各文件）

1. runner schema：`registered_at` 必备字段（D1 裁决）；收据精度统一（D2）；schema 跨 builder 对齐（D5）；
2. v3 合同或勘误版：work_registry 指向 v2 台账、7 条收据入机读六账（盲审 D2）；
3. B13a 验收回放收据与实并合同不符 + README 15/24 vs 16/24（盲审 D3）；
4. r1030 README「tools/lab.py 已修」声明修正（r1031#1 波及）；
5. freeze.lock「活文档 pin」与「合同 pin」分列管理（D4）；
6. provider-cache 语义请求级验证（cache_creation 全 0 之谜）；runner 代际（r1030/r1031）对 spread 的贡献消融；
7. WB 若进 A 组 → 需独立正式批次+slots；O6 命名前缀与历史 yuanbao run_id 撞名。

## 五、循环台账

预注册封印 `be39fc2`（13:22:39）→ 章程 `3695f5a` → AMENDMENT-1 `292cf18`/`474a8ed`/`999d345` → 包B `5f2884d` → 包C `87299ef` → 运行里程碑 `d57125a` → 版本映射 `91a29f5` → 本验收报告对应提交见 git log。全部分支 `loop1-2026-10-29`。

**下一步：用户审阅本报告；放行后 L2 从问题池选题，照章办事（预注册封印→执行→独立验收→停止交报告）。**

## 六、合并后校验事件（封印纪律自证，2026-10-29 14:55）

PR #3/#5 合并后的例行 sweep 抓到：**v2 freeze verify exit=2，原因 `sealed file drift: 准入预检 README.md`**——包C 的 r2 增补节经 lead 授权写进了封印清单内的文件。judge（D4）与 auditor 均标记过该 pin 漂移，但当时只做了逐 pin 哈希对照、未跑 verify CLI；直到合并后全量 sweep 才暴露为硬失败。处置：README.md 字节级还原至封印版（`0511cdc` 谱系），r2 增补节**一字未改**迁出至未封印的 [README-r2.md](<../../1-评测方案/准入预检-2026-10-29/README-r2.md>)；复跑 verify `ok=true`。同时复核正式表结构无误（`groups.A_same_model` = 10 行，首次检查读错键路径为虚惊）。教训入池：封印后对 pinned 文件的一切编辑必须走「还原 + 旁挂」；「活文档 pin 与合同 pin 分列」保持为 L2 项。本节随修复 PR 一并入 main。
