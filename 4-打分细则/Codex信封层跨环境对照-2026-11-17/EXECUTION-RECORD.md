# 执行记录：Codex 信封层跨环境对照（含 DSH 跨会话控制）— 2026-11-17 环20

## 问题与方法
见冻结页 README.md（SHA fa86b7e8…，birth/mtime 09:03:09，先于全部数据读取）。对 7 个既有捕获 run 的 req1 做层内 (role,kind,bytes,sha256) 清单与跨环境/跨会话/跨 run 分类；0 新运行；公开档不含正文、路径值或 id。

## 实际结果
- verdict：`codex_inputenv_mixed_tools_stable__dsh_sys_stable_tools_stable`。
- Codex（4 run，同一声明 CODEX_HOME、不同 workspace；原稿误写两套 CODEX_HOME，见文末订正披露）：input 布局恒为 [developer 17374B, developer 398B, user 453B, user=任务]；顶层 `instructions` 字段在全部 4 体中缺失（frozen L-INS=absent，一致）；跨环境 E2：item0/item1（developer 层）逐字节 identical，item2（user 453B）同字节数但内容 differs（环境生成层），item3 任务 differs（247 vs 93B，任务不同所致，结构性排除）；tools 8 digest identical（e327d59a…）。同环境跨 run E3 两对：全部 identical。
- DSH（3 会话：loop1-capture/loop7-t2/loop8-t3）：system 2593B 全对 identical；tools 22 digest 全对 identical（fa446b06…）；任务 messages[1] 字节数 214/113/60 随任务变化（只登记）。
- 解释（有界）：Codex 二进制层提示（17.4KB developer）与工具集在全部已捕获 run（声明同一 CODEX_HOME、不同 workspace）逐字节稳定（指向随二进制分发而非随 HOME 生成）；453B user 环境消息为同长不同内容→运行时生成的环境层被字节级定位（〔发布后订正〕环21 行级复核证实其差异仅为 cwd/workspace_roots 中的 workspace 路径值：同一模板只差路径值，归一后 11/11 请求同串 SHA 5a3ef8b4efb5504a33c86d7bac1877d06275ff0bf645e5f65a10f09614e6998e；HOME 因果不作主张）；DSH 同 build 系统提示跨任务会话字节稳定，与跨 build +323B 演进（§4.60）互补。均不认证模型/provider/HTTP 或二进制身份。

## 验证器与套件
- verify.py：stdlib；双模式 fail-closed；FROZEN_ROWS 固定 7 行 items/tools/req1_sha/requests_in_run（公开重放强制全行 pin）；parse_float/parse_constant 拒非有限；role/kind 白名单；codex instructions_field_present 必为 False；`--output` 必须新文件。
- 实测四路：build 普通/-O 与公开 evidence/result 逐字节一致；公开重放普通/-O result 逐字节一致。
- test_verify.py：14 用例（合成档 build+端点断言+合成档公开重放被冻结 pin 拒绝；形状错置/重复键/非有限/缺任务项/system 非首位/模式旗标/输出已存在/公开 role、sha、baseline 篡改拒绝；env 门控真档 build+重放字节等+真档篡改拒绝）。带 ENVELOPE_TEST_ROOT=until14-20261117 根时 14/14 OK（普通/-O）；无根时 skipped=2（12 项合成仍绿）。

## 时间线（FS stat；birth=mtime 除注明外）
- README 09:03:09 → FREEZE.json 09:03:19 → 结构探查 09:04–09:06（无顶层 instructions 事实确认，frozen 规则按 absent 执行未改）→ verify.py 09:07:12 起、mtime 09:11:20（三次修正见下）→ 首建 evidence/result 09:10:08（与终版 verify 重建逐字节一致；中间件 evidence-first/result-first 已删除，等同性在会话收据登记）→ test_verify.py 09:08:11 起、mtime 09:10:00 → loop20 四路+套件 09:10–09:12。
- verify.py 修正三次（前两处不影响已建 evidence/result 的值，经终版重建复核逐字节一致）：① no_duplicate_pairs 迭代整对致 unhashable → 改键列表判定；② loads 增加 parse_float 拒绝（1e999 经 parse_float 而非 parse_constant）；③ FROZEN_ROWS JSON 往返为 list → 定义处 tuple 规范化（公开重放此前必拒）。
- test_verify.py 修正两次：① write_run 需 makedirs exist_ok + 每合成 run 补 002 请求文件以满足 requests_in_run 冻结集；② 合成档公开重放从期望成功改为期望拒绝（冻结 pin 生效），新增 env 门控真档 build/重放/篡改用例；env_b 默认改 ENV-X 使 E2 mixed 分支被实际覆盖。

## 发布前订正披露（独审 L1，2026-11-17 独审后）
- README「主 verdict」模板首版含 ins 段且示例串漂移；独审指出后按实际实现订正（absent 层不入 verdict 段），原字节先归档私档 loop20/pre-delta/README.md（fa86b7e8…）；verify.py 无需改（README_SHA 动态计算）；evidence 仅 readme_sha256 字段随 README 更新，全部科学行与 verdict 不变；四路复验 IDENTICAL、14×4 套件绿。L2（output_path 死代码）/L3（测试空行）维持登记不改。

## 已知限制
- 全部为 product-archived wire bytes 的描述性分类；stable=字节恒等不证语义；varying 不定位变化字段；任务消息按结构性规则排除，布局不符会以分类失败暴露（本次未发生）。
- 单 codex 0.163.0、单 DSH build、单模型通道、每层单任务面（t2/t3/capture）；不外推其他版本/任务/产品。
- item2 453B 同长异内容仅字节级定位为环境生成层，未拆分内部字段（如 HOME 路径/会话 id）——公开档不携带内容，如需字段级归因须新预注册。
- 公开 evidence 含 req1_sha256 与逐 item sha——哈希表本身可被整体替换伪造（frozen pin 使公开重放拒收与 pin 不符的档，但不认证私档原始性；纵深防御=SELF-ACCEPT 封印 + 独审）。

## 发布后订正披露（2026-11-17，环21行级复核触发）
- 初稿与 README 均把本对照称为「跨两套（独立）CODEX_HOME」；环14/环15 EXECUTION-RECORD 实均声明同一 CODEX_HOME=~/.codex-capture-loop14，运行时 HOME 身份无进程收据。订正为「同一声明 HOME、不同 workspace（capture-r1/capture-t3）的两 run 对照」，因果措辞不升级。原字节先归档 loop20/pre-delta2/（MANIFEST.sha256）。
- 科学行（7×4 item 表、tools digest、REQ1 pin）与 verdict 不变；evidence 仅 readme_sha256 随 README 订正更新，result 仅哈希绑定字段更新。非作者delta复核由 envelope-auditor 承担（SEAL-V2 基础上追加）。
