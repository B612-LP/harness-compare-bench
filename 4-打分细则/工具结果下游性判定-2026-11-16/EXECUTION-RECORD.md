# EXECUTION-RECORD — 工具结果下游性判定-2026-11-16

预注册包验证器构建与结果生成记录。本文件由 builder 在交付时一次性写入；预注册页
README.md 冻结不动（SHA256 钉定见下）。隐私纪律：本包不含任何私有绝对路径、工具参数
或工具输出内容；命令中的档案根以占位符表示。

## 钉定自验（开工即验）

- 预注册 README.md SHA256 = `df7e86497676da79fe238824a5178dfd9dd8fc91eef0d8e9979d89245f38a3dd`
  （开工自验通过，交付后复查未变）。
- 仓库 HEAD（运行时解析，无子进程 git）= `ad7ed0a3b48b5a419a39d93ae28bf19f9ec38dcd`。
- R3 参考包钉定：`R3不稳定来源分解-2026-11-16/result.json`
  SHA256 = `8b03be40cb53f0a562d8b6b8a006a8e97d1733d8a9da15df8dfc67b0fbb83188`；
  `R3不稳定来源分解-2026-11-16/verify.py`
  SHA256 = `32607970570d086797562fd1805a88e0a4b9fcfc1afee67d86e7a5618020bc7b`；
  R3 包自身 baseline = `4b5aaecc04a11fd47a04af47abdcb70a520657d7`。

## 数据源（只读）

私有 Codex trace 档案根以 `--archive-root` / 环境变量 `D_DOWNSTREAM_ARCHIVE_ROOT` 传入
（until22-20261109/launch-r1109；路径不写入本包）。五槽轨迹按 ARCHIVE_SOURCES 钉定
（archive-relative 路径与 SHA256，均与 R3 result.json 的 trace_bindings 运行时双向对账）：

| slot | 轨迹（codex/runs/<slot>/agent-session/ 下） | sha256 |
|---|---|---|
| codex__exercism-py-6__r1 | rollout-2026-11-09T13-38-41-01a1bed0-dc97-7b41-b228-5d6153a1118c.jsonl | e355baeb2cfcf644a5f9cf6e9017011a78d95e2050a11ce2d37acfc081639cac |
| codex__exercism-py-6__r2 | rollout-2026-11-09T13-39-10-01a1bed1-4f76-72f1-9b82-6a08a5a4e671.jsonl | a866cd55cc64db6b5ad69436bec7b1c3124d406d42541137bc1077ebd0412796 |
| codex__exercism-py-6__r3 | rollout-2026-11-09T13-39-33-01a1bed1-a937-7a62-a054-84041d4c6f33.jsonl | 0e64e0c436a0f24a5cd51cbabcf2425b4da559781d298e4447c8bf0db7f12c49 |
| codex__dabstep-payments-10__r2 | rollout-2026-11-09T13-27-41-01a1bec6-c9ba-7813-8188-781d6e4d7396.jsonl | e5ee7b2bdd44d0fbedf9ff55d27edd4cdb0db6457ba0335a6331d387b71457a9 |
| codex__dabstep-payments-10__r3 | rollout-2026-11-09T13-33-42-01a1becc-4bf9-79a3-a988-6c97b6ccba16.jsonl | be045ce4457d98ac8934cfcaddfc0a1759ee3ce6cce79139822cac7490b66c2e |

## 命令（占位符；REPO_ROOT=公开仓库根，ARCHIVE_ROOT=上述档案根）

1. `python3 <PKG>/verify.py --root <REPO_ROOT> --archive-root <ARCHIVE_ROOT>` → stdout 人类摘要，exit 0。
2. `python3 <PKG>/verify.py --root <REPO_ROOT> --archive-root <ARCHIVE_ROOT> --output <PKG>/result.json`
   → 独占创建生成正式结果（GenExit=0）。
3. fresh 复跑（python3 与 python3 -O 双档，--output 写 /tmp 临时文件）→ 与存储 result.json
   逐字节一致（cmp 通过，双档一致）。
4. `python3 -m unittest test_verify` 与 `python3 -O -m unittest test_verify`（在包目录内，
   设 D_DOWNSTREAM_ARCHIVE_ROOT）→ 20/20 双档全绿。

## R3 硬等结果（重算 == 冻结常量 == R3 result.json 文件值，五槽全过）

| slot | r3_total_bytes | function_call / function_call_output / message / reasoning |
|---|---|---|
| exercism r1 | 91495 | 10475 / 68188 / 7239 / 5593 |
| exercism r2 | 60064 | 6318 / 40782 / 7246 / 5718 |
| exercism r3 | 80553 | 7174 / 58562 / 7200 / 7617 |
| dabstep r2 | 334724 | 65049 / 133869 / 10617 / 125189 |
| dabstep r3 | 286469 | 52273 / 105274 / 13625 / 115297 |

槽内联结全干净：15/15、9/9、10/10、43/43、35/35（0 orphan、0 一对多歧义、0 缺 call_id）。

## 联结结构与判定（核心发现）

- call_id 全值形如 `call_<两位序号>_<随机后缀>`：序号逐轮重置、后缀逐运行随机 → 跨槽
  全值 call_id 零交集（4 对 cross_slot_call_id_intersection 均为 0）。
- 预注册唯一联结键是 call_id 全值；位置对齐与 call_id 前缀部分匹配都属于「猜测配对」，
  被冻结条款禁止 → 不做。全部 output 项如实记 unlinked（24/25/19/78，共 146）。
- 触发预注册 §3 反证分支「联结面与预期不符」：判定 **D-STRUCTURAL-DEGRADED**
  （结构降级，如实登记联结结构，不给下游性结论，downstream_conclusion_issued=false）。
- 逐对三分类计数（outputs_differ_calls_differ / outputs_differ_calls_same / outputs_same /
  unlinked）：exercism_r1vsr2 = 0/0/0/24；exercism_r1vsr3 = 0/0/0/25；
  exercism_r2vsr3 = 0/0/0/19；dabstep_r2vsr3 = 0/0/0/78。calls_same_items = 空。
- 含义：本预注册版本无法在检测面裁定下游性/工具非确定性；如需序列对应判定，须先发布
  新预注册版本（显式定义跨运行对应规则），不在本包内放宽。

## 开发期异常（如实记录）

- 测试首跑 4 处失败，两处根因均已修正并复跑全绿：
  1) 合成分类测试初稿按「每单元 1 项」预期，与冻结口径「联结单元两侧各计一项」（每单元
     2 项）不符 → 修正测试预期（实现未改）；
  2) 字节翻转防篡改测试用 symlink 建假档案根，`.resolve()` 跟随符号链接触发路径逃逸
     fail-closed（行为正确）→ 改用硬链接构造。
- 无 STOP：未发现冻结条款冲突；实现严格按预注册联结/分类/判定/内容无关条款执行，
  「联结面与预期不符」分支本身是预注册明文反证路径。

## 边界与未动文件

- 新增文件仅本包 4 个：verify.py、test_verify.py、result.json、EXECUTION-RECORD.md。
- 未修改任何既有文件（含 README.md 冻结页）；无 git 操作（无 add/commit/checkout）；
  未联网；无新产品/模型调用；临时产物只写 /tmp。
- 测试门控：真档案端到端测试经环境变量 `D_DOWNSTREAM_ARCHIVE_ROOT` 启用，未设置时
  loudly FAIL（拒绝静默跳过）。
- 本验证不认证私档原件真实性，只证明内容无关算术与源钉定一致性；canonical JSON 字节
  非 wire 字节、token 或成本；不回写 R3 / v1.1 任何结论或门判定。
