# r20261029-mechanism 证据索引

详见[公开实验方案/五段结果](<../../1-评测方案/机制实验-2026-10-29/RESULTS.md>)和[可执行复现入口](<../../1-评测方案/机制实验-2026-10-29/README.md>)。

## 实际产品研究场（固定六场，未挑样）

|顺序|场景|实际证据|
|---|---|---|
|1|large/full|[v3场元信息](<v3/20261028T170651Z-01-large-full-e0b04d78/run-meta.json>) · [实际第二request](<v3/20261028T170651Z-01-large-full-e0b04d78/02-request.json>) · [原始stdout](<v3/20261028T170651Z-01-large-full-e0b04d78/stdout.txt>) · [持久化stream补证](<v3/20261028T170651Z-01-large-full-e0b04d78/session-recovered.jsonl>)；无原始SSE，不重跑补齐|
|2|large/bounded|[v4场元信息](<v4/20261028T170952Z-02-large-bounded-0fe26b85/run-meta.json>) · [第二request](<v4/20261028T170952Z-02-large-bounded-0fe26b85/02-request.json>) · [第二raw SSE](<v4/20261028T170952Z-02-large-bounded-0fe26b85/02-response.sse>)|
|3|large/bounded|[v4场元信息](<v4/20261028T170955Z-03-large-bounded-8f5358a9/run-meta.json>) · [第二request](<v4/20261028T170955Z-03-large-bounded-8f5358a9/02-request.json>) · [第二raw SSE](<v4/20261028T170955Z-03-large-bounded-8f5358a9/02-response.sse>)|
|4|large/full|[v4场元信息](<v4/20261028T170958Z-04-large-full-624b8e98/run-meta.json>) · [第二request](<v4/20261028T170958Z-04-large-full-624b8e98/02-request.json>) · [第二raw SSE](<v4/20261028T170958Z-04-large-full-624b8e98/02-response.sse>)|
|5|small/full|[v4场元信息](<v4/20261028T171001Z-05-small-full-0799bc72/run-meta.json>) · [第二request](<v4/20261028T171001Z-05-small-full-0799bc72/02-request.json>) · [第二raw SSE](<v4/20261028T171001Z-05-small-full-0799bc72/02-response.sse>)|
|6|small/bounded|[v4场元信息](<v4/20261028T171003Z-06-small-bounded-e5d016bc/run-meta.json>) · [第二request](<v4/20261028T171003Z-06-small-bounded-e5d016bc/02-request.json>) · [第二raw SSE](<v4/20261028T171003Z-06-small-bounded-e5d016bc/02-response.sse>)|

每场目录还含首调request、transport/HTTP状态（不含headers）、完整工具原文、stdout/stderr、退出码、profile覆盖值。所有首request JSON一致。原始SSE的model别名为deepseek-flash；low体现在output_config.effort；实际目标host为api.deepseek.com。仅user/workspace路径脱敏，不记录凭据值。

## 分账与完整性

- [分析原收据](<analysis.json>)不再覆盖；[导入事件](<experiment-events.json>)将实际六场记为product_run/research/experiment=true，初始化/配置预检与自测、复算分账，不进正式产品表。[事后identity/facts适配](<import-adapter.json>)明确不是运行前冻结identity。
- [v1冻结](<freeze.json>)、[v2冻结](<v2/freeze.json>)、[v3冻结](<v3/freeze.json>)、[v4冻结](<v4/freeze.json>)保留原字节。v1挂载失败、v2发送前工具白名单阻止均0API；[零网络runtime预检](<runtime-preflight-b0b1de8d/receipt.json>)用throwing sentinel，不是mock模型实验。
- [原生完整spill事后收据](<spill-recovery-posthoc.json>)和[两个完整副本之一](<v4/20261028T170955Z-03-large-bounded-8f5358a9/native-spill-complete.txt>)：与完整工具原文hash一致。原meta中home/spill空数组是漏查系统tmp，不是无spill证据；触发只由该场request标记判定。
- [离线初版4测试](<offline-verification.json>)与[最终6测试](<offline-verification-v2.json>)分开保留；后者含fresh布局的离线合成适配测试，绝非新在线模型运行。
