# 上下文机制实验入口

- [五段结论](<RESULTS.md>)：6次真实agent运行、12次官方API；单因素原生工具输出保留预算12500 vs512。首场取证降级、随机thinking差异、小输出负对照均不隐去。
- [历史预注册](<PREREGISTRATION.md>)与[修正v2](<AMENDMENT-v2.md>)、[修正v3](<AMENDMENT-v3.md>)、[只修取证v4](<AMENDMENT-v4.md>)。原始[runner v1](<run_experiment.py>)和[fixture v1](<fixture-plugin.mjs>)保留作失败史料，不是推荐可用入口；v4是带carry-in的剩余五场续跑，也不能拿来fresh六场。
- **在线全新复现**：[后验干净六场入口](<run_reproduction.py>)，复用已实测的[逐chunk observer](<capture-preload-v4.mjs>)和[确定性fixture](<fixture-plugin-v2.mjs>)。未为验证该入口再花API；新运行会在新目录先冻结，再发固定六场。使用已有CLI内部认证，不读取凭据值。
- **离线完整重算**：[分析器](<analyze.py>)自动识别本研究v3+v4布局或全新六场根目录布局；`--verify`不改原分析，`--output`只创建新文件。缺场、额外请求、错model、非200、源码hash不匹配均非0拒绝。[正例/负例及fresh布局测试器](<validate_offline.py>)零API，测试记录见[最终6项测试收据](<../../3-表现现场/r20261029-mechanism/offline-verification-v2.json>)。fresh布局测试仅搬排原六场做离线适配，不是新六次在线实验。
- [公有证据入口](<../../3-表现现场/r20261029-mechanism/README.md>)、[六场机器可读分析](<../../3-表现现场/r20261029-mechanism/analysis.json>)、[分账导入事件](<../../3-表现现场/r20261029-mechanism/experiment-events.json>)。

```bash
# 零API历史证据完整复核
python3 '1-评测方案/机制实验-2026-10-29/analyze.py' --verify
# 全新API复现（需要预装dsh与既有认证；不重用已有现场目录）
python3 '1-评测方案/机制实验-2026-10-29/run_reproduction.py' \
 --workspace "$HOME/bench-workspaces/r20261029-mechanism-new" \
 --evidence '3-表现现场/r20261029-mechanism-new' \
 --credential-store "$HOME/.dsh/.credentials.yaml"
# 分析新布局；输出临时新文件，不覆盖原收据
python3 '1-评测方案/机制实验-2026-10-29/analyze.py' \
 --evidence '3-表现现场/r20261029-mechanism-new' \
 --output /tmp/mechanism-new-analysis.json
```

不包含私有自动化实现。实验只有fixture工具、不让模型读truth/solution；恢复文件存在≠模型可读恢复能力。研究场不进入正式榜单，不修改CHANGELOG/旧账/旧题库，不提交git。
