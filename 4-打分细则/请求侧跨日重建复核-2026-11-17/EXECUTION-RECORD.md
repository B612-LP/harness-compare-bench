# 执行记录：请求侧跨日重建复核（环9 / R-A5）

## 时间线（2026-11-17，Asia/Shanghai）

- 00:40 前：环9立项（私有 loop9/DIRECTION.md），终点 P1–P4 与结局命名（cross_day_stable / UNSTABLE）预先写入；作者已知 r1–r5 结果（事后维度扩展，见公开 README 披露）。
- 00:40:53–00:40:59：r6 真实运行。参数与五 run 完全一致：workspace `capture-r1`（TASK.md `68599aec…`、dominoes.py `89f1fede…`，运行前后核对一致）、提示词 214B（`loop5/prompt-r2.txt`，SHA `7a7c57c7…`）、模型 glm-5.3-flash；唯一差异 = 新建 profile `capture-r6`（clone 自 capture-r1，仅 baseURL 端口 8791→8797）。干跑 1 次（mock 8799，0 真实请求）通过。
- 捕获：3/3 上游 200（req1 33091B→13203B；req2 1042B→1570B；req3 34107B→1768B）。私档 `loop9/capture-r6/`；事件层副本 `loop9/event-layer-r6/session.v4.jsonl.zstd`（SHA `6a6644a0…`）。final 响应侧输出与旧 run 一致（`# Capture task r1 — can_chain`，不入终点）。
- 00:44：跨日终点分析（`loop9/r6-analysis.json`，SHA `3820fdb5…`）：req1/req2 与 r1–r5 逐字节相等（5/5）；req3 与各旧 run 恰 4 差异叶全 call_id、归一恒等 5/5；prefix/appended/delta 1016 同旧。**结局 cross_day_stable**。
- 00:45–00:48：公开包六件实现（verify.py 两轮修正：①pairs 计算路径真正计算 diff 值与 call_id 判定（不复制常量）；②日期常量 PRIOR_DATE/R6_DATE 提取；③`__main__` 包装 ValueError/OSError→`input or output failure` exit 2）。测试 18 用例普通/-O 全绿（真档重放分支在 evidence.json 安装后激活）。

## 数据与预算

- 窗口内真实运行累计 10 次（r1–r6 + t2×2 + t3×2），全部在用户授权范围内；本环新增 1 次（r6）+1 次 mock 干跑（0 真实请求）。
- proxy 日志含客户端断连 `ConnectionResetError` 栈迹（良性噪音），留档 `loop9/capture-r6/proxy.log`。

## 已知限制

- 公开重放只核封印与算术，不认证私档真实性；bytes 非 token；单任务单模型 n=6；不外推模型行为确定性（响应体不恒等属预期）。
- 事后维度扩展（作者已见五 run 结果），非盲前预注册；比较规则与协议 v3 相同。
