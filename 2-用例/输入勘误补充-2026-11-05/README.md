# MCC同code标签冲突：派生输入勘误补充

2026-11-05。**本页记录同一类文档标签冲突的三个例子，不据此认定产品缺陷、修订评分或增加产品样本。** 旧输入、金标、成绩与历史正式25格不改，本补充不是历史产品当时收到的输入，也不是上游发布的更正。

## 三例对照：保留原code，不反向改题

[旧手册:44、49](<../dabstep-payments-10/inputs/manual.md>)中的示例标签，与手册自身指向的[同包CSV字典](<../dabstep-payments-10/inputs/merchant_category_codes.csv>)的同code条目不同。CSV表头为`,mcc,description`，**MCC在第二列，第一列只是索引**。

| 保留的MCC | 旧手册标签与行号 | 同code的完整字典标签与行号 | 仅辅助的反向字典条目 |
|---|---|---|---|
| 5451 | Automated Fuel Dispensers；44行 | Dairy Products Stores；497行，首列495 | 5542：Automated Fuel Dispensers；506行 |
| 5812 | Automotive Parts and Accessories Stores；44行 | Eating Places and Restaurants；537行，首列535 | 5533：Auto Parts and Accessories Stores；504行 |
| 5521 | Motor Vehicle Dealers - New and Used Cars；49行 | Car and Truck Dealers (Used Only) - Sales, Service, Repairs, Parts, and Leasing；501行，首列499 | 5511：Car and Truck Dealers (New and Used) - Sales, Service, Repairs, Parts, and Leasing；500行 |

反向5542/5533/5511只帮助定位描述，不替代原5451/5812/5521，不修改费用规则。Auto与Automotive不是逐字相同；5521的Used Only也不能省略成New and Used。这里不认定虚构ABC商户的真实类别，不认证外部通用MCC标准或官方唯一分类。

[手册:53](<../dabstep-payments-10/inputs/manual.md>)将该CSV称为complete list，但这**不是已有的“冲突时字典优先”规则**。本补充新采用“按本仓固定字典查阅”的解释政策，让读者看见并定位同code冲突；不把新政策冒充历史合同。

## q1305：只登记载荷，不重算

[题文:5](<../dabstep-payments-10/inputs/questions.jsonl>)使用Eating Places and Restaurants，与字典5812同名；[旧金标:48](<../dabstep-payments-10/truth.json>)的`/gold/1305`原载荷为字符串`0.123217`。本补充未计算费用、选择费率、核对产品答案或认证该金标正确/错误。描述相关不等于某个历史产品读过错例或因此失分，实际影响仍为not_established。

[旧规格:8、120、175](<../dabstep-payments-10/spec.md>)保留按手册作答、context原样及历史裁定边界。本补充不重开q49、q2697，不修改旧报告、判卷器、现场或奖励。本页所说gold_changed=false仅表示此次不改金标字节，不是数值正确性认证；不承诺未来产品行为或得分无变化。将本补充提供给未来产品属于**新的输入/提示条件，须另行登记与预注册**；本页不授权启动运行。

## 固定来源与机器复核

[errata.json](<errata.json>)记录三行同code/反向辅助映射、源位置、五个旧源SHA256及上述未知边界。[verify.py](<verify.py>)只读以下五个固定旧源与派生JSON，不搜索目录、不读支付流水或商户个体、不读产品答案/轨迹、不执行旧代码、SQL、网络或模型。

| 固定旧源 | SHA256 |
|---|---|
| [手册](<../dabstep-payments-10/inputs/manual.md>) | `bb7f4ca6fdc759af1f480702b3a3b12e17e9293b0d38a1dbfbbc8ffc1e572d2c` |
| [MCC字典](<../dabstep-payments-10/inputs/merchant_category_codes.csv>) | `83247d79f5ddcdd180e02f184b644f4912731942a2fc58d91f2a06b911d04b41` |
| [题文](<../dabstep-payments-10/inputs/questions.jsonl>) | `d99d3109e216b8e091d478602fce7cb687b47c40338ce8d016300c9ee7013730` |
| [金标载体](<../dabstep-payments-10/truth.json>) | `9e6e395fc7b0e5cf60238b8c3ab30fdaa399422fc047f554f0198488156e46d8` |
| [规格](<../dabstep-payments-10/spec.md>) | `ef0f822d01b56089bb6fe56f1a9a6bcf7f4a1ee9796689908c8ac04a45c53852` |

Python 3.9+，仅标准库。以下为公开目录投放后、从仓库根运行的复核命令，不表示本文撰写时已经执行：

```bash
python3 -B '2-用例/输入勘误补充-2026-11-05/verify.py' --root .
python3 -O -B '2-用例/输入勘误补充-2026-11-05/verify.py' --root .
python3 -B '2-用例/输入勘误补充-2026-11-05/verify.py' --root . --rebuild
python3 -B '2-用例/输入勘误补充-2026-11-05/test_verify.py'
python3 -O -B '2-用例/输入勘误补充-2026-11-05/test_verify.py'
```

默认root按公开目录位置取脚本的parents[2]；自定义root须为非链接的实际仓库目录。`derive(root)->dict`与`--rebuild`仅输出JSON，不写文件；默认verify比较严格类型的派生JSON与重建事实。所有业务守卫使用显式异常而非assert。拒绝JSON重复键、NaN/Infinity/溢出浮点、bool冒充整数、非规范/越界路径、符号链接与多硬链接；单文件上限4MiB，前后重读并比较字节和文件身份/mtime/ctime。CLI失败非零且不输出成功JSON。

[test_verify.py](<test_verify.py>)只编译固定SHA的新验证器字节，不使用Loader或旧仓库模块，也不生成pyc；可用显式`MCC_TEST_ROOT`指定同样固定五源的实际根。测试分为固定源pin拒绝、直接纯语义负例、路径/JSON/稳定性层；错code、行索引、错完整标签、漏第三例、反向替代、伪造历史priority/金标已修/未来无影响等不依赖hash不匹配才能拒绝。重新给错误派生件计算自身hash也不能使语义获准。测试只在自有临时目录造合成变体，软件检查数不是产品n。

信任边界：需先审阅新代码及固定SHA。文件系统/标准库/哈希和执行环境受信，前后检查不构成OS sandbox或原始档案真实性认证；root及路径查验不保证抗恶意并发文件系统。固定五源不等于全仓旧文件保护，其他旧文件是否保持须由独立发布清单核对。本补充不提供第三方见证、完整上游权利链、新许可授予或法律合规认证。**本文编写时仅完成静态实现；以上命令不等于第三方见证或历史产品复测，实际复核须按所列代码与固定来源执行。**
