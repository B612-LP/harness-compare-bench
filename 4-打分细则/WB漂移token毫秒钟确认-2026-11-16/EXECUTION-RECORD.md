# 执行记录 — WB漂移token毫秒钟确认-2026-11-16（builder）

- 日期：2026-11-16（ Asia/Shanghai ）
- 分支：`main`；开工 HEAD：`8b657e8`（8b657e84c2a07436ca9a0ca62a3d55bad0abf964，符合任务「8b657e8 或后代」前置）；**收尾 HEAD：`dc2ac23`**（执行期间同行先后落两提交 `16b704c`（WB 漂移 token 值语义裁决收口）与 `dc2ac23`（结论复核索引绑定行），均不触本包 4 文件）；result.json 的 `baseline_commit=dc2ac23b31bb367637d2262824f02cc132dc74a9`（登记语义=复算执行时真实 HEAD，最终 --output 生成时点取值；与既有各环 result.json 同一口径）。
- 模式：完全离线复算。无网络、无新产品/模型调用；只读公开仓库与冻结判据指定的私档；仅在包目录内新建 4 个文件；无任何 git 写操作；临时物仅写 /tmp。

## 一、开工检查（全部通过，无 STOP）

- `git log`：HEAD=8b657e8，符合任务前提交付条件。
- 预注册 README 冻结封印：SHA256 `b28942fa8943a55f4eddba5434a88f92387fd5bf8c69a80b921418b6f610e27d`，与预注册值逐字节一致（开工验证 + 收尾复验均通过）。
- 同行包 `4-打分细则/WB漂移token值语义-2026-11-16/` 已在工区，按任务约定未读取后改动、未触碰。

## 二、实现与命令

按冻结 README §2/§3 逐条实现：

1. `verify.py`：`--root`（公开仓库根）与 `--archive-root`（档案根）必填；`--output` 独占创建（目标已存在即 exit2）；双硬等（环 11 offsets 全集、环 15 run 边界投影键集）fail-closed；分支判定按 §3 字面（含 REFUTED→exit2）；stdout 为确定性摘要（无路径、无时间戳、无毫秒、无日期、无任务正文）。
2. `test_verify.py`：unittest 24 例；真档案端到端用例经 env `WB_TOKEN_CLOCK_ARCHIVE_ROOT`（`root1:root2`，os.pathsep 分隔双根）门控，未设置时响亮 FAIL；合成场景覆盖 mm:ss 正/反例（59:59 过、60:00 拒、99:99 拒）、±1s 边界（0/+1/−1 过、+2 拒→PARTIAL）、25:55 过 V1′（区别环 17 旧正则）、README SHA 防篡改、双硬等防篡改、`--output` 拒绝覆盖等。
3. `result.json`：由 `--output` 生成后入库；CLI 重跑逐字节一致（fresh==stored 由套件断言）。

实际执行命令（仓库根）：

```bash
python3 4-打分细则/WB漂移token毫秒钟确认-2026-11-16/verify.py \
  --root <公开仓库根> \
  --archive-root <archive-root> \
  --output 4-打分细则/WB漂移token毫秒钟确认-2026-11-16/result.json
```

套件（包目录内）：

```bash
WB_TOKEN_CLOCK_ARCHIVE_ROOT="<archive-root>:/tmp/<第二副本>" python3 -m unittest test_verify -v
# Ran 24 tests ... OK（双档全绿；未设 env 时仅真档案 2 例按设计响亮 FAIL，其余 22 例绿）
```

## 三、结果摘要

- 双硬等：offsets（dabstep-payments-10: 7、tb-cargo-plan: 7）与 run 边界 entries（7、7）均与参照逐字节一致 → `true/true`。
- token（5 字节 = 两组各 2 位数字 run + 中间 1 分隔字节 `:`）：dab `03:24/08:19/12:46`，tb `16:04/21:23/25:55`。
- V1′：6/6 匹配 `^([0-5]\d):([0-5]\d)$`（25:55 合法——环 17 旧正则的误判口径在此修正登记，环 17 冻结判定不改写）。
- V2′ 秒差矩阵（|token−首消息|，首消息时刻截断整秒）：

