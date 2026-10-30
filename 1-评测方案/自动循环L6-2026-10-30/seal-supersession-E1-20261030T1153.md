# E 封印废止纪要（E1=1c27a6b，2026-10-30）

- **废止对象**：E1 execution seal `1c27a6b6d15986868d3cc73c6420fbf8708a45bb`
  （binding registered_at=2026-10-30T11:52:45+08:00，commit bfa9388；manifest
  `0bc9401e…`，design=1211b5b787049b9367af8b85aa99ab15d9d7104c 不变）。
- **消耗核算**：**零消耗**——wb-probe 实证零 claim/零 registration/零发送/零模型调用，
  阻断发生在 runner 读计划阶段（fail-closed），无任何真实侧副作用。
- **根因（lead 预注册声明缺陷，非执行方）**：PREREGISTRATION 声明「runner 五件套按位
  拷贝(diff=0)、零改动」，但 `l5_wb_runner.py` 内嵌站点常量（L5 计划目录、仓外工作区根、
  batch 字符串、evidence_dir 相对化前缀）——按位拷贝无法寻址 L6 现场与 L6 plan，
  `wb_slots()` 读 L5 计划 → L6 slot 不存在 → 运行期必然拒绝。属可预见的适配遗漏，
  由 E 后首槽前静态验证暴露（零成本）。
- **授权最小 diff**（仅 `runner/l5_wb_runner.py`，其余两 runner 文件已核零 L5 引用）：
  1. :35 计划目录常量 `自动循环L5-2026-10-30` → `自动循环L6-2026-10-30`（变量名不动）；
  2. :40 `WORKSPACE_ROOT` `l5-20261030-wb-gateway` → `l6-20261030-wb-gateway`；
  3. :196 meta `batch` 字符串 → l6；
  4. :397 TASK.md 头行 batch → l6（进入真实 prompt 证据）；
  5. :619 `evidence_dir` 相对化前缀 `3-表现现场/l5-…` → `3-表现现场/l6-…`（运行期关键）；
  6. :1090/:1371 preflight/self_test 收据 `batch` 标签 → l6（站点证据诚实性）。
  **明确不动**：selftest 合成 fixture 的 L5 slot id/plan 体（:1535-1728 段）保持原样，
  T22d 已知失败（70/71）继续作为 documented known-state；verify_execution.py /
  safe_driver.py / driver-snapshot 零改动。
- **处置**：wb-probe 施行上述 diff + 复跑 selftest/preflight（preflight 应对 L6 contract
  转绿）→ lead 提交 → 重封 **E2**（design 仍为 1211b5b，PREREG/plan/contract 零变化；
  新 manifest 钉修订后 runner 字节）→ 重新放行单槽。E1 的 binding/manifest 留 git
  （bfa9388/1c27a6b）可考，runtime-binding.json 由 E2 重写（旧值仅存 git）。

## 授权补充（2026-10-30 12:10，lead dated）

E1→E2 适配在原 6 处清单外新增（均限自测/静态面，运行时函数零触碰）：

- **A 批形状断言**（:1024-1039 一带 4 项）：由 L5 双槽硬编码改写为「读 L6 plan/contract
  对事实一致性断言」（count/order/case-sequence/unique），hunks 全录（diff 收据
  appendix A）。
- **B SUMS 重算**：driver-snapshot/SHA256SUMS.txt 在 runner 终态字节定稿后重算
  （记录必须=最终字节）。
- **C 自测架适配**（harness 段，fixture 数据段仍禁触）：:1151 SLOT_B 单槽别名、
  :1470 用例间前置 reset（appendix C 2 hunks）；**:1724 单行例外**——合成 contract19
  的 `rule_version` 标签 `l5-20261030-batch-v1`→`l6-20261030-batch-v1`（合成世界必须
  镜像活体合同，否则 T19 的 gate 比对失真；仅标签，slot id/plan 体语义未动）。
- **dry 残件清理**：selftest/dry-evidence-v20f 等 L5 dry 件删除清单进 REPORT dated 备注。
- **验收口径**：preflight 全绿（已达）；selftest 除 T22d（L5 锚定已知败）外全过。

## E2 废止与 E3 授权补充（2026-10-30 12:20，lead dated）

- **E2=46d64ee 废止**（registered_at=2026-10-30T12:15:41+08:00）：第二次 REFUSED，
  **零消耗**（REFUSED 先于 claim，零 claim/零 registration/零发送，runs/ 空）。
- **根因（同类第二次）**：`runner/verify_execution.py` 调 gate 时未传 `plan_dir`，
  gate `DEFAULT_PLAN_DIR` 硬编码 L5 计划目录 → gate 读 L5 plan，与 L6 binding
  plan_sha 错配 → fail-closed。字面 grep 不可见（L5-性存在于 gate 默认值，非 runner
  文件内），属语义默认值遗漏。链上先例：L4→L5 漏 gate 路径、L5→L6 漏 plan_dir。
- **授权 diff（E3）**：`verify_execution.py` 增站点常量
  `PLAN_DIR = REPO/"1-评测方案"/"自动循环L6-2026-10-30"`，调用处显式
  `plan_dir=PLAN_DIR`（2 行级；gate 文件本身零改动，L5 现场不受影响）。
- **E3 前置硬条件**：wb-probe 完成「运行路径默认值审计」——沿 pre-claim 校验→claim→
  prompt→启动→collect→checker→meta 全链，逐常量/默认值清点 l5/L5-era 引用或语义
  默认（含间接：所调模块的 DEFAULT_*），出 nil-or-found 清单收据；无审计收据不封 E3。
- **SUMS/manifest**：verify_execution 变更后 runner 目录终态重算 SUMS；E3 manifest
  重新钉全部源字节。
- **F1（2026-10-30 12:25 追加）**：verify_execution 修复后进至
  `manifest-external-required-locked` REFUSED——gate 的 EXTERNAL_REQUIRED 硬要求
  manifest.external_files 含 3 件环境身份（`~/.dsh/profiles/bench-cli/cordis.patch.yml`、
  同目录 `package.json`、`~/.dsh/AGENTS.md`）。处置=**超量满足，不放松验证器**：
  L6 execution_seal.py 的 REQUIRED_EXTERNAL_FILES 补回前两件（AGENTS.md 原已钉），
  WorkBuddy 两件保留；gate 零改动（DEFAULT_PLAN_DIR 残留维持「显式传参覆盖+默认值
  冻结」处置，L5 行为不变）。审计收据=runner 侧
  `receipts/l6-runtime-defaults-audit.json`（85 项分类，唯一残留=gate 默认，已覆盖）。

live_doc_drift: none（0 项）
