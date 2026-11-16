# 请求侧跨模型捕获：执行记录（R-A6）

窗口：until14-20261117（用户授权「随便测试，继续推进到明天12点」，2026-11-16T22:24+08）。预算：本环≤4次真实（2计划+2重试），实际2次真实+1次mock干跑（0真实调用）。

## 时间线（2026-11-17，Asia/Shanghai）

- 01:14 loop10/DIRECTION.md 私立题（终点P1–P4、预算、先干跑后真实）。
- 01:15:01 公开README冻结（SHA 3de9ded761959a7c43821b62c2438c3de0ac8dc9469fbba1c7b4a77484a0ec16）——先于任何DS真实运行。
- 01:15 profile capture-ds1 = capture-dry克隆，patch加ds-capture provider（baseURL http://127.0.0.1:8798、apiKeyEnv DEEPSEEK_API_KEY、api openai-completions、models=[deepseek-chat]）+agent-default-model=ds-capture/deepseek-chat；yaml.safe_load与--dump-config核过。首插错位（zai重复models键，YAMLException duplicated mapping key (32:9)）已修复并留档教训。
- 01:16 mock干跑：proxy 8798→http://127.0.0.1:8799，exit0、2请求、0真实调用（dry-ds1）。旧mock进程占8799曾致绑定失败，kill后重起。
- 01:16:45–50 真实r1：proxy 8798→https://api.deepseek.com，capture-ds-r1，exit0，3/3上游200，session-bfdb0fe9…，final "# Capture task r1 — can_chain"。
- 01:17:02–06 真实r2：capture-ds-r2，exit0，3/3上游200，session-53a4571c…，final "Capture task r1 — can_chain"（无#，响应侧差异，不入终点）。
- workspace前后核对一致：TASK.md 68599aec…、dominoes.py 89f1fede…（rebuild no-op）。事件层副本 loop10/event-layer-ds-bfdb0fe9/（SHA 064b60f8…）与 event-layer-ds-53a4571c/（SHA 72d7bb36…）。

## 主要终点（P1）

| 请求 | ds_r1 | ds_r2 | 结论 |
|---|---|---|---|
| req1 | 0372557d46f071948f5f32e59466da624fc3748c56dc8b0f7fbcc9d036874ed3 | 同左 | 跨run逐字节恒等 |
| req2（标题请求） | 05183eb7906bdc6612c93581e2ec66fc88f6ccaf2474c35314a41f60d0b6f7aa | 同左 | 逐字节恒等 |
| req3 | c1d78d83dd85b4947ae17e0511d35974fb446c7f8cfc7252db4cc8371bfb0787 | 9c60dec286a8fd1dd59dfe7a2bb1ecd282a529ea2a34166d5a7ba35338397aef | 恰4差异叶、全部provider id；id归一后canonical恒等 |

**结局：ds_assembly_stable**（req1字节级 + req3归一级）。DS的provider id格式为 `call_NN_<base62>`（与GLM `call_<24hex>` 不同形状），归一正则按形状族覆盖两格式。

## 运行内前缀（P2）

两run均为：req1是req3内容级严格前缀；追加恰 `[assistant,none,0] + [tool,str,227] + [tool,str,203]`（与GLM六run同形状）；delta=1028字节（GLM为1016；+12来自DS id更长，appended JSON 1057 vs 1045字节）。

## 跨provider描述对照（P3；非因果、非评分）

- 任务载荷Harness稳定：user消息1–4内容跨provider逐字节相等；roles同为[system,user,user,user,user]；n_messages同5。
- system不等：GLM 2593B vs DS 2962B（模板同、模型名插槽不同、DS侧多2工具的指引）。
- 工具面：GLM 22 vs DS 24；DS-only=web_fetch、web_search（其余同序同内容）。同一profile克隆，工具面差异来自Harness按provider/model的适配，不是workspace差异。
- 请求方言：GLM用max_tokens=128000+thinking{disabled}+tool_stream；DS用max_completion_tokens=8192+store:false、无thinking/tool_stream字段——序列化按provider API方言由Harness适配。
- GLM req1 SHA 92220699…120ac10（§4.50已发布pin）。

## 标题请求与回流（P4）

标题请求同provider同模型（deepseek-chat、max_completion_tokens 4096、2消息、0工具、TITLE_PREFIX前缀成立）。标题输出字符串（Capture task r1/can_chain）也出现在req3，但可完全由TASK.md H1文件内容解释（reflow probe explained_by_task_file_content_only=True），不能当作标题回流证据。

## 验证器与套件

- verify.py：六件封包前在真实私档上构建（evidence SHA 5b0d0b…见SELF-ACCEPT）、公档重放normal/-O与result逐字节同；evidence只含SHA/字节计数/形状元组/布尔，无请求体、无完整id、无凭据、无绝对路径。
- test_verify.py 19用例×2（normal/-O）全OK（1 skip=未设XM_ARCHIVE_BASE时跳过真档重放）；设XM_ARCHIVE_BASE后19×2含真档分支全OK。
- 诚实披露：测试修就史——no_duplicate_pairs首版漏return dict、fixture三处JSON序列化截断、refresh常量顺序、delta/P3常量fixture化、GLM fixture模型名区分；全部发生在真档证据构建前后均可由SELF-ACCEPT的SHA链复核。

## 已知限制与边界

- deepseek-chat经官方api.deepseek.com（apiKeyEnv）与桌面账号路由（deepseek-flash）非同一路由；跨provider对照为family-level描述。
- 单任务、单DSH构建、每provider n=2；bytes非token；响应体（模型输出）不在终点；product-reported counters不认证backend行为；私档真实性不能由公档认证。
- 本次执行属于用户2026-11-16T22:24「随便测试」预算内的请求侧离线捕获，不新增评测批次、不改旧门旧分。
