# 工具链（CLI 赛道评测执行件镜像）

2026-10-16 两批（glm 批 `r1016-*` / 小米批 `r1016x-*`）实际执行所用工具链的镜像副本。

**本仓自足**：脚本默认以本仓为根运行——用例读 `2-用例/`，适配器与路由配置读本目录，作业目录写 `3-表现现场/`（与已归档现场同结构）。路径可用环境变量覆盖，此前硬编码的旧仓 Windows 路径已移除：

| 变量 | 默认值 | 用途 |
|---|---|---|
| `BENCH` | 本仓根目录 | 仓库根，决定 `TOOLS` |
| `CASES` | `$BENCH/2-用例` | 用例目录（Harbor `-p` 的父目录） |
| `JOBS` | `$BENCH/3-表现现场` | 作业落盘目录（`--jobs-dir`） |

> 旧调研档案仓（早期按 `cases/` + `jobs/` 组织）不是本仓交付物、也不随本仓公开；复跑以上表默认路径为准，不依赖旧仓。

复跑前置：WSL/Linux + `harbor` CLI + Docker，凭据放 `/root/.codex/{zai,xiaomi}.env`（不入库）。

| 文件 | 作用 |
|---|---|
| `dsh_agent.py` | Harbor 自定义 agent 适配器（`-a dsh_agent:Dsh`）：安装 dsh 0.2.0-rc.2（**强制 Node 24**——dsh 的 `import.meta.main` 入口守卫在 Node 22 上静默零输出）、上传模型路由 patch、`dsh headless --json` 执行、事件流 → ATIF v1.7 轨迹转换、会话证据回收 |
| `bare_model.py` | **C 组零脚手架基线**（`-a bare_model:BareModel`）：指令原样进 `/v1/responses`（无系统提示/无工具/无循环），回答原文 `printf` 落盘到 `--ak output_path=`，同一评分器判卷；请求/响应 JSON 全量留证 |
| `cordis.patch.yml` | DSH 模型路由 patch · **glm 批**：zai → `open.bigmodel.cn/api/v1`（openai-responses）+ `glm-5.3-flash` |
| `cordis-xiaomi.patch.yml` | DSH 模型路由 patch · **小米批**：xiaomi → `token-plan-cn.xiaomimimo.com/v1`（openai-responses）+ `mimo-v2.6-flash` |
| `config-xiaomi.toml` | Codex 模型路由 · 小米批（`wire_api="responses"`——小米 Token Plan 端点实测支持 `/v1/responses`） |
| `compose-proxy-overlay-v2.yml` | 容器级代理 overlay v2：国内 API 流量走代理（WSL 直连智谱/小米端点 2026-10-16 均中断），Ubuntu 源仍直连保速度 |
| `run-gates.sh` | oracle-gating 四连跑（两用例 × nop/oracle；闸门为用例级，与模型无关，两批共用） |
| `run-codex.sh` / `run-dsh.sh` | glm 批 A 组跑批（Codex/DSH × glm-5.3-flash） |
| `run-codex-xiaomi.sh` / `run-dsh-xiaomi.sh` | 小米批 A 组跑批（Codex/DSH × mimo-v2.6-flash） |
| `run-bare.sh` | 小米批 C 组跑批（bare-model × 两用例） |

## 关键机制备注

- **认证**：`--ae XIAOMI_API_KEY` / `--ae ZAI_API_KEY` 由 Harbor Trial 注入容器环境；Codex 经 `config.toml` 的 `env_key` 读取，DSH 经 patch 的 `apiKeyEnv` 读取，bare 经 `Authorization: Bearer`（小米端点对 `api-key` 与 `Bearer` 双头均实测 200）。密钥不入库（WSL 侧 `~/.codex/xiaomi.env`/`zai.env`，chmod 600）。
- **权限对齐**：Codex `--dangerously-bypass-approvals-and-sandbox` ≡ DSH `DSH_PERMISSION_MODE=danger-full-access`。
- **模型锁定**：Codex 的 `-m` 直达 CLI；DSH headless **无 `--model` 覆盖**（官方设计如此），模型走配置层 patch，`-m` 仅作轨迹标注。
- **C 组口径**：bare-model 没有任何脚手架——连"把回答写进文件"都是 adapter 机械完成的；模型想调工具只会产出死文本（实测如此，见表现现场）。这正是 A−C 归因的测量对象。
- **成本口径**：LiteLLM 无 GLM/MiMo 定价，`cost_usd` 均为 null，按各自官方费率离线换算（见 `../../4-打分细则/`）。
