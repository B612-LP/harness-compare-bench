# r1025 候选题库 · 建造规范（builder 必读）

> 目标：把已选定的公开评测题/自建题，造成本仓**五件套**形态的候选用例；造完由 lead 用 Codex + DSH 两个 CLI 实测，通过再晋升进 `2-用例/`。
> 本目录 `3-表现现场/r1025-candidates/` 是 staging：你只写 `cases/<你的 case-id>/` 与 `selftest/<case-id>.log`，**不碰仓库其它任何文件**。

## 1. 用例目录（对齐现有 v0.3 形态）

参考模板：`2-用例/corpus-squeeze/`（含 `instruction.md` / `spec.md` / `truth.json` / `checker.py` / `inputs/` / `solution/`）。你必须产出：

```
cases/<case-id>/
  instruction.md    # 任务书（中文，自包含，不泄露评分点；路径一律相对运行目录，如 inputs/xxx）
  spec.md           # 判分规格：定位/判分模式/观察项表(权重)/运行目录约定/负例清单/来源与许可证
  truth.json        # 期望值 + 输入 SHA-256 + 来源/许可证/版本；checker 启动时交叉校验
  checker.py        # 唯一正式判分入口，见 §2
  inputs/           # 拷进 run_dir 的素材（agent 可见）
  solution/         # oracle 产物（oracle 回归用；不拷进 run_dir）
  task.toml         # Harbor 元数据：name/version/description/时间上限/artifacts 列表
  case.json         # staging 运行器用：{"inputs":[["inputs","inputs"]],"timeout_s":1800}
  selftest.stdout.txt  # `python3 checker.py --selftest` 的原始输出（证据）
```

## 2. checker 契约（硬要求）

```
python3 checker.py <run_dir> [--json]     # 正式判分：只打印一行 JSON 到 stdout
python3 checker.py --selftest             # 自测：内部跑 nop/oracle/负例，全过 exit 0，否则 exit 2
```

正式判分输出（**最后一行**，`--json` 时只打这一行）：

```json
{"case":"<case-id>","reward":0或1,"weighted":0-100,"checks":[{"id":"...","pass":true/false,"note":"..."}]}
```

规则：
- `BINARY=True`：headline 二值；多题计分题按「达标线」给 reward（阈值写进 `truth.json`，如 0.8），`weighted` = 实际得分率×100。
- **只读 run_dir 产物**，绝不联网、不装包、不读 `/tmp` 或仓库里的其他路径；truth 与 gold 只从 `checker.py` 同目录读。
- **三重守卫**：① `truth.json` 里 `input_sha256` 与实际 `inputs/` 不符 → 直接 ERROR exit 2；② run_dir 里若带输入副本且被改 → reward=0（记 `input_integrity` fail）；③ truth 与 checker 常量不一致 → ERROR。
- **禁止 LLM judge**；判分必须是确定性程序。
- 仅用 Python 标准库（`sqlite3`/`unittest`/`subprocess`/`hashlib`/`json` 都算）。
- `--selftest` 必须覆盖：
  1. **nop**：空 run_dir → reward 0；
  2. **oracle**：把 `solution/` 产物拷进临时 run_dir → reward **1**；
  3. **≥6 组近正确负例**：每组构造一种「接近正确但违规」的产物，必须判 0（如漏一题 / 格式错 / 改输入 / 多写 / 少写 / 阈值边界 / 用错列）；
  4. 守卫项：篡改 `inputs/` 后 → 0 或 ERROR。
  自测用 `tempfile.TemporaryDirectory()`，不得污染仓库。

## 3. staging 运行器约定

`case.json` 固定：`{"inputs": [["inputs","inputs"]], "timeout_s": <秒>}` —— 运行器会把 `cases/<id>/inputs/` 整个拷成 `run_dir/inputs/`。所以 `instruction.md` 里路径一律写 `inputs/...`。

## 4. 环境约束（五款产品同起跑线）

- agent 侧只承诺：`python3`（系统 3.9，**只有标准库**）+ 基础 shell；**不得要求 pandas/numpy/openpyxl/pytest**。
- 判分器本身也只用标准库（判分机是同一台 Mac，但不要依赖第三方库）。
- 输入体积目标 ≤ 25MB/例；若超，给裁剪方案并写进 spec。
- 桌面三款（元宝/豆包）要能做：任务只能要求「读文件 + 写文件」，不要求真终端；题面允许「直接计算/手写产物，不必真的执行」。

## 5. 版权与来源

- `truth.json` 与 `spec.md` 必须写：来源名 + URL + 许可证 + 读取日期 + 是否改写。
- 第三方题面**不要整段照抄**：用自己的话重写题面（保留关键约束与输入输出格式），数据可原样使用并署名。
- 判分器若移植自官方（DABstep scorer / LCB judge / Exercism tests），在文件头注明来源与许可证。

## 6. 自测与回报

跑 `python3 checker.py --selftest`，把输出存到 `selftest/<case-id>.log` 与 `cases/<case-id>/selftest.stdout.txt`。然后把下面这段发给 lead：

```
case-id:
一句话定位:
来源/许可证:
agent 侧依赖:
判分: 观察项 + 权重 + 达标线
selftest: nop=0? oracle=1? 负例 N/ N 全 0?
体积: 输入 X MB / 总 Y MB
未决问题:
```

时间盒 **50 分钟**。禁止：跑 codex/dsh、改仓库其他目录、上网下新数据（需要新数据先问 lead）。