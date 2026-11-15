# EXECUTION-RECORD — 豆包输出侧结构分解-2026-11-16（builder 收据）

- 执行时刻：2026-11-16T07:06+08:00 前后（单次构建，无重试批次）
- 预注册：本包 [README.md](<README.md>)（冻结 2026-11-16T06:56+08:00）
  - SHA256 = `aabe1f09ab2710e6a95d7efa4e9a497c3ccc40ba09df78b4e24075a0e187ec5e`（开工已验、收尾复验一致）
- baseline_commit：`737330c60b8a9842efaf7f03b5c96f5ab04892c6`（main，构建时 HEAD；由 verify.py 对 `--root` 只读 `git rev-parse HEAD` 取得，无任何 git 写操作）
- 分支：`main`；`git status --porcelain` 仅本包新增 4 文件（verify.py / test_verify.py / result.json / EXECUTION-RECORD.md），无既有文件改动。

## 命令（双档）

```bash
# 档一：指定私档根（记录中以 <archive-root> 占位；语义 = .../bw-retest/doubao）
python3 verify.py --root <repo> --archive-root <archive-root> --output result.json
# 档二：同一档案内容在 /tmp 的完整副本（临时物），用于双档一致性
python3 verify.py --root <repo> --archive-root /tmp/doubao-archive-copy > /tmp/out2.txt
# 套件（双档全绿；未设 env 时真档案用例响亮 FAIL，拒绝静默跳过）
DOUBAO_STRUCT_ARCHIVE_ROOT=<archive-root> python3 test_verify.py     # 25 tests OK
DOUBAO_STRUCT_ARCHIVE_ROOT=/tmp/doubao-archive-copy python3 test_verify.py  # 25 tests OK
python3 test_verify.py                                               # 22 run, gated class ERROR（预期门控行为）
```

- 双档 stdout 逐字节一致：`cmp` 通过（两侧 sha256 均 `b4529aad…`，档二与档一同内容）。
- fresh==stored：终版 result.json 由 verify.py `--output` 独占创建后，套件 `test_22_fresh_result_equals_stored` 双档通过（逐字节一致）。
- 无网络、无新产品/模型调用；仅 stdlib；不硬编码勘察计数值（verify.py 内仅冻结 README SHA256 常量与硬等期望值两处预注册常量）。

## 逐 rep 登记值（复算）vs 勘察基线

| rep | 行数 | assistant | tool | tool_call | 纯assistant轮 | result字节 | 复算=勘察 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| r1 | 45 | 18 | 27 | 27 | 0 | 40282 | 全符 |
| r2 | 37 | 16 | 21 | 21 | 1 | 36111 | 全符 |
| r3 | 44 | 19 | 25 | 25 | 1 | 41900 | 全符 |

- r3 工具集缺 Write/task_create/task_update：复算确认（r3 仅 Bash/Read/Edit/present_files）。
- 逐工具 canonical JSON 字节（function 口径 = `json.dumps(fn, sort_keys=True, ensure_ascii=False, separators=(',',':'))` UTF-8）总和：r1=26924、r2=18396、r3=21281（按 name 分列见 result.json `per_rep.*.function_canonical_bytes_by_name`）。
- tool_result content 字节口径：str 按 UTF-8（本批三 rep 全部为 str，types={"str": n}）；非 str 将按 canonical JSON 计并登记类型名。

## 序列比对与分支判定

- 序列长：r1=54、r2=42、r3=50（元素=工具名或 `T`）。
- 两两 LCP：r1-r2=16、r1-r3=17、r2-r3=16；三方 LCP=16。
- 首分岔 index=16；分岔处元素：r1=`Read`、r2=`Bash`、r3=`Read`（r2 先转 Bash，r1/r3 继续 Read）。
- min(序列长)=42，阈值=21.0；16 < 21.0 ⇒ **H-EARLY-DIVERGENCE**（结构波动早期分岔型；与 bird §4.34 同判据形式的同型性观察，非因果、非跨产品规律）。

## 计数硬等

- 从公开 `4-打分细则/预注册复测选题-2026-11-08/复测登记-r1109.md` §③ 解析「豆包 × tb」行：reward=[0, 0, 0]、weighted=[81.48, 70.37, 81.48]——与预注册期望一致，**PASSED**（Decimal 精确比较；解析失败/漂移均 exit2）。
- app 版本事实（2.34.12→2.35.19、r1 2400s 帽）仅注记于 result.json `notes`，不参与判定。

## 异常与实现决策（如实登记）

1. **行 schema 为勘察注记的超集**：assistant 行实测可含 `content` 键（keys ⊆ {role, tool_calls, content}；纯 assistant 行= {role, content}）；tool 行恰 {role, content, tool_call_id}；tool_calls 元素恰 {function, id, type}；function 恰含 name、可选 arguments。verify.py 按超集校验、未登记键/role 即 exit2；content 值一律不读取。
2. **前缀终止边界的 `<END>` 哨兵**：套件暴露当某 rep 序列恰终止于三方 LCP 边界（为其余序列前缀）时该侧无分岔元素，verify.py 以结构标识 `<END>` 登记该侧（真档案未触发此分支，r1/r2/r3 均有实元素）。
3. 硬等解析以「§③ 标题截断 + 恰 1 条 豆包×tb 行 + reward/weighted 各 3 个数值 token」为结构门；防篡改用例（漂移、行破坏）均实测 exit2。

## 内容无关声明与隐私扫描

- stdout 与 result.json 只含计数、字节数、工具名标识符与槽位名；`function.arguments` 与 tool/assistant content 值零落盘；trajectory 路径以 `<agent>` 占位（不含会话/代理目录 id）；无绝对路径、无时间戳（保证双档与重跑逐字节一致）。
- 隐私扫描（grep `bench-private`、`/Users/`、代理目录 id、`launch-r1109`、`until22`）对 4 个包文件与 stdout 全部零命中。

## 未动文件清单

- 本包 `README.md`：未改动（SHA256 复验 = 冻结值，见上）。
- 公开树其余全部文件（含 `4-打分细则/预注册复测选题-2026-11-08/复测登记-r1109.md`、3-表现现场、CHANGELOG 等）：未改动。
- 档案（`--archive-root` 及其下全部 trajectory.jsonl）：只读；/tmp 副本为临时物，档案本体无写。
- 未执行任何 git 写操作（status/rev-parse 只读查询除外）。

## 交付物 SHA256 / 字节（本记录写入前）

| 文件 | SHA256 | 字节 |
| --- | --- | --- |
| verify.py | 见收尾自查（下方「终验」节如有更新以终验为准） | — |
| test_verify.py | 同上 | — |
| result.json | `eab12e0e78a93d9aa0acb34536031f7e03ef16c4f28566e88811c4191e9ffc55`（终版复算后不再变动） | 7990 |
| EXECUTION-RECORD.md | 本文件 | — |

终版四文件 SHA256/字节以 RUN-RECEIPT（仓外）与最终消息为准；result.json 自终版复算起未被再次改动。
