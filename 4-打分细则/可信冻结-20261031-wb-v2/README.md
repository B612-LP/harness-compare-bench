# WorkBuddy 判废项唯一替代合同（W-v2）

规则：`freeze-20261031-wb-v2`。本合同承接 [W-v1 首批](<../可信冻结-20261031-wb-v1/README.md>)，仅为首批已判废的 DAB、LCB、cargo 三项提供一次语义 replacement；不更改任何原分、原裁定或旧代合同。首批有效的 bird、exercism 不重跑、不在本代重新准入。

## 预注册、前承与上限

[新计划](<../../1-评测方案/正式批次-2026-10-31-WB-replacement/registration-plan.json>) 的机械队列仍为新 plan 下 first/order1/parent=null，**不意味着无前承**。独立 `predecessors` 闸门绑定完整首批事件包、最终拒绝表、build recipe、output manifest，以及原场裁定证据；原事件必须是首批 first、同 W_gateway/workbuddy/case，终局 invalid/suspect，失效闸门为 false 且最终表有对应拒绝理由。

`invalid_cases`、`predecessors`、本代官方槽位与注册集必须完全一致。每父仅一个子槽、replacement_index=1、max_replacements=1；有效低分、未知终局、非首批父场不能替代。每槽仅一次发射，不自动重试或再替代。所有本代已注册尝试必须完整导入，包括失败、污染和证据不足；不按分择优。

## 题目、提示与归因

[配置](<config.json>) 中完整五题字节快照与 W-v1 相同，truth、checker、输入与分母不变。只运行三项失效槽位。

提示增加 [边界说明](<../../1-评测方案/正式批次-2026-10-31-WB-replacement/prompt-revision.json>)，明确 `/tmp`、`/private/tmp`、`/var/folders` 等目录不在工作区内，临时脚本/测试数据/日志/中间结果应放当前工作区 `.tmp/`；提示头改为产品上下文提供的当前 cwd，避免包含个人绝对路径。三份公开 TASK 是真实发送的原字节，原 instruction 保持完整后缀。计划、配置、锁及每场 prompt-proof 共同绑定实际发送 SHA，不拿脱敏派生 SHA 冒认原文。

**提示头路径中立化与临时边界具体化是跨批协议差异**，不能据此声称单变量因果提升。模型选择仍仅 UI 事实：DeepSeek V4.1-Flash（`deepseek-v4.1-flash`）、low。非官方路由可评价整体产品，但后端实际模型/参数不可证，只限制同模型归因；原 W-v1 精确 backend-only 问题例外不扩大。其他未知、污染、证据、时间、完整分母与准入闸门全部保留。DAB2697 不支持能力归因，不加入 A/B 或混合排名。

## 复核与小产物

[锁文件](<freeze.lock.json>) 使用 contract pins，漂移即失败；哈希封印不是独立可信时间戳或原始证据真实性证明，仍须人工审查实际行为与证据语义。冻结时钟记录于配置。

本代只生成三槽子批档案、六类分账、未知问题与前承引用表，不复制或重生成历史巨档案。计数范围是本替代子批，不是全仓累计。原父 X 分保留在原包及前承引用中，不进入本代正式表；替代无效时不能回退挑父分或取两次最大值。

仓库根目录离线复核（不运行模型、桌面或 checker）：

```bash
python3 -B -m unittest discover -s '4-打分细则/可信冻结-20261031-wb-v2' -p 'test*.py'
python3 -B '4-打分细则/可信冻结-20261031-wb-v2/freeze.py' build
python3 -B '4-打分细则/可信冻结-20261031-wb-v2/freeze.py' verify
# 实际三场证据齐备后，build 和 verify 都须显式 --imports <完整替代事件包公开相对路径>。
```

无 imports 的产物仅代表 pending 空表，不代表替代已运行或通过。最终五格应明确合并 W-v1 有效格与 W-v2 合规替代格，各格保留来源代际；不重写原官方表。测试只使用 SYNTHETIC fixtures，不计产品运行数。
