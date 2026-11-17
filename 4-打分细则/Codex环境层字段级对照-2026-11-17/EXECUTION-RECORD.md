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
