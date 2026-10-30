# L5 CLI 评测现场摘要（事后脱敏）

> 本文是事后脱敏整理的摘要，不是历史封印原件；不能证明旧验收时序，也不表示重新验证。修复自检、真实产品运行和中止尝试分别记账，不因自检通过推定正式准入。

## 工具修复与自检

- CLI runner 增加输入文件哈希核对和结构化判卷信息；按检查计数推导 guard 时可能有多个调和集合，固定取索引序首个。该方法只保证计数一致，不证明防篡改或 guard 语义正确。
- 运行准备元数据移出模型可见工作区；DSH 会话捕获按真实目录编码匹配，并记录匹配方式。旧匹配方法在六个 L4 会话名回放中为 0/6，新方法为 6/6；这是历史自检记录，不是新的实测。
- 原记录的零模型自检结果：Codex mock 全链 PASS，DSH 会话回放与脱敏 3/3，专项 11/11。mock 输入核对使用单文件桩，不能代替真实合同输入核对。

## 真实运行与边界

DSH 的 E2 中断、E3 实际运行及得分见 [DSH 现场摘要](<dsh/REPORT.md>)；两槽的原始得分收据分别为 [dab](<dsh/runs/l5-20261030-cli-dsh-dabstep-payments-10-r1/score-receipt.json>)、[cargo](<dsh/runs/l5-20261030-cli-dsh-tb-cargo-plan-r1/score-receipt.json>)。Codex 的独立运行收据为 [dab](<codex/runs/l5-20261030-cli-codex-dabstep-payments-10-r1/score-receipt.json>)、[cargo](<codex/runs/l5-20261030-cli-codex-tb-cargo-plan-r1/score-receipt.json>)；本文不据此补写未经核对的得分或准入结论。

历史记录的完整性检查与污染判断应以各槽原始证据及独立裁定为准；没有核实的状态保持未知。正式比较须另核规则冻结、题面和证据有效性及污染情况，不从本摘要推断。
