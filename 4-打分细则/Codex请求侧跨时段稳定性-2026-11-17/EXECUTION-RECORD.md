# 环23 执行记录：Codex 请求侧跨时段稳定性（2026-11-17）

## 问题与设计
- 继承 §4.62（分钟级 run 对内 req1 组装恒等，差异恰 11 叶 id 类、归一恒等 351bc938…）。本环将对照拉到小时级时段：早间（04:11，已发布 capture-codex-r1/r2）vs 晚间（当晚新运行）。
- 终点：E1 req1 差异叶分类+归一恒等（主）；E2 run 内前缀性；E3 第二主请求字节数（描述性）；E4 版本/工作区/prompt 不变。
- 冻结页 README（5ba5d7e9…）先于任何晚间请求落盘；先验披露：作者已读全部早间事实、未读晚间捕获。

## 运行时间线（FS stat）
- 冻结 README 5ba5d7e9… birth/mtime 见下表；FREEZE.json 同批。
- 旧晨间捕获代理残留进程（loop15/codex-t3-r2 的 8800 监听，PID 52841）在起本环代理前被 kill（其捕获目录已封存，未受影响）。
- e1：attempt1 失败（`Not inside a trusted directory`，缺 `--skip-git-repo-check`，0 请求）；attempt2 失败（DEEPSEEK_API_KEY 未导出，0 请求）；attempt3 成功 19:01:02（2 请求 200：req1 37568B 55db3139…、req2 39266B ca93052a…）。
- e2：attempt1 失败（同缺 key，0 请求）；attempt2（预算内重试）成功 19:02:20（2 请求 200：req1 37568B be9a5ab6…、req2 38653B 0c680080…）。
- 预算披露：冻结允许 ≤1 次 0 请求重试，实际 3 次 0 请求失败——FREEZE-AMENDMENT.json（c702767a…）如实登记；消耗的计划预算恰为 2 run；失败均无请求发出。

## 结果
- E1：e1/e2 req1 对早间 req1 差异恰 11 叶全 id 类（client_metadata×6+input id×4+prompt_cache_key），e2vsE1 同；无其他字段。
- 归一恒等：§4.62 同款 normalize 后 canonical SHA 三方向均=351bc9383e483c876fdeafb7e73fd5f45da4eb40b53512cc5fe2066f02476d4e。
- E2：两 run 内严格前缀扩展（追加 5/4 条）。
- E3：第二主请求 39266/38653B vs 早间 39102B——模型自由度，只登记。
- E4：codex-cli 0.163.0 前后一致；TASK.md/dominoes.py SHA 不变；prompt 214B 7a7c57c7…。
- verdict=codex_timeofday_stable_ids_generated（期望命中，反证未触发）。

## 验证器与套件
- verify.py：公档重放仅核冻结 pin（先验 SHA/11 叶/字段分类/归一 SHA/前缀/边界）；私档重建另读晚间 4 请求原文+早间 req1 原档（SHA 钉定跨根）；strict JSON/dup key/1e999/路径逃逸/独占输出。
- test_verify.py 12 用例：分类/差异叶/归一掩码/浮点/重复键/路径逃逸/独占；真档 build+校验+篡改 evening pin 拒绝（env XTOD_TEST_ROOT 门控；无 env skip=1）。四档全绿（真档 12 OK×2、无 env 12 OK skipped=1×2）。
- 四路一致：build→install→replay normal/-O 全 IDENTICAL；evidence/install 与封印 cmp 同。

## 已知限制
- 同日跨时段（非跨日）；单任务单模型；bytes 非 token；第二主请求形状为模型自由度不计分；归一恒等不证明模型行为不变；公档重放只核 pin 不认证私档真实性；evidence/result 顺序写非原子。

## FS stat 附表
- README.md birth=2026-11-17T18:57:50.189309+08:00 mtime=2026-11-17T19:05:39.945395+08:00
- verify.py birth=2026-11-17T19:05:05.048379+08:00 mtime=2026-11-17T19:05:05.050532+08:00
- test_verify.py birth=2026-11-17T19:06:04.831058+08:00 mtime=2026-11-17T19:06:43.938742+08:00
- evidence.json birth=2026-11-17T19:07:02.558687+08:00 mtime=2026-11-17T19:07:02.558825+08:00
- result.json birth=2026-11-17T19:07:02.561300+08:00 mtime=2026-11-17T19:07:02.561399+08:00
- FREEZE.json birth=2026-11-17T18:58:09.625163+08:00 mtime=2026-11-17T18:58:09.625254+08:00
- FREEZE-AMENDMENT.json birth=2026-11-17T19:05:39.941418+08:00 mtime=2026-11-17T19:05:39.941543+08:00
- codex-e1-stdout birth=2026-11-17T18:58:50.786932+08:00 mtime=2026-11-17T19:01:06.101003+08:00
- codex-e2-stdout birth=2026-11-17T19:01:52.976240+08:00 mtime=2026-11-17T19:02:22.680489+08:00

## 发布前订正披露（独审后 delta，2026-11-17）
- 独审 PASS 后按低危 L2/L3 做最小订正：README 冻结时刻 19:00→18:58:09（按 FREEZE.json frozen_at，原字节已归档私档 loop23/pre-delta/README.md=a0f5ad7c…）；verify.py 重放路径补 evidence 非对象根→Invalid rc2（探针 [1,2] rc=2，pre-delta verify.py=5641b697…）。L1（冻结字节无快照）/L4（边界清单未逐条对齐）/L5（失败原始 stderr 未保留）维持登记不改。
- E/R 随新 README/verify 重建（evidence f73e8fcc…/result 4c7627bf…），四路 replay×normal/-O 与封印件逐字节同，四档套件绿（真档 12 OK×2、无 env 12 OK skipped=1×2）。
