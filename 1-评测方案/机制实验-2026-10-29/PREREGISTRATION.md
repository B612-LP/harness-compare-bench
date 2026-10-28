# 预注册：原生工具输出保留预算的上下文机制干预

冻结版本 v1，2026-10-29（Asia/Shanghai）。执行器在首个模型调用前生成含本文与原创脚本 SHA-256 的 freeze.json；不得按结果换任务、追加样本或丢弃失败。独立研究实验，不进入正式产品排行榜。既有 token-cause decomposition 仅算术拆分，不作为本实验因果依据；也不重开已完成的 WorkBuddy 网络隔离格。

## 因素与控制

- 唯一实验因素：DSH 原生 `spill-policy.maxInlineTokens`，full=12500，bounded=512（估算 token 预算，不等同服务端 tokenizer）。
- 模型：既有 CLI 路由 deepseek-official / deepseek-flash，reasoningEffort=low。实际响应模型名、usage 与发出的请求必须取证；不可仅凭配置认定调用成功。
- 使用已装 CLI 的内部认证解析，不读取、输出或复制凭据值，不登录/退出；隔离 DSH_HOME/profile/session/storage，禁配置编辑、用户 instructions、memory、skills、浏览器、标题模型、遥测、retry、子 agent。测试仅提供一个原创无网络无文件读取工具 fixture_output，返回固定的实验输入；不是 mock LLM。
- 固定 prompt、system persona、工具 schema、输出生成规则、maxTokens=1024、cwd、最高文件权限/不询问。工具能力被人为约束，故不评价自然 agent 的恢复能力或题库能力。
- 大输出：固定两端证据和中段非目标噪声（约32KB，低于默认12500估算 token/执行器截断线），两端目标应在两臂均保留。小输出负对照：相同两端证据、无噪声，低于512预算。
- 被测模型不见 truth/solution/checker；工具返回的是任务输入中的观测证据。所有判卷在驱动侧后验执行。

## 排序、预算与停止

固定6场，依次 large/full、large/bounded、large/bounded、large/full、small/full、small/bounded。前四场构成两对交叉顺序，后两场为负对照。每场预期2个真实API调用（工具选择→回答）；最多3个请求/场、240秒/场，总最多18请求，累计输入预算150000 tokens（完成一场后检查）；不重试失败。另容许零API配置预检，不将其混入产品实验。

如果认证不可用、CLI挂载失败、请求含意外私有上下文、模型路由不是预定模型、真实API无法取证、模型未使用唯一工具或两臂前置条件不一致，保留原始stdout/stderr/退出码并停止正式因果裁定；不读取凭据，不擅自退到mock。正常停止条件：6场完成或任一安全/配额停止条件触发。若运行超时，终止自己创建的进程组，保留失败。

## 预注册观测与裁定

1. 每场：独立run ID、时间、CLI/Node/OS版本、代码与题面hash、profile/隔离/权限、原始stdout/stderr与退出码；请求仅留实际body与目标host/path，不留任何headers；响应保留SSE与provider usage。发布前对body/输出做路径与凭据模式脱敏扫描。
2. 操纵检查：首调模型可见的system/messages/tools与参数在同规模两臂相同；第二调唯一预期差别是tool_result被原生spill替换（动态tool-call ID与独立session元数据不作为机制）。记录原始工具完整stdout及hash，恢复文件是否存在、是否可读。
3. 主要终点：large两对实际第二调用input usage差值（full−bounded），以及实际body工具结果字节差、spill标记/中段噪声消失。小输出负对照预期不spill且同样tool_result。
4. 次要终点：头尾两项回答精确正确率、output usage、首调usage/请求一致性。允许正确率相同但输入成本不同，不得据n=2推断普遍任务质量或产品优劣，不把计费/缓存变化归咎于保留策略。
5. 成立的最窄机制结论：本隔离CLI实验中，单改原生保留预算确实改变下一次真实模型调用看到的工具结果，并改变实际输入usage。若只观察到字符串长度而无真实usage，则只承认上下文传输效应，不承认token成本因果证据。

## 保留与恢复的边界

spill-policy保留两端+完整输出文件路径；文件由原生spill后端保存。实验只给fixture_output，不给read/bash，固定要求一次工具后直接作答，因此恢复文件对模型并不可读取，这是两臂共同的人为任务约束，而非DSH天然无法恢复。输出长度控制是唯一改变的因素；不做丢中段答案的质量实验。

## 复现

运行同目录 `run_experiment.py --workspace <仓外新目录> --evidence <仓内新证据目录> --credential-store <已配凭据文件路径>`。凭据参数只是交给已装DSH内部服务的引用；驱动不打开该文件。先跑 `--preflight-only` 可检查CLI挂载与隔离、零模型调用。需要本机预装DSH CLI 0.2.0-rc.2/相容版本和已配DeepSeek官方认证；未配置者应安全失败，不能把离线自测当真实API。
