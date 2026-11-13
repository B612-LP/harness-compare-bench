# 原生外溢回读与短历史：选面关系复算

## 1. 结论与适用范围

在两次脚本控制的本地原生 CLI 会话中，四次**真实内置 Read**把同会话新产生的外溢文件呈现为 192 个编号源行。按已知输入的 LF 与末尾 LF 重构，四份结果分别匹配对应 16000B 安全合成源及其独特 head/tail。原先 fixture 截取没有的共同第 100 行，出现在随后组装请求的 Read 呈现中。此结论不是假 Read，但也不是模型主动选择工具或模型答题得分：远程转发 0，最终 `OK` 及零 usage 来自本地脚本响应。

短历史中，r3/r4 的旧 fixture 选面，以及 r4 的第一 Read 选面，逐 role、消息/块位置和内容保持一致。这里只复算选中的 18 个 tool-result 关系，不把它扩写为任意长历史、全部消息始终不变或后端实际摄入的认证。

## 2. 证据与分账

[证据表](evidence.json) 内的 18 个呈现与四份合成源：[A1](sources/A1.txt)、[B1](sources/B1.txt)、[A2](sources/A2.txt)、[B2](sources/B2.txt)：每 case 的两份 fixture 在 r2/r3/r4 各一次（6），第一 Read 在 r3/r4 各一次（2），第二 Read 在 r4 一次（1）。[验证器](verify.py)检查参数映射、调用/结果别名、原角色/位置、源身份、内容稳定、遗漏区间及哈希。[完整文件清单](SHA256SUMS.json)覆盖全部公开文件；这是派生包内部一致性承诺，不是私档原件的公开认证。

| 层次 | 本次观测（每份） |
| --- | ---: |
| fixture 原源 / 保留源字节 / 省略源字节 | 16000 / 1676 / 14324 B |
| fixture 包装后呈现 | 1979 B |
| Read 完整编号 XML 呈现（在随后请求中） | 17105 B |
| 192 行内容，去掉所有行间/末尾 LF | 15808 B |
| 按已知 terminal LF 重构的源 | 16000 B |
| wrapperNoLF = 17105 − 15808 | 1297 B |
| netOverLF = 17105 − 16000 | 1105 B |

1297B 含与无 LF 正文比较的换行基准差，不能再加到 16000B 上。Read 的 stdout tool-result **仅 8192B 且 `truncated=true`**；完整呈现证据是 r3/r4 捕获的下一请求，而非 stdout 预览。源行、包装呈现、原/派生文本哈希、请求 raw 字节/哈希与格式化 JSON 哈希分列；脚本 usage 不代表生产 token 或成本。

新对照：2 case、8 seen/8 accepted 本地请求、4 fixture、4 actual Native Read、0 remote forward。旧失败版本单列：原计划 4 Read、实际 0 Read、decoder invalid；旧已 seen 3 与新 8 合计 11 **本地 seen**，不是 11 次成功请求，不能由新四 Read 回填旧失败。

## 3. 机制解释与竞争解释

两 factory 先产生真实外溢文件，随后按捕获路径调用内置 `read(file_path-only)`。C1 按 A→B，C2 按 B→A；源与顺序共变，只防串线，不估顺序效应。每源各有独特的 700hex head/tail，四源共同 middle 只证明内容恢复，不能作为来源身份；全源哈希及 head/tail 联合校验防止换源或混头尾。

默认 workspace-write + ask 保留，Read 上限仍为 51200B、2000 行、每行 2000 UTF16 单元。没有通过改权限或扩大 Read 限制制造恢复。实现源码 pin 不等于全部运行时身份认证。

## 4. 可见性、变换与永久认证边界

公开仅安全合成源与选面关系。私有完整初包/policy、Native 线程、控制器与计划不公开。选面中仅已绑定的四条真实路径替换为**等 UTF8 字节长的 X**；调用 ID 换为等长匿名 ID，原 ID/路径/文本/块 commitment 与派生 hash 分列。不同原路径可能得到相同 X 串；来源由 targetSource/参数内部映射及独特 nonce/全源 hash 校验，不能用 X 串认证路径身份。原捕获文件没有被修改。

公开读者不能据此认证缺失私档中的路径安全/SID/新鲜性/完整初包及原生执行链；这些边界不由派生包自哈希消除。此处只对已知 LF 与末尾 LF 输入重构源，不声称 wire 中连续出现原始 16000 字节，也不声称任意 EOF/换行格式都透明。没有后端摄入、agent 主动策略、长 history、成本或普遍产品能力结论。

## 5. 复算与反例

仅 Python 3.9+ 标准库，无网络、产品、模型、CLI 或第三方依赖。在本目录运行：

```sh
python3 -B verify.py
python3 -B test_verify.py
python3 -B -O test_verify.py
```

[测试](test_verify.py)覆盖错源/混 nonce、共同 middle 误归因、错 LF/编号/假 EOF、8192B 预览冒充完整呈现、错误标记优先、角色/位置/参数改动、遗漏或重复选面、旧失败回填、字节口径/包装、哈希分层、路径变换与隐私/清单。复算只读公开文件；不需要也不触发一次真实产品运行。
