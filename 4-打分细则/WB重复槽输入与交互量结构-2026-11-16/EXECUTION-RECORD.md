# EXECUTION-RECORD — WB重复槽输入与交互量结构-2026-11-16（builder 执行记录）

本文件是执行记录，不属于预注册内容；预注册以同目录 README.md 为准（冻结，未改动）。
命令中的 `<archive-root>` 为 WorkBuddy 复测档根占位符（其下含 `runs/` 与
`evidence-tools/grading/`），按隐私纪律不写入本包；真实路径只存在于私有运行收据。

## 1. 环境

- 公开仓库根：本仓库（HEAD = `f14a5150c0218f4e74d23c82132941172b7fc386`，运行时 git 读取）。
- 预注册 README.md SHA256 = `2957a69b066d6c4c73c66372e2661244ebf80f93436a9f2c6cc99712096b3584`（开工前自验一致，收尾复查一致）。
- 档案布局（`--archive-root` 契约）：`runs/<slot>/trace/<session-uuid>.jsonl`（每槽恰 1 个 session jsonl）＋ `evidence-tools/grading/<slot>/execution.json`（判分现场）。
- 完全离线执行；除只读仓库与只读档案、包内 4 个新文件、私有收据与 /tmp 临时产物外，未写任何文件，未做 git 写操作。

## 2. 钉定常量的来源（fail-closed 设计）

预注册不预置槽级事实；`verify.py` 中的 `DEFAULT_PINS` 由建包人从档案读定后钉入：
- 每槽 trace 文件名（session uuid）、trace SHA256、trace 字节数；
- 每槽唯一 role=user 消息文本的 SHA256 与字节数（内容本身不入包）；
- 每槽 grading 文件 SHA256、case/rep/session_id 交叉核验、reward(int)/weighted(float) 与公开页
  `3-表现现场/r1109-bw-retest/README.md` 表格常量硬等（类型+数值双等，bool 排除）。
canonical 投影顶层剔除键集按实际档案读定：`__codebuddyLocal, _meta, callId, cwd, id,
messageId, parentId, providerData, sessionId, timestamp`（记录于 result.json
`canonical_projection` 节）。

## 3. 命令（复算入口）

```bash
# 验证（人类摘要到 stdout；exit 0=PASS，exit 2=fail-closed）
python3 verify.py --root <repo> --archive-root <archive-root>

# 写完整 result.json（独占创建；目标已存在则拒改 exit 2）
python3 verify.py --root <repo> --archive-root <archive-root> --output result.json

# 测试套件（22 个用例；真档案端到端经 WB_STRUCT_ARCHIVE_ROOT 门控，
# 未设该环境变量时真档案测试 loudly FAIL，拒绝静默跳过）
python3  test_verify.py
python3 -O test_verify.py
```

## 4. 执行结果摘要

- 真档案验证：PASS（exit 0）。W1 全局分支 = `B-W1-TASK-DRIFT`，两组均
  `w1_task_text_drift`（信封外差异存在）；W3 六槽硬等 6/6 OK；fc==fcr 全部相等；
  W2 描述性计数详见包内 result.json。
- 双档一致性：`python3` 与 `python3 -O` 的 stdout 逐字节一致（cmp 实测）。
- fresh `--output` 重跑与包内存储 result.json 逐字节一致（cmp 实测，并经测试套件复验）。
- 测试套件：22 tests，`python3` 与 `python3 -O` 双档全绿（OK），双档日志逐行一致。

## 5. 执行中的异常与修正（如实记录）

1. 首轮测试套件 6 failures + 2 errors，两组根因，均已修正后全绿：
   - 测试侧缺陷：合成档案用例未把合成 pins 注入 `run_verification`（落到冻结
     DEFAULT_PINS 上误报文件名不符）；改为 `VerifyTestBase.run_verify` 默认注入合成 pins。
   - 实现侧语义排序偏差：`classify_w1_group` 原先先做信封缺失/未闭合登记再判全同，
     与冻结定义「全同→w1_stable；信封定位仅在『有差异』时参与」不符；已重排为
     全同判定优先，未闭合信封（结构登记）优先于标记缺失（登记不归类）。真实档案
     判定结果不受该修正影响（真档案三 rep 文本互异且信封闭合完整，仍为
     w1_task_text_drift）。
2. 无 STOP 事件：预注册预期与档案实况全部相符（每槽恰 1 个 session jsonl、
   role=user 恰 1 条、事件型集合符合、W3 归档判分与公开页常量六槽全部硬等一致）。

## 6. 文件清单与 SHA256（本记录自身的 SHA 不自指，见私有收据）

| 文件 | 说明 |
|---|---|
| `verify.py` | 验证器（CLI；fail-closed；冻结 DEFAULT_PINS） |
| `test_verify.py` | 22 用例测试套件（含门控真档案端到端） |
| `result.json` | 正式结果（由 verify.py --output 生成，fresh 重跑逐字节同） |
| `EXECUTION-RECORD.md` | 本记录 |

各文件最终 SHA256 与字节数以构建完成时的实际值为准，登记于私有运行收据与汇报；
本包内不含绝对私档路径、不含信封/任务文本内容、不含差异字节值（只含偏移、计数、
span、字节数与 SHA）。

## 7. 未动文件清单（声明）

- 预注册 `README.md`：未改动（SHA256 开工前与收尾两次核验一致）。
- 包目录外所有既有文件：未改动、未删除；无 git add/commit/push 等写操作。
- 新建文件仅上述 4 个；临时产物只写 /tmp 并已清理。
