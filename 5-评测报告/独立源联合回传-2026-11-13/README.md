# 独立源联合逐字回传：公开派生证据（2026-11-13）

## 1. 结论：事后再判成立，原冻结主门仍失败

在固定合成夹具、客户端请求观测面和**精确原生组装事后适配**规则下，两个independent cell均正确联合回传四个700hex nonce；两个duplicate复制对照也正确。每条件n=2，仅描述这四次观察，不估计普遍成功率或因果效应。

| 判定层 | 实际结果 | 不可改写的边界 |
|---|---|---|
| 原冻结门 | valid **0/4，FAIL**：`initial_prompt_not_exact` | 不是原预注册通过，不追认为成功 |
| 精确原生组装posthoc再判 | valid **4/4，exactJSON 4/4** | 有限事后测量适配，不是新预注册确认 |
| 非作者独立离线审计 | PASS，仅限上述事后再分析与证据一致 | 108份消费源前后hash稳定，18项内存反例拒绝；不是108项研究发现 |

原分析器把唯一user的两个text块整体串接后与裸任务prompt比较，因原生附加固定策略快照而失败。适配只在原初始prompt串接比较一处要求**恰好两块、纯text、首块逐字等于原prompt、次块逐字等于固定snapshot**；拒绝多块、改字、伪type、单块substring。未改全局PROMPT、任何原始轨迹或其余源/nonce/JSON门。适配源封印后才执行再判；“当时只看首包未看答案”的声明被留存，但不能据此独立证明人的全部先验见闻。

## 2. 证据：合成源、去标识观测面与字节分解

[证据清单](evidence.json)固定顺序 **dup1 → ind1 → ind2 → dup2**。rep1重复先、独立后；rep2独立先、重复后。四cell不是四组独立随机样本：同rep的A源在两条件复用。四份16000B纯合成ASCII源可完整公开：[A1](sources/A1.txt)、[B1](sources/B1.txt)、[A2](sources/A2.txt)、[B2](sources/B2.txt)。每源head `[11,711)`、tail `[15299,15999)` 各700hex；全部8个源nonce不同。

| cell | 源映射 | I_text 去重ASCII B | 单工具M_source最大 B | 两工具源bytes合计 B | 原始请求1/2 B | exactJSON |
|---|---|---:|---:|---:|---|---|
| dup1 | A1+A1 | 1400 | 1732 | 3464 | 1504/6078 | 正确 |
| ind1 | A1+B1 | 2800 | 1732 | 3464 | 1504/6189 | 正确 |
| ind2 | A2+B2 | 2800 | 1732 | 3464 | 1504/6078 | 正确 |
| dup2 | A2+A2 | 1400 | 1732 | 3464 | 1504/6078 | 正确 |

[8份selected tool_result face](faces/)仅替换省略提示中的本机临时路径：用**相同UTF-8字节长的ASCII `X`**占位；原跨度hash、byte interval、变换标记，以及原face/派生face hash和长度分别记录，不能混作同一hash。源内容、nonce、工具名、原opaque call ID、`{}`入参、call/result引用不改。公开的是从末次请求抽取的派生面，不是原Messages、完整原生轨迹或原SSE；原末答只含nonce JSON，逐字保存在[末答目录](answers/)，未改写或重新格式化。

表中“两工具源bytes合计3464”是两份face的M求和，不跨工具对同源去重；duplicate两份同源按source_id联合去重仍只有1732B，不能称3464B独立源信息。

每工具保留的源区间由源与face重新匹配：`[0,868)` + `[15136,16000)`，union **1732B**；省略14268B；wrapper **247B**；完整face **1979B**。相对旧mock近似1728B实际有 **+4B residual**，只定位到head可见预算，不猜内部原因。wrapper与占位路径不计入M；同一工具历史重复区间应取union而非求和。本次每cell实际仅一份后续请求，末包即全部后续请求，故每工具只有一对prefix/suffix区间。

四个原始首包均1504B、逐字相同，wire SHA256：

`eb98ea308bc89eff42a3f4a9bca425e5f37091beeff93859758f36159d020e7a`

