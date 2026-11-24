# 等价域施于 wire 请求面（2026-11-25，预注册）

> 状态：已验收（11-17 失败例链冻结原档字节重编码，零新增运行）。本页收口[观测口径收口综述](<../观测口径收口综述-2026-11-25/README.md>)剩余不确定性 #5（等价域此前只施于事件/轨迹层）；响应侧 framing 等价见[响应侧工具参数源头](<../响应侧工具参数源头-2026-11-17/EXECUTION-RECORD.md>)。

## 1. 判定（合同：wire-request-domain.json，内容无关）

| 预测 | 判定 | 数据 |
|---|---|---|
| PT1 请求体 canon 稳定 | PASS | 16 个请求 JSON body ×5 风格（canon/indent2/ensure_ascii/orig_key_order/spaced）reparse 深等值+canon 逐字节稳定，16/16 |
| PT2 骨架/正文分层 | PASS | 16 个原始文件字节 SHA 全互异（互异来源为 messages 历史增长；seq 类字段在伴随 meta）；投影层稳定与字节层互异并存 |
| PT3 SSE 帧级等值 | PASS | 16 个响应共 497 个 JSON data 帧 canon 幂等全部成立（28/7/22/27/35/37/38/38/35/37/35/38/38/35/35/12）；[DONE] 哨兵逐文件恰 1 处（行号登记，非 JSON 如实分类） |
| PT4 语义变体普查 | PASS（如实） | int 载体恰 1 路径/请求（16/16 一致）；NFC 载体 0（no-carrier 如实登记） |

## 2. 链锚钉定

合同 chain_anchor 与 R9 页钉定值对表（001.request=`765b958d…52220`、001.response=`b4db600a…a066`）——复算器常量层硬校验（声明式绑定升级为钉定对表，较 [读取准入](<../读取检测准入合同候选-2026-11-25/README.md>)复算器的声明式绑定更强）。

## 3. 近错（Q0 正常对照+QU1/QU3/QU4 共 4 项全拒；影子合同真跑；PREREG 预告的 QU2 以 PT1 orig_key_order 风格旁及、未作独立影子项，如实登记）

掉字段拒 / 哨兵形态破坏拒 / 链锚篡改拒（钉定化后）。

## 4. 复算与测试

```sh
python3 4-打分细则/等价域wire请求面-2026-11-25/recompute.py
python3 4-打分细则/等价域wire请求面-2026-11-25/test_recompute.py
```

`recompute.py` 校验：schema、文件数（16+32）、PT1–PT4 声明、int 载体计数（恰 1/请求）、哨兵行形态、链锚钉定对表、近错声明、内容无关门。`test_recompute.py` 9 项（1 正常+8 注入）全拒。

## 5. 结论边界

本链（16 请求/16 响应）为 wire 请求面等价域的**单链落点**；其余会话链的请求面待扩（如实）；帧级 canon 明细只入私档；不产生分数；R9 的 SOURCE_MISSING_PRESERVED 判定不因本页改变。

## 6. 正例链扩展（2026-11-25 登记式追加，合同 wire-positive-chain.json）

11-16 正例链（glm-5.3-flash 历史切片批次，模型与等价域无关）3 请求+3 响应（meta.request_body_sha256 绑定 3/3 对表）：PT 同法复测——3 请求×5 风格全 stable（int 载体逐请求 `$.max_tokens`、NFC 0）；3 原始 SHA 互异；3 响应 69 JSON data 帧（55/7/7）canon 幂等、[DONE] 哨兵逐文件恰 1。loop3 独立副本互证：请求 001/002 字节同、003 不同（同槽两轮捕获演化体，如实登记，不并入绑定）。复算器 `recompute-positive.py`（+`test_recompute-positive.py` 1 正常+6 注入）；帧数/哨兵**正值**篡改不属公开层检测面（无原档重读），真值由原档 SHA 钉定+独审承担（同 §3 双层分账）。至此 wire 请求面等价域=**双链落点**（11-17 失败例链+11-16 正例链）。
