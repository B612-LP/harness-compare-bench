# WorkBuddy 桌面版 零打扰自动化驱动

把 WorkBuddy（Electron，`/Applications/WorkBuddy.app`，5.8.3）变成可编排的跑批端：
**新建任务 → 绑工作区 → 设模型/思考档 → 发题面 → 等完成 → 收轨迹**，全程不抢焦点、
不弹窗、不碰剪贴板、不发全局键鼠事件。

驱动文件：`workbuddy_driver.py`（系统 python3 + websocket-client，无其它依赖）。

## 核心思路（为什么零打扰成立）

不走 UI 自动化，而是给 App 带 CDP 远程调试端口启动，在渲染进程里直接调用它
**自己的内部 RPC 桥 `window.wb.invoke(channel, ...)`**。建任务/发题面都是纯 JSON
往返，天然与窗口可见性、焦点、键鼠无关：

```
open -g /Applications/WorkBuddy.app --args --remote-debugging-port=9332
        │ (不激活、不抢焦点)
        ▼
CDP WS (ws://127.0.0.1:9332/devtools/page/<id>, suppress_origin)
        ▼  Runtime.evaluate
window.wb.invoke("wb:conversations:create", {cwd, model, ...})   ← 建任务+绑目录
window.wb.invoke("wb:conversations:sendPrompt", id, blocks)      ← 发题面
        ▼
~/.workbuddy/projects/<slug>/<sessionId>.jsonl                    ← 轨迹落盘
~/.workbuddy/workbuddy.db sessions 表                             ← 状态/id 映射
```

实测全程 `CGWindowListCopyWindowInfo(onScreenOnly)` 中 WorkBuddy 窗口数为 0。

## 端口与启动

- 端口：**9332**（`--remote-debugging-port=9332`，127.0.0.1 only）。
- `ensure_app(port)` 可重入：
  - CDP 已通 → 直接复用；
  - App 在跑但无调试端口 → SIGTERM 仅 WorkBuddy 进程后带端口重启；
  - 未跑 → `open -g <app> --args --remote-debugging-port=<port>`。
- 连接后固定做两件事：`Emulation.setFocusEmulationEnabled{enabled:true}`（防后台节流）、
  轮询等 `window.wb` 桥就绪。

## 关键 RPC 通道（渲染进程 `window.wb.invoke`）

| 通道 | 用途 |
|---|---|
| `wb:conversations:create` | 建会话：`{cwd, title, mode:'craft', model:'deepseek-v4.1-flash', permissionMode:'fullAccess', useSandboxCLI:false, thoughtLevel:'low', welcomeMode:'work'}` → 返回 `info.id`。**会话级禁工具**（2026-10-27 实测）：顶层 `sessionSettings={"workbuddy.claw.runtime":{"disabledTools":[...]}}` **runtime 生效**；顶层 `disabledTools` 通道无效（被 create 处理丢弃，不落库）。生效证据三方口径：DB sessions.session_settings 落库 + daemon.log `toolsCount` 43→43−N + jsonl 中被禁工具 0 成功调用（强行 DeferExecuteTool 调用统一硬报错 "not available"）|
| `wb:conversations.local:list` | 刷新会话路由缓存（**新会话后必调**，见坑 1） |
| `wb:conversations:configSetThoughtLevel` | `(convId, 'low')` 落库思考档 |
| `wb:conversations:ensureRuntime` | 拉起 Agent 运行时（sendPrompt 前置） |
| `wb:conversations:sendPrompt` | `(convId, [{type:'text',text:<题面全文>}], {mode:'craft'})` |
| `wb:workspaceTrust:getWorkspaceTrust / submitDecision` | 目录信任查询/预授权（见下） |

模型名映射：UI `DeepSeek V4.1-Flash` → id `deepseek-v4.1-flash`（内置表，其余按
空格转 `-` 推导）。评测定案默认 `model="DeepSeek V4.1-Flash"`、`thought_level="low"`。

## workspace 授权机制结论（重点）

1. **没有 macOS 级目录授权环节**。App 自身有全盘访问权，会话 `cwd` 可以直接绑到
   任意目录（实测 `~/bench-workspaces/_probe/wb*` 直接成功），**不需要安全书签、
   不需要 TCC、不会弹文件夹权限弹窗**。
2. App 级信任表 `workspace_trust_decisions`（workbuddy.db）存在但对 bench 目录
   **从未触发**（`getWorkspaceTrust` 返回 `decision:null` 也照常跑）。若某天触发
   "信任此目录"类 UI，两条无弹窗出路：
   - RPC：`wb:workspaceTrust:submitDecision(path, 'trusted')`；
   - 直写 DB（App 退出时）：`INSERT INTO workspace_trust_decisions(workspace_key,decision,revision,created_at,updated_at) VALUES('<path>','trusted',1,<ms>,<ms>)`。
3. **原生 NSOpenPanel 只在 UI 路径出现**（composer 的「选择工作空间/新建工作空间/
   打开本地文件夹」）。驱动全程不点这些入口，永远走 `conversations:create` 的
   `cwd` 参数，所以原生选择器一次都不会出现。
4. 一次授权永久复用的问题在此架构下不存在：每个 case 一个新会话、新 cwd，零弹窗。

## 流程时序（new_task 内部）

```
local:list(预热缓存) → conversations:create{cwd,...} → local:list(让路由看见新会话)
→ configSetThoughtLevel(id,'low') → ensureRuntime(id) → sendPrompt(id,[{type:'text',text}])
→ 等 <slug>/<id>.jsonl 出现（≤90s）→ 返回 {"id","started_at",...}
```