| 槽 | r1 | r2 | r3 |
|---|---|---|---|
| dabstep-payments-10 | 0 | +1 | 0 |
| tb-cargo-plan | 0 | +1 | 0 |

全 6 处 |Δ|≤1s；边界归属：r1=exact_0s、r2=boundary_+1s、r3=exact_0s（两组同型）。
- V3′：6/6（token 前 2 位 = 首消息「分」）。
- 首/末消息 HH:MM:SS（元数据面）：dab r1 12:03:24/12:08:07、r2 12:08:18/12:12:35、r3 12:12:46/12:15:52；tb r1 12:16:04/12:21:13、r2 12:21:22/12:25:44、r3 12:25:55/12:31:34。
- 分支：`B-MMSS-CONFIRMED-POSTHOC`，exit=0。posthoc 声明已写入 result.json（假设来源=环 17 Lead 验证期观察；非独立预测；证据等级=事后确认）。

## 四、异常与处置

1. 合成场景首版 token 数字跨 rep 相同（如三 rep 均为 `10:xx`），导致部分字节位退出三对差异并集、簇 run 组数=1，触发结构防篡改。处置：重设场景使每个 token 数字位跨 rep 至少一对相异（例：`03:20/15:11/28:58`），符合环 15 DD?DD 结构前提。属测试数据构造问题，非 verify.py 判定缺陷。
2. `--root` 参数语义首次误传（传了档案根而非公开仓库根），README 封印检查按设计 exit2 拦截；改为仓库根后通过。fail-closed 行为符合预期，非缺陷。
3. 执行中途 HEAD 因同行两提交前移（8b657e8→dc2ac23）：`baseline_commit` 为执行时 HEAD 登记语义，首版 result.json 生成于 8b657e8 时点，套件 fresh==stored 断言随即失败（仅该字段差异）；处置：删除首版 result.json（本包自有新文件，非既有文件）后按最终 HEAD 重新 `--output` 独占生成，全套件 24 例双档重跑全绿。「重跑逐字节一致」性质=在 HEAD 未变的前提下成立；后续新提交会使 baseline_commit 变化，属登记语义而非判定漂移（各环既有 result.json 同口径）。
4. 其余无异常；双档 stdout 逐字节一致、双跑一致、fresh==stored 全部通过。

## 五、未动文件清单（自查）

- 未改动任何既有文件：`git status --porcelain` 仅本包 4 个新增未跟踪文件（README.md 为开工前已存在的冻结件，亦未改动、SHA 复验一致）。
- 同行包 `4-打分细则/WB漂移token值语义-2026-11-16/` 未触碰。
- 无 git 写操作（无 add/commit/branch/checkout）；临时物仅在 /tmp（探测脚本与第二档案根副本）。

## 六、交付物（包目录 4 新文件）

| 文件 | 说明 |
|---|---|
| `verify.py` | 复算脚本（判据、双硬等、V1′/V2′/V3′、分支、发布边界） |
| `test_verify.py` | unittest 24 例（合成 + CLI 守卫 + 双根真档案端到端） |
| `result.json` | `--output` 生成入库（schema=wb-token-clock-v1） |
| `EXECUTION-RECORD.md` | 本文件 |

发布边界自查：result.json 与 stdout 仅含 token 5 字节值、逐处秒差整数、逐槽首/末消息 HH:MM:SS（秒精度墙钟）与结构登记（offset/run 边界/字节类/字段名）；零任务正文、零字母序列、零多字节切片、零消息文本、零毫秒级时刻、零日期、零私有绝对路径；档案根一律以 `<archive-root>` 占位。
