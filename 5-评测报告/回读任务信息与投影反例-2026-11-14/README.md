# 回读任务信息与投影反例

研究对象是**任务所需信息在指定展示投影中是否仍可辨识**，不是模型能否答对，也不是所有恢复策略的完备性。

## 两层证据，不能互相冒充

| 层 | 可复核对象 | 不支持的推论 |
|---|---|---|
| 源码条件下的有限 proof | 同一 synthetic 路径、参数下，不同安全合成源、不同任务答案，却有相同完整展示 | 历史 runtime 身份、真实产品召回率、模型失败 |
| Native 客户端派生证据 | 各指定 Read **结果块去唯一 path 行后的完整正文**、原/派生 hash、role/call-ID/实参、当前 locator 与完整源文件的绑定 | 整个请求或 whole history 不可区分、系统不能作答、含不同路径的返回逐字相同 |

[规格](<specs.json>) 只声明有限行为；[cleanroom](<cleanroom.py>) 是独立 Python 3.9 标准库实现，不含 vendor 源码、提取 VM、runner、模型调用或工具后端。相对包名与 source hash 只是 commitment，不是 runtime 证明。公开派生不包含初包 policy、真实私有路径、SID、凭据或完整 raw 请求，不冒称原始完整轨迹。

Native 派生材料的执行状态、固定分母和证据范围由独立 manifest 明示。本包完整验收只接受 v2 声明及全部必需材料；单独运行静态 cleanroom 证明不代表已执行 Native。公开验证可以复核安全源、指定结果正文、参数及派生 hash，**不能公开重放已省略的原请求/control**；其原 hash 仅保留绑定。invalid/unknown 不洗成模型或工具能力阴性。

## 六个安全反例

所有静态比较统一为 `/synthetic/same-path.txt`，并比较含该路径、行号和 footer 的完整投影：

1. `alpha\r\nbeta\r\n` 与 `alpha\nbeta\n`：源换行编码不同，完整展示相同。
2. `alpha\n` 与 `alpha`：末 LF 有无不同，完整展示相同。
3. `alpha\r` 与 `alpha`：末 CR 有无不同，完整展示相同。
4. 长的合法 JSON：2000 UTF16 单元公共前缀后的 decision 为 ALLOW / DENY!；任务答案不同，展示相同。
5. 1999 个 ASCII 后的不同 astral 字符：2000 单元切分留下同一个未配对 `0xd83d`。JSON 的 `\ud83d` 转义保留该单元；UTF8 **display** 编码的 U+FFFD 替换是另一表示，不是实际 JSON wire 必然替换的证据。
6. `q×2000+LF` 与 `q×2000+CR+SECRET+LF`：完整展示相同，**没有 line-truncated 标志且显示 EOF**。把后者 CR 换成 Z 的负对照有标志。因有界前缀先保留2001单元，恰好在边界的 CR 被去掉后长度为2000；因此“无 marker + EOF”也不证明源字节完整。

这里的 SECRET、hex 与其它值均为安全合成数据，不是认证或真实私密信息。前五组的完整展示 display hash 与独立静态复核的 commitment 一致；同 hash 不能自动将另一个任务/会话绑定到这些源。

### 单位与恢复通道

- 每行帽按 **UTF16 code unit**，不是 codepoint 或 UTF8 bytes。默认每窗口 byte 帽为51200B，另有行 offset/limit。
- 30行、每行2000 UTF16单元的 ASCII/CJK/astral 示例，首窗分别选25/8/12行、50024/48007/48011B；计数不含行号/包装。逐窗行分页可恢复全部30行。
- 同一**单行**的第2000单元之后不能用正整数行 offset 指向；offset=1/limit=1不改善，offset>1是越界。这与可分页恢复的 byte 帽分开，不能概括为“所有工具都不可恢复”。
- post-execute 的有限条件另列：accepted、无 parent delegation、无 **own** value 时，工具名 read 与别名分支不同；own value 为 undefined/null/false 均 bypass，不能按 truthiness 判。改变 opaque call-ID 不改变此名字条件。此 proof 不等于 PTC/全运行时因果结论。

## Native 比较的精确量词

计划为同一新 session 的 S/A/B 三安全源、四次 Read：S，A，B，A(offset=1,limit=1)。A/B 各16000B单行，仅中部64hex不同、前2000字符相同；S为A每100字符插LF、无末LF，**多159个LF，不是源字节等控**。

S正控先读已经把A的目标提供给会话历史。即使后续A/B指定结果块中目标缺失且去path完整正文碰撞，也不能说A目标从未出现在后续整请求中，或系统无法借历史作答。A/B 的真实 locator 不同；其来源必须以本轮 call-ID、当前 locator、physical spill/full payload/full file hash 绑定，不能靠共同前缀猜。

结论不否定其他查询、工具、外部信息或恢复策略，**包含可交互计数通道**。本目录不新增原生 grep 实验，也不把源码查询条件变成已测 Native 结论。

### 本次 Native 客户端派生见证（2026-11-14）

