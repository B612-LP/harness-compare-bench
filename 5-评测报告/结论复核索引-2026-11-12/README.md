# 一页结论—绑定提交—公开复算—私档缺口

对应[第四周反馈](<../../反馈/2026-11-11-第四轮/README.md>)与[当前整合报告 v1.39](<../竞品评测报告-v1.39.md>)。每行绑定确切证据/实现快照，不是“任意HEAD全部可核”。离线重算、实际小样本与零上游客户端对照分列；不回填正式25格、旧n或历史分数。中期解释以当前报告及下列新对照收窄，版本留痕不等于互斥解释同时成立。

| 关键问题 | 当前可说的结论 | 绑定提交 | 公开复算/证据入口 | 不能公开或尚未识别的缺口 |
|---|---|---|---|---|
| 回读保留任务信息吗 | 1会话4次原装Read：S完整覆盖16159B；三个长行结果仅覆盖源前2000B+34B marker，行分页未补目标。指定Read去唯一路径正文相同；另有六个源码条件有限反例。 | [9564ffd](<https://github.com/B612-LP/harness-compare-bench/commit/9564ffd7cf56fc7c8316b90d0ba9cb25dcde2191>) | [定义](<https://github.com/B612-LP/harness-compare-bench/blob/9564ffd7cf56fc7c8316b90d0ba9cb25dcde2191/5-评测报告/回读任务信息与投影反例-2026-11-14/README.md>) · [Native披露](<https://github.com/B612-LP/harness-compare-bench/blob/9564ffd7cf56fc7c8316b90d0ba9cb25dcde2191/5-评测报告/回读任务信息与投影反例-2026-11-14/native/manifest.json>) · [复算](<https://github.com/B612-LP/harness-compare-bench/blob/9564ffd7cf56fc7c8316b90d0ba9cb25dcde2191/5-评测报告/回读任务信息与投影反例-2026-11-14/verify.py>) · [反例](<https://github.com/B612-LP/harness-compare-bench/blob/9564ffd7cf56fc7c8316b90d0ba9cb25dcde2191/5-评测报告/回读任务信息与投影反例-2026-11-14/test_cleanroom.py>) | 6本地脚本请求/0模型；S已向历史提供A目标，不是含路径整返回、整请求或整个Harness不可恢复。原header/control/错误字段完整性仅私档承诺；ASCII不实测Unicode单位，CR无marker仅源码反例。 |
| Read正例能作漏检分母吗 | 既有78行档案含28唯一配对、8个非空成功Read，旧9行是其精确前缀；没有可信同目标同窗配对，不能把8当FD漏检分母。 | [9564ffd](<https://github.com/B612-LP/harness-compare-bench/commit/9564ffd7cf56fc7c8316b90d0ba9cb25dcde2191>) | [定义](<https://github.com/B612-LP/harness-compare-bench/blob/9564ffd7cf56fc7c8316b90d0ba9cb25dcde2191/5-评测报告/读取正例与检测支持集-2026-11-14/README.md>) · [派生](<https://github.com/B612-LP/harness-compare-bench/blob/9564ffd7cf56fc7c8316b90d0ba9cb25dcde2191/5-评测报告/读取正例与检测支持集-2026-11-14/evidence.json>) · [复算](<https://github.com/B612-LP/harness-compare-bench/blob/9564ffd7cf56fc7c8316b90d0ba9cb25dcde2191/5-评测报告/读取正例与检测支持集-2026-11-14/verify.py>) · [反例](<https://github.com/B612-LP/harness-compare-bench/blob/9564ffd7cf56fc7c8316b90d0ba9cb25dcde2191/5-评测报告/读取正例与检测支持集-2026-11-14/test_verify.py>) | 1124个FD记录不是读取机会，日志时刻不是物理IO时钟，词法别名不认证物理对象；真实读取数、FN、recall与风险上界仍null。无新增产品运行，原档前缀和未见bait仅私档承诺。 |
| 正式25格 | 每格n=1；A10/B10/W5只作轨内观察，不合五款总榜。 | [ababe63](<https://github.com/B612-LP/harness-compare-bench/commit/ababe63694b46db7ed8cd2c5210243155b5cde5c>)（历史可执行代） | [旧版25行来源闭合](<https://github.com/B612-LP/harness-compare-bench/blob/ababe63694b46db7ed8cd2c5210243155b5cde5c/5-评测报告/正式行复核-2026-11-05/README.md>)；该代v1.9与当前v1.9/v1.10/v1.11/v1.12/v1.13/v1.14的§3字节相同。 | 38b2/06ef当前树运行旧verify会在q2697文档SHA门失败；只在左列固定历史代实际通过。来源闭合非重新判卷或原件认证，详见下方漂移与命令。 |
| 输入为何减少 | 18场捕获区间保留旧历史；工具源正文省略与包装差共存，不能只归为等文本重组。 | [06ef6ef](<https://github.com/B612-LP/harness-compare-bench/commit/06ef6ef19272f398466278500d30a8eb8d5fae11>) | [定义/18场分账](<https://github.com/B612-LP/harness-compare-bench/blob/06ef6ef19272f398466278500d30a8eb8d5fae11/5-%E8%AF%84%E6%B5%8B%E6%8A%A5%E5%91%8A/%E8%BE%93%E5%85%A5%E6%BA%90%E8%A6%86%E7%9B%96%E4%B8%8E%E6%9C%BA%E5%88%B6%E5%8C%BA%E5%88%86-2026-11-12/README.md>) · [A重算](<https://github.com/B612-LP/harness-compare-bench/blob/06ef6ef19272f398466278500d30a8eb8d5fae11/5-%E8%AF%84%E6%B5%8B%E6%8A%A5%E5%91%8A/%E8%BE%93%E5%85%A5%E6%BA%90%E8%A6%86%E7%9B%96%E4%B8%8E%E6%9C%BA%E5%88%B6%E5%8C%BA%E5%88%86-2026-11-12/verify.py>) · [结果](<https://github.com/B612-LP/harness-compare-bench/blob/06ef6ef19272f398466278500d30a8eb8d5fae11/5-%E8%AF%84%E6%B5%8B%E6%8A%A5%E5%91%8A/%E8%BE%93%E5%85%A5%E6%BA%90%E8%A6%86%E7%9B%96%E4%B8%8E%E6%9C%BA%E5%88%B6%E5%8C%BA%E5%88%86-2026-11-12/result.json>) | 同DSH六对与原生三block不合n=9；引用不等实际回读，未控制后端历史/思考/cache，不推token/费用。 |
| WB粗估平台与读取窗口 | 既有13点/12会话，2000行及每行2000 UTF16窗口精确13/13；全文件8/13、固定169860B帽10/13。alt真实窗口115910B而非ceil逆算115912B。 | [582594f](<https://github.com/B612-LP/harness-compare-bench/commit/582594f4c8c0473514d03ba64b78bc09b610ba52>) | [定义](<https://github.com/B612-LP/harness-compare-bench/blob/582594f4c8c0473514d03ba64b78bc09b610ba52/5-评测报告/读取窗口与粗估单位-2026-11-13/README.md>) · [派生](<https://github.com/B612-LP/harness-compare-bench/blob/582594f4c8c0473514d03ba64b78bc09b610ba52/5-评测报告/读取窗口与粗估单位-2026-11-13/evidence.json>) · [复算](<https://github.com/B612-LP/harness-compare-bench/blob/582594f4c8c0473514d03ba64b78bc09b610ba52/5-评测报告/读取窗口与粗估单位-2026-11-13/verify.py>) · [反例](<https://github.com/B612-LP/harness-compare-bench/blob/582594f4c8c0473514d03ba64b78bc09b610ba52/5-评测报告/读取窗口与粗估单位-2026-11-13/test_verify.py>) | 23 Read/10排除及5缺失坏setup单列；无新增产品n。CJK/UTF16公式只源码条件预测，13 ASCII不能识别单位；静态source pin非历史runtime认证，桌面Unicode仍缺样。 |
| 真正原生Read与短历史 | 两会话4次真实内置Read均按已知LF重构192行/16000B源；下一请求保留旧clip及第一Read。Read XML17105B，wrapperNoLF1297与netOverLF1105分列。 | [582594f](<https://github.com/B612-LP/harness-compare-bench/commit/582594f4c8c0473514d03ba64b78bc09b610ba52>) | [定义](<https://github.com/B612-LP/harness-compare-bench/blob/582594f4c8c0473514d03ba64b78bc09b610ba52/5-评测报告/原生外溢回读与短历史-2026-11-13/README.md>) · [派生](<https://github.com/B612-LP/harness-compare-bench/blob/582594f4c8c0473514d03ba64b78bc09b610ba52/5-评测报告/原生外溢回读与短历史-2026-11-13/evidence.json>) · [复算](<https://github.com/B612-LP/harness-compare-bench/blob/582594f4c8c0473514d03ba64b78bc09b610ba52/5-评测报告/原生外溢回读与短历史-2026-11-13/verify.py>) · [反例](<https://github.com/B612-LP/harness-compare-bench/blob/582594f4c8c0473514d03ba64b78bc09b610ba52/5-评测报告/原生外溢回读与短历史-2026-11-13/test_verify.py>) | 8本地请求/0转发是脚本客户端对照，非模型主动能力；旧解析版本4计划/0Read invalid不回填，累计11seen非11成功。stdout8192截断预览不当全文；完整初包/SID/路径安全仅私档，公开选面不认证后端/长期历史/成本。 |
| 独立源联合逐字回传 | 原裸提示门valid0/4仍FAIL；精确原生快照posthoc再判4/4正确。独立条件I_text2800>单M1732但<两源3464，重复I1400；这是字面长度，不作熵或后端容量推断。 | [893f15b](<https://github.com/B612-LP/harness-compare-bench/commit/893f15beaa76b5bfc34708eef437e314b956348a>) | [定义](<https://github.com/B612-LP/harness-compare-bench/blob/893f15beaa76b5bfc34708eef437e314b956348a/5-评测报告/独立源联合回传-2026-11-13/README.md>) · [派生](<https://github.com/B612-LP/harness-compare-bench/blob/893f15beaa76b5bfc34708eef437e314b956348a/5-评测报告/独立源联合回传-2026-11-13/evidence.json>) · [复算](<https://github.com/B612-LP/harness-compare-bench/blob/893f15beaa76b5bfc34708eef437e314b956348a/5-评测报告/独立源联合回传-2026-11-13/verify.py>) · [反例](<https://github.com/B612-LP/harness-compare-bench/blob/893f15beaa76b5bfc34708eef437e314b956348a/5-评测报告/独立源联合回传-2026-11-13/test_verify.py>) | 每条件n=2、A按rep复用、中段共文；+4残差、thinking/cache未等控，usage不算钱。初包、策略快照和原生轨迹未公开，hash只承诺不认证；公开仅selected face关系，不把事后再判追认原主门或推出全文摄入。 |
| 工具身份×阶段·头尾窗口 | 同值40,000B四格：read两阶段完整、alias两阶段裁剪；反证stage-only，不是pure-name唯一因果。豆包三份ASCII完整Read均head2048+tail2048+wrapper176/178，非纯尾窗；两80k内容同hash非独立重复。 | [beed8f2](<https://github.com/B612-LP/harness-compare-bench/commit/beed8f21134c1630ea7f14209b8ac98febef5373>) | [定义](<https://github.com/B612-LP/harness-compare-bench/blob/beed8f21134c1630ea7f14209b8ac98febef5373/5-%E8%AF%84%E6%B5%8B%E6%8A%A5%E5%91%8A/%E5%B7%A5%E5%85%B7%E8%BF%94%E5%9B%9E%E8%AE%A1%E9%87%8F%E4%B8%8E%E8%BA%AB%E4%BB%BD%E5%AF%B9%E7%85%A7-2026-11-13/README.md>) · [派生](<https://github.com/B612-LP/harness-compare-bench/blob/beed8f21134c1630ea7f14209b8ac98febef5373/5-%E8%AF%84%E6%B5%8B%E6%8A%A5%E5%91%8A/%E5%B7%A5%E5%85%B7%E8%BF%94%E5%9B%9E%E8%AE%A1%E9%87%8F%E4%B8%8E%E8%BA%AB%E4%BB%BD%E5%AF%B9%E7%85%A7-2026-11-13/derived-evidence.json>) · [复算](<https://github.com/B612-LP/harness-compare-bench/blob/beed8f21134c1630ea7f14209b8ac98febef5373/5-%E8%AF%84%E6%B5%8B%E6%8A%A5%E5%91%8A/%E5%B7%A5%E5%85%B7%E8%BF%94%E5%9B%9E%E8%AE%A1%E9%87%8F%E4%B8%8E%E8%BA%AB%E4%BB%BD%E5%AF%B9%E7%85%A7-2026-11-13/verify.py>) · [测试](<https://github.com/B612-LP/harness-compare-bench/blob/beed8f21134c1630ea7f14209b8ac98febef5373/5-%E8%AF%84%E6%B5%8B%E6%8A%A5%E5%91%8A/%E5%B7%A5%E5%85%B7%E8%BF%94%E5%9B%9E%E8%AE%A1%E9%87%8F%E4%B8%8E%E8%BA%AB%E4%BB%BD%E5%AF%B9%E7%85%A7-2026-11-13/test_verify.py>) | 四格n=1，合成工具/native fs未测、name+call_id共变、0上游仅本relay；三ASCII记录/两尺寸，Unicode单位未裁定。选择去标识派生不认证原轨迹或后端摄入；+4裁剪残差保留。 |
| 引用回读·多结果裁剪（既有） | DSH bounded+read 6/6自发回读并恢复MIDDLE；当前请求面区分正文省略与包装、旧预览后续保留。N=2四产品/N=3两CLI小样本按结果或调用分别处理；不据同源多副本证明独立内容联合利用。Codex直接请求面支持严格bytes>10,000及头尾各5,000B，取代旧usage反推。 | [e4f5e83](<https://github.com/B612-LP/harness-compare-bench/commit/e4f5e83c4f367698980cfee02003e6778668761f>) | [定义](<https://github.com/B612-LP/harness-compare-bench/blob/e4f5e83c4f367698980cfee02003e6778668761f/5-%E8%AF%84%E6%B5%8B%E6%8A%A5%E5%91%8A/%E5%BC%95%E7%94%A8%E5%9B%9E%E8%AF%BB%E4%B8%8E%E5%B7%B2%E7%9F%A5%E8%AF%BB%E5%8F%96%E6%AD%A3%E6%8E%A7-2026-11-13/README.md>) · [结果](<https://github.com/B612-LP/harness-compare-bench/blob/e4f5e83c4f367698980cfee02003e6778668761f/5-%E8%AF%84%E6%B5%8B%E6%8A%A5%E5%91%8A/%E5%BC%95%E7%94%A8%E5%9B%9E%E8%AF%BB%E4%B8%8E%E5%B7%B2%E7%9F%A5%E8%AF%BB%E5%8F%96%E6%AD%A3%E6%8E%A7-2026-11-13/result.json>) · [复算](<https://github.com/B612-LP/harness-compare-bench/blob/e4f5e83c4f367698980cfee02003e6778668761f/5-%E8%AF%84%E6%B5%8B%E6%8A%A5%E5%91%8A/%E5%BC%95%E7%94%A8%E5%9B%9E%E8%AF%BB%E4%B8%8E%E5%B7%B2%E7%9F%A5%E8%AF%BB%E5%8F%96%E6%AD%A3%E6%8E%A7-2026-11-13/verify.py>) · [测试](<https://github.com/B612-LP/harness-compare-bench/blob/e4f5e83c4f367698980cfee02003e6778668761f/5-%E8%AF%84%E6%B5%8B%E6%8A%A5%E5%91%8A/%E5%BC%95%E7%94%A8%E5%9B%9E%E8%AF%BB%E4%B8%8E%E5%B7%B2%E7%9F%A5%E8%AF%BB%E5%8F%96%E6%AD%A3%E6%8E%A7-2026-11-13/test_verify.py>) | 单版本与小样本；各产品观测层分列，thinking/cache/后端摄入未知；元宝专家首三槽partial，尺寸槽模式不同、256k通道阻断不裁产品；WB旧ASCII估计器不能外推Unicode。原捕获私存，字节不当token/成本，旧25格及分数不改。 |
| 30次测了什么 | 30槽/10组重复性，不是M1外溢效果；完整旧门6不通过+4不可核，DSH4/5仅字节子门。 | [06ef6ef](<https://github.com/B612-LP/harness-compare-bench/commit/06ef6ef19272f398466278500d30a8eb8d5fae11>) | [版本化澄清v1.1](<https://github.com/B612-LP/harness-compare-bench/blob/06ef6ef19272f398466278500d30a8eb8d5fae11/4-%E6%89%93%E5%88%86%E7%BB%86%E5%88%99/%E6%9C%BA%E5%88%B6%E9%87%8D%E5%A4%8D%E5%8F%A3%E5%BE%84%E6%BE%84%E6%B8%85-2026-11-12/README.md>) · [B重算](<https://github.com/B612-LP/harness-compare-bench/blob/06ef6ef19272f398466278500d30a8eb8d5fae11/4-%E6%89%93%E5%88%86%E7%BB%86%E5%88%99/%E6%9C%BA%E5%88%B6%E9%87%8D%E5%A4%8D%E5%8F%A3%E5%BE%84%E6%BE%84%E6%B8%85-2026-11-12/verify.py>) · [新安全投影](<https://github.com/B612-LP/harness-compare-bench/blob/06ef6ef19272f398466278500d30a8eb8d5fae11/4-%E6%89%93%E5%88%86%E7%BB%86%E5%88%99/%E6%9C%BA%E5%88%B6%E9%87%8D%E5%A4%8D%E5%8F%A3%E5%BE%84%E6%BE%84%E6%B8%85-2026-11-12/evidence.json>) | 69历史公共源来自38b2；新投影不在该基线，只能公开核算术。24继承meta/缺a1_gate、4基名缺口保留；不认证私档内容。 |
| 日志输入代理有效吗 | 15槽S3合计中68.49%为静态声明且排除工具返回；R3混合多类payload。只识别日志计量面。 | [284ea40](<https://github.com/B612-LP/harness-compare-bench/commit/284ea40bf327109e759fc4b4ebca66e67e20732b>) | [30源分解](<https://github.com/B612-LP/harness-compare-bench/blob/284ea40bf327109e759fc4b4ebca66e67e20732b/5-%E8%AF%84%E6%B5%8B%E6%8A%A5%E5%91%8A/%E6%97%A5%E5%BF%97%E8%AE%A1%E9%87%8F%E6%9C%89%E6%95%88%E6%80%A7-2026-11-12/README.md>) · [重算](<https://github.com/B612-LP/harness-compare-bench/blob/284ea40bf327109e759fc4b4ebca66e67e20732b/5-%E8%AF%84%E6%B5%8B%E6%8A%A5%E5%91%8A/%E6%97%A5%E5%BF%97%E8%AE%A1%E9%87%8F%E6%9C%89%E6%95%88%E6%80%A7-2026-11-12/verify.py>) · [结果](<https://github.com/B612-LP/harness-compare-bench/blob/284ea40bf327109e759fc4b4ebca66e67e20732b/5-%E8%AF%84%E6%B5%8B%E6%8A%A5%E5%91%8A/%E6%97%A5%E5%BF%97%E8%AE%A1%E9%87%8F%E6%9C%89%E6%95%88%E6%80%A7-2026-11-12/result.json>) | 新投影非52b5基线原件；公开不核私档原文。956是两完整异步事件，3次指定签名重复不是全部语义重复；usage不认证发送切点。 |
| 代理能唯一决定请求吗 | 同发送前L与独立切点，三renderer请求不同；新增绑定body观测可缩小候选。 | [284ea40](<https://github.com/B612-LP/harness-compare-bench/commit/284ea40bf327109e759fc4b4ebca66e67e20732b>) | [条件逻辑附证](<https://github.com/B612-LP/harness-compare-bench/blob/284ea40bf327109e759fc4b4ebca66e67e20732b/4-%E6%89%93%E5%88%86%E7%BB%86%E5%88%99/%E6%97%A5%E5%BF%97%E4%BB%A3%E7%90%86%E5%8F%8D%E8%AF%81-2026-11-12/README.md>) · [重算](<https://github.com/B612-LP/harness-compare-bench/blob/284ea40bf327109e759fc4b4ebca66e67e20732b/4-%E6%89%93%E5%88%86%E7%BB%86%E5%88%99/%E6%97%A5%E5%BF%97%E4%BB%A3%E7%90%86%E5%8F%8D%E8%AF%81-2026-11-12/verify.py>) · [结果](<https://github.com/B612-LP/harness-compare-bench/blob/284ea40bf327109e759fc4b4ebca66e67e20732b/4-%E6%89%93%E5%88%86%E7%BB%86%E5%88%99/%E6%97%A5%E5%BF%97%E4%BB%A3%E7%90%86%E5%8F%8D%E8%AF%81-2026-11-12/result.json>) | 仅有限模型/结构兼容，非真实模型输出、官方API、采集来源或历史HTTP认证；不是新增产品trial或第三次独立效果研究。 |
| 零命中如何判 | 在当前检测面未观察到；WB1124个记录≠读取机会，豆包未采≠零命中。 | [06ef6ef](<https://github.com/B612-LP/harness-compare-bench/commit/06ef6ef19272f398466278500d30a8eb8d5fae11>) | [sensor×truth分账](<https://github.com/B612-LP/harness-compare-bench/blob/06ef6ef19272f398466278500d30a8eb8d5fae11/4-%E6%89%93%E5%88%86%E7%BB%86%E5%88%99/%E8%AF%BB%E5%8F%96%E8%A7%82%E6%B5%8B%E8%A3%81%E5%AE%9A-2026-11-12/README.md>) · [C重算](<https://github.com/B612-LP/harness-compare-bench/blob/06ef6ef19272f398466278500d30a8eb8d5fae11/4-%E6%89%93%E5%88%86%E7%BB%86%E5%88%99/%E8%AF%BB%E5%8F%96%E8%A7%82%E6%B5%8B%E8%A3%81%E5%AE%9A-2026-11-12/verify.py>) · [结果](<https://github.com/B612-LP/harness-compare-bench/blob/06ef6ef19272f398466278500d30a8eb8d5fae11/4-%E6%89%93%E5%88%86%E7%BB%86%E5%88%99/%E8%AF%BB%E5%8F%96%E8%A7%82%E6%B5%8B%E8%A3%81%E5%AE%9A-2026-11-12/result.json>) | 合成28试次不能给产品召回率；两个世界兼容同一日志，真实读取分母/FN/非平凡风险上界未知，不证明隔离。 |
| 判分链能否支撑归因 | q2697在216语义组合下不可复现原gold；判卷对象、gold、参考解和自测先于未来能力归因。 | [38b2e13](<https://github.com/B612-LP/harness-compare-bench/commit/38b2e13f63c5aeacb58094d2e977980ab12e8041>) | [金标复算](<https://github.com/B612-LP/harness-compare-bench/blob/38b2e13f63c5aeacb58094d2e977980ab12e8041/5-%E8%AF%84%E6%B5%8B%E6%8A%A5%E5%91%8A/%E6%B4%BE%E7%94%9F%E5%88%86%E6%9E%90-q2697gold%E5%A4%8D%E7%AE%97-20261111/README.md>) · [前置门](<https://github.com/B612-LP/harness-compare-bench/blob/38b2e13f63c5aeacb58094d2e977980ab12e8041/4-%E6%89%93%E5%88%86%E7%BB%86%E5%88%99/%E5%88%A4%E5%88%86%E9%93%BE%E5%89%8D%E7%BD%AE%E9%AA%8C%E8%AF%81%E8%A7%84%E8%8C%83-2026-11-11/README.md>) | 兼容历史分保留；不因不复现而猜新gold、回判正式行，交付终点失败不自动等于算法能力失败。 |
| 台账能否全量认证 | 只能按对应generation.head和同一sidecar复算，不能说任意最新HEAD全可核。 | [38b2e13](<https://github.com/B612-LP/harness-compare-bench/commit/38b2e13f63c5aeacb58094d2e977980ab12e8041>)；generation=[66e98ea](<https://github.com/B612-LP/harness-compare-bench/commit/66e98ea25caaeec041a794f8efa3d926f4213a82>) | [复算合同](<https://github.com/B612-LP/harness-compare-bench/blob/38b2e13f63c5aeacb58094d2e977980ab12e8041/4-%E6%89%93%E5%88%86%E7%BB%86%E5%88%99/%E6%A0%B8%E9%AA%8C%E5%8F%B0%E8%B4%A6-2026-11-07/README.md>) · [绑定清单](<https://github.com/B612-LP/harness-compare-bench/blob/38b2e13f63c5aeacb58094d2e977980ab12e8041/4-%E6%89%93%E5%88%86%E7%BB%86%E5%88%99/%E6%A0%B8%E9%AA%8C%E5%8F%B0%E8%B4%A6-2026-11-07/ledger.json>) | 5类公开不可复核缺口与14件私档sidecar分列；机器见证非真人签名或原件真实性认证。 |
| complete与反馈闭环 | grader字段不等于Agent声明；旧F5引用链支持不足。两案可见修补，只有所选r1导出有后续复验/全局终答；不改原标签或分数。 | [f4fb597](<https://github.com/B612-LP/harness-compare-bench/commit/f4fb59799cb83dd6b7d386495b45da1e63b787c9>) | [定义](<https://github.com/B612-LP/harness-compare-bench/blob/f4fb59799cb83dd6b7d386495b45da1e63b787c9/5-%E8%AF%84%E6%B5%8B%E6%8A%A5%E5%91%8A/%E5%8F%8D%E9%A6%88%E9%97%AD%E7%8E%AF%E5%86%8D%E5%88%86%E6%9E%90-2026-11-12/README.md>) · [原语](<https://github.com/B612-LP/harness-compare-bench/blob/f4fb59799cb83dd6b7d386495b45da1e63b787c9/5-%E8%AF%84%E6%B5%8B%E6%8A%A5%E5%91%8A/%E5%8F%8D%E9%A6%88%E9%97%AD%E7%8E%AF%E5%86%8D%E5%88%86%E6%9E%90-2026-11-12/core.py>) · [测试](<https://github.com/B612-LP/harness-compare-bench/blob/f4fb59799cb83dd6b7d386495b45da1e63b787c9/5-%E8%AF%84%E6%B5%8B%E6%8A%A5%E5%91%8A/%E5%8F%8D%E9%A6%88%E9%97%AD%E7%8E%AF%E5%86%8D%E5%88%86%E6%9E%90-2026-11-12/test_core.py>) · [数据](<https://github.com/B612-LP/harness-compare-bench/blob/f4fb59799cb83dd6b7d386495b45da1e63b787c9/5-%E8%AF%84%E6%B5%8B%E6%8A%A5%E5%91%8A/%E5%8F%8D%E9%A6%88%E9%97%AD%E7%8E%AF%E5%86%8D%E5%88%86%E6%9E%90-2026-11-12/events.json>) · [复算](<https://github.com/B612-LP/harness-compare-bench/blob/f4fb59799cb83dd6b7d386495b45da1e63b787c9/5-%E8%AF%84%E6%B5%8B%E6%8A%A5%E5%91%8A/%E5%8F%8D%E9%A6%88%E9%97%AD%E7%8E%AF%E5%86%8D%E5%88%86%E6%9E%90-2026-11-12/verify.py>) | 两历史评分目标身份unknown；两例目的性选择非新n。目标写串行已核；并行同路径提交顺序不在原语认证范围。私原不公开，37检查只核派生自洽。 |
| Cargo三红与政策 | 在本次固定的两条政策中，只有参考式政策命中三项点值；点门全绿不等于完整五段可行，也不识别所有可能政策中的唯一答案。最终返回储备及简化模型下两者可核，完整合同、物理法规和原评分文件身份仍unknown，原分不变。 | [7f1324e](<https://github.com/B612-LP/harness-compare-bench/commit/7f1324ec5b507e35b1dbad9b9295170b82b24497>) | [定义](<https://github.com/B612-LP/harness-compare-bench/blob/7f1324ec5b507e35b1dbad9b9295170b82b24497/5-%E8%AF%84%E6%B5%8B%E6%8A%A5%E5%91%8A/%E7%87%83%E6%B2%B9%E6%94%BF%E7%AD%96%E4%B8%8E%E5%88%A4%E6%8D%AE%E8%BE%A8%E5%88%AB-2026-11-12/README.md>) · [新数学](<https://github.com/B612-LP/harness-compare-bench/blob/7f1324ec5b507e35b1dbad9b9295170b82b24497/5-%E8%AF%84%E6%B5%8B%E6%8A%A5%E5%91%8A/%E7%87%83%E6%B2%B9%E6%94%BF%E7%AD%96%E4%B8%8E%E5%88%A4%E6%8D%AE%E8%BE%A8%E5%88%AB-2026-11-12/core.py>) · [测试](<https://github.com/B612-LP/harness-compare-bench/blob/7f1324ec5b507e35b1dbad9b9295170b82b24497/5-%E8%AF%84%E6%B5%8B%E6%8A%A5%E5%91%8A/%E7%87%83%E6%B2%B9%E6%94%BF%E7%AD%96%E4%B8%8E%E5%88%A4%E6%8D%AE%E8%BE%A8%E5%88%AB-2026-11-12/test_core.py>) · [数据](<https://github.com/B612-LP/harness-compare-bench/blob/7f1324ec5b507e35b1dbad9b9295170b82b24497/5-%E8%AF%84%E6%B5%8B%E6%8A%A5%E5%91%8A/%E7%87%83%E6%B2%B9%E6%94%BF%E7%AD%96%E4%B8%8E%E5%88%A4%E6%8D%AE%E8%BE%A8%E5%88%AB-2026-11-12/result.json>) · [复算](<https://github.com/B612-LP/harness-compare-bench/blob/7f1324ec5b507e35b1dbad9b9295170b82b24497/5-%E8%AF%84%E6%B5%8B%E6%8A%A5%E5%91%8A/%E7%87%83%E6%B2%B9%E6%94%BF%E7%AD%96%E4%B8%8E%E5%88%A4%E6%8D%AE%E8%BE%A8%E5%88%AB-2026-11-12/verify.py>) | 目的性旧单例非新n；原评分文件SHA、完整程序/行为及唯一储备范围未知；不翻组Y，29检查只核派生自洽。 |

## 最小复算（在独立克隆/工作树中）

先在独立克隆复核2026-11-14新增的两个证据包（只读复算；纯测试不是新产品样本）：

```sh
git checkout --detach 9564ffd7cf56fc7c8316b90d0ba9cb25dcde2191
(cd '5-评测报告/回读任务信息与投影反例-2026-11-14' && python3 -B verify.py && python3 -B test_cleanroom.py)
(cd '5-评测报告/读取正例与检测支持集-2026-11-14' && python3 -B verify.py && python3 -B test_verify.py)
```

六静态反例与指定Native派生分别复算；根清单依固定提交绑定，不自证真实性。以下旧命令及其绑定保持原样，不在有未提交改动的工作目录直接切换：

```sh
git checkout --detach 06ef6ef19272f398466278500d30a8eb8d5fae11
python3 -I -S -B '5-评测报告/输入源覆盖与机制区分-2026-11-12/verify.py' --root .
python3 -I -S -B '4-打分细则/机制重复口径澄清-2026-11-12/verify.py' --root .
python3 -I -S -B '4-打分细则/读取观测裁定-2026-11-12/verify.py' --root .

git checkout --detach e4f5e83c4f367698980cfee02003e6778668761f
python3 -I -S -B '5-评测报告/引用回读与已知读取正控-2026-11-13/verify.py'
```

前四命令默认只读并输出JSON；末一命令为 2026-11-13 新增行（只读 result.json 重算统计与常量，无 --root 参数），同目录 `test_verify.py` 可另在普通/`-O`模式运行。成功只说明各自固定公开字节与声明范围相符，不恢复私档原文、不证明产品效果或历史全部封印通过。各原始usage保持逐场辅助记录，bytes不当token/费用。

## 独立源联合回传（事后口径与原门分列）

另取本次确切科学提交；只需Python 3.9+标准库：

```sh
git checkout --detach 893f15beaa76b5bfc34708eef437e314b956348a
python3 -I -S -B '5-评测报告/独立源联合回传-2026-11-13/verify.py'
(cd '5-评测报告/独立源联合回传-2026-11-13' && python3 -B test_verify.py && python3 -B -O test_verify.py)
```

原裸提示门仍FAIL 0/4；公开重算的4/4只对应精确原生快照适配后的选择派生文本。7组回归不是新增产品样本；不能用公开hash恢复未公开首包、策略或原生轨迹，不能将I_text当熵或费用。

## 工具身份与头尾窗口（选择派生）

另取新对照的确切快照；只需Python 3.9+标准库：

```sh
git checkout --detach beed8f21134c1630ea7f14209b8ac98febef5373
python3 -I -S -B '5-评测报告/工具返回计量与身份对照-2026-11-13/verify.py'
(cd '5-评测报告/工具返回计量与身份对照-2026-11-13' && python3 -B -m unittest -q test_verify.py)
```

31项测试/反例与`DERIVED_RELATIONSHIPS_PASS`仅验选择派生关系；不认证完整原始运行、实际模型摄入或正式成绩。原件来源核对留私档；字节等长路径去标识、JSON/wire原hash分账，公开文本不冒充原始轨迹。

## 日志有效性与条件附证（各自固定快照）

在另一独立克隆/工作树运行；旧三项命令和其06ef绑定保持不变。

```sh
git checkout --detach 284ea40bf327109e759fc4b4ebca66e67e20732b
python3 -I -S -B '5-评测报告/日志计量有效性-2026-11-12/verify.py' --root .
python3 -I -S -B '4-打分细则/日志代理反证-2026-11-12/verify.py' --root .
```

两命令默认只读stdout；新安全投影及条件构造不认证私档原文、真实发送或模型效果。

**历史复核漂移（本次实际重放）：**旧正式来源校验器在 `ababe63694b46db7ed8cd2c5210243155b5cde5c` 返回 `ok=true`，402项中397匹配、5历史缺失；在38b2/06ef返回 `trusted source SHA mismatch: 4-打分细则/裁定-2026-10-26-dab-q2697.md`。后者为396匹配、5历史缺失、1已改文档不匹配：预期SHA `7a163a5bd803712acc237f0d5da8c71f18218ea558c51999b6f6b0b11362d152`，当前 `48320c5369325790103ca14842e17eebaa1d9908b771cad33a6536a018cc6f39`；不更新旧pin或倒洗原件来造全绿。历史代v1.9与当前v1.9/v1.10/v1.11/v1.12/v1.13/v1.14的§3（从 `## 3.` 起至 `## 4.` 前）均3121B、SHA `ae22e337ff75f089a35577a096a2036e454dd711a22c4a62c687533146965419`，这是字节桥接，不认证后续分析。要重放旧入口，请在另一独立克隆：

```sh
git checkout --detach ababe63694b46db7ed8cd2c5210243155b5cde5c
python3 -I -S -B '5-评测报告/正式行复核-2026-11-05/verify.py' --root .
```

**先解释再增样本：**30次已完成，不能按Issue审阅时点的“尚未运行”重跑；新的序列诊断、首三条内容一致或模型输出波动不替代旧AND主门，不提高正式n。


## 反馈字段与闭环（既有两案）

本次两条档案中，每个assistant轮最多一次修改目标文件，前一成功写入回包早于后一写调用；已逐项核对。对于同轮并行修改同一路径的轨迹，原语不能仅凭调用数组顺序认证文件实际提交顺序，不属于本次复核覆盖。

在另一独立克隆/工作树按确切快照执行，本入口不要求旧接口的`--root`参数：

```sh
git checkout --detach f4fb59799cb83dd6b7d386495b45da1e63b787c9
python3 -B '5-评测报告/反馈闭环再分析-2026-11-12/verify.py'
python3 -B -O '5-评测报告/反馈闭环再分析-2026-11-12/verify.py'
```

37项派生检查与52合成测试只验证安全投影的内部一致性；私档完整读取、调用配对与串行前提已另作独立复核，但公开PASS不是私原历史认证。Edit成功不证明已绿，导出未见后续终答不证明世界中从未发生；旧分数与原F5不回写。


## Cargo合同、两政策与三项点门（既有单例）

在本次固定的两条政策中，只有参考式政策命中三项点值；点门全绿不等于完整五段可行，也不识别所有可能政策中的唯一答案。最终返回储备及简化模型下两者可核，完整合同、物理法规和原评分文件身份仍unknown，原分不变。

在另一独立克隆/工作树按确切科学快照执行，不加旧接口的`-I`或`--root`：

```sh
git checkout --detach 7f1324ec5b507e35b1dbad9b9295170b82b24497
python3 -B '5-评测报告/燃油政策与判据辨别-2026-11-12/verify.py'
python3 -B -O '5-评测报告/燃油政策与判据辨别-2026-11-12/verify.py'
```

29项派生检查与52新测试验证公开输入及新五段计算的一致性；不执行旧程序、裁定唯一合同、认证原评分文件或真实适航，不改原24/27、88.89/reward1及其他历史分数。

## 读取窗口与原生回读跟进的最小复算

两包均绑定实际提交`582594f4c8c0473514d03ba64b78bc09b610ba52`，不是任意HEAD或原件认证；Python3.9+标准库，软件回归不计产品n。

```sh
git checkout 582594f4c8c0473514d03ba64b78bc09b610ba52
cd 5-评测报告/读取窗口与粗估单位-2026-11-13
python3 -B verify.py
python3 -B -m unittest -v test_verify.py
python3 -O -B verify.py
python3 -O -B -m unittest -v test_verify.py
cd ../原生外溢回读与短历史-2026-11-13
python3 -B verify.py
python3 -B -m unittest -v test_verify.py
python3 -O -B verify.py
python3 -O -B -m unittest -v test_verify.py
```
