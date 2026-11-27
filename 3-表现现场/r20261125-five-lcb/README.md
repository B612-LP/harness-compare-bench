# r20261125 — 五产品同题实跑记录（LCB 近期 hard 四题，2026-11-25）

用户于当日授权真实运行五款评测对象并取回可获得的全部数据。共同题目为 [`2-用例/lcb-recent-hard-4`](../../2-用例/lcb-recent-hard-4/instruction.md)（四个独立 Python 源文件、公开样例+隐藏测试 checker 判分）。本页是表现现场：原始回执、提示词与产物逐字公开；全部运行各一次首发，失败后按预注册登记偏离重发一次；**判卷沙箱隔离经项目内独审不达标（NO-GO），本轮未运行 checker、无 reward 分数**，各产品「完成」均为主报。

## 共同输入与口径

| 项 | SHA-256 |
|---|---|
| 题面 instruction.md（2292B） | `1c39b2fa66982a7d54851e20822cb4064d8254122f2b047634b64fecdbd6045c` |
| inputs/problems.json（7884B） | `0ce2f9c1eee0039fa9cfc7cd9969d99118d3fba4ac41571c49d9f5289592a673` |

- 各产品工作区在仓库外独立目录，仅含题面与输入；checker/truth 不入工作区（发射前后哈希一致，独立抽查 5/5）。
- A 轨目标配置：DeepSeek 官方 `deepseek-flash`、reasoning `low`（Codex/DSH/WorkBuddy）；B 轨为产品开箱默认（豆包/元宝）。配置名与界面读数不等同上游路由，本轮不声称同条件等控，不做跨产品归因。
- 发射前偏离均预登记：CLI 首发失败（明确错误终态，非 unknown）后经隔离 HOME 重发一次；豆包不上传附件改本地工作区读取；元宝以正文投影代附件上传。

## Codex CLI（codex-cli 0.163.0）

- 首发 17:22 终态失败（账号用量限制）；r2 于 18:18 经专用 `CODEX_HOME`（隔离 skills/instructions/联网搜索）重发，`turn.completed`、exit 0（thread `01a21236-bb02-7c41-ac77-6b60fd469e11`）。真实 `~/.codex` 前后快照零差异。
- 配置 [`codex-config-r2.toml`](codex/codex-config-r2.toml)：`model_provider="deepseek"`、`model="deepseek-flash"`、effort low、workspace-write（无网络）。自报 usage：input 2,017,204（cached 1,992,960）/ output 60,749（reasoning 43,704）。
- 证据：[`stdout-r2.jsonl`](codex/stdout-r2.jsonl)（84 事件）、[`stderr-r2.txt`](codex/stderr-r2.txt)、[`launch-r2.json`](codex/launch-r2.json)、[`postflight-r2.json`](codex/postflight-r2.json)、[`isolation-r2.json`](codex/isolation-r2.json)。
- 产物 SHA-256：abc387_f `4ff13ed6…15942bc37`、abc388_f `d1702fae…2074ee8702`、abc388_g `95913887…2d7965b16`、abc389_g `6abcbda9…4d13cf17fc`（[`solutions/`](codex/solutions/)）。

## DSH CLI（dsh 0.2.2-rc.3）

- 首发 17:22 终态失败（MISSING_CREDENTIAL）；r2 于 18:18 经临时 `DSH_HOME`（无用户 skills/memory/插件）重发，`reason=completed`、exit 0（session `279e1d9f-2371-4f93-96de-e42d65f38199`，78 事件/1 turn/15 steps）。stderr 见官方端点模型列表加载成功（凭据被接受，不含值）。
- 回读确证 provider `deepseek-official`、model `deepseek-flash`、reasoningEffort low、approval never（[`dump-config-r2.txt`](dsh/dump-config-r2.txt)）。末步自报 cacheRead 51,584。
- 证据：[`stdout-r2.jsonl`](dsh/stdout-r2.jsonl)、[`stderr-r2.txt`](dsh/stderr-r2.txt)、[`launch-r2.json`](dsh/launch-r2.json)、[`postflight-r2.json`](dsh/postflight-r2.json)、[`isolation-r2.json`](dsh/isolation-r2.json)。
- 产物 SHA-256：abc387_f `f03cfec6…f6386c6a08`、abc388_f `7297268a…945b6c9e`、abc388_g `9c57caff…3c7cc71d77`、abc389_g `e6ac90a8…872ee0615`（[`solutions/`](dsh/solutions/)）。

## WorkBuddy 桌面（5.11.3）

- 未发射：自升级后启动即无窗口、无调试通道；经用户授权的正常退出+带调试参数重启两次均 ≤300ms 无痕瞬退（版本内 CDP 入口仅环境变量通道，CLI 参数无效）。用户决定本窗搁置，恢复方式待定；无任务、无产物，不计失败分。

## 豆包工作桌面（2.37.15，B 轨默认 DeepSeek V4.1 Flash·低·本地电脑）

