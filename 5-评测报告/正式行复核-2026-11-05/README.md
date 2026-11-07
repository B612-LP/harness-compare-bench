# 正式 25 行：公开离线来源闭合复核（2026-11-05）

**现有数字未发现漂移；补的是公开可执行的来源闭合能力，不是重新评测/重新判卷。** 正式每产品×每题 **n=1**；A10、B10、W5 分轨，不能拼五款总排名。

## 一条命令，无私档/网络/第三方依赖

在公开仓库根目录，Python 3.9+：

```sh
python3 -I -S -B 5-评测报告/正式行复核-2026-11-05/verify.py --root .
```

成功退出 0，stdout 是 JSON，包含 `rows` 的 **25 行逐来源映射**：正式表路径/指针、事件ID/run ID及身份来源、grade数值与收据指针、合同配置与checker/truth/case版本字段、逐来源哈希状态、v1.8的行号/单元格；另有5条唯一替代关系和402条历史来源库存。失败退出1，在stderr给出错误。默认不落盘、不改仓库；不调用Git、产品、模型、网络、候选程序、旧checker或旧运行器，不导入任何历史仓库代码。若需保存stdout，调用者可重定向到自己的新文件；保存副本不是新的可信锚。

[复核源码](<verify.py>)；[负例测试](<test_verify.py>)：

```sh
python3 -B -m unittest discover -s 5-评测报告/正式行复核-2026-11-05 -p test_verify.py -v
python3 -O -B -m unittest discover -s 5-评测报告/正式行复核-2026-11-05 -p test_verify.py -v
```

所有测试只复制公开输入到临时目录，修改/删除/符号链接仅作用于其临时副本。生产校验不用`assert`，`-O`不削弱拒绝条件。测试目录位置与`--root`无关，直接用公开克隆自带文件，无本机绝对路径或私有依赖。

## 实际闭合什么

