# 第三周独立复核入口（2026-10-29）

本目录保存实际复核命令、退出码、原始输出和独立审查意见。复核者必须区分：代码检查、自测、历史证据复算、重新调用模型的实验重现。前三者不计新增受评产品运行；无模型认证时离线复核不能声称重跑过在线实验。

## 验收约束

1. 从公开仓库文件构建干净副本，不读取 `~/bench-automation`、`~/bench-workspaces`、用户登录态或私有凭据；不使用旧工作区隐式补齐证据。
2. 原历史总账、题库、现场和 Changelog 保持原字节。新增判定与原分分开，历史缺失信息保留未知。
3. 检验统一档案、六类分账、正式主表准入、固定选样/重试规则及未知/局限分离。历史候选格完整不意味着满足第三周新协议。
4. 复算机制实验的逐事件证据与统计，检查预注册在先、干预是否实际生效、控制与负例是否充分；限定结论，不把诊断或模拟当作真实产品因果效应。
5. 对缺字段、源哈希漂移、污染、题面无效、未冻结规则、重复 ID、研究变体和挑选最佳结果等情况执行拒绝性测试。
6. 出现失败必须保留首次失败收据；修复后另存验收，不能用成功结果覆盖失败记录。

## 本轮收据

- [原判卷回归收据](<checker-regression-receipt.json>)、[结构化结果](<checker-regression.json>)、[标准输出](<checker-regression.stdout.txt>)和[错误输出](<checker-regression.stderr.txt>)：一次 `grading_regression` 工作事件，内部五题自测不是五场产品运行。

- **独立公有副本复核125/125通过**：[五段审查意见](<reviewer/review.md>)、[最终原始收据](<reviewer/final-03.json>)；全新副本、空HOME、禁原HOME/旧tmp/spill与网络，未调用模型。作者38项自测另作为一次子命令重跑，不计38场产品运行。
- [首轮失败](<reviewer/final-01.json>)及[第二轮失败](<reviewer/final-02.json>)均保留；问题为复核器自身的正向探针、合成分母和CLI展示前缀假设，修复后另开新副本，不改被验封条。
- [Lead最终验证和38项自测](<lead-final-test-01.json>)、[交付保护检查](<delivery-check-01.json>)均退出0；1542份受保护历史原件字节未变。交付检查只扫描明显凭据模式，不冒称全面安全审计。
- [前置历史资产指纹](<protected-baseline.json>)及[326条来源实核](<history-source-audit.json>)供公开复核；242条公有源hash一致，84条私有引用不作已公有化声明。
- [Git暂存字节核对与空白例外](<git-staging-review.json>)：188项机制清单在Git暂存区仍逐字节匹配；SSE协议尾部分隔空行及冻结生成Markdown的末尾空行保留，未为通过空白检查裁剪证据，也未修改全局Git配置。

## 复跑

先验已发布物，再重建；从仓库根目录执行，前三条仅需Python标准库，最后一条强隔离复验需要macOS自带sandbox-exec：

```bash
python3 -B '4-打分细则/可信冻结-2026-10-29/freeze.py' verify
python3 -B '4-打分细则/可信冻结-2026-10-29/test_freeze.py'
python3 -B '1-评测方案/机制实验-2026-10-29/analyze.py' --verify
python3 -B '5-评测报告/独立复核-2026-10-29/reviewer/clean_room.py' \
  --root "$PWD" --ready-freeze --ready-mechanism \
  --check-script '5-评测报告/独立复核-2026-10-29/reviewer/independent_checks.py' \
  --label independent-new
```

每次强隔离复验需使用新的label，收据不覆盖。本轮验收后生成的整合报告和导航不冒称包含在较早的独立复制输入中；被验代码、封条和机制证据清单保持原hash。
