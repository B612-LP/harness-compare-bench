# EXECUTION-RECORD — Codex元数据值语义-2026-11-16

预注册包 builder 执行记录（环 19，环 7「Codex输入面残差定位」键路径的值语义检验）。
本文件零正文引用、零 content[].text 值；私有档案根仅以 `launch-r1109` 标记指代。

## 开工门槛

- 冻结 README.md SHA256 开工实测 = `824bfc0e4bb48a8fcb3377900e3783beb72b2f6108fab4cad61e9bfe2b5cd9db`，与预注册一致，未 STOP；收工复测同值（未动）。
- 公开仓库基线：`82a18e777b73ee27ceffbec6d94b8a44c268de96`（index: rebind report v1.56），`baseline_commit` 按复算时点 HEAD 记录。
- 工作模式：完全离线，0 新模型调用、0 新产品运行；只读冻结档案（marker `launch-r1109`）与上游环 7 result.json；仅在本包目录新建 4 个文件，无 git 操作，未触碰任何既有文件。

## 交付物与校验值

| 文件 | SHA256 | 字节 |
|---|---|---|
| verify.py | `72314a17115bc9b1c8303d5ca59ae1d1af961cfb5c270948a0859335da0c320a` | 39842 |
| test_verify.py | `3e0e636f6bc3be9107889cf3b783b77a4731369fc8931ef9724cd6a2c28a7a2b` | 34413 |
| result.json | `69b67d7ec8690c42732c0aad077e604289adfea0c96d3bd0b1e6fb0bfbff7b72` | 40167 |
| README.md（冻结，未动） | `824bfc0e4bb48a8fcb3377900e3783beb72b2f6108fab4cad61e9bfe2b5cd9db` | 3849 |

## 命令（复现口径）

```bash
# 主检验（--root、--archive-root 必填；--output 独占创建，拒覆盖 exit2）
python3 verify.py --root <本仓库根> \
  --archive-root <冻结档案根，marker=launch-r1109> \
  --output result.json

# 测试套件（双档；真档案端到端用例需 env CODEX_META_SEM_ARCHIVE_ROOT="root1:root2"）
python3  test_verify.py
python3 -O test_verify.py
```

实际执行：CLI 以公开仓库根为 `--root`、以 `launch-r1109` 冻结档案为 `--archive-root` 生成包内 result.json；档案根的两个独立副本（root1:root2）各跑一次 CLI，stdout 与 result.json 逐字节一致（双根无路径泄漏）；`python3` 与 `python3 -O` 双档 stdout 经 `cmp` 逐字节一致；fresh `--output` 重跑与包内存储 result.json `cmp` 逐字节一致（fresh==stored）。

## 验收结果

- 双档（python3 / python3 -O）：stdout 逐字节一致，exit 0。
- 套件：30 个用例双档全绿（含真档案双根端到端 3 项；env 未设置时响亮 FAIL，不静默跳过）。
- 双根门控：两独立档案副本 CLI 输出逐字节一致；result.json 不含用户主目录路径与私有仓库名，档案仅以 `launch-r1109` marker 指代。
- 发布边界自查：result.json 中 `"text"` 字段值出现 0 次；content[].text 仅以布尔 + text_items 条数登记（合计 15 条消息，全零差异）；payload.id / create_time / turn_id 原值按冻结边界发布。

### V1–V5 关键值（摘自 result.json）

- 硬等 1 键路径：10/10 (case,role) 单元重提取值差路径集合与环 7 登记一致（PASS，漂移即 exit2）。
- 硬等 2 content[].text：15/15 单元跨 rep 逐字节零差异（PASS，破即 exit2）；15 个 rollout SHA256 全部与环 7 trace_bindings 一致。
- V1 create_time 解析：45/45 可解析，登记格式 `epoch_seconds×45`（首事件单位 `iso8601_utc×15`，解析为 epoch 秒后对齐比较；单位判定依据逐值登记于 value_matrix）。
- V2 时间差：15/15 槽全部 |create_time − rollout 首事件| ≤120s；worst=0.087858s（tb-cargo-plan r1，三消息 0.0762/0.0764/0.0879s）；全部 45 行差值 ≤0.088s，逐槽逐消息登记于 value_matrix。
- V3 turn_id：15 槽 within 模式全部 `equal`（同槽内三 developer/user 消息共享同一 turn_id）；跨槽模式一致=True；跨 rep 两两不交 5/5 case（各 case 三 rep 的 turn_id 集合互斥）。
- V4 payload.id：15/15 组三 rep 全异，全异率 100%。
- V5 稳定槽对（环 7 等字节对）：37 对 × 3 键 = 111 检查逐 rep 值互异 111/111（登记性断言，supported=True，不参与分支判定）。
- 全局分支：**B-METADATA-CONFIRMED**（V1 ∧ V2 15/15 ≥ 14 ∧ V4=100%）。

## 开发期异常与修正（如实）

1. verify.py 初版在 create_time 不可解析（登记性失败，`delta_seconds=None`）时 `max()` 比较崩溃（TypeError，exit 1 非受控）。修正为跳过 None 后取 worst——登记性失败不得使程序 fail-open 崩溃；由合成用例锁定（unparseable → V1 fail、该槽 V2 fail、branch B-MIXED、exit 0）。
2. 合成 fixture 初版三 rep 的 create_time 取同一值，导致槽内值差并集缺 create_time 路径、键路径硬等（应 PASS 的场景）误报 exit2——为测试装置缺陷而非 verify.py 缺陷，修正为 create_time 随 rep 递变。
3. 合成 fixture 初版给 developer 单元登记 k0/k1 两级，与真实环 7 登记形态（developer 仅 k0、user k0/k1）不符导致 V5 对齐范围 fail-closed，修正对齐真实结构。
4. 无网络、无私档写入、无既有文件改动；未发生 STOP 条件。

## 未动文件清单

`git status --porcelain` 收工时仅新增本包目录（未跟踪）：
`?? 4-打分细则/Codex元数据值语义-2026-11-16/`（内含 README.md 冻结原件 + 本包 4 个新文件）。
无修改、无删除、无暂存；公开仓库 HEAD 保持 `82a18e7`；未做任何 git 操作。
临时物仅写 /tmp（第二档案副本与 CLI 输出对照文件），未遗留于仓库。