它与原格式化JSON文件hash、原末包raw request hash、原face hash、派生face hash分列。**首包原文不公开，因此公开者不能仅凭hash重新验证四原文相同或认证原始捕获**；这里是私档审计留下的承诺，不是原始认证声明。原prompt全文、策略快照全文、认证材料、native session轨迹及实验运行器不在此包。

## 3. 解释：具体联合逐字利用，不是信息论超限

这里`I_text`是目标nonce**去重后的hex ASCII字面bytes**：A+A为1400，A+B为2800。独立条件的 `2800 > 1732` 是与**单工具对应源可见union最大值**比较，不是与两工具总3464比较；不能写成“联合输入超过全部可见源”。**2800hex字符至多表示1400B熵，I_text不是Shannon熵。**

实际记录指向DSH `0.2.0-rc.2`、`deepseek-official/deepseek-flash`、effort low、thinking enabled、max_tokens4096、spill cap512、retry0；版本为留存pin而非本次重新启动CLI验版本。工具由相同factory/description/schema构造，源映射是条件差异；配置禁文件/搜索/恢复等入口，实际无恢复调用。配置及捕获不构成对宿主全部能力的隔离认证。

公开重算支持本探针具体联合逐字复制；不证明后端不存在cap/压缩、不证明完整源已摄入、不排除中间思考自回显/重编码、不推其他任务或产品能力。四首包同并不消除缓存、实际reasoning量等混杂。

## 4. 限制：usage分账、私档缺口与可信度

Provider usage采用每请求末次`message_delta`原字段；[证据清单](evidence.json)还保留各请求`message_start`和`message_delta`的原字段/原事件，**不相加推总token或算钱**，cache_creation均0。

| cell | 请求1 input/cache_read/output | 请求2 input/cache_read/output |
|---|---|---|
| dup1 | 516 / 0 / 36 | 2216 / 512 / 2536 |
| ind1 | 134 / 382 / 63 | 2214 / 512 / 3473 |
| ind2 | 134 / 382 / 36 | 2246 / 512 / 3818 |
| dup2 | 134 / 382 / 36 | 1341 / 1408 / 2918 |

初包字节相同但cache usage不同，实际reasoning/cache**未等控**；bytes≠tokens≠cost。客户端记账为 **8 durable intent / 8 confirmed / unknown上界0**，每cell2；unknown0不等于后端内部处理已知。剩余额度不继续使用。

私档独审还核了原raw/JSON/SSE/native stdout、回调全源、精确快照及全部调用对应；公开包不能重放这些未公开层，**公开复算通过不等于原始整链认证通过**。原初包原文、策略全文、原生轨迹不公开属于明确缺口；缺native calibration仍缺，纯mock不替代。source face原hash和被替换跨度hash不能只靠派生文本还原核验；它们绑定私档而非公开认证。非作者私档审计收据SHA256 `01dcaa7b028769b3466950886350560537a0317d73e06dffed961b4411844f1a`；公开层关系审阅与未公开原始链认证必须分开裁定。

## 5. 复核：Python 3.9+标准库，无网络或产品调用

本目录独立复制即可，不依赖私有路径、第三方包、认证或产品安装。从本目录执行：

```sh
python3 -B verify.py
python3 -B test_verify.py
python3 -B -O test_verify.py
```

[verify.py](verify.py)核[文件hash清单](SHA256SUMS.json)、严格JSON重复键、四cell/两call身份、源hash/nonce真值、prefix/suffix实际字节区间、M/省略/wrapper、I去重、末答四nonce逐字比较、usage原字段及事后/隐私标记；它不是产品runner，不重算未公开的SSE/native/初包内容。hash清单是可核完整性清单，不是可信时间戳或独立签名。

[test_verify.py](test_verify.py)包含7个分组测试：wrong nonce，extra/duplicate JSON keys，A+A冒充independent，伪M/I/区间/省略数，漏重cell/call和错引用，first hash改变，usage合并推算字段，posthoc冒充preregistered，未标隐私变换和路径残留等反例。常规与`-O`均运行相同显式校验，未用可被优化删除的`assert`。这7组本地回归与私档非作者18反例分账，不冒充真实产品校准或独立科学样本。
