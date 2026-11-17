# Codex 请求侧跨时段稳定性（2026-11-17，预注册）

## 状态
已冻结（2026-11-17 18:58:09 Asia/Shanghai），**尚未运行**。运行后在本页追加结果节，不追改冻结文本；探索性事后对照（作者已读全部早间事实）。

## 问题
Codex CLI 同任务请求组装的稳定性此前只在分钟级 run 对内验证（§4.62：req1 跨 run 差异恰 11 叶全 id 类、归一恒等=codex_assembly_stable_ids_generated）。跨**小时级时段**（早间 04:11 vs 晚间）是否仍同一分类？

## 固定观测对象
- 早间锚（已公开于 §4.62 包）：capture-codex-r1 req1=37568B SHA 6a156cdb57c908fc385076e840ef281ca6f75573b5881af10fbeda73fa08ced9、002=39102B b6fd7749…、003=39984B 2bae0e38…；r2 req1=37568B（差异 11 叶 id 类，归一 SHA 351bc9383e483c876fdeafb7e73fd5f45da4eb40b53512cc5fe2066f02476d4e）。
- 工作区 capture-r1：TASK.md 68599aec…、dominoes.py 89f1fede…（运行前后重核）。
- 提示词 loop5/prompt-r2.txt：214B SHA 7a7c57c759d2aaccbdab600e4cb4c7b429bb820268a801f97967f82565ecb765。
- Codex 版本 codex-cli 0.163.0（冻结时核对）；CODEX_HOME=~/.codex-capture-loop14（与 §4.62 同配置）；捕获代理 127.0.0.1:8800 → https://api.deepseek.com:443。

## 终点（全部描述性，n=1/臂）
- **E1（主）**：晚间 run req1 对早间 r1 req1 差异叶分类——期望仍恰为 id 类叶集合（client_metadata/input_id/prompt_cache_key 键族）且按 §4.62 同一归一化后恒等（归一 SHA==351bc938…）；反证=出现非 id 类叶或归一不等。
- E2：晚间 run 内前缀性（req3 对 req1 前缀+追加，delta 字节登记）。
- E3：辅助请求（002 形态）与 req3 字节数对早间锚登记。
- E4：codex 版本与 CODEX_HOME 配置 SHA 运行前后一致。

## 预算
晚间计划 2 run（capture-codex-e1/e2）；0 请求失败允许 ≤1 次重试；不新增 workspace/提示词/配置变更。

## 边界
同日跨时段，非跨日；单任务单模型；bytes 为传输层非 token；id 类叶=provider 生成标识，非语义漂移；归因不覆盖模型内部。原文只入私档（until22-20261117/loop23/）。

## 结果（运行后追加，冻结文本未改）

两次晚间运行（capture-codex-e1 19:01:02、capture-codex-e2 19:02:20，各 2 请求全 200）：

- **E1**：e1/e2 req1（37568B，与早间同字节数）对早间 req1 差异**恰 11 叶全 id 类**（client_metadata×6 + input id×4 + prompt_cache_key），e2 对 e1 同样 11 叶同分类；无其他字段差异。
- **归一恒等**：按 §4.62 同一归一化（client_metadata/prompt_cache_key/input id 置 NORMALIZED 后 canonical）三方向（早间/e1/e2）canonical SHA 均 = `351bc9383e483c876fdeafb7e73fd5f45da4eb40b53512cc5fe2066f02476d4e`——期望命中、反证未触发。
- E2：两晚间 run 内 req2 对 req1 严格前缀扩展（追加 5/4 条）。
- E3：第二主请求字节数 e1=39266B、e2=38653B（早间 39102B）——run 间形状随模型自由度变化，只登记不计分。
- E4：codex-cli 0.163.0 运行前后一致；工作区两文件 SHA 不变；stderr 的 `Model metadata` 提示早/晚均出现（一致，非新漂移）。
- 预算披露：冻结允许 ≤1 次 0 请求重试，实际发生 3 次 0 请求失败（缺 `--skip-git-repo-check`、两次缺 key 导出），已按 FREEZE-AMENDMENT 如实登记；成功消耗的计划预算恰为 2 run。
