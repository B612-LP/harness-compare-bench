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
- 产物 SHA-256：abc387_f `f03cfec6…f6386c6a08`、abc388_f `7297268a…945b6c9e`、abc388_g `9c57caff…3cc71d77`、abc389_g `e6ac90a8…872ee0615`（[`solutions/`](dsh/solutions/)）。

## WorkBuddy 桌面（5.11.3）

- 未发射：自升级后启动即无窗口、无调试通道；经用户授权的正常退出+带调试参数重启两次均 ≤300ms 无痕瞬退（版本内 CDP 入口仅环境变量通道，CLI 参数无效）。用户决定本窗搁置，恢复方式待定；无任务、无产物，不计失败分。

## 豆包工作桌面（2.37.15，B 轨默认 DeepSeek V4.1 Flash·低·本地电脑）

- 17:28 附件上传点击 outcome=unknown（不重试）；按用户指示改**本地工作区**路线并发前登记偏离（原题面原文+一行读取指令）。18:13:21 单次发送，18:25:02 终态 `completed_local`（trace 终态+渲染回复+regenerate 三重证据）。原生 CID `38455827958268674`，轨迹 73 条。
- 证据：[`prompt-20261125.txt`](doubao/prompt-20261125.txt)（SHA-256 `910c95687c0bc9c1…c73db2`，发送前登记）、[`trajectory-38455827958268674-copy.jsonl`](doubao/trajectory-38455827958268674-copy.jsonl)（整文件 SHA-256 `8fc1d0e0…44d8d5a7`，与导出 turn.sha256 一致）、[`intent.json`](doubao/intent.json)、[`click.json`](doubao/click.json)、[`release.json`](doubao/release.json)。
- 产物 SHA-256：abc387_f `6acce673…206503ee2`、abc388_f `67551b01…6b35ebf14`、abc388_g `c06fab5d…1fc6f`、abc389_g `21ab7362…84c5a6959`（[`solutions/`](doubao/solutions/)）。

## 元宝专家模式（网页，B 轨开箱默认）

- 17:36:40 单次提交；发前偏离：附件控件无效，改为正文携带题面（从页面 DOM 重建的 JSON 投影与源输入同哈希）。页面「正在思考」贯穿 3000 秒观察窗（18:02–18:19 思维链冻结 ≥16 分钟后恢复推进，非死链）。
- 18:29–18:36 原浏览器页面随客户端会话消亡（非代理操作）；经产品「最近会话」列表**只读**恢复原会话（标题「AtCoder近期竞赛难题解析」），确认回答完成于 (18:29:20, 18:48:38]，总时长约 ≤72 分钟——超出 3000 秒任务窗后仍在生成直至完成。页面无 token/usage 显示；回答 prose（约 17.5K 字符）未能持久化为已登记缺口，四题代码块完整。
- 证据与产物（SHA-256）：abc387_f `c8e1ff0a…27cb897`、abc388_f `6da7914e…3888fce`、abc388_g `b65eee96…b56d86`、abc389_g `10dba9eb…90a384`（[`yuanbao/`](yuanbao/)，含代码块捕获 [`codes-evaluate-capture-1852.json`](yuanbao/codes-evaluate-capture-1852.json) 与溯源清单 [`MANIFEST.json`](yuanbao/MANIFEST.json)）。

## 限制声明

- 全部终态为客户端/本地层证据，不证明服务端摄入、后端身份或上游路由；usage 为产品自报层。
- 判卷隔离不达标故无分数；四产品 12 份产物仅经语法层核验（ast.parse 12/12，未执行）。
- 独立复核为项目内非作者静态独审（登记覆盖、回执链、隔离快照、SHA 重算、泄漏扫描），不是老师要求的外部受控第三方核验；元宝恢复路径的动态过程仅有观察者时间戳记录。
- WorkBuddy 未运行，不计 0 分；本轮不回填正式 25 格与历史成绩。
