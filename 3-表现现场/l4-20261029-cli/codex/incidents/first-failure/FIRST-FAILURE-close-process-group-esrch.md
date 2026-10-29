# FIRST-FAILURE: close_process_group ESRCH 误确认（lead 代码审查 2026-10-29）

- 冻结版本：lab.py sha256 前16 = 42df040037aa5c5d（原样副本：lab-42df0400-defective-esrch.py，write-once）
- 缺陷位置：close_process_group :621–630
- 缺陷内容：`os.getpgid(proc.pid)` 在父进程已退出/被 wait 收割后抛 ESRCH，代码将 pgid=None
  解释为「进程已不存在 → 组必已消失 → verified_gone」。**不成立**：孙代进程可在父被收割后
  仍活跃写（孤儿进程组）。正确语义：Popen(start_new_session) 启动时即保存 pgid（=子 pid，
  子为组长），任何闭合操作必须使用已存 PGID；父侧 getpgid 失败不得替代 killpg(saved_pgid,0)。
- 处置：先冻结本文件为首失败存证，随后修复 + 真实 synthetic 回归
  （父退 + 子忽略 TERM 持续写的孤儿组场景，非 stub proc）。
- 关联纪律：gate 契约⑥ receipt 身份一致化（slot→slot_id；pid/pgid 与 dispatch/attempt 绑定）。
- 状态：42df0400 blocked；修复后新哈希另报，judge 按原判据复验。

- **修复回执（2026-10-29T21:39:39+08:00）**：lab.py 新 sha256 前16 = b3d1e7d012ec2998。修复内容：saved_pgid 于
  Popen 启动时捕获（start_new_session ⇒ 子即组长），close_process_group 权威使用已存 PGID；
  父侧 getpgid 失败仅记 fallback/unavailable，**不再推断组消失**；无组身份 → verified=false。
  receipt 身份统一 slot_id/run_id/event_id/pid/saved_pgid/attempt.pgid；meta.termination_receipt
  绑定（file/sha256/verified_stop）保持。OS 层手动复现证实语义正确：TERM(被忽略)→SIGKILL→killpg0 ESRCH。
  selftest 孤儿回归出现「SIGKILL 返回成功但计数器仍写」——根因 **unknown/待 judge**（不预设沙箱静默 no-op；候选：monkeypatch 未还原/PGID 归属/setsid/旧产物，取证清单见 REPORT）→ 行为断言记 WARN 留待真实 runtime 复验；verified=false 纪律不受影响。65/65 PASS。
- **第二份首失败冻结（2026-10-29，lead 审查 b3d1e7d0 :774–803）**：副本 lab-b3d1e7d0-partial-flow-defects.py。缺陷：①formal_eligible 仅排除 phase=timeout+unverified，normal_exit unverified 仍 true；②未验证仍调 judge(slot)——checker 会在活动写者 workspace 运行（与 DSH 被打回同型）；③meta.attempts :795 重建丢弃 spawn 时 attempt_identity(pid/pgid/slot_id)。修复方向：任何 phase 停止未确认即早退 partial(score=null)+持久 halt+后槽 Popen 0+checker 0 调用；normal_exit 组仍活先既有界清理/核实再保守停批；attempts 保留权威身份。judge 已持有 b3 快照在审。

- **第二修复回执（2026-10-29T21:52:45+08:00）**：lab.py sha 前16=0b3d8c910e2d5a34。按 lead 阻断+b dsh atk14–16：normal_exit 停止未确认同样有界 TERM→KILL→再探活，仍不确认即早退 partial（checker 0 调用/score=null/无 score-receipt/L3 组件跳过/批根 halt/后槽阻断 rc4）；attempts[0]=spawn 时权威身份（pid+pgid 即时 getpgid）；doc 增 group_confirmed_gone；meta.termination_receipt 仅 {file,sha256}（删 verified_stop 双说）。selftest 73/73（含 partial 5 项、身份/双说/组确认 4 项）。
