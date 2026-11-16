# 执行记录：DSH 请求侧最小捕获（2026-11-16，唯一一次授权真实运行）

## 授权与边界

- 用户于本窗口明确选择「授权最小捕获 + 1 次有界真实运行」：本地观测层记录一次真实 DSH headless 任务的完整请求体；不改产品安装包/权限/模型上下文；单任务单 attempt；请求/响应原文只入私档，公开仅派生元数据。
- 冻结协议：同目录 [README.md](README.md)（先冻结后运行）。私档根：`until14-20261117/`（仓外私有）。
- 0 次其他产品/模型运行；正式 25 格、历史分数、冻结原件、旧报告版本未动。

## 运行时间线（Asia/Shanghai）

1. **基建 dry-run（mock 上游，0 次真实 API）**：capture-dry profile→127.0.0.1:8792→mock 8799；`text=OK`，代理捕获 2 请求（32906B 主 + 872B 副），响应 tee 逐字节一致（RESPONSE_TEE_IDENTICAL），Authorization 掩码生效。
2. **基建事故（如实披露，不消耗捕获额度）**：dry-run 前验证期 2 次计划外真实 DeepSeek 调用（`DEEPSEEK_API_KEY` 在 env 时默认 provider 直连 `api.deepseek.com` 绕过本地代理；各一句 OK 任务）。处置：捕获包装器不再导出该 key，显式 patch 默认模型到 `zai-coding-cn/glm-5.3-flash`；已写入公开协议「已知差异」。
3. **首次捕获发射失败**：capture-r1 初版未 patch 默认模型 → `MISSING_CREDENTIAL` exit 1；代理 0 请求，0 模型调用，不消耗额度。
4. **唯一一次授权真实运行（成功，18:33）**：exit 0；代理见 3 请求全部 HTTP 200（上游 `https://open.bigmodel.cn:443`）。session id 只入档 sha256；final 文本只入档 sha256，原文未出私档。

## 捕获事实（私有原文核对，公开只派生）

| seq | kind | request B | response B | 用时 ms | 结构摘要 |
|-----|------|-----------|------------|---------|----------|
| 1 | loop | 33091 | 13203 | 5862 | system 2593B + 4×user（214 任务 / 3111 / 679 / 5525 注入块）+ 22 工具；thinking disabled；max_tokens 128000 |
| 2 | auxiliary | 1042 | 1570 | 1161 | system 481B + user 302B；0 工具；thinking **enabled**；max_tokens 4096（形态推断为标题生成，非产品源码断言） |
| 3 | loop | 34107 | 1765 | 2241 | 前 5 消息与 req1 逐字节同（内容级比较）；追加 assistant(content=null,tool_calls×2) + tool 227B + tool 203B；delta=+1016B |

- 请求体 SHA-256：seq1 `92220699…20ac10`、seq2 `9f2b6b3e…34e76`、seq3 `19e98d96…06b8b4`（完整值在 evidence）。
- stdout 步进 usage（product-reported 计数）：step1 input 7620 / output 62 / total 7682；step2 input 211 / cacheRead **7616** / output 9 / total 7836。
- workspace：`TASK.md` 85B（SHA `68599aec…3f2c`）、`inputs/exercises/dominoes/dominoes.py` 34B 已知骨架（SHA `89f1fede…43b`）。任务复用 dominoes 已知多轮读文件结构；0 网络/额外工具调用。
- 单 attempt 内两个并行 read 于同一步完成：请求数 3 = 2 loop + 1 辅助，与协议「≥3 请求」一致；「读→读→答」为任务设计意图描述，实际 agent 侧为 2 loop 步（并行读合并为一步）。

## 四问终点（本 run，n=1）

- **Q1 历史外溢**：`append_only_prefix_extended`——第 2 轮请求 = 第 1 轮请求前缀（内容级逐字节相等）+ 追加 3 条消息；无重建/无缩短见证。
- **Q2 截断/重组**：`no_truncation_or_reorg_witness_in_this_run`——delta 恰 +1016B，全部可归因于追加的 assistant/tool 消息；未见截断标记或乱序。
- **Q3 字节 vs 计数**：`descriptive_only_n1`——33091B↔7620 tok、34107B↔211+7616(cache) tok；step2 cacheRead≈step1 input，与「前缀字节恒等→提供方缓存命中」一致；仅描述，不推 tokenizer/缓存语义因果。
- **Q4 系统提示与工具面**：`structure_only`——system 2593B + 22 工具名单（公开产品面）；辅助请求形态单列，不作 agent 请求。

## 验证器与测试

- [verify.py](verify.py)（stdlib）：私档重建（PROXY-START/summary/meta/请求字节+SHA/Authorization 掩码校验/workspace SHA/stdout 步进）→ 派生无内容证据（roles=kind+bytes、工具名单、哈希、计数）→ 公档校验（schema/pin/roles/thinking/max_tokens/前缀/delta/steps/workspace/pins）→ result 四终点。内容级前缀相等在构建期判定；公档重放只复核形态级前缀（字节真值由请求 SHA pin 承载，见 result limits）。
- [test_verify.py](test_verify.py)：43 反例（合成捕获全管线、公档重放一致、无长内容泄漏、请求/响应字节与 SHA 篡改、Authorization 泄漏/未掩码、method/path/summary/PROXY-START 篡改、内容级前缀破坏、workspace 篡改与 symlink 逃逸、roles/thinking/max_tokens/tool_names/多请求/步进/负数/坏 SHA/pins/schema/baseline/model/status/role/kind/负字节 pin、duplicate key/non-finite、独占输出、CLI 互斥），普通与 `-O` 各 43 全绿（18:41–18:43）。
- 修复史（全部在首次证据生成前或同时留痕）：`end_headers()`、Authorization 大小写无关查找、evidence_sha 以落盘文件字节计（保证 raw 与公档重放 result 逐字节同）、公档校验补 roles/thinking/max_tokens 固定 pin、前缀判定升级为内容级（对抗测试发现形状级不足）。
- 本轮重建（私档原始捕获 → evidence/result）：raw 与 `--evidence` 公档重放 result **逐字节一致**（cmp 0）。私收据：`until14-20261117/loop1/{evidence-v2.json,result-v2.json,result-public.json}`。

## 已知限制

- n=1、单任务、单 provider（zai GLM）；辅助请求目的为形态推断。
- 公开证据不含任何请求/响应内容；字节为传输层，不认证提供方 tokenizer/缓存语义或实际思考量。
- Authorization 只存 sha256 前 16 hex + `...`；私档原文不公开。
- 本包不改变此前「归档计数生成者未认证」「无最终完整 body 不可识别」等历史结论的适用范围：本 run 恰好补上了**这一次**运行的完整请求体，不外推其他 run。
