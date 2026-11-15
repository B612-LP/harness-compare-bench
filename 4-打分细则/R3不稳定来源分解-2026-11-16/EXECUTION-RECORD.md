# R3 不稳定来源分解 · 执行记录（2026-11-16）

本文件是 [R3不稳定来源分解](<README.md>) 包的执行记录。预注册 README（SHA256 `c4546f35…e6ea00`）被包内 verify.py 钉定、字节冻结不改；本批次页 `3-表现现场/r1109-mech-n3/README.md` 亦被 [v1.1 澄清包](<../../机制重复口径澄清-2026-11-12/README.md>) evidence.json 作 normative 源钉定（首版执行记录曾误写入该页并破坏钉定，已回退——事件经独审 MINOR-1 提示后由验收复验捕获，登记于此）。执行记录按 v1.1 先例改记本文件。

## 执行流程

1. builder（r3dec-builder）按冻结预注册实现 `verify.py`/`test_verify.py`/`result.json`，真实数据零分类歧义（1,578 个 response_item、4 种 payload 类型、166 条 message 全部有可识别 role），无 STOP 条件。
2. Lead 验证：双模式 exit 0、stdout 摘要跨模式逐字一致、`--output` 全量输出与存量 result.json 逐字节相等、测试 20/20 双模式通过、隐私扫描清洁（仅 token_usage_record 用语命中）、v1.1 verify/result SHA 钉定核验通过。
3. 非作者独审（r3dec-auditor）：**PASS-WITH-FINDINGS**，11/11 检查全过——独立自写解析器重算 15 槽 0 差；v1.1 逐槽硬等复核；6 组近错探针全为安全向（字节翻转 exit 2、v1.1 result 篡改双层拦截、roleless→ClassifierStop、turn_context→E 兜底精确分族、net==Δ/2 不判主导）；预注册忠实逐行核对、无事后数值；两条已触发反证分支如实并录。MINOR-1=包 README 钉定不可追加执行记录（已按上文处置）。
4. Lead 验收后复验捕获：执行记录误写批次页导致 v1.1 normative SHA 失配——回退批次页字节至钉定原样（复验 v1.1 独立运行与本包流水线均恢复 exit 0，15 槽硬等不变），记录移入本文件并登记事件。
5. 收据（builder RUN-RECEIPT、LEAD-VALIDATION、LEAD-ACCEPT、独审报告）存私档，`archive://until12-20261116/loop2/` 定位。

## 结果摘要（与本包 result.json 一致）

- **M\*（assistant message+reasoning+function_call）4/5 组主导**：bird 93.70%（Δ=154,301）、dabstep 83.26%（Δ=296,848）、lcb 94.43%（Δ=165,538）、tb 89.41%（Δ=471,897）。
- **exercism-py-6 唯 E 族主导**：Δ=31,431 中 E 净 +27,407（87.20%），其中 `function_call_output` +27,406；三对两两分解均 E 主导（r1vsr3 对 Δ=10,942 中 E 占 9,626）。
- **对账**：逐组 Δ 与 v1.1 记录值全等；15 槽 R3 总和与 v1.1 result.json 逐槽硬等；五组首三条 message 哈希组内一致（稳定核复验通过）。robustness 附注：dabstep r2vsr3 对 E 族亦主导（28,596=59.26%），已如实入档。
- **解释边界**：族分类按 payload 类型机械划分；`function_call_output` 内容依赖模型所选调用，故 exercism 的 E 主导只把漂移定位在工具结果面，不构成环境独立漂移的证据。不动任何门判定与分数，无新增运行。
