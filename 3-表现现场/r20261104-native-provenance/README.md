# 2026-11-04 原生来源链现场（公开派生）

**研究轨；原生配置、n=3配对观察；非同schema/同输出预算消融，非产品总排名。正式新增行0。** 本目录是明确脱敏的派生件，不是原始完整轨迹。方法、事前分支和限制见[技术门方案](../../1-评测方案/原生来源链技术门-2026-11-04/README.md)。

## 1. 观察结论

6个confirmation会话构成3个有效block。Codex native的请求侧选定输入增量在本次配置中均大于DSH bounded，D中位数**10351 UTF8 bytes**，范围10005—10382 bytes，达到预注册“三个D>0且中位数>=4096”分支。**这不是费用、token或同schema因果结论。** 两产品各3个确认Δ全正；本次双键端点均通过，但不表示整个夹具内容完整保留。

## 2. 逐场与配对依据

| block／预定顺序 | Codex Δ bytes | DSH bounded Δ bytes | D bytes | 技术门／双键 |
|---|---:|---:|---:|---|
| 1：Codex→DSH | 12764 | 2382 | 10382 | 双方通过／双方通过 |
| 2：DSH→Codex | 12528 | 2523 | 10005 | 双方通过／双方通过 |
| 3：Codex→DSH | 12733 | 2382 | 10351 | 双方通过／双方通过 |

逐场before/after原canonical值、原/派生body长度、native控制、opaque大小、原生usage事件和双键在各会话observations内；确切路径清单由[场景manifest](publication-manifest.json)列全。原native请求和完整SSE只做已声明隐私替换，工具schema没有被删减。原源码pin与依赖完整hash表见[源pin表](source-pins.json)。

## 3. 固定分母与失败分账

[分账ledger](ledger.json)是机器逐槽复算：新合同pilot2会话/4upstream、confirmation6会话/12upstream，总8/16，均exit0、每槽fixture1、严格gate通过；pilot不进入三block。strict mock为**3**会话/0upstream：Codex工程失败mock01保留，Codex/DSH各mock02通过并各有两请求和一次fixture。不能把2个ready样本称全部mock或全部校准。更早校准、113/21/6条工程测试另账，不进产品分母。

旧2026-11-03合同的一次live停止仍是**0确认/1upstream**：Req2的三项reasoning/call/return被旧门拒绝，不算新合同的有效效果。旧gate早退写0的字段原样作为历史记录保留；独立01/02收据是1+0，不能回写旧成功。新Codex mock01也保持失败：合成非UUID ID暴露native投影差异，仅mock夹具ID修到真实UUID形状后重跑，**真实guard未放宽**。无效Req2的Δ仅为诊断，不混入三block或能力得分。

## 4. 投影与只读复核

[来源投影表](projection-map.json)每条分列私源hash/bytes与派生hash/bytes，保留确切source标签/输入白名单与等长变换类别。请求侧原born canonical主值和派生重新measure相等，不padding凑数。先从全部选定原生请求/完整SSE收集已标记opaque、签名、身份值和路径，再按原值全局稳定等长alias：同串即使复用于message.id、其他字段、字符串子串或嵌套JSON也闭合替换；包内所有文件再检查原literal及递归解码形式不残留。过短敏感值、碰撞、字节不守恒均拒绝生成，不padding；不声称能自动识别任意未标注的语义敏感文本。投影内同值关系和长度可复核，不声称保留不同字符串的包含关系，也不是原密文同值的第三方见证。完整私源源码只列hash、不导出；真人见证pending。

从仓库根目录：

```sh
python3 -B 3-表现现场/r20261104-native-provenance/verify.py
```

默认仅stdout、纯stdlib、无模型/网络/私档访问，不写缓存或收据；显式`--output`可exclusive-create一个新收据，不能覆盖。verifier校验确切文件集合、每层wrapper键/类型、source白名单、完整sourcepin键集合与固定承诺、源/派生分列、投影canonical和body字节、完整SSE来源链和Req2 suffix、fixture、双键、逐请求计数、三block与4096分支。自带承诺的信任边界仍是版本化核验器/仓库，不是抗任意代码替换的外部签名。

## 5. 边界与不确定性

固定的是模型、提示、low档、夹具与客户端版本；实际reasoning token不透明，native协议/菜单不同，Codex provider-default输出上限未知，而DSH发1024。不能据此归因缓存机制、token费用、服务端最终输入或总体产品能力。n=3只是三次同向重复，不是统计显著性；未把A/B/W拼总榜。本轮没有真人签名、没有对所有私源公开独立重放，不能将投影核验通过说成历史各代原封印全部通过。
