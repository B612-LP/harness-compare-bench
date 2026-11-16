# 执行记录：Codex 响应侧计数与缓存抖动（2026-11-17）

## 问题与方法
环9（[请求侧计数与缓存抖动](<../请求侧计数与缓存抖动-2026-11-17/README.md>)）的 prompt 稳定/cache 波动结论当时只覆盖 DSH 适配层捕获。本环把同一描述性口径延伸到环14/环15 已授权捕获的 4 个 Codex run（11 个响应，全部 GLM 官方 API、经 Codex CLI 直连）：从私档 SSE `response.completed` 事件提取 `usage`，与已发布 evidence 的 per-request SHA 列表逐条绑定（位置+字节双重校验），登记三个端点。**0 新产品运行**。

## 观察值（product-reported；公开 evidence 逐行携带）
| task/run/seq | input | cached | reasoning | request_bytes |
|---|---|---|---|---|
| t1 r1 1→3 | 8117 / 8533 / 8821 | 4608 / 8320 / 8576 | 133 / 4 / 25 | 37568 / 39102 / 39984 |
| t1 r2 1→2 | 8117 / 8725 | 7936 / 8576 | 54 / 0 | 37568 / 39423 |
| t3 r1 1→3 | 8078 / 8455 / 8792 | 7808 / 8192 / 8576 | 19 / 59 / 41 | 37414 / 38690 / 39849 |
| t3 r2 1→3 | 8078 / 8929 / 9423 | 7936 / 8576 / 9216 | 59 / 213 / 111 | 37414 / 40269 / 42156 |

- **E1 = 2/2**：两对 req1（长度相等+id 归一恒等）`input_tokens` 逐值相等（8117/8117、8078/8078）→ prompt 计数稳定性延伸到 Codex 侧。
- **E2 = 2/2**：同对 `cached_tokens` 互异（4608↔7936、7808↔7936）→ 缓存计数波动同样成立；且两 run 首请求 cached>0（4608/7808），与 loop9 的 DSH 首请求 0 不同——只登记，不解释。
- **E3（登记）**：链内字节增量与 input 增量无恒定比例（如 t1 r1 第2步 +1534B/+416tok、第3步 +882B/+288tok）；`reasoning_tokens` 与环15 encrypted 回放观测并列呈现。

## 先验披露（诚实性）
作者在冻结前已用临时脚本读出全部 11 个响应的 usage 值（见私档 loop16/DIRECTION.md）；本环为**事后描述性确认**，不是盲预测；终点写成登记+分类，不写命中。

## 验证器与套件
- `verify.py`：公档重放核对封印链内登记的 README SHA（`evidence.frozen_readme_sha256` 与 verify 常量互核；重放不重复哈希磁盘文件，磁盘 README 变动由 Git 追踪承接）、环14/15 两个公开 evidence 的文件 SHA pin、11 行 schema/整数域/请求绑定（SHA 在已发布列表中的位置与字节）、E1/E2/E3 重算、verdict 装配；私档重建模式从捕获目录解析 SSE/JSON 响应重建同一 evidence。`--evidence` 必须与封印 evidence 字节一致（防旁路）。fail-closed rc=2。
- `test_verify.py` 13 用例：CLI 基础 3、真档重放/重建一致+端点绑定 2（无 `CXUSAGE_TEST_ROOT` 时 skip）、合成篡改/删行/bool/坏SHA/坏绑定/非finite/SSE解析/端点数学 8。四档全绿（普通/-O × 有无私档；无档 skip=2）。
- 实现订正（首版封包内、均在首次 SELF-ACCEPT 封印前）：`--evidence` 旁路在套件反例驱动下改为封印字节强校验（初版任意 evidence 可过算术校验、verdict 可被单值篡改改变——按「公档完整性以封印为锚」收紧）；REPO 层级公式修正（dirname×2）。

## 非作者独审与发布前订正（第二版）
非作者独立独审（task-41）判定 PASS，附 4 条低危备注；发布前按其订正并经同一独审者 delta 复核：
- L1：复算入口措辞改如上（公档重放不重复哈希磁盘 README，以封印链内 SHA 为锚）。
- L2：README/套件 docstring 用例数改 13（skip=2），与实际一致。
- L4：「钉定」统一指 SELF-ACCEPT 封印（首版 06:09:09）；本节订正发生在独审之后、公开集成之前，全部重建/重放四路逐字节一致、套件 13×4 重跑全绿。
- 随订正 `verify.py` 的 `README_SHA`/`PIN_EVIDENCE` 同步为订正后字节（9818fc01…/2bddde19…）；evidence/result 以订正版 verify 从同一私档幂等重建（与 -O 版逐字节一致）。
- 追加（集成回归暴露，仍在公开发布前）：`verify.py` 默认仓库根层级修正（`--root` 省略时 dirname×3→×2；此前默认重放只在我方显式传 `--root` 的路径下验证过，回归工具以无 `--root` 重放暴露该缺陷）。修正后默认根重放（普通/-O）与封印 result 逐字节一致，套件 13×4 重跑全绿。
- L3（私有说明）：`loop16/FREEZE.json` 记录的 readme_sha256=b72566e6… 是冻结时点版本；E1/E2 措辞在冻结记录后、任何 evidence 存在前收紧（最终先发布版 509870b9…→订正版 9818fc01…）。冻结页内容变化已在私档 `FREEZE-AMENDMENT.json` 留痕，公开协议页以 evidence 封印内的 SHA 为准。

## 时间线（按文件系统 birth/mtime，Asia/Shanghai）
- 首版：06:05:45 README birth；06:07:02 verify birth；06:07:12 evidence/result birth（重建自私档，rc0）；06:07:57 test birth；06:08:35 首版套件四档全绿（verify 首 mtime）；06:09:02 本记录；06:09:09 SELF-ACCEPT 封印（即「钉定」）。
- 独审后订正版：06:17:02 README mtime；06:17:08 test mtime；06:17:34 verify 首次订正 mtime；06:17:42 evidence/result mtime（幂等重建）；verify 默认根修正 mtime 见 FS（约06:22，第三订正）。
- 本节两版时间均取自 FS stat、未凭印象补写；EXEC 自身的修改时间随订正后移，以独审 delta 复核收据为准。

## 已知限制
- 全部数值为 product-reported counters，不认证计费/KV 复用/缓存机制/实际摄入；响应原文只在私档。
- Codex req1 对条件弱于 DSH 同字节对（长度相等+id 归一恒等），结论只到该层面。
- E3 只登记不建模；单模型、n=2 任务对。
- 公档重放只核算术与绑定，不认证私档响应内容真实性；双输出顺序独占写，非事务。
