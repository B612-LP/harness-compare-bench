# 五案例来源与复用边界 · 2026-11-05

本页把五类用例**已经记载的来源、许可声明及改写范围**集中到一处；[机器清单](<sources.json>)保留原文行、文件SHA-256和未核项。它是现状索引，**不是新许可证、授权收据或法律合规结论**。

本次没有取得或核验完整上游许可/版权通知副本，也没有替维护者选择原创工具与报告的统一许可；这两个剩余边界**未解决**。新增授权为false，正式25格、A/B/W、n、历史得分、gold及判卷不变。返回[用例索引](<../README.md>)。

## 1. 五类来源：声明不等于整仓统一授权

| 用例 | 既有来源及许可声明 | 原样、改写与适用范围 | 回到已有证据 |
|---|---|---|---|
| BIRD | BIRD mini_dev / california_schools；数据声明CC BY-SA 4.0 | 中文题面、q26 SQL/口径版本化修改，数据库等价重导出；规格声明inputs数据库与gold SQL同源共享。checker是本仓自建，不是官方脚本移植。 | [规格:184–193](<../bird-ca-schools-15/spec.md>) |
| DABstep | Adyen / Hugging Face；CC-BY-4.0 | 题目去answer、6个context文件原样；中文任务书；官方scorer六函数移植，其余逻辑和文档自写。 | [规格:114–121](<../dabstep-payments-10/spec.md>) |
| Exercism | Aider打包、Exercism Python及problem-specifications；既有MIT声明 | 测试/骨架原样，文档中文重写，checker和参考解本仓新写。打包来源不能替代原始练习/测试来源。 | [规格:91–98](<../exercism-py-6/spec.md>) |
| LCB | LiveCodeBench v6仓库声明MIT；AtCoder另为题面与测试原始出处 | 中文题面、原样测试、标准库重写评测逻辑；**仓库MIT不扩给AtCoder素材**。“教学用”不是本次已核授权依据。 | [规格:93–105](<../lcb-recent-hard-4/spec.md>) |
| Cargo | Terminal-Bench cargo-flight-dispatch；既有Apache-2.0声明 | 去Docker/uv/pytest、中文题面、路径调整；参考实现与27断言从上游测试移植，原件已有归档。 | [规格:78–80](<../tb-cargo-plan/spec.md>) |

表内行号用于源码与机器核对；规格链接打开渲染页，不把行号片段当作精准落点。

上表只转录仓内既有声明；不宣称已重新确认上游站点、当前许可证或完整权利链。DAB规格已有[CC BY 4.0通用条款地址](https://creativecommons.org/licenses/by/4.0/)；Exercism规格另列[原始测试数据项目](https://github.com/exercism/problem-specifications)。LCB四题的AtCoder原作链接均在其规格中，清单以其中一题作代表，不把LiveCodeBench聚合仓库当作所有素材的原始权利方。

## 2. 已知、未核与null分别是什么

- `declared_license`是**既有文件中的许可声明**；机器写法统一为CC-BY-SA-4.0、CC-BY-4.0、MIT或Apache-2.0，不表示本索引新授予这些权利。AtCoder项的`not_established_by_cited_material`仅表示本次引用未确立其适用许可，不等于断言禁止使用或侵权。
- `license_scope`按来源分层：BIRD数据/题目/gold；DAB数据/题目/移植函数；Aider打包与Exercism练习/测试；LiveCodeBench仓库代码与AtCoder原作；Cargo上游任务/参考实现/断言。它不替原创代码/报告或全部历史材料设定许可证。
- `upstream_version.status=unknown`仅指**与原始许可/通知核对绑定的上游版本或commit未核定**。不是抹去已有v6、读取日期、题目日期或BIRD数据库发行快照；那些仍按原规格阅读。
- `upstream_terms.status`及`notice_status`为`not_locally_verified`：本索引没有已核验的上游完整条款/通知副本。`original_license_url`专指与取得上游版本绑定的原始许可文件地址，不是项目主页或通用CC链接；未知地址、版本绑定副本路径及SHA保留null，不杜撰版权人、年份或NOTICE。
- 这不声称全仓“没有任何许可说明”，也不声称每个上游一定存在NOTICE文件；本次未核的是其实际适用条款、通知及可靠副本。

若后续获准补齐核验，需保留原始来源项目/数据集/原作URL、适用版本/commit或等价不可变发行标识、原始许可及版权通知位置、真实本地副本与SHA及核验记录。只核SHA证明存储字节，不证明授权主体或法律合规；本次没有联网补取这些材料。

## 3. 原创材料的选择仍由维护者决定

清单的`original_assets`保持`license_status=not_selected`、`license=null`及`owner_decision_required`。只有维护者可决定对其拥有相应权利的原创工具、报告和文档采用何种许可及范围；**本页不替其选MIT，也不替第三方重新授权**。

`license_grant.new_license_granted=false`且`legal_compliance_certified=false`。unknown或null不等于已给出开源授权，更不等于合规问题已经解决。公开可读、来源已署名、可复算与复用授权是不同事实。本索引不处理产品输出、第三方对话轨迹、个人数据或全部历史代码的再授权。

## 4. 离线只读核对

[校验源码](<verify.py>)与[测试源码](<test_verify.py>)采用标准库、固定本页/清单及五份规格的字节和逐行引文；纯语义检查另核声明范围、未知状态与不授新权边界。不运行原checker、解法、候选或产品，不发网络/模型请求，不写仓库。

在仓库根执行：

```sh
python3 -B '2-用例/来源与复用边界-2026-11-05/verify.py' --root .
python3 -B '2-用例/来源与复用边界-2026-11-05/test_verify.py'
# 优化模式同样不能跳过数据检查：
python3 -B -O '2-用例/来源与复用边界-2026-11-05/verify.py' --root .
python3 -B -O '2-用例/来源与复用边界-2026-11-05/test_verify.py'
```

核对成功只表示**固定公开声明与当前索引一致、边界没有被改写**；不认证原始授权真实性、完整通知已补齐、维护者已选许可或全仓法律合规。测试中的临时合成负例不是产品样本。本次解决的是现状可以一处追溯，不把仍待核的条款及仍待选择的原创许可算作完成。
