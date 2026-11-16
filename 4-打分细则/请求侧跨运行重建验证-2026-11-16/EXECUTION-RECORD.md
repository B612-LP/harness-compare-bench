# EXECUTION-RECORD — 请求侧跨运行重建验证（R-A）

状态：已完成并经独占归档留证；本页描述执行与验证事实，不重复 README 结论。

## 授权与时序（Asia/Shanghai，2026-11-16）

1. 22:24 用户明确解除测试额度限制（逐次授权本次运行）。
2. 22:29 workspace 执行前核对（TASK.md `68599aec…`、dominoes.py `89f1fede…` 与 capture-1 基线一致）→ 同路径重建 no-op，全目录先归档（`pre-r2-workspace-archive/`）。
3. 22:29 建 `capture-r2` profile（clone 自 `capture-r1`；功能配置唯一 diff=本地捕获代理端口 8791→8793；注释自描述；`PROFILE-FUNCTIONALLY-IDENTICAL` diff 验证）。
4. 22:30 mock dry-run（mock 8799 + 代理 8793→http 127.0.0.1:8799，0 真实调用）：exit 0，7 事件，2 请求捕获（`dry-r2-done/`）。
5. 22:31 切换真实上游（代理 8793→https://open.bigmodel.cn:443；`PROXY-START.json`）。
6. 22:32:55–22:33:00 **R-A 唯一新授权真实运行**：exit 0，session `session-436b3d4a-3224-4486-9c00-b313d99aba94`，final `# Capture task r1 — can_chain`（与 run1 相同），3/3 请求 HTTP 200（req 33091/1042/34107 B；resp 13203/1566/1577 B）。
7. 22:33 事件层副本归档（`event-layer/session-436b3d4a…/session.v4.jsonl.zstd` 18331B）。
8. 22:34 主要终点：req1/req2 与 run1 逐字节恒等；req3 不同。比较命令为 shell `shasum -a 256`/`cmp` 一行命令（已 verbatim 记录于私有回执 `R-A-RECEIPT.md`）；req3 键级分类经内联探查后由本包 `verify.py` 冻结重算（该脚本先于其首次执行冻结；首版 `call_[0-9a-f]{26}` 正则与实测 24 位 hex 不符即被测试捕获并修正为 `{24}`，修正发生于任何证据构建之前）。

## 结果（详见 README 与 result.json）

- req1 `92220699…` 两 run 同 → 主要结局①（组装稳定，恒等）。
- req2 `9f2b6b3e…` 两 run 同。
- req3 差异叶恰 4，全部 provider call_id（值 SHA 分列于 evidence）；byte delta 两 run 均 1016；run2 内 req1 为 req3 内容级严格前缀。
- 附件结构（两 run 同）：[assistant, none, 0]、[tool, str, 227]、[tool, str, 203]。

## 验证

- `test_verify.py` 16 反例：真档 SHA 篡改、正文叶差异 UNEXPECTED、叶数 0/5、前缀破坏（同长改写）、summary 非 200、公档篡改（leaf class/baseline/limits/status/pins）、result 形态、真档 evidence 重放（需 `REBUILD_EVIDENCE_PATH`，公开套件默认不依赖私档）、CLI 独占/缺参/公档重放。普通与 `-O` 各 Ran 16 OK（日志私有 `loop5/tests-normal.log`/`tests-O.log`）。
- `verify.py` 构建命令（真档）：`--run1-root <capture-1私档> --run2-root <loop5/capture-r2> --build-evidence evidence.json --output result.json`，exit 0；公开重放 `--evidence evidence.json` 输出与 `result.json` 逐字节相同（cmp 验证）。
- 公开 evidence/result 不含请求正文、消息内容、路径字面量与完整 ID 值（ID 值以 SHA 分列）；`evidence.json` SHA `057c048171e2ae57d50d9717c50a50445588e074bec14fde1a656ccee52fcd03`，`result.json` SHA `0bd2fa8628a411966fc729af7817ccedd7de4ea0f86de3380e85ca2ba6836b18`（当前字节）。
- 本包文件 SHA（执行记录时点）：README `a6206a2a122d2acb825bf7e30142e1b5a01d0ea6a04fc33bce9ea7e9859d3aff`；verify.py `69d80ba52b1a107c609438a2c2fe7eb14ef5fea8750656122e1456335e491f94`；test_verify.py `9e7ce72971f678d28887a8e3eaa41959fd3b248e09bb9e8c88d4dfb876a13d89`。

## 范围与限制

- n=1 run 对；单任务；model glm-5.3-flash；bytes 非 token；恒等性不外推其他任务/模型/provider；响应体为模型输出不在终点内；不认证 provider 服务端内部行为；预注册页（v3）本身不再改写，执行差异全部在本页披露。
- 私档（原文、summary、代理日志、事件层）不在公开仓库；公开复算入口见 README「复算」节。
