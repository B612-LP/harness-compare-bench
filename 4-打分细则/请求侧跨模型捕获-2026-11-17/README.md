# 请求侧跨模型捕获协议（R-A6，2026-11-17，先冻结后运行）

在 [请求侧最小捕获](../DSH请求侧最小捕获-2026-11-16/) 与其预注册协议族（v3）基础上，本环把请求侧捕获第一次扩展到第二个 provider/model：同一 Harness（DSH，同版本）、同一任务工作区、同一提示词，改经官方 api.deepseek.com（模型 id `deepseek-chat`，apiKeyEnv 认证）执行 **两次** 真实运行，全部请求体经本地捕获代理留档。

## 授权与预算

- 用户已于当日窗口内授权测试额度（「随便测试」）；本环计划 2 次真实运行，失败允许同授权重试 1 次；先 mock 干跑（0 真实请求）再真实运行。
- 运行环境只注入 `DEEPSEEK_API_KEY`；不注入智谱 key，避免意外第三方调用。

## 与既有运行的可比性（诚实边界）

- 相同：workspace 文件（TASK.md `68599aec…`、dominoes.py `89f1fede…`）、提示词（`7a7c57c7…`）、DSH 版本、捕获法（本地代理→上游 HTTPS）、观测设置。
- 不同：provider（api.deepseek.com vs open.bigmodel.cn coding 端点）、模型（`deepseek-chat` vs `glm-5.3-flash`）、认证方式（apiKeyEnv vs 同为 apiKeyEnv 但不同家）。**`deepseek-chat` 是官方 API 模型 id，与桌面账号登录路由（`deepseek-flash`，内建 account provider）不是同一模型面**——本环比较的是「同 Harness 跨 provider/模型族」，结论不得表述为同款模型对照。

## 预登记终点（运行前冻结）

| 终点 | 定义 | 结局命名 |
| --- | --- | --- |
| P1（主） | 两次 DS run 首条主任务请求组装稳定性：字节恒等，或差异叶全部可归类（provider 逐请求生成 id 类 / 其他记 UNEXPECTED）；归一 id 后 canonical 比较 | `ds_assembly_stable` / `ds_assembly_divergent` |
| P2 | 每次 DS run 内首条主任务请求是否为后续主任务请求的内容级严格前缀；追加形状与 delta 字节数 | 描述性 |
| P3 | 跨 provider 描述对照（**无恒等预期**）：DS vs GLM（`92220699…`）首请求的 system 提示字节、消息 roles 序列、工具声明数、model 字段、max_tokens/thinking 字段分列 | 描述性 |
| P4 | 标题辅助请求是否走同一 provider；标题输出文本是否回流后续主任务请求（字面检索） | 描述性 |

任何一次运行失败：按预注册同授权重试一次；非恒等按规则记录，不追加运行凑恒等。

## 复算与私档边界

公开包只含 SHA、字节数、形状与布尔值（无请求正文、无完整 id、无密钥）；私有归档（DS run 的请求/响应原件、事件层副本）不在公开仓库。公开重放只核封印与算术，不能认证私档真实性——固定索引对应行载明私档缺口。

## 限制

- 单任务、单 DSH 版本、每模型 n=2；bytes 非 token；响应体不恒等属预期，不在终点内；跨 provider 对照是描述性的，不归因评分。
