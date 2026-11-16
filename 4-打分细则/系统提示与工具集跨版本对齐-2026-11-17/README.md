# 系统提示与工具集跨版本对齐（2026-11-17，探索后冻结）

目的：把「请求侧最小捕获」run（2026-11-16/17，DSH 当前 build）与归档 r1109 批 15 个 DSH 槽（2026-11-09 build）的 **system 提示原文层** 与 **工具声明层** 精确对齐，归因两 build 间哪些字节属模型槽、哪些属 DSH 版本漂移、哪些属环境参数槽；并修正 [捕获与归档形态对齐](<../捕获与归档形态对齐-2026-11-16/README.md>) P2 的层别错配。纯公开派生算术，0 新运行、0 正文公开。

先验曝光（如实）：作者在冻结前已完成全部测量（私档 loop11/constants-probe.json），本协议为探索后冻结，非盲前预注册；数值先验不改变判定规则。

## 固定数据源（公开 pin，缺一即硬失败）
- [输入事件等长与同一性 evidence](<../输入事件等长与同一性-2026-11-16/evidence.json>) SHA256 `cc9089b18ca42f0357003d169ef9e01134e10e4b7881d66247f00d8bb8cb86b0`：15 槽任务标签与顺序（私档定位用）。
- [捕获包 README/verify/result](<../DSH请求侧最小捕获-2026-11-16/README.md>) SHA256 `a26c7ec7df5dc052ce708434a3cbfa2b50deca2745effa1b91a5877f279c04e7` / `de8abc83118f5063effa1165c67f078c2d5caaadd0e2da2bb4eb2a3dff0f0e28` / `3de57557fe7f3c74e6abc041e5181fc415595299b9678ed59d271f8abe596357`：capture req1 wire 层唯一来源（私档 `loop1/capture/requests/001.request.bin`）。
- [对齐包 README](<../捕获与归档形态对齐-2026-11-16/README.md>)：P2 修正对象。
- 本 README（自 pin）。

## 冻结定义
- 槽 system 原文 = 该槽 `session.v4.jsonl.zstd` 内唯一 `system/message` 事件全部 text 块串接（UTF-8 字节）。
- 路径槽归一 = 把 `Your working directory is \S+\.` 行内路径替换为 `<PATH>` 占位后取 SHA-256。
- 行级差分 = archive(bird r1) vs capture req1 system 原文按行 SequenceMatcher 非等块；分类规则：含 `powered by the` → `model_slot`；含 `working directory` → `path_line_relocated`；否则 `template_evolution`。
- 工具 canonical = `{description, parameters}` 规范 JSON（ensure_ascii=false、sort_keys、紧凑分隔符）的 UTF-8 字节；归档原生格式与 wire `function` 字段同名映射后比较。
- 对齐层别修正：对齐包 P2 曾把 capture **wire 原文** 字节（2593）与归档 **I 事件 canonical 信封** 字节（2535–2541，含 seq/time/type/data 包络）直接比较；两者不同层，其差值（约 +52B/+2.0%）不构成 wire 层陈述。本包给出同层（原文 vs 原文）结果。

## 主要终点（描述性判定，非通过/失败门，不外推因果）
- P1 归档 15 槽 system 原文分组数 = 5（每任务 3 rep 逐字节相等）；路径槽归一后模板数 = 1（模板 SHA 冻结）；原文字节 2265–2271（逐任务冻结）。
- P2 capture req1 system 原文 = 2593B；与归档 6 个非等块，分类 = {model_slot:1, template_evolution:4, path_line_relocated:1}；逐块字节差冻结且净和 = +323，与 2593−2270 完全对账。
- P3 工具集：归档 21 → capture 22；removed = {exit_plan_mode, interrupt_agent}，added = {skill, wait_agent, working_directory}；共同 19 中 canonical 相等 12、演进 7（逐工具 desc/params 相等性与字节数冻结）。
- P4 对齐层别修正登记：raw 2270–2271 vs 2593（+323，逐块可归因）替代原 +52B 陈述；对齐包其余判定（user 面同层、信封单列）不受影响。
- P5 归因边界：全部差异位于 **build 边界**（11/09 build → 11/16 build）；单 run 内 req1 跨 8 run 与跨日字节恒等（[重建验证](<../请求侧跨运行重建验证-2026-11-16/README.md>)、[跨日复核](<../请求侧跨日重建复核-2026-11-17/README.md>)）不受影响；跨版本比较必须钉住 build。

## 边界
两层均由 DSH 生成；版本漂移是 Harness 侧变化，非 provider/model 效应；模型槽行为（模型名/工具指引）随 provider 改变已在[跨模型捕获](<../请求侧跨模型捕获-2026-11-17/README.md>)单独量化；n=1 捕获；字节非 token/成本；不公开正文，仅哈希/长度/工具名/分类词。

## 验收
verify.py `--build-evidence` 由私档实算并硬等冻结常量后落 evidence；公开重放 `--evidence` 只校验 evidence 对冻结常量与 README pin 的一致性，不认证私档真实性；测试含常量篡改/hunk 篡改/工具名篡改/净和对账破坏/独占输出反例；非作者独审后整合 v1.69；旧包/旧分/冻结原件不动。
