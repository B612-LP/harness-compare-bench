# 原生来源链技术门与请求侧输入观察（2026-11-04）

## 1. 研究问题与分轨

在固定模型、提示、思考档与35767-byte夹具的本次配置中，Codex native与DSH bounded的原生请求侧输入增量是否在三个独立配对block中同向？这是**研究轨的原生客户端观察，不是同schema/同输出预算的因果消融，不是五产品正式总排名**。正式新增行0；三轨仍各自解释，不合并A/B/W排名。

本合同8个live会话、16个上游尝试为封顶预算：pilot2会话/4请求只验技术门，confirmation6会话/12请求用于3个配对block。首个技术失败立即停止且不替换、不按方向选择会话。历史2026-11-03一次失败live及其1上游另账；工程失败mock01和双真实CLI mock02共3会话、0上游另账，不能将2个通过ready样本叫作所有mock或所有校准次数。113条transport、21条控制器、6条分析分支测试及更早校准也是非产品工程检查，不进入live分母。

## 2. 事前固定与合同

| 项目 | 固定值／不可声称已控制的项 |
|---|---|
| 模型/思考档 | `deepseek-flash` / `low`；实际reasoning token未知 |
| 客户端 | Codex CLI `0.163.0`；DSH `0.2.0-rc.2` |
| 夹具 | 35767 UTF8 bytes；SHA256 `fed57592028c9d8a9180c2b97f74a3cd5e0daa841aab244cf4aad78fe44626a2` |
| prompt SHA256 | `82f49e6223aad78640e412663d7f96dae4c14c3619d1af8ce292298e7ef75042` |
| 输出上限 | DSH请求`max_tokens=1024`，夹具内联512；Codex未发上限字段，provider default未知；不可称同预算 |
| 工具 | 实际执行只准一次`fixture_output`、无额外工具；原生菜单/协议不同，完整schema保留在请求派生件 |
| 技术门 | 请求前、每次完整响应转发前、结束后检验源hash/版本/日期/合同/控制/夹具与来源链；不通过不继续 |

固定用户提示：

> Call fixture_output exactly once. Then return only a JSON object with HEAD_KEY and TAIL_KEY containing the two observed values. Ignore checksum noise. Do not call any additional tool.

完整冻结源码pin集合和7个legacy依赖hash见[源pin表](../../3-表现现场/r20261104-native-provenance/source-pins.json)。它保留全部相对文件名与hash，不公开内部运行器、配置、凭据、内部计划或代理记录；**hash_only_private_source不是公开可重跑全部私源的声明**。

## 3. 主指标、技术门与终点分离

主值是截获请求中选定字段对象的canonical JSON UTF8字节数（键排序、紧凑分隔、ensure_ascii=False），不是产品自报token。Codex选择存在的`instructions/input/tools/previous_response_id`；DSH选择`system/messages/tools`。每会话`Δ = B_after − B_before`；另保留完整HTTP body序列化字节与组件差异。路径/UUID正规化仅用于控制指纹，**不用于主值**。

来源链不是只信最终snapshot：Responses验证created→in_progress→item added→content/summary part added→delta→text done→part done→item done→response completed，顺序、索引、完整重建和opaque字段逐层同值；call arguments独立重建，最后snapshot必须匹配。Req2只接受同会话前缀和原响应可证明的完整snapshot/已观察原生投影加唯一工具返回，不删除reasoning/opaque/未知业务字段来放宽。Messages验证每块text/thinking/signature/tool_use完整生命周期，拒绝晚到、错类型、未知事件和签名后thinking。SSE封套、重复键、非有限数、过早/重复终止也拒绝。

上游尝试计数在任何科学门早退**之前**读取独立逐请求收据和closure；无法闭账时是null及上下界，不是0。旧失败原gate早退0仍保留为历史字段，与原01/02收据的1+0分开解释。

技术有效与双键终点独立：即使答案错，只要技术合同完整也不得据结果替换；双键只检`HEAD_KEY=AMBER-731`、`TAIL_KEY=COBALT-492`，不能解释为完整内容保真。native usage按原生事件保留、不同粒度不求和；opaque给字段路径/serialized长度/原与派生hash，不能倒推思考token或服务端缓存。

## 4. 预注册分析分支（不据结果选样）

三个block的顺序事先为Codex→DSH、DSH→Codex、Codex→DSH。仅当双方技术有效才形成`D_b = ΔCodex − ΔDSH bounded`，pilot/mock/无效Req2诊断不进入D。

1. 有效block不足3：`direct_observation_incomplete`。
2. 三个D均>0且中位数>=4096 bytes：`larger_codex_native_selected_input_growth_in_this_configuration`。
3. 三个D均<0：`reversed_native_direction`。
4. 其余：`below_threshold_or_unstable_native_direction`。

另外分别检查每产品3个确认Δ是否全正，不将n=3视为总体显著性、置信区间或机制因果识别。逐场原值、配对与端点见[现场](../../3-表现现场/r20261104-native-provenance/README.md)与[分账](../../3-表现现场/r20261104-native-provenance/ledger.json)。

## 5. 公开复核与不能回答的问题

公开件为明确标注的派生，不是未改写原轨迹：先遍历全部选定原生输入/输出收集路径、opaque/签名和身份值，按原值全局稳定等长alias（含跨字段复用、子串和嵌套JSON），再全包扫描原literal/解码形式；过短值或不守恒则拒绝，不自动泛化未标注语义敏感项。保留同值关系，不保证不同字符串包含关系；既不padding也不补尾凑字节。每个请求的原canonical主值、原body字节与派生实算必须精确一致；原hash与派生hash分列，不能强行相等。完整SSE和业务键保留用于投影内来源链复核。投影不能独立证明原密文内容/私源真实执行，未有真人第三方签名；当前只是内部核验。

从仓库根目录运行（默认只读stdout，不写任何新收据）：

```sh
python3 -B 3-表现现场/r20261104-native-provenance/verify.py
```

私源hash、派生hash、每层schema、确切文件/source白名单、字节复算、分账、三block分支都在本场景核验范围内。安装home/auth、内部计划和放行记录不在公开材料中。不能从10351 bytes推导费用、token、缓存命中、服务端最终输入或延迟；native工具菜单和Codex未知输出上限仍是归因限制。
