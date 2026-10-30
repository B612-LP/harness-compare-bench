# L6 WB 现场准备报告（纯静态，零模型调用）

批次：l6-20261030-wb-gateway ｜ 生成：2026-10-30T11:51:00+08:00
D=8c3e4b9e595a8d49ddd10150a67cf101a8bea19c ｜ 状态：**待放行**（E 公告前不跑任何真实槽）
写界：仅本目录 ｜ live_doc_drift=[] ｜ 零 WorkBuddy 启动/零 bench-workspaces 写入

## 1. 按位拷贝（diff=0，receipts/site-copy-receipt.json）

| 文件 | sha256_8 | diff |
|---|---|---|
| runner/l5_wb_runner.py | e1def090 | 0（lead 已独立抽验一致） |
| runner/safe_driver.py | 5a3a5203 | 0 |
| runner/verify_execution.py | 904bb6d1 | 0 |
| driver-snapshot/workbuddy_driver.py | f9d4b076 | 0 |
| driver-snapshot/driver-README.md | 16cfec0f | 0 |

新站点 SHA256SUMS.txt 已重算（上列五件）。runner/runner-config.json 为**新写**（L6 适配）：
rule_version=l6-20261030-batch-v1、design_seal_commit_D=8c3e4b9e…；renderer_ready_timeout_s=120/
poll_s=2、forensic_boundary、no_secrets、source_paths 原样继承 L5。

## 2. 封装前目录终态清单（E manifest 钉定范围，封后不再动）

- `runner/` 恰 4 文件：l5_wb_runner.py、safe_driver.py、verify_execution.py、runner-config.json
  （无 __pycache__ 等其他任何文件，后续运行以 PYTHONDONTWRITEBYTECODE=1 防生成）。
- `driver-snapshot/` 恰 3 文件：workbuddy_driver.py、driver-README.md、SHA256SUMS.txt。
- 除 runner-config.json（任务第 2 项）外，两目录无任何其他新增/修改。

## 3. 静态验证结果

- **verify_execution 缺 binding fail-closed ✓**：对尚不存在的
  `自动循环L6-2026-10-30/runtime-binding.json` 调用 → GateError「binding 不存在或为软链」，
  ok=false，零调用。
- **preflight**：all_pass=False，唯一失败=`checker_sha256[bird]` want=994be0b3（L5 合同旧 pin）
  vs got=fa1a68a3（lead 已修订的 L6-A checker）——**这正是 L6-A 主题本体的过渡态信号**；
  L6 contract（--contract-only，pin 新 sha）生成后此项转绿。其余检查全过。
- **selftest**：70/71 过，唯一失败=T22d.frame_identity_fields（测试字面量锚定 L5 D
  8b1043d0；站点 config 已是 L6 D 8c3e4b9e——按位拷贝冻结与 L6 config 的预期耦合，
  E 阶段授权适配时随路径指向一并更新，非功能缺陷）。receipt=
  selftest/selftest-receipt-l5-wb-v1.json（receipt_check 由 judge 独立跑）。

## 4. dry/mock 产物显式标注（防与真实槽混淆）

- 本站点 `selftest/` 下全部 `dry-*` 目录/文件、`dry-frame-probe*.json`、以及曾在
  `receipts/claims/` 出现的 `l5-20261030-…claim`（现已清除）——**全部是 L5 工具链的
  dry/mock 自测产物**：拷贝代码硬编码引用 L5 计划所致，**不代表任何真实槽执行**，
  与 L6 真实证据零关联。
- L6 真实槽证据（E 放行后）只会出现在 `runs/l6-20261030-…`/ 下（路径含 l6 前缀+真实
  registration/trace/score-receipt）；selftest 夹具永远落在 `selftest/dry-*`。
- runner 路径常量当前仍指 L5 计划/合同/binding（diff=0 拷贝要求）；L6 指向将在 E 封装
  阶段以授权 diff 一次性落地（同 L5→L5-gate 先例），本报告静态验证不依赖该指向。

## 5. 状态

待放行。E 公告前：不启动 WorkBuddy、不写 bench-workspaces、不跑真实槽、不改 2-用例/与
L5 现场。


---

## v6.2 dated 收口（2026-10-30T12:13:52+08:00）：E1 废止 + 全部授权 diff + 复验终态

- **E1=1c27a6b6 废止**（根因=预注册按位拷贝漏站点常量，lead 自认非本员问题；零消耗入档，
  纪要=1-评测方案/自动循环L6-2026-10-30/seal-supersession-E1-20261030T1153.md）。
- **授权 diff 全清单**（receipts/e1-to-e2-authorized-diff.json，hunks 全录）：
  - 主 diff 7 行（lead 裁决 6 处）：:35 计划目录→L6、:40 workspace 根→l6、:196/:1090/:1371
    收据 batch 标签、:397 TASK.md 头、:619 relative_to（运行期关键）；e1def090→fe763264。
  - appendix A：preflight 批形状 4 断言改写为「读 L6 plan/contract 事实一致性」（不硬编码
    槽位清单；:1024-1039 整块 before/after 全录）；fe763264→6ad752e7。
  - appendix B：SHA256SUMS.txt 定稿重算（全部 diff 定稿后，记录=最终字节）。
  - appendix C：自测架适配 2 hunk——:1151 SLOT_B=wb_slots()[-1] 单槽别名；T12 前置
    reset_slot（单槽别名下触发顺序=全新 claim→ws-exists，与原 setup-failure 语义一致；
    首次插入位置写反当场修正，最终形态=赋值后 reset）；6ad752e7→e0588e6a。
  - appendix D（lead 选①单行例外，废封纪要「授权补充 12:10」节）：:1724 合成 contract19
    rule_version 标签镜像活体 L6 合同（slot id/plan 体语义未动）；e37f23af→**06d171bb（终态）**。
- **dry 残件清理（lead 授权 C 项）**：站点 receipts/claims/l5-20261030-…claim（自测夹具，
  零发送）、selftest/dry-* 各轮目录、dry-frame-probe*.json——均为 L5 工具链 dry 件、不在
  钉定根内，已删/由自测启动清理再生； REPORT §4 已标注其 mock 属性。
- **复验终态**：preflight **all_pass=True**（preflight-static-20261030T1213330800.json，
  含 bird pin ffa7389a 绿）；selftest **70/71**（唯一 T22d=L5 D 锚定已知败，未修）；
  runner 终态 sha256=06d171bb…（SUMS 已同步）；零模型调用、零真实槽、零 WorkBuddy 启动。
- 状态：待 lead 提交+重封 E2 后执行唯一真实槽 wb-bird-r1。