## 完成判定（wait_completion 双保险）

- **主信号**：workbuddy.db `sessions.status` 进入终态（`completed/failed/error/...`）。
- **副信号**：`~/.workbuddy/projects/<workspace 路径 / 换成 ->/<id>.jsonl` 尺寸连续
  20s 不变 + 末事件为 `message`。DB 行状态滞后时兜底。
- evidence 里带回 DB 行（id/cwd/status/model/thought_level/时间戳）+ jsonl
  （路径/字节/行数/末事件），供编排器留档。

sessionId ↔ 任务映射：`sessions.id` 即返回的 task_id；`cwd` 列即工作区目录，
无需额外对账。

## collect 产物

`collect(task_id, dest_dir)` 复制/生成：
- `<sessionId>.jsonl`（Codex 内核事件流全量）+ `<sessionId>.file-rollback.ndjson`（若有）
- `session-row.json`（DB 行导出）、`collect-meta.json`

## 坑（全部踩过并已固化在代码里）

1. **本机 harness 环境带 `ELECTRON_RUN_AS_NODE=1`** → Electron 二进制以纯 Node 起，
   秒退、`bad option` 报错，`open` 也会继承。启动前必须从子进程 env 里剔除
   （`_clean_env()`）。
2. **`open -a WorkBuddy` 在这台机器静默失败**（rc=0 但不启动）。必须用显式路径
   `open -g /Applications/WorkBuddy.app`。
3. **Chrome 138 WS Origin 校验**：`websocket-client` 连接要 `suppress_origin=True`，
   否则 403。
4. **新会话后不调 `wb:conversations.local:list` 就 `ensureRuntime`/`sendPrompt`**
   → `[ConversationPool] conversation not found`。路由缓存问题，list 一次即好。
5. **RPC 参数传字符串时绝不能带外层引号**：Python 侧 `%r`+`json.dumps` 双重编码
   会把 `"id"`（含引号）送进 daemon，get 能容错但 pool 查找必挂。驱动里统一
   `json.dumps(a)` 拼进 JS 字面量。
6. **UI 的 Slate composer 无法程序化输入**（execCommand/Input.insertText/合成
   beforeinput 全被忽略，且窗口隐藏时 CDP 输入管线丢弃按键）——所以整个方案
   绕开 composer 走 RPC，这也是它能零打扰的根本原因。
7. `wb:conversations:get`（不带 `.local`）会优先路由到云端；本地会话一律用
   `wb:conversations.local:list` / 池接口。
8. 思考档位必须 `configSetThoughtLevel(convId,'low')` 显式落库；仅靠 create 参数
   `thoughtLevel` 不会写 DB 列。
9. **禁工具≠禁网**（r20261027 正式场血泪）：disabledTools 只过滤基础工具表
   （buildDesiredConfig 只动 mode 工具清单，插件/MCP 工具不过滤）；WebSearch/WebFetch
   禁掉后 agent 会改用 **Bash curl 直连**抓题解（L79-89 实录，见
   runs/r20261027-workbuddy-lcb-clean2/run_summary.md）。会话禁工具只封「工具名」，
   不构成网络隔离，不能据此宣称 clean。

## 接口用法

```python
import sys; sys.path.insert(0, "/Users/b612-lp/bench-automation/drivers/workbuddy")
from workbuddy_driver import ensure_app, new_task, wait_completion, collect

ensure_app(9332)                                   # App+CDP 就绪（可重入）
t = new_task(                                      # 建任务+发题面
    workspace_dir="/Users/b612-lp/bench-workspaces/<batch>/workbuddy/<case>",
    prompt_text=open("TASK.md", encoding="utf-8").read(),   # 上千字+换行，零丢失
    model="DeepSeek V4.1-Flash")                   # → {"id","started_at",...}
r = wait_completion(t["id"], timeout_s=1800)       # → {"status":"completed","evidence":{...}}
c = collect(t["id"], dest_dir="<证据目录>")         # → {"files":[...]}
```

CLI 自测：`python3 workbuddy_driver.py probe --workspace ~/bench-workspaces/_probe/wb`。

## 已验证（2026-10-25 实测）

- 冷启动（App 未跑）与热路径（已跑）均可拉起带 9332 的实例；
- 4 个探针会话（_probe/wb、wb2、wb3、wb4）：全部 completed，answer.txt/echo.txt
  内容逐字节正确；**2611 字含换行/中文标点/emoji/制表符/连续空格的题面经
  Agent 回写 diff 完全一致（零丢失）**；thought_level=low 落库；collect 3~4 个文件；
- 全程 on-screen WorkBuddy 窗口数 0（零打扰）。

## 限制与注意

- 仅适配 WorkBuddy 5.8.3（内部 RPC 通道名是逆向所得，App 大版本更新后需用
  daemon.log 的 MethodCh 目录重新核对）。
- `ensure_app` 重启 App 时会 SIGTERM 全部 WorkBuddy 进程（含后台 daemon）；只影响
  WorkBuddy 自身，不影响其它 App。若用户正手工用 WorkBuddy 聊天请勿重启。
- 不会主动删除探针/历史会话；`_probe` 会话会留在 WorkBuddy 侧栏（无功能影响）。
- wait_completion 的"jsonl 稳定"兜底默认 20s；Agent 长思考（无工具调用）时
  jsonl 可能阶段性不涨，此时依赖 DB status 主信号。
- 驱动不读/不记任何 token；RPC 均在本机 loopback 内完成。
