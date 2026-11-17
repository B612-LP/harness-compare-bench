# 环21 冻结协议：Codex 环境生成层（input[2]）字段级对照（2026-11-17，探索性事后、先验已披露）

## 状态：已冻结，未读取目标载荷内容（本页先于内容读取落盘）

## 背景与缺口
环20（§4.68/Codex信封层跨环境对照）发现跨 run（同一声明 CODEX_HOME、不同 workspace；〔修订二订正：原稿误写「跨两套 CODEX_HOME」，与环14/15 执行记录冲突〕）的 user 环境消息（input[2]）同字节数（453B）而内容互异，但公开档仅含 (role,kind,bytes,sha256)，**字段级差异未拆分**——这是该包 EXECUTION-RECORD 已声明的限制。本协议离线复用既有捕获档拆分该层，0 新运行。

## 数据面（冻结锚）
- 环境A：`loop14/capture-codex-r1/requests/001.request.bin`
- 环境B：`loop15/codex-t3-r1/requests/001.request.bin`
- 两 req1 的整体 SHA256 已被环20 FROZEN_ROWS pin；本包直接复用该 pin（不另设），环境层 leaf 表为新的冻结对象。
- 先验披露：作者在环20已见 input[2] 的 role/bytes/sha；**内容与键名结构在本冻结前未读取**。

## 方法（冻结）
1. 提取各 req1 `input[2]`（role 必须 == "user"，kind == "str"，环20 布局 pin 复用），取其 content 文本字符串。
2. `json.loads`（严格：拒绝重复键、拒绝 NaN/Infinity/非有限浮点；UTF-8）。解析失败 ⇒ 终点 `UNPARSEABLE`，只登记不解释。
3. leaf 展开：递归到标量，路径以 `.` 连接键名、数组以 `[i]`；每 leaf 记录 (path, json类型, UTF-8字节数, sha256(canonical json of value))。容器节点（对象/数组）只入结构计数不作为 leaf。
4. 三分类（按 leaf path 对齐）：`identical`（类型+sha 全同）/ `differs` / `only_a` / `only_b`。值匹配 `^/` 前缀或含 8+ 连续路径段样式的字符串额外标记 `PATH_LIKE`（仍只发 sha，不发值）。
5. verdict = `env_field_<common>_<differs>_<onlyA>_<onlyB>_<pathlike>`；`common==0` 时 verdict 加后缀 `_no_shared_schema` 且不跨档比较语义。

## 终点（全部描述性）
- E1 两档 leaf 总数与共同 path 集；E2 共同 path 中 identical/differs 计数与 differs 的 path 名单（键名是结构性信息，可公开；值不可）；E3/E4 only 侧 path 名单与计数；E5 PATH_LIKE 计数。
- 不认证：环境变量语义、生成时机、provider 行为、HOME 差异因果；单任务面单版本，不外推。

## 公开与隐私
- 公开 evidence/result 只含：path 名单、类型、字节长度、sha256、分类、计数。**任何 leaf 值不公开**（可能含绝对路径/会话 id）；PATH_LIKE 只标记不展开。
- 公开重放：从两归档按本规则重建 leaf 表并逐项等于冻结表；FROZEN pin = 全部 leaf (path,type,bytes,sha) 有序表 + 两 req1 sha（引用环20常量值但不 import 其代码）。
- fail-closed：任何解析/形状/pin 失败 exit 2 零产物；`--output` 必须新文件。

## 验收
- 独立实现（非作者代码）重建 leaf 表与公开档逐字节等；公开重放普通/-O result 逐字节等；套件双档运行（合成 + env 门控真档）；对抗 ≥8 类（leaf 篡改/重复键/非有限/形状错置/输出冲突/README pin）全部 rc2；隐私扫描（公开件无正文/绝对路径值/id）。

## 修订一（冻结后首读披露，2026-11-17）
首读发现 `input[2].content` 是 **content-part 列表**（非字符串；恰 1 个 part，type=`input_text`，text 为 410 字符纯文本块），规则 1–2 的"content 字符串 + json.loads"不适用。按以下修正执行（不回改上文，差异如实披露）：
- 叶表 = **行级**：`line<k>`（k=1 起），每行 (type=str, UTF-8 字节数, sha256)；行数须两档相等否则分类失败。
- 补充提取：对含 `<workspace_roots>` 的行，抽取 `<root>…</root>` 内文本标记 PATH_LIKE（只发 sha 不发值）；同时按行级 sha 判 identical/differs。
- 〔修订二，发布后 2026-11-17〕PATH_LIKE 检测扩展至 `<cwd>…</cwd>` 行；line2（cwd）判 PATH_LIKE，verdict=`env_line_5_2_2_7`（2 行差异均为路径样式行）取代初版 `env_line_5_2_1_7`。两 run 的 410B 环境文本在把 cwd/workspace_roots 路径值归一后逐字节相同（4 run×11 请求 11/11 同串，私档 SHA 5a3ef8b4efb5504a33c86d7bac1877d06275ff0bf645e5f65a10f09614e6998e）。触发=非作者只读复核（私档 discovery-round9 收据），原字节先归档 loop21/pre-delta2/。运行时 HOME 身份无进程收据，不作主张。
- 解析仅用于确认 part 结构；文本不做 json 解析。
- 首读仅定位到行级结构，未展开任何行值到公开材料；上表方法中 json 相关步骤作废。
