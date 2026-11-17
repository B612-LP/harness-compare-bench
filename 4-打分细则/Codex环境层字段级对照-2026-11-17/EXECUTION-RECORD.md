# 执行记录：Codex 环境生成层（input[2]）行级对照 — 2026-11-17 环21

## 问题与方法
见冻结页 README.md（含修订一披露）。离线复用环14/环15 既有捕获档（0 新运行），拆分环20遗留的 453B 环境消息差异到行级；公开档只含行号/字节数/sha256/分类，无任何行值。

## 实际结果
- verdict：`env_line_5_2_1_7`（7 行两档等长；5 行 identical；2 行 differs；其中 1 行 root_path_like）。
- 两 req1 整体 SHA 复用环20 pin（loop14-r1 6a156cdb…、loop15-t3-r1 2cf01fa3…）。
- differs 行：line2（55B，非路径样式——某 HOME 生成值，公开档不携带内容不解释语义）与 line6（209B，含 `<workspace_roots><root>` 的文件系统/workspace 行，PATH_LIKE）。
- 解释（有界）：跨两套 CODEX_HOME 的环境层差异被定位到恰 2 行，其中 workspace 路径行被标签域标记证实；其余 5 行逐字节稳定。不认证环境变量语义、生成时机或 provider 行为；单任务面单版本。

## 验证器与套件
- verify.py：stdlib；双模式 fail-closed；REQ1_SHA 两 pin + FROZEN_LINES 全 14 行 (line,type,bytes,sha256,root_path_like,classification) 硬 pin；公开重放逐行强制；`--output` 必须新文件；行数不等/形状错/role 错/part 类型错即 exit 2。
- 四路：build 普通/-O 与公开 evidence/result 逐字节一致；公开重放普通/-O result 逐字节一致。
- test_verify.py：11 用例（合成档 build+终点断言 env_line_5_2_1_7+行数不等/role 错/part 类型错拒绝；模式旗标/输出冲突；公开 evidence 行 sha/baseline/README pin 篡改拒绝；env 门控真档 build+公开重放字节等+行篡改拒绝）。带 ENVLAYER_TEST_ROOT 时 11/11 OK（普通/-O，0 skip）；无根 11 OK skipped=1（普通/-O）。

## 时间线（FS stat 实测；birth=mtime 除注明外）
- README：初版冻结 09:14:39（先于内容首读，会话记录在案；该版本 birth 已被修订一重写覆盖），现版（含修订一）birth/mtime 09:15:36 → verify.py birth 09:16:16、mtime 09:17:13（REQ1_SHA 截断值与 FROZEN bool 两修在此窗口内，均先于首建成功）→ 首建 loop21/ev.json+r.json 09:17:13 → 公开重放 r2.json 09:17:22 → 安装公开 evidence/result 09:17:22 → test_verify.py birth 09:18:01、mtime 09:18:26（含跨测试泄漏修复）→ 四档套件绿+四路字节比对（re-* 产物 09:18:37）→ EXECUTION-RECORD 09:18:58 → SELF-ACCEPT 09:19:06（v2：本时间线订正后重封，v1 见私档 loop21/SELF-ACCEPT-v1.json）。
- 两次实现错误（均修复于首建成功前或未产生公开件）：REQ1_SHA 截断值（die 拒绝，改为环20 pin）；FROZEN_LINES JSON 布尔字面量进 Python 源（NameError）。

## 已知限制
- 行级粒度：line2 的 55B 差异只定位到"存在一行非路径样式差异"，未拆字段（公开档无内容，字段级拆分须新预注册）。
- root_path_like 是标签域标记（`<root>…</root>` 出现即标记），不是完整 XML 解析器。
- 单任务面（capture-r1 vs t3-r1 的环境层）、单 codex 版本；不外推。
- 公开 evidence 含逐行 sha——哈希表可整体伪造；公开重放拒收与 pin 不符档但不认证私档原始性；纵深防御=SELF-ACCEPT 封印+独审。

## 发布后订正披露（2026-11-17，修订二）
- 非作者只读复核（scout，私档 discovery-round9/：RESEARCH-FINDINGS.md 37b18b3c…、probe 98c65dcb…、environment-paths-result.json f2c071df…）实证 line2=XML `<cwd>` 路径行（两侧 55B 同长异值、值=42B 绝对 workspace 路径）；初版 ROOT_RE 仅匹配 `<root>` 致 line2 标非路径、verdict=env_line_5_2_1_7。Lead 独立抽取两档 410B 文本逐行核对确认。
- 订正：PATH_LIKE 规则扩展 `<cwd>`；FROZEN line2 flag→True；verdict→env_line_5_2_2_7；evidence/result 幂等重建（build→install→replay normal/-O cmp 同）；套件 fixture 同步改 cwd 行，11×3 档 OK（+env 普通/-O、无 env skip=1）。背景框架同步订正：两 run 为同一声明 CODEX_HOME（环14/15 EXEC 均写 ~/.codex-capture-loop14）不同 workspace，非两套 HOME；运行时 HOME 身份无收据。
- 归一化观察（私档）：4 run×11 请求 cwd+root 值归一后整段逐字节同（SHA 5a3ef8b4…）——环境层差异全部为 workspace 路径值。原字节归档 loop21/pre-delta2/。

### 修订二b（delta复核D1后终态订正，2026-11-17 10:06）
- delta独审发现D1：README 修订二落盘后 evidence/result 仍 pin 修订前 README（61d065c3…），公开重放入口 rc=2、真档套件 FAILED——终态声明与现状态矛盾（中间时序为真、终态未重建）。按审计路径以现 README（f722c778…）在位重新 build→install：evidence bd8cfd262d8dfda361b5c1e54efcaf950c46ba6c97d5853eca610e3f338f6631、result b0cae8867624551a177ef591fe93afc81038c2732e91280452a30e90624206e6；四路复验（build临时cmp/安装/replay normal/-O cmp）全过、套件三档 OK（env 普通/-O、无env skip=1）。上一节「四路全过/三档OK」句的首次执行早于 README 落盘，以本节为准。
- 次要补充（审计观察）：line2 55B = 2 缩进 + `<cwd>`(5) + 42B 路径值 + `</cwd>`(6)。