- 17:28 附件上传点击 outcome=unknown（不重试）；按用户指示改**本地工作区**路线并发前登记偏离（原题面原文+一行读取指令）。18:13:21 单次发送，18:25:02 终态 `completed_local`（trace 终态+渲染回复+regenerate 三重证据）。原生 CID `38455827958268674`，轨迹 73 条。
- 证据：[`prompt-20261125.txt`](doubao/prompt-20261125.txt)（SHA-256 `910c95687c0bc9c1…c73db2`，发送前登记）、[`trajectory-38455827958268674-copy.jsonl`](doubao/trajectory-38455827958268674-copy.jsonl)（整文件 SHA-256 `8fc1d0e0…44d8d5a7`，与导出 turn.sha256 一致）、[`intent.json`](doubao/intent.json)、[`click.json`](doubao/click.json)、[`release.json`](doubao/release.json)。
- 产物 SHA-256：abc387_f `6acce673…206503ee2`、abc388_f `67551b01…6b35ebf14`、abc388_g `c06fab5d…1fc6f`、abc389_g `21ab7362…84c5a6959`（[`solutions/`](doubao/solutions/)）。

## 元宝专家模式（网页，B 轨开箱默认）

- 17:36:40 单次提交；发前偏离：附件控件无效，改为正文携带题面（从页面 DOM 重建的 JSON 投影与源输入同哈希）。页面「正在思考」贯穿 3000 秒观察窗（18:02–18:19 思维链冻结 ≥16 分钟后恢复推进，非死链）。
- 18:29–18:36 原浏览器页面随客户端会话消亡（非代理操作）；经产品「最近会话」列表**只读**恢复原会话（标题「AtCoder近期竞赛难题解析」），确认回答完成于 (18:29:20, 18:48:38]，总时长约 ≤72 分钟——超出 3000 秒任务窗后仍在生成直至完成。页面无 token/usage 显示。回答为纯代码交付：四个带文件名标识的代码块、无解释性正文（与题面「不需要写解释文档」一致）；窗口关闭后经只读恢复复核，四代码块与下述已发布产物逐字节一致（SHA-256 重算相同），回答已完整持久化，无遗失内容。
- 证据与产物（SHA-256）：abc387_f `c8e1ff0a…27cb897`、abc388_f `6da7914e…46b0388fce`、abc388_g `b65eee96…b56d86`、abc389_g `10dba9eb…90a384`（[`yuanbao/`](yuanbao/)，含代码块捕获 [`codes-evaluate-capture-1852.json`](yuanbao/codes-evaluate-capture-1852.json) 与溯源清单 [`MANIFEST.json`](yuanbao/MANIFEST.json)）。

## 自述与产物对照（2026-11-25 补记）

对四个完成运行的产品做了一轮只读「自述分账」：从公开回执中提取每家最后一条 assistant 主张文本，与其 `solutions/` 产物文件名集合做机械对照（只对文件名，不读内容、不执行、不判正确性）。

| 产品 | 最终主张是否持久化 | 主张提及四题文件 | 产物 4/4 存在 | 集合 diff | 分类 |
|---|---|---|---|---|---|
| Codex | 是（10 条进展主张 + 最终主张） | 是 | 是 | 空 | 4/4 对 claimed_and_present |
| DSH | 是（15 步 thinking，1 条可见文本=final） | 是 | 是 | 空 | 4/4 对 claimed_and_present |
| 豆包工作 | 是（仅 2 条 assistant 文本） | 是 | 是 | 空 | 4/4 对 claimed_and_present |
| 元宝 | 否（会话正文未持久化，代码块已持久化） | — | 是 | — | 4/4 对 no_claim_evidence（证据局限） |

三家有主张产品合计 12/12 对 `claimed_and_present`；元宝 4/4 对主张缺失。

要点与边界：

1. 三家 CLI/桌面的最终主张均为「四题完成 + 样例/暴力对拍通过 + 自报耗时」句式，且提到的文件名与磁盘产物集合完全一致（无多余、无缺失文件）。**这些「通过/耗时」是被试自述**：本轮判卷隔离不达标、未执行任何候选，主张中的运行结果与耗时数字不可独立复核，不得引用为实测。
2. 元宝「主张缺失」是证据层缺口（正文未持久化），不据此推断其未作主张或行为差异；其交付与题面「不需解释文档」一致，为纯代码。
3. 提取与对照方法固定于当日私有预注册（方法先于数据、脚本可确定性重跑），经项目内非作者独审后发布；本节不构成正确性结论，不改判卷 NO-GO，不回填 25 格。

## 限制声明

- 全部终态为客户端/本地层证据，不证明服务端摄入、后端身份或上游路由；usage 为产品自报层。
- 判卷隔离不达标故无分数；四产品 12 份产物仅经语法层核验（ast.parse 12/12，未执行）。
- 独立复核为项目内非作者静态独审（登记覆盖、回执链、隔离快照、SHA 重算、泄漏扫描），不是老师要求的外部受控第三方核验；元宝恢复路径的动态过程仅有观察者时间戳记录。
- WorkBuddy 未运行，不计 0 分；本轮不回填正式 25 格与历史成绩。

## 勘误记录（2026-11-28）

本页两处截断 SHA 展示尾段笔误，经 2026-11-28 三题小实例复算页的内部非作者独审发现（MF-4）并更正：DSH abc388_g 展示尾段 `…3cc71d77` → `…3c7cc71d77`；元宝 abc388_f `…3888fce` → `…46b0388fce`。仅展示截断笔误，各文件完整 SHA-256 与磁盘归档一贯一致（本页其余截断尾段经逐一子串核验无误；钉定以完整 64 位哈希为准）。