一次新会话中完成6个本地脚本请求、3个 fixture 和4次原生 Read；0上游转发、0模型请求。S的160行完整重构16159B并包含目标；A、B及A行分页的指定结果均仅覆盖源前2000B，另带34B合成 marker，目标均未出现在这些结果正文。后三者仅去唯一 path 行的完整正文 SHA256 同为 `882938003121824aa87d548cd0225b46f842f7b734eeb84014a0011584033c71`。这不撤销上节“S先向历史提供A值”的限制。

以下是**原捕获 Read 结果的 UTF8 计量**，不是替换 synthetic 路径后的文件大小：

| 指定 Read | 完整源B | 实际源覆盖B（含保留LF） | 合成marker B | 原结果B | 原analysis `wrapper_bytes` | 结果减展示重构B |
|---|---:|---:|---:|---:|---:|---:|
| S | 16159 | 16159 | 0 | 17106 | 1106 | 947 |
| A | 16000 | 2000 | 34 | 2290 | 256 | 256 |
| B | 16000 | 2000 | 34 | 2290 | 256 | 256 |
| A(offset=1,limit=1) | 16000 | 2000 | 34 | 2290 | 256 | 256 |

S的原 `wrapper_bytes=1106` 是原结果减去各行内容之和16000，**没有减去159个保留LF**；相对完整16159B源的净余量为947。长行原 `displayed_source_bytes=2034` **包含34B合成marker**，不能写作2034B源覆盖；其分解是2000源+34 marker+256其它包装=2290。原字段原样保留在[Native清单](<native/manifest.json>)，新增分解不回写原analysis。清单分列 original/derived 计量；导出仅替换 preview locator 和 Read path header，正文不改，派生文件大小会随 synthetic 路径变短。

原结果的细分也逐项保留：S为16000非LF源+159源LF+692编号+183 path行（含末LF）+36其它XML+31 EOF+5脚手架LF；长行为2000源+34 marker+3编号+183 path行+36其它XML+29 EOF+5脚手架LF。长行相对纯源覆盖的全部非源增量为290，而不是只计其它wrapper256。

6个 serialized request body 的捕获大小为4581/11126/28807/31513/34219/36946B，合147192B。只表示这一软件捕获面的序列化体，不与Read文本再合计，不是网络流量、增量信息、模型样本数、token/cache/成本或inline反事实。

公开验证可重算安全派生的源、正文、marker与计量分解；原header长度、原结果大小和原字段属于带hash绑定的披露值，不能由省略了原header的公开包独立恢复其真实性。原请求、control、全历史及原错误字段完整性仍仅有承诺，不是完整公开重放。结束记录只见证该组时点自己的进程组 signal-0 检查为 absent，不认证整个 runtime 或全机无其它任务。实际轨迹的科学独审与安全派生包的公开独审是不同层；作者自测不替代任一层验收，也不为后续发布状态作保证。

## 公开复核

```bash
python3 -B test_cleanroom.py
python3 -B verify.py
```

不安装依赖、不联网、不运行产品。62项纯测试含六反例、CR负控、UTF16/UTF8/JSON分层、分窗恢复、own-property、**人工制造**的 Native 形状派生正反例，以及实际安全文件的只读副本变异；这些测试不是新实跑。证明主门使用显式异常，不依赖可被 `python -O` 移除的 assert。主验证实际读取12份静态源、6份JSON展示和6份UTF8展示，逐项计算任务答案不同、完整同路径投影相同，并绑定保存的proof与明确的有限spec。normal/`-O` 均须拒绝重新计算清单后的同源同答案、错JSON/UTF8展示、错spec、schema降级、失败终态及缺失错误存在性。完整验收要求v2、metrics、精确类型计数、三preview和四Read，固定1session/4Read，不从缺材料补全。

每个 Native 派生结果显式记录 `is_error:false`、必需布尔 `native_is_error_present`、所选原字段及原 result-block hash；存在性须与披露的 `is_error` 字段一致。公开验证优先拒绝 true/失败元数据/错误包络；若披露status/state，只接受明确成功值 `completed`、`success`、`succeeded`、`ok`，超时、空值或未知状态均拒，即使正文看似完整。已披露的终态见证必须为completed true、数值exit_code 0（非False）、timeout/logs_withheld false、native_identity_verified true、自有组absent，且两个有限范围标记为true；不以此认证全机。被省略的原 block/请求仍只有 hash commitment，公开包不能独立证明导出者没有遗漏原字段，不能冒称原错误门的完整公开重放。

最终文件集由 `MANIFEST.json` 递归列明全部普通文件及 hash（明确不自含本清单）；验证拒绝额外文件、空目录、任何列明或额外 symlink。Native 子树也有同样的精确清单门。根清单本体须由绑定提交/外部 commitment 固定，不能自证真实性；没有根清单时验证器明确不报告完整文件集已核验。

若记录软件捕获 request-body bytes 的重复加和，仅表示该软件捕获面的 body 计数：不等于 HTTP/TCP 流量、token、cache、成本、模型样本数，也没有 inline 反事实。源码条件 proof、Native结果、旧记录的软件计数须分账。
