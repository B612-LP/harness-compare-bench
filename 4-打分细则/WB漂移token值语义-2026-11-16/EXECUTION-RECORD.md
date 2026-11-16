# 执行记录 — WB漂移token值语义-2026-11-16

- 执行日期：2026-11-16（Asia/Shanghai）
- 角色：builder（wbsem-builder，由 lead 委派）；完全离线执行，无网络、无新产品/模型调用
- 基线 commit：`8b657e84c2a07436ca9a0ca62a3d55bad0abf964`（开工复核与收工复核一致）
- 预注册封印：README.md SHA256 =
  `b2e891a79eba14558b116627110dc4bd1f90db20e52700b0fb1b93f3b78643b6`（开工先验通过；收工复验未变）
- 执行模式：只读公开仓库与指定私档；只在本包目录新建 4 个文件；无 git 写操作；临时物只写 /tmp

## 命令

```
# 真档案复算（root1=私档根；--output 独占创建包内 result.json）
python3 verify.py --root <repo> --archive-root <archive-root> --output result.json
# 双档第二根：<archive-root> 的 /tmp 独立副本（cp -R），双档 stdout/result 逐字节一致
python3 verify.py --root <repo> --archive-root <archive-root>            # stdout 摘要
# 测试套件（合成 19 例 + 真档案 2 例，共 21 例，双档全绿）
WB_TOKEN_SEM_ARCHIVE_ROOT="<archive-root>:<tmp-copy>" python3 -m unittest test_verify -v
```

## 交付物（本包目录内 4 个新文件）

| 文件 | 字节数 | SHA256 |
|---|---|---|
| verify.py | 51380 | `862b7687ca45cd64c82b37430bba15cb0457dac48bbeea1e6f9f6c011f02f86b` |
| test_verify.py | 27319 | `cf48ba42ecf638ea999751b48bf6e71541f8fc8dcddaa6360e555d298a5db392` |
| result.json | 23708 | `d1b162edef5d6c1fe0e1e75fac04a3f5a36afdb7eac9745eee2383a740b7d2ae` |
| EXECUTION-RECORD.md | （本文件） | 见收工复测 |

README.md（冻结原件，3030 字节）未改动，SHA 复验一致。

## 裁定结果（值面）

- 双硬等全过：漂移 offsets（7+7）与 run 边界（7+7 条目×3 rep 全字段）均与两份参照逐项一致；
  信封 span 复算相符（close：dabstep-payments-10=6330、tb-cargo-plan=6286）。
- 时间戳：字段名 `timestamp`＝epoch 毫秒整数；固定 UTC 偏移 +08:00 从档案自身
  trace/collect-meta.json 的 `collected_at` 派生，6 槽一致。
- token（簇 5 字节，分隔字节 6/6 = `:`）：
  - dabstep-payments-10：r1=`03:24`、r2=`08:19`、r3=`12:46`
  - tb-cargo-plan：r1=`16:04`、r2=`21:23`、r3=`25:55`
- V1 = 不通过（5/6 匹配 ^([01]\d|2[0-3]):[0-5]\d$；`25:55` 非法小时；分隔字节 6/6 同一）。
- V2 = 不通过（可评 5/6；naive |Δ|≤1min 主断言 0/5；方向窗 [-1,+5]min 0/5）。
  差值分钟矩阵（signed；括号为午夜循环差）：
  - dabstep-payments-10：r1=−519（519）、r2=−229（229）、r3=+34（34）
  - tb-cargo-plan：r1=+228（228）、r2=+542（542）、r3=null（token 非法 HH:MM，不可评）
- V3 = 6 处孤立位单数字登记（信封内 2 + 信封外 1 × 2 case）：逐 rep `1/2/3`，同 rep 6 处一致、
  跨 rep 相异；按冻结仅登记不判语义。
- 定长同格式 = 成立（长度集合 [5]、类序列 DD?DD、分隔字节全同）。
- 分支（§3 字面）：**B-COUNTER-OTHER**（V1 破但 6 token 定长同格式 ⇒ 时钟类否证），exit 0。
- 超出冻结判据的定性披露 3 项（不改变裁定、不发布秒级值）：token 值面与 |Δ|∈[34,542]；
  6 token 逐 rep 字典序严格递增；孤立位『逐 rep 相异、同 rep 一致』与 rep 序号类候选相容。

## 异常与修正（测试期发现，均已修入交付物）

1. run 边界硬等的两侧键形不对称（参照投影仅含 run 六字段，复算侧对非数字 offset 另带
   `drift_byte_class`）导致合成档案误报硬等失败；改为两侧投影到同一规范键集
   （RUN_FIELDS_CANON）再逐键比较。真档案复算结果不受影响（复跑双硬等仍全过）。
2. stdout 摘要头原用 `PASS` 字样，对裁定为 B-INDETERMINATE/exit2 的合成场景构成自相矛盾
   表述；改为中性 `RESULT`。
3. 测试自身的三处修正：场景表 `(day, hh, mm)` 元组笔误（09:xx 写成 hh=0）；
   「首消息非 user」用例重排后需同步给 user 消息补单调时间戳；
   值边界「无日期」断言需先剔除包名/参照路径标签中的包日期 `2026-11-16`（非消息面）。

## 自查（六项）

1. 双档 stdout 逐字节一致；双档 result.json 逐字节一致 ✅
2. fresh == stored（--output 重跑与包内 result.json 逐字节一致）✅
3. 测试套件双档全绿（21 tests，含真档案端到端双根门控）✅
4. git status 仅本包目录 4 个新增文件（`?? 4-打分细则/WB漂移token值语义-2026-11-16/`）✅
5. README SHA 未变（= 冻结值）✅
6. 值发布边界自查：发布仅含 token 5 字节值、分隔字节值、孤立位单数字、HH:MM（分钟精度）
   与字段名/换算规则；result.json 无秒级/毫秒/日期时刻串、无字母序列与多字节切片、
   无任务正文、无私有绝对路径（值边界断言在 test_verify.py 内固化）✅

## 未动文件清单

- 公开仓库所有既有文件零改动（git status 仅本包目录新增；README.md SHA 复验一致）。
- 私档（archive-root 及其下 6 槽、两份参照包）零改动，只读。
- 临时物（已存在于 /tmp，可随时清理）：`/tmp/wbsem-smoke1.txt`、`/tmp/wbsem-gen.txt`、
  `/tmp/wbsem-fresh1.txt`、`/tmp/wbsem-fresh2.txt`、`/tmp/wbsem-fresh-result.json`、
  `/tmp/wbsem-archive2/`（双档第二根）、`/tmp/wbsem-test-*`（unittest 临时目录，已自清理）。

## 范围声明

本记录不包含任何任务正文切片；`<archive-root>` 等私有路径一律以占位符表示。
本包裁定基于冻结 README §2 值面判据；超出判据的观察仅作定性披露，检验其中任何候选
语义须另立预注册。
