# 一页结论—绑定提交—公开复算—私档缺口

对应[第四周反馈](<../../反馈/2026-11-11-第四轮/README.md>)与[当前整合报告 v1.21](<../竞品评测报告-v1.21.md>)。绑定的是每条结论的证据/实现快照，不是“任意 HEAD 全部可核”。此前各行为事后重算/方法检验、不新增产品运行；2026-11-13 新增行为预注册小样本（机制最小对照+已知读取正控，v2 同日扩 Codex/元宝首场，v3 同日再补尺寸响应探针，v4 同日补外溢 cap 扫描，v5 同日补 MIDDLE 位置对照，v6 同日补外溢边界细化，v7 同日补元宝正控三场终版），按其预注册范围披露，不入正式格，旧协议、报告、25格及原成绩不回写。

| 关键问题 | 当前可说的结论 | 绑定提交 | 公开复算/证据入口 | 不能公开或尚未识别的缺口 |
|---|---|---|---|---|
| 正式25格 | 每格n=1；A10/B10/W5只作轨内观察，不合五款总榜。 | [ababe63](<https://github.com/B612-LP/harness-compare-bench/commit/ababe63694b46db7ed8cd2c5210243155b5cde5c>)（历史可执行代） | [旧版25行来源闭合](<https://github.com/B612-LP/harness-compare-bench/blob/ababe63694b46db7ed8cd2c5210243155b5cde5c/5-评测报告/正式行复核-2026-11-05/README.md>)；该代v1.9与当前v1.9/v1.10/v1.11/v1.12/v1.13/v1.14的§3字节相同。 | 38b2/06ef当前树运行旧verify会在q2697文档SHA门失败；只在左列固定历史代实际通过。来源闭合非重新判卷或原件认证，详见下方漂移与命令。 |
| 输入为何减少 | 18场捕获区间保留旧历史；工具源正文省略与包装差共存，不能只归为等文本重组。 | [06ef6ef](<https://github.com/B612-LP/harness-compare-bench/commit/06ef6ef19272f398466278500d30a8eb8d5fae11>) | [定义/18场分账](<https://github.com/B612-LP/harness-compare-bench/blob/06ef6ef19272f398466278500d30a8eb8d5fae11/5-%E8%AF%84%E6%B5%8B%E6%8A%A5%E5%91%8A/%E8%BE%93%E5%85%A5%E6%BA%90%E8%A6%86%E7%9B%96%E4%B8%8E%E6%9C%BA%E5%88%B6%E5%8C%BA%E5%88%86-2026-11-12/README.md>) · [A重算](<https://github.com/B612-LP/harness-compare-bench/blob/06ef6ef19272f398466278500d30a8eb8d5fae11/5-%E8%AF%84%E6%B5%8B%E6%8A%A5%E5%91%8A/%E8%BE%93%E5%85%A5%E6%BA%90%E8%A6%86%E7%9B%96%E4%B8%8E%E6%9C%BA%E5%88%B6%E5%8C%BA%E5%88%86-2026-11-12/verify.py>) · [结果](<https://github.com/B612-LP/harness-compare-bench/blob/06ef6ef19272f398466278500d30a8eb8d5fae11/5-%E8%AF%84%E6%B5%8B%E6%8A%A5%E5%91%8A/%E8%BE%93%E5%85%A5%E6%BA%90%E8%A6%86%E7%9B%96%E4%B8%8E%E6%9C%BA%E5%88%B6%E5%8C%BA%E5%88%86-2026-11-12/result.json>) | 同DSH六对与原生三block不合n=9；引用不等实际回读，未控制后端历史/思考/cache，不推token/费用。 |
| 引用能否回读·读取正控 | DSH bounded 引用⇒全文可回读实证成立：6/6 自发调用 read、被截断区 MIDDLE 键 6/6 恢复（Wilson95 [0.610,1]）；C1 复制门 delta=2382B 与 1103 基线逐字节一致；会话字节≈内联的32%。已知读取正控覆盖四产品：WB/豆包/Codex CLI 各 3/3 全文回读（Codex cat 聚合输出全量 35,767B 无截断），元宝 n=3 终版 partial（v7：仅 1/3 场到达可观测读取步骤且 2/3，另两场中尾键伪造、无一次全键正确；不下产品结论）；旧 0 命中不能归因读取失效，但仍非漏检上界。同日尺寸响应探针（v3）：Codex/WB/豆包 ×1k/8k/64k/256k，1k–64k 全内联，256KB 首现工具显式 token 上限拒绝（WB 20,000/豆包 25,000）且模型自发定向补偿（WB offset/limit、豆包 Grep）、三键仍全对；WB 64k 持久化预览展示+usage 增量证模型侧全文摄入（展示形态≠摄入）。同日外溢 cap 扫描（v4）：DSH cap 512–131072 五档 ×2，自发 read 于 ≤8192 全出现、≥32768 全消失（交叉点 [8192,32768]），MIDDLE 10/10，会话字节非单调、512 最省（13,128.5B）8192 最贵（74,846B）。同日 MIDDLE 位置对照（v5，cap 8192）：所问记录在头段（4.6%）/尾段（96.3%）各 ×2 槽零 read 三键全对；捕获实证 DSH bounded 预览=头+尾保留省略中段（noise-0405@96.3% 在预览内、noise-0210@50% 不在、尾部 Omitted 3319 bytes 页脚）——模型恰在所问记录位于被省略中段时才 read，答案可见性裁决 v4 停用规则两解释。同日外溢边界细化（v6，cap 9216/16384 各 ×2 槽、问中段记录）：4/4 零 read 三键全对、无外溢页脚，c16384 无外溢预测成立、c9216 预测不成立如实记录（实测无外溢）——外溢消失边界收敛到 (8192,9216]（预算≈cap×4 字符 vs 夹具≈8,942 token 推算），E1 答案可见性门覆盖全部六个实测条件。同日边界单帽精度（v8，Ring 18/18b/18c，DSH 7 会话）：截断量律 omitted=35767−4×(cap−80) 三点零自由参数精确（8941→323/8942→319/8192→3319，Δcap+1→omitted−4）、外溢消失边界收窄 [8943,9020]（8942 溢、9020/9021/9022 不溢）、触发判据≠chars/4 估计（候选=真实 tokenizer，不可直接观测），三个事前预测被否证如实记录；元宝 1k 尺寸点（v8 interim）：990B 探针专家模式 3/3 全对。 | [0793d60](<https://github.com/B612-LP/harness-compare-bench/commit/0793d6084d632b8f5589b25b05f970a0654a6192>) | [定义](<https://github.com/B612-LP/harness-compare-bench/blob/0793d6084d632b8f5589b25b05f970a0654a6192/5-%E8%AF%84%E6%B5%8B%E6%8A%A5%E5%91%8A/%E5%BC%95%E7%94%A8%E5%9B%9E%E8%AF%BB%E4%B8%8E%E5%B7%B2%E7%9F%A5%E8%AF%BB%E5%8F%96%E6%AD%A3%E6%8E%A7-2026-11-13/README.md>) · [结果](<https://github.com/B612-LP/harness-compare-bench/blob/0793d6084d632b8f5589b25b05f970a0654a6192/5-%E8%AF%84%E6%B5%8B%E6%8A%A5%E5%91%8A/%E5%BC%95%E7%94%A8%E5%9B%9E%E8%AF%BB%E4%B8%8E%E5%B7%B2%E7%9F%A5%E8%AF%BB%E5%8F%96%E6%AD%A3%E6%8E%A7-2026-11-13/result.json>) · [复算](<https://github.com/B612-LP/harness-compare-bench/blob/0793d6084d632b8f5589b25b05f970a0654a6192/5-%E8%AF%84%E6%B5%8B%E6%8A%A5%E5%91%8A/%E5%BC%95%E7%94%A8%E5%9B%9E%E8%AF%BB%E4%B8%8E%E5%B7%B2%E7%9F%A5%E8%AF%BB%E5%8F%96%E6%AD%A3%E6%8E%A7-2026-11-13/verify.py>) · [测试](<https://github.com/B612-LP/harness-compare-bench/blob/0793d6084d632b8f5589b25b05f970a0654a6192/5-%E8%AF%84%E6%B5%8B%E6%8A%A5%E5%91%8A/%E5%BC%95%E7%94%A8%E5%9B%9E%E8%AF%BB%E4%B8%8E%E5%B7%B2%E7%9F%A5%E8%AF%BB%E5%8F%96%E6%AD%A3%E6%8E%A7-2026-11-13/test_verify.py>) | 单一夹具几何不外推；真实thinking/cache/后端序列化不可观测；正控按探针条件披露，不证明隔离、不构成FN上界；WB模型档位未控、豆包本地轨迹无usage字段、Codex按设计启用shell工具、元宝n=3终版partial、读取步骤检测面=页面可见文本、上传经合成DragEvent通道；字节≠token≠成本；新增17会话+尺寸响应12会话+DSH 机制加测 21 会话（含边界精度 7）+元宝 1k 点 1 会话（interim）不入正式格，原始捕获/轨迹留私档；尺寸探针观察面各产品本地轨迹/回执、每槽n=1、256KB以上未探、WB/豆包上限为观察面工具侧限制；cap 扫描机制面单一夹具、n=2/臂；边界已收窄 [8943,9020] 但段内未逐点定位；触发判据候选=真实 tokenizer 不可直接观测、−80 常数含义未解释；元宝 1k 点 interim、尺寸响应中间点未测；位置对照限于三个探针位置（4.6%/50%/96.3%）、头+尾分割精确比例与 read 动机不可直接观测。 |
| 30次测了什么 | 30槽/10组重复性，不是M1外溢效果；完整旧门6不通过+4不可核，DSH4/5仅字节子门。 | [06ef6ef](<https://github.com/B612-LP/harness-compare-bench/commit/06ef6ef19272f398466278500d30a8eb8d5fae11>) | [版本化澄清v1.1](<https://github.com/B612-LP/harness-compare-bench/blob/06ef6ef19272f398466278500d30a8eb8d5fae11/4-%E6%89%93%E5%88%86%E7%BB%86%E5%88%99/%E6%9C%BA%E5%88%B6%E9%87%8D%E5%A4%8D%E5%8F%A3%E5%BE%84%E6%BE%84%E6%B8%85-2026-11-12/README.md>) · [B重算](<https://github.com/B612-LP/harness-compare-bench/blob/06ef6ef19272f398466278500d30a8eb8d5fae11/4-%E6%89%93%E5%88%86%E7%BB%86%E5%88%99/%E6%9C%BA%E5%88%B6%E9%87%8D%E5%A4%8D%E5%8F%A3%E5%BE%84%E6%BE%84%E6%B8%85-2026-11-12/verify.py>) · [新安全投影](<https://github.com/B612-LP/harness-compare-bench/blob/06ef6ef19272f398466278500d30a8eb8d5fae11/4-%E6%89%93%E5%88%86%E7%BB%86%E5%88%99/%E6%9C%BA%E5%88%B6%E9%87%8D%E5%A4%8D%E5%8F%A3%E5%BE%84%E6%BE%84%E6%B8%85-2026-11-12/evidence.json>) | 69历史公共源来自38b2；新投影不在该基线，只能公开核算术。24继承meta/缺a1_gate、4基名缺口保留；不认证私档内容。 |
| 日志输入代理有效吗 | 15槽S3合计中68.49%为静态声明且排除工具返回；R3混合多类payload。只识别日志计量面。 | [284ea40](<https://github.com/B612-LP/harness-compare-bench/commit/284ea40bf327109e759fc4b4ebca66e67e20732b>) | [30源分解](<https://github.com/B612-LP/harness-compare-bench/blob/284ea40bf327109e759fc4b4ebca66e67e20732b/5-%E8%AF%84%E6%B5%8B%E6%8A%A5%E5%91%8A/%E6%97%A5%E5%BF%97%E8%AE%A1%E9%87%8F%E6%9C%89%E6%95%88%E6%80%A7-2026-11-12/README.md>) · [重算](<https://github.com/B612-LP/harness-compare-bench/blob/284ea40bf327109e759fc4b4ebca66e67e20732b/5-%E8%AF%84%E6%B5%8B%E6%8A%A5%E5%91%8A/%E6%97%A5%E5%BF%97%E8%AE%A1%E9%87%8F%E6%9C%89%E6%95%88%E6%80%A7-2026-11-12/verify.py>) · [结果](<https://github.com/B612-LP/harness-compare-bench/blob/284ea40bf327109e759fc4b4ebca66e67e20732b/5-%E8%AF%84%E6%B5%8B%E6%8A%A5%E5%91%8A/%E6%97%A5%E5%BF%97%E8%AE%A1%E9%87%8F%E6%9C%89%E6%95%88%E6%80%A7-2026-11-12/result.json>) | 新投影非52b5基线原件；公开不核私档原文。956是两完整异步事件，3次指定签名重复不是全部语义重复；usage不认证发送切点。 |
| 代理能唯一决定请求吗 | 同发送前L与独立切点，三renderer请求不同；新增绑定body观测可缩小候选。 | [284ea40](<https://github.com/B612-LP/harness-compare-bench/commit/284ea40bf327109e759fc4b4ebca66e67e20732b>) | [条件逻辑附证](<https://github.com/B612-LP/harness-compare-bench/blob/284ea40bf327109e759fc4b4ebca66e67e20732b/4-%E6%89%93%E5%88%86%E7%BB%86%E5%88%99/%E6%97%A5%E5%BF%97%E4%BB%A3%E7%90%86%E5%8F%8D%E8%AF%81-2026-11-12/README.md>) · [重算](<https://github.com/B612-LP/harness-compare-bench/blob/284ea40bf327109e759fc4b4ebca66e67e20732b/4-%E6%89%93%E5%88%86%E7%BB%86%E5%88%99/%E6%97%A5%E5%BF%97%E4%BB%A3%E7%90%86%E5%8F%8D%E8%AF%81-2026-11-12/verify.py>) · [结果](<https://github.com/B612-LP/harness-compare-bench/blob/284ea40bf327109e759fc4b4ebca66e67e20732b/4-%E6%89%93%E5%88%86%E7%BB%86%E5%88%99/%E6%97%A5%E5%BF%97%E4%BB%A3%E7%90%86%E5%8F%8D%E8%AF%81-2026-11-12/result.json>) | 仅有限模型/结构兼容，非真实模型输出、官方API、采集来源或历史HTTP认证；不是新增产品trial或第三次独立效果研究。 |
| 零命中如何判 | 在当前检测面未观察到；WB1124个记录≠读取机会，豆包未采≠零命中。 | [06ef6ef](<https://github.com/B612-LP/harness-compare-bench/commit/06ef6ef19272f398466278500d30a8eb8d5fae11>) | [sensor×truth分账](<https://github.com/B612-LP/harness-compare-bench/blob/06ef6ef19272f398466278500d30a8eb8d5fae11/4-%E6%89%93%E5%88%86%E7%BB%86%E5%88%99/%E8%AF%BB%E5%8F%96%E8%A7%82%E6%B5%8B%E8%A3%81%E5%AE%9A-2026-11-12/README.md>) · [C重算](<https://github.com/B612-LP/harness-compare-bench/blob/06ef6ef19272f398466278500d30a8eb8d5fae11/4-%E6%89%93%E5%88%86%E7%BB%86%E5%88%99/%E8%AF%BB%E5%8F%96%E8%A7%82%E6%B5%8B%E8%A3%81%E5%AE%9A-2026-11-12/verify.py>) · [结果](<https://github.com/B612-LP/harness-compare-bench/blob/06ef6ef19272f398466278500d30a8eb8d5fae11/4-%E6%89%93%E5%88%86%E7%BB%86%E5%88%99/%E8%AF%BB%E5%8F%96%E8%A7%82%E6%B5%8B%E8%A3%81%E5%AE%9A-2026-11-12/result.json>) | 合成28试次不能给产品召回率；两个世界兼容同一日志，真实读取分母/FN/非平凡风险上界未知，不证明隔离。 |
| 判分链能否支撑归因 | q2697在216语义组合下不可复现原gold；判卷对象、gold、参考解和自测先于未来能力归因。 | [38b2e13](<https://github.com/B612-LP/harness-compare-bench/commit/38b2e13f63c5aeacb58094d2e977980ab12e8041>) | [金标复算](<https://github.com/B612-LP/harness-compare-bench/blob/38b2e13f63c5aeacb58094d2e977980ab12e8041/5-%E8%AF%84%E6%B5%8B%E6%8A%A5%E5%91%8A/%E6%B4%BE%E7%94%9F%E5%88%86%E6%9E%90-q2697gold%E5%A4%8D%E7%AE%97-20261111/README.md>) · [前置门](<https://github.com/B612-LP/harness-compare-bench/blob/38b2e13f63c5aeacb58094d2e977980ab12e8041/4-%E6%89%93%E5%88%86%E7%BB%86%E5%88%99/%E5%88%A4%E5%88%86%E9%93%BE%E5%89%8D%E7%BD%AE%E9%AA%8C%E8%AF%81%E8%A7%84%E8%8C%83-2026-11-11/README.md>) | 兼容历史分保留；不因不复现而猜新gold、回判正式行，交付终点失败不自动等于算法能力失败。 |
| 台账能否全量认证 | 只能按对应generation.head和同一sidecar复算，不能说任意最新HEAD全可核。 | [38b2e13](<https://github.com/B612-LP/harness-compare-bench/commit/38b2e13f63c5aeacb58094d2e977980ab12e8041>)；generation=[66e98ea](<https://github.com/B612-LP/harness-compare-bench/commit/66e98ea25caaeec041a794f8efa3d926f4213a82>) | [复算合同](<https://github.com/B612-LP/harness-compare-bench/blob/38b2e13f63c5aeacb58094d2e977980ab12e8041/4-%E6%89%93%E5%88%86%E7%BB%86%E5%88%99/%E6%A0%B8%E9%AA%8C%E5%8F%B0%E8%B4%A6-2026-11-07/README.md>) · [绑定清单](<https://github.com/B612-LP/harness-compare-bench/blob/38b2e13f63c5aeacb58094d2e977980ab12e8041/4-%E6%89%93%E5%88%86%E7%BB%86%E5%88%99/%E6%A0%B8%E9%AA%8C%E5%8F%B0%E8%B4%A6-2026-11-07/ledger.json>) | 5类公开不可复核缺口与14件私档sidecar分列；机器见证非真人签名或原件真实性认证。 |
| complete与反馈闭环 | grader字段不等于Agent声明；旧F5引用链支持不足。两案可见修补，只有所选r1导出有后续复验/全局终答；不改原标签或分数。 | [f4fb597](<https://github.com/B612-LP/harness-compare-bench/commit/f4fb59799cb83dd6b7d386495b45da1e63b787c9>) | [定义](<https://github.com/B612-LP/harness-compare-bench/blob/f4fb59799cb83dd6b7d386495b45da1e63b787c9/5-%E8%AF%84%E6%B5%8B%E6%8A%A5%E5%91%8A/%E5%8F%8D%E9%A6%88%E9%97%AD%E7%8E%AF%E5%86%8D%E5%88%86%E6%9E%90-2026-11-12/README.md>) · [原语](<https://github.com/B612-LP/harness-compare-bench/blob/f4fb59799cb83dd6b7d386495b45da1e63b787c9/5-%E8%AF%84%E6%B5%8B%E6%8A%A5%E5%91%8A/%E5%8F%8D%E9%A6%88%E9%97%AD%E7%8E%AF%E5%86%8D%E5%88%86%E6%9E%90-2026-11-12/core.py>) · [测试](<https://github.com/B612-LP/harness-compare-bench/blob/f4fb59799cb83dd6b7d386495b45da1e63b787c9/5-%E8%AF%84%E6%B5%8B%E6%8A%A5%E5%91%8A/%E5%8F%8D%E9%A6%88%E9%97%AD%E7%8E%AF%E5%86%8D%E5%88%86%E6%9E%90-2026-11-12/test_core.py>) · [数据](<https://github.com/B612-LP/harness-compare-bench/blob/f4fb59799cb83dd6b7d386495b45da1e63b787c9/5-%E8%AF%84%E6%B5%8B%E6%8A%A5%E5%91%8A/%E5%8F%8D%E9%A6%88%E9%97%AD%E7%8E%AF%E5%86%8D%E5%88%86%E6%9E%90-2026-11-12/events.json>) · [复算](<https://github.com/B612-LP/harness-compare-bench/blob/f4fb59799cb83dd6b7d386495b45da1e63b787c9/5-%E8%AF%84%E6%B5%8B%E6%8A%A5%E5%91%8A/%E5%8F%8D%E9%A6%88%E9%97%AD%E7%8E%AF%E5%86%8D%E5%88%86%E6%9E%90-2026-11-12/verify.py>) | 两历史评分目标身份unknown；两例目的性选择非新n。目标写串行已核；并行同路径提交顺序不在原语认证范围。私原不公开，37检查只核派生自洽。 |
| Cargo三红与政策 | 在本次固定的两条政策中，只有参考式政策命中三项点值；点门全绿不等于完整五段可行，也不识别所有可能政策中的唯一答案。最终返回储备及简化模型下两者可核，完整合同、物理法规和原评分文件身份仍unknown，原分不变。 | [7f1324e](<https://github.com/B612-LP/harness-compare-bench/commit/7f1324ec5b507e35b1dbad9b9295170b82b24497>) | [定义](<https://github.com/B612-LP/harness-compare-bench/blob/7f1324ec5b507e35b1dbad9b9295170b82b24497/5-%E8%AF%84%E6%B5%8B%E6%8A%A5%E5%91%8A/%E7%87%83%E6%B2%B9%E6%94%BF%E7%AD%96%E4%B8%8E%E5%88%A4%E6%8D%AE%E8%BE%A8%E5%88%AB-2026-11-12/README.md>) · [新数学](<https://github.com/B612-LP/harness-compare-bench/blob/7f1324ec5b507e35b1dbad9b9295170b82b24497/5-%E8%AF%84%E6%B5%8B%E6%8A%A5%E5%91%8A/%E7%87%83%E6%B2%B9%E6%94%BF%E7%AD%96%E4%B8%8E%E5%88%A4%E6%8D%AE%E8%BE%A8%E5%88%AB-2026-11-12/core.py>) · [测试](<https://github.com/B612-LP/harness-compare-bench/blob/7f1324ec5b507e35b1dbad9b9295170b82b24497/5-%E8%AF%84%E6%B5%8B%E6%8A%A5%E5%91%8A/%E7%87%83%E6%B2%B9%E6%94%BF%E7%AD%96%E4%B8%8E%E5%88%A4%E6%8D%AE%E8%BE%A8%E5%88%AB-2026-11-12/test_core.py>) · [数据](<https://github.com/B612-LP/harness-compare-bench/blob/7f1324ec5b507e35b1dbad9b9295170b82b24497/5-%E8%AF%84%E6%B5%8B%E6%8A%A5%E5%91%8A/%E7%87%83%E6%B2%B9%E6%94%BF%E7%AD%96%E4%B8%8E%E5%88%A4%E6%8D%AE%E8%BE%A8%E5%88%AB-2026-11-12/result.json>) · [复算](<https://github.com/B612-LP/harness-compare-bench/blob/7f1324ec5b507e35b1dbad9b9295170b82b24497/5-%E8%AF%84%E6%B5%8B%E6%8A%A5%E5%91%8A/%E7%87%83%E6%B2%B9%E6%94%BF%E7%AD%96%E4%B8%8E%E5%88%A4%E6%8D%AE%E8%BE%A8%E5%88%AB-2026-11-12/verify.py>) | 目的性旧单例非新n；原评分文件SHA、完整程序/行为及唯一储备范围未知；不翻组Y，29检查只核派生自洽。 |

## 最小复算（在独立克隆/工作树中）

先取下列确切研究提交，不在有未提交改动的工作目录直接切换：

```sh
git checkout --detach 06ef6ef19272f398466278500d30a8eb8d5fae11
python3 -I -S -B '5-评测报告/输入源覆盖与机制区分-2026-11-12/verify.py' --root .
python3 -I -S -B '4-打分细则/机制重复口径澄清-2026-11-12/verify.py' --root .
python3 -I -S -B '4-打分细则/读取观测裁定-2026-11-12/verify.py' --root .

git checkout --detach 0793d6084d632b8f5589b25b05f970a0654a6192
python3 -I -S -B '5-评测报告/引用回读与已知读取正控-2026-11-13/verify.py'
```

前四命令默认只读并输出JSON；末一命令为 2026-11-13 新增行（只读 result.json 重算统计与常量，无 --root 参数），同目录 `test_verify.py` 可另在普通/`-O`模式运行。成功只说明各自固定公开字节与声明范围相符，不恢复私档原文、不证明产品效果或历史全部封印通过。各原始usage保持逐场辅助记录，bytes不当token/费用。

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
