# 不可核例固定：r1109 bird 组请求捕获缺席（2026-11-25，预注册）

> 状态：已验收（UNKNOWN_CAPTURE 固定登记）。本页把老师反馈 3 三代表链分账的第三例（不可核例）固定为显式登记：`dsh__bird-ca-schools-15__r1` 事件可重投影、请求捕获缺席。零新增捕获、零发射。

## 1. 研究问题

既有三代表链核验候选（项目本机规则所引三例）中，正例（[事件层↔请求层溯源](<../捕获会话事件层与请求层溯源-2026-11-16/README.md>)）与失败例（[响应侧工具参数源头](<../响应侧工具参数源头-2026-11-17/README.md>)，2026-11-25 非作者复现收口）均有收据；第三例（bird 组缺完整请求捕获的槽）此前仅停留在候选表述。本研究问：能否以「事件重投影支据 + 请求捕获缺席证明」把该槽固定为 UNKNOWN_CAPTURE，使三链分账闭合，且不被误读为失败或分数？

## 2. 固定事实（合同：unknown-capture-contract.json，SHA16 58aba9ba9413262f）

- **PU1 绑定**：槽 `dsh__bird-ca-schools-15__r1` 的 session 原档 zstd SHA-256 与 11-12 钉定 evidence.json 的 identity.sha256 逐字节相等。
- **PU2 事件可重投影**：R1 环复算器复跑 15 槽全行等值（含本槽）——「能重投影事件」支据成立。
- **PU3 请求捕获缺席**：r1109 launch 全树清点（1,526 文件）零 `*.request.bin`/`*.response.bin`/`requests/`/`responses/` 工件，bird 组 3 槽命中 0；r1109 相关 wire 捕获仅存在于两处独立捕获档案（[11-16 页](<../捕获会话事件层与请求层溯源-2026-11-16/README.md>)钉定 dabstep 链 3 主请求；[11-17 页](<../响应侧工具参数源头-2026-11-17/README.md>)钉定深链 t3），均非 bird 组。
- **PU4 分账**：三链 verdicts 固定 {REPRODUCED_ALIGNED, SOURCE_MISSING_PRESERVED, UNKNOWN_CAPTURE}；不可核例不产生分数、失败、成本结论。

## 3. 近错（4/4 拒绝）

1. verdict 枚举：FAIL/SCORED 等分数型结论落入不可核槽 → 拒。
2. 伪造请求：向槽注入伪造 request.bin，其正文不含任何事件投影内容 → 无对齐通道，不因文件存在翻可核 → 拒。
3. 错绑：同组 r2 原档冒充 r1 → SHA 对表拒绝。
4. 重投影篡改：事件行 type 改写 → 逐行比较拒绝。

## 4. 复算与测试

```sh
python3 4-打分细则/不可核例固定-2026-11-25/recompute.py
python3 4-打分细则/不可核例固定-2026-11-25/test_recompute.py
```

`recompute.py` 校验：schema、槽名、SHA hex64 与绑定等值、重投影双支据、缺席计数三零、verdict 枚举与分数开关、三链分账、近错声明。`test_recompute.py` 9 项（1 正常 + 8 注入）全拒。

## 5. 结论边界

UNKNOWN_CAPTURE 是**证据面缺席登记**，不是失败判定，也不证明「当时没有发生请求」——仅证明冻结档案内无可核对的请求侧原件；若未来出现合法来源的 bird 组 wire 捕获，本例应重新进入三链核验协议。伴随文件（trace-incident.json 等）不在本环解读范围。
