# 执行记录：请求侧计数与缓存抖动（2026-11-17）

## 时间线（Asia/Shanghai；02:5x 按文件系统时间订正，初稿分钟数系事后补写、系统性晚 4–7 分钟）
- 02:33 环12私立题 `loop12/DIRECTION.md`（零新运行；E1–E5 终点预声明）。
- 02:34 本包冻结页 README.md 落盘（先于证据构建）。
- 02:34–02:36 verify.py 实现（首版）；02:36:05 evidence/result.json 首次由实现中的构建器产出（见下「构建过程披露」）。
- 02:36–02:39 test_verify.py 实现：首版对合成档 1 失败 13 错误——合成档把 run 名编进请求字节，使同 provider 同 seq 的请求互异，而 refresh 按 (provider, idx) 覆盖键 → pin 失配；修正 fixture 为同 provider 同 seq 请求字节恒等（与真实结构一致）、仅 usage 按 run 波动。修正只改合成 fixture 构造，与真档 24 行内容无关（独立重算逐行一致）。
- 02:39 verify.py 定稿（第三次修正：parse_float 拦 1e999 并放行有限小数）；同版对真档幂等重建 evidence/result 与已装件逐字节同。
- 02:39–02:40 20 用例 × 4 档（普通 / -O × 有无 UV_ARCHIVE_BASE 真档分支）全绿；公开重放 normal/-O 与 result.json 逐字节同。

## 数据来源（8 个真实 run × 3 请求 = 24 行，全部既有授权捕获）
- GLM 6 run：loop1/capture、loop5/capture-r2、loop6/capture-r3..r5、loop9/capture-r6（明文 SSE）。
- DeepSeek 2 run：loop10/capture-ds-r1/r2（响应 gzip，gunzip 后解析）。
- req1/req2 字节恒等已由前置包（rebuild/extension/crossday/xm）证明，本包以 SHA pin 引用；req3 SHA 逐 run 记录、不作恒等 pin。

## 实际结果（终点表）
| 终点 | 结果 |
|---|---|
| E1 同字节请求 prompt_tokens 稳定 | 24/24（GLM 7620/190/7827；DS 8089/188/8361） |
| E2 cached_tokens 跨 run 波动 | GLM req1 {0,7616} req2 {0,128} req3 {7616,7808}；DS req1 {0,7936} req2 {0} req3 {8192} |
| E3 字节/计数比值 | 描述性：GLM req1 ≈4.34 B/token；DS req1 ≈4.17 B/token（bytes 非纯 prompt，不换算成本） |
| E4 方言 | GLM=cached_tokens；DS=prompt_cache_hit/miss 且与 cached_tokens 镜像 |
| E5 completion_tokens | 响应侧（62 恒定/8–10 波动），不计分、不进任何评分 |

## 验证器与套件
- verify.py：stdlib-only；CLI `--archive-base`(仅build) `--build-evidence/--evidence` 互斥 `--output` 必需；strict JSON（拒重复键/NaN/Infinity/1e999）、泄漏扫描（/Users/、api_key、sk-、authorization）、exclusive 输出。
- test_verify.py：20 用例（合成8run档 + 真档分支 skip 守卫 + CLI 篡改/独占/缺参 rc=2）。

## 已知限制与诚实披露
- 构建过程披露（02:5x 订正）：evidence/result 首次于 02:36:05 由实现中的 verify.py（非最终版）构建；最终版（02:39 定稿）对同一私档幂等重建，与已装两件逐字节相同（作者 cmp 复核 + 非作者独审独立复证），最终工具的订正未改变任何已装内容。
- 时间线初稿的分钟数系事后凭记忆补写，与文件系统时间存在 4–7 分钟系统性偏移，已按 mtime 订正；先后承重关系（README 02:34 冻结先于证据 02:36 构建）不受影响。delta 前原字节留私档 loop12/pre-delta/。
- n=1 任务 × 2 provider；计数为产品侧报告值（usage 字段），不认证后端语义；cache 语义由 provider 定义；无成本换算。
- 原始响应体（含 usage 的 SSE/gzip）留私档，公档只记 response_body_sha256 与计数。
- 缓存抖动（同字节不同 cached_tokens）为观测事实，不据此推断任何评分或成本结论。
- E3 比值是字节与 token 计数之比，请求字节含 envelope/工具声明，非纯 prompt 文本，只能描述不能精确换算。