1. 从六代官方表精确消费准入ID：不吞重复、不丢无法解析ID；按官方组别连接现有product_run事件。分开正式25、直接尝试30、唯一替代5，观察/研究变体不准入。
2. 连接事件顶层身份、identity及来源指针；必需事实字段不得静默消失，`known`必须有非null值和refs，`unknown`必须显式null且保留refs列表。逐事实和五个准入门的available JSON pointer核值，正式准入五门必须已知且为true，不把source hash匹配当作值相等。连接grade原分子/分母/reported/reward与其公开收据，再检查分数算术；对收据信封中所有可用case/product/run ID与事件强绑定，不能用另一run的同分收据替换。
3. 连接各代config的rule_version、checker/truth SHA、case版本/manifest SHA，核事件事实与grade的合同字段；不把多代合同混成一个版本。
4. 连接旧ledger的30条直接尝试、25正式副本逐字段一致性和正式子图：每次尝试的slot/admission，五条唯一替代的登记来源、父场拒收状态及同轨同产品同题关系。当前30条尝试的config均绑定登记计划，包含无前承首发，故selection与有效plan_source不得缺失或为null；逐selection核plan_pointer指向的event身份/登记字段，并接config中的slot/plan绑定（不推广为臆造其他历史未登记事实）；替代边转换集合前拒绝重复，准入边核目标与source的path/SHA/pointer。**不是重生成整个含重复观察的522节点/628边旧图。**
5. 解析[v1.8正式成绩节](<../竞品评测报告-v1.8.md#3-正式成绩25-格均-n1>)的25个分数、已写分数分式、W逐行headline和各产品汇总，与来源复算相等；在转dict前拒绝重复case行，不丢弃冲突行；不改原报告。
6. 逐hash核[历史来源账](<../证据口径-2026-11-03/source-ledger.public-derived.json>)的402项：397现存字节匹配、5份历史原件缺失单列；不从汇总反填每次产品版本。B重复观察的40条version未知保持未知，不提升正式n。
7. （2026-11-08 适配，schema v1.1）对[现行报告版 v1.9 正式成绩节](<../竞品评测报告-v1.9.md#3-正式成绩25-格均-n1>)执行与第5条相同的逐格与逐产品汇总机器闭合，并断言 v1.8/v1.9 两版逐event单元格文本一致；v1.9 是活版文档，**只做数值闭合、不做字节pin**（避免未来报告修订使本工具失效），输出`report_editions`区分两种语义，逐行附`report_current`。v1.9 分数/汇总漂移由其自身数值校验拒绝，保值的格式漂移由两版一致性断言拒绝。
8. （2026-11-08 适配，schema v1.2）§4.4 盲区引用数字闭合：从[读取检测校准](<../../3-表现现场/r20261104-read-detection/read-detection.json>)28 trials独立重算（FD 8/12/4/4、vnode 1/19/0/8、短时双漏12、open-only FD误报4、`product.file_read_denominator`）与[桌面观测汇总](<../../3-表现现场/r20261104-desktop-observation/fd-summary.json>)（1124样本/0命中/errors.none==samples/exit0==samples）三方一致——v1.8 与 v1.9 两版 §4.4 解析引用 == 校准包重算；两包自身工具仍是其数据真实性边界，本闭合仅做引用一致性（consistency-only），输出`blindspot_closure`。

当前输出摘要：

| 轨 | 产品 | 正式格 | recorded weighted合计 | recorded headline |
|---|---|---:|---:|---:|
| A | Codex | 5 | 444.81 | 3/5 |
| A | DSH | 5 | 444.07 | 3/5 |
| B | 元宝 | 5 | 213.33 | 2/5 |
| B | 豆包 | 5 | 406.85 | 3/5 |
| W | WorkBuddy | 5 | 434.07 | 3/5 |

合计只作分轨来源核对，异构题合计与跨轨数字不支持稳定产品总排名。`reward`是历史收据记录，不是本工具执行checker重判；本工具没有验证候选代码是否正确，也不恢复不可公开的真值/原始现场。

## 可信锚和不能证明的事

固定锚在经审阅的`verify.py:TRUSTED`代码内，而不是由旁边可重封的manifest自荐：

- 历史ledger SHA256：`9784e714cd0134cece788fb3d67b080820dcbc0b95be29761123ab623deea420`。
- v1.8 SHA256：`d1e303afae28570a916fe088b08ff2d3a6a2a0312b031dd9ad2fbec98dd0a3d5`。

ledger固定字节提供402源pin，再逐文件/逐指针复核。仅改source后重封ledger/派生件不能通过；修改验证器本身则是修改信任根，必须另行代码审阅，不属于本工具能够自证的真实性。哈希链不是第三方签名，不认证私档raw、采集时间、后端模型身份或全盘读取真相。

部分历史score receipt没有case/product/run ID信封；这些行在`score_sources.ownership_check`明确标为`no_envelope_identity_trusted_assignment_only`，只能由审阅固定ledger的来源赋值及available指针相等来连接，不冒称从缺失信封独立认证身份。可用信封字段会逐一校验并列在`envelope_identity_fields_checked`，路径命名本身不充当身份真相。

`ok=true`精确表示**经审阅公开字节及其记录相互一致**，不是“完整历史验证通过”。输出固定保留`complete_historical_verification=false`；5份缺原件与40条未知不洗绿，历史不存在的原件不能静默补造。既有v1.6/v1.7的旧封印局限及固定commit说明不变。本工具不重封任何旧ledger/table/report，不追认原历史verify或第三方见证，也不把B/W当A同模型。

## 负例能力，不夸大拒绝机制

43项测试明确分层（登记缺失测试含3个子例；2026-11-08 适配后共47项（43+4）；同日 schema v1.2 再加 §4.4 闭合四条负例后共51项（47+4）：现行版缺失/分数漂移/汇总漂移/保值格式漂移+§4.4 现行引用漂移/审阅版引用漂移/§4.4 节缺失/校准数据漂移）：

- **生产固定pin拒绝**：源分数修改、源修改后重封ledger、派生成绩重封、v1.8字节漂移、缺关键事件/grade收据；不是声称这些靠判卷语义重算拒绝。
- **独立数据语义拒绝**：测试中专门临时关闭字节比较（仅test的mock，无生产CLI开关），基线仍过，再检验孤儿/重复/缺officialID、跨轨、run ID替换、算术自洽但与receipt不同的score、合同/事件checker改变、空score refs/坏pointer、同分跨run收据替代、必需事实缺失/known无value与refs/错误state/unknown伪装有值、门false与无效指针/来源也false但仍企图准入、首发selection=null/删除selection/plan_source=null三种登记跳过、registration指针错slot、ledger score与formal副本差异、lineage错slot/重复或删除替代/准入目标与来源path、SHA、pointer错误、报告重复冲突case行/分数/达标题数漂移。证明不是只有固定SHA拒绝；这些包含独审发现的9条私有探针对应公共回归（8个原语义接受现拒绝，已修准入引用继续拒绝）。
- **输入/边界**：duplicate JSON key、NaN/Infinity/数值溢出、bool冒充数字、路径越界/符号链接逃逸，以及把缺失历史原件静默补造，均拒绝。
- 真实基线测试同时拦截socket/subprocess调用并比较输入文件树前后哈希，要求只读；常规与`python -O`同样通过。

发现阶段的两个旧生成器合成反例并非当前真实数据漂移；旧完整测试的真实指针断言也能捕获冲突，不能因此把旧套污名为整体错误PASS。这里新增的是面向新克隆的正式来源闭合验证器，不把旧生成器原样包装成验证器。
