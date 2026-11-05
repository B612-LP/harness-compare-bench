# 两题前瞻交付合同澄清 · 2026-11-05.1

**状态：未运行的前瞻交付澄清；0新产品/模型运行，0新正式准入，不追溯改分。** 本包没有启动评测的授权。历史25行成绩及其当时实际题面保持原样；本包不能据此认定历史失分均由合同导致，也不能把历史现场标为使用过新题面。

## 解决什么，不解决什么

| 用例 | 旧文本与实际判卷的差距 | 新独立指令如何对齐 |
|---|---|---|
| BIRD | [原instruction](<../bird-ca-schools-15/instruction.md#L29-L36>)未明说两项B2硬门；[checker](<../bird-ca-schools-15/checker.py#L243-L251>)实际执行 | 每行精确两个键；单引号字符串字面量之外禁止`--`，不把注释当完成声明。将原指令依赖spec的q27口径完整写入；不复制结果行数、答案SQL或参考解。 |
| Cargo | [原instruction](<../tb-cargo-plan/instruction.md#L21>)称根JSON必需，[spec](<../tb-cargo-plan/spec.md#L53-L62>)称可选，[checker](<../tb-cargo-plan/checker.py#L180-L206>)实际临时复跑代码 | 根JSON明确为可选便览、非评分源。只叠应用同层`.py`，传入路径必须生效，评分读取复跑输出。顶层精确五键，航段额外字段允许，不借本包并入B13b。 |

不改原instruction/spec/checker/truth/参考材料/输入，33个旧文件的SHA-256全部固定。这里澄清交付而非放宽判卷；不改变既定阈值、数据、结果比较与断言语义，也不声称新任务已改善产品表现。对未来任务文本的改变本身是一个新变量，不能与历史结果直接解释为同条件提升。

## 当前任务包单一入口与复制边界

供未来**另获授权**的运行方读取的单一机器入口是 [currentpack.json](<currentpack.json>)；每个case指定独立完整agent指令、精确SHA和显式输入白名单，运行方不得再拼接旧instruction或要求agent自己找spec。两份指令无需本README或评测规格即可理解任务、输入、交付与完成条件：

- [BIRD完整agent指令](<bird-instruction.md>)。
- [Cargo完整agent指令](<cargo-instruction.md>)。

本包是**公开仓库内的版本化覆盖层，不是可单独拷走即运行的输入压缩包**。输入字节沿用旧题目录，未重复放置数据库：未来运行方从入口的`staging[].source`读取源，在一个新空工作目录中按`destination`复制；先核对[source-bindings.json](<source-bindings.json>)中的SHA，再只向agent提供对应新instruction及这份输入副本。路径均相对仓库根，目标相对运行目录；不存在隐含spec依赖。

只复制白名单：BIRD四份输入；Cargo三份未修应用代码和四份JSON数据。不要复制整题目录，**不要给agent提供checker、spec、truth、solution、reference、源绑定或本包审计脚本**。源绑定包含旧评测材料的路径/hash，仅用于审核历史字节未变，不含其答案内容；这些不是agent任务依赖。`evaluator_source`只为运行方绑定原评测器，标记为`not-agent-visible`。

[contract.json](<contract.json>)机器记载新合同号、未运行状态、两项BIRD硬门、Cargo复跑/根JSON/结构及阈值；[source-bindings.json](<source-bindings.json>)绑定33份旧文件，包括原任务、评测器、规格和输入。不要用同名的在线数据库或另一版旧inputs替换本地冻结源。

## 只读复核与负例

从仓库根运行以下三条命令（仅Python标准库、无私档、无网络）：

```bash
python3 -B 2-用例/交付合同-2026-11-05/verify.py --root .
python3 -B -m unittest discover -s 2-用例/交付合同-2026-11-05 -p 'test*.py' -v
python3 -O -B -m unittest discover -s 2-用例/交付合同-2026-11-05 -p 'test*.py' -v
```

[verify.py](<verify.py>)默认只向stdout输出JSON，默认根为脚本所在公开仓库，退出0为本版静态审计通过、1为不通过。它核对五个包文件固定hash、33份旧源hash、prompt/合同/入口闭合和11条输入白名单，不生成文件、不执行SQL、不导入或执行旧checker/候选。路径越界与符号链接拒绝。修改prompt、旧source、合同或重新封装source-bindings/currentpack均应拒绝，不因内部hash互相一致就放行。

[test_verify.py](<test_verify.py>)在临时副本上测试改prompt及重封入口、宽化合同、改变根JSON策略、改checker为执行陷阱、缺输入、改输入并重封、误将评测材料放入agent白名单、越界和符号链接；另用无意义的合成SQL字符串覆盖两键/注释/转义/重复和缺题等格式边界，不查询数据库。正常与`-O`模式均须通过。临时副本只为读取/hash，旧checker执行陷阱绝不会被运行。

附带`bird_delivery_errors`只是规范交付格式示例，不是正式checker替代：整数题号是推荐输出，原判卷按字符串化去首尾空白后的题号识别；helper对非整数题号、重复JSON键和非有限值的严格拒绝只是canonical preflight规范，不是与旧checker等价的新增评分硬门，旧parser的历史宽容不能据此回改；字符串是否真为可执行查询及结果正确性不由这个函数判定。合成无意义SQL通过格式检查不等于任何题得分。Cargo无候选复跑测试，本轮不验证修复后的飞行计划。

## 复核信任边界

固定hash基于这一版公开复核器作为信任锚；若同时改复核器和所有材料，不构成第三方真实性认证。这里不认证私档原件、不替代历史封印，也不证明checker一般正确；只能证明与本版公开锚对应的字节和合同关系。当前真实产品重复、思考/cache控制、桌面隔离与实读取真值均不由本包补齐。

来源与许可随原题保留：BIRD中文题面及数据为CC BY-SA 4.0；Cargo任务改造自Terminal-Bench，Apache-2.0。新指令只披露任务合同，不包含答案SQL、最优航路、预期数值、修复代码或原参考解。
